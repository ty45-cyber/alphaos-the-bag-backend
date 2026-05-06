import logging
from datetime import datetime
from decimal import Decimal
from uuid import uuid4, UUID
from app.infrastructure.signal_repository import SignalRepository
from app.infrastructure.creator_repository import CreatorRepository
from app.infrastructure.bags_client import BagsClient
from app.infrastructure.redis_client import (
    publish_signal,
    cache_set,
    cache_get,
    SIGNAL_CHANNEL,
    WHALE_ALERT_CHANNEL,
    BREAKOUT_CHANNEL,
)
from app.domain.signal import Signal, SignalType, SignalSource
from app.domain.creator import Creator

logger = logging.getLogger(__name__)

WHALE_WALLET_THRESHOLD_USD = Decimal("50000")
VELOCITY_SURGE_MULTIPLIER = Decimal("2.5")
NARRATIVE_SPIKE_ENGAGEMENT_THRESHOLD = 500


class SignalService:
    """
    Orchestrates signal computation, persistence, and real-time publishing.
    Computes velocity, whale accumulation, and social momentum signals
    from Bags API data and on-chain sources.
    """

    def __init__(
        self,
        signal_repo: SignalRepository,
        creator_repo: CreatorRepository,
        bags_client: BagsClient,
    ) -> None:
        self._signal_repo = signal_repo
        self._creator_repo = creator_repo
        self._bags_client = bags_client

    async def ingest_and_compute_signals(self, bags_id: str) -> list[Signal]:
        """
        Full signal ingestion pipeline for a single creator:
        1. Fetch fresh data from Bags API
        2. Upsert creator record
        3. Compute all signal types
        4. Persist signals
        5. Publish actionable signals to Redis
        """
        bags_data = await self._bags_client.fetch_creator(bags_id)
        creator = await self._creator_repo.upsert_from_bags(bags_data)

        holders_data = await self._bags_client.fetch_creator_holders(creator.token_mint)

        signals: list[Signal] = []
        signals.extend(self._compute_whale_signals(creator, holders_data))
        signals.extend(self._compute_velocity_signal(creator, bags_data))
        signals.extend(self._compute_social_signal(creator, bags_data))

        if signals:
            await self._signal_repo.save_batch(signals)
            await self._update_creator_scores(creator, signals)
            await self._publish_actionable_signals(creator, signals)

        logger.info(
            "Ingested %d signals for creator %s", len(signals), creator.display_name
        )
        return signals

    async def fetch_live_signals(
        self,
        min_strength: float = 65.0,
        since_hours: int = 24,
    ) -> list[Signal]:
        cache_key = f"signals:live:{min_strength}:{since_hours}"
        cached = await cache_get(cache_key)
        if cached:
            logger.debug("Signal cache hit: %s", cache_key)
            return cached

        signals = await self._signal_repo.fetch_actionable_signals(
            min_strength=min_strength,
            since_hours=since_hours,
        )
        await cache_set(cache_key, [self._signal_to_dict(s) for s in signals], ttl_seconds=60)
        return signals

    async def fetch_signals_for_creator(
        self, creator_id: UUID, limit: int = 20
    ) -> list[Signal]:
        return await self._signal_repo.fetch_latest_for_creator(creator_id, limit)

    def _compute_whale_signals(
        self, creator: Creator, holders: list[dict]
    ) -> list[Signal]:
        """
        Detects whale accumulation by identifying wallets holding
        positions worth more than the threshold in USD terms.
        """
        signals = []
        if not creator.market_cap_usd or creator.holder_count == 0:
            return signals

        price_per_token = creator.market_cap_usd / Decimal(max(creator.holder_count, 1))
        whale_wallets = [
            h for h in holders
            if Decimal(str(h.get("balance", 0))) * price_per_token
            >= WHALE_WALLET_THRESHOLD_USD
        ]

        if not whale_wallets:
            return signals

        whale_ratio = Decimal(len(whale_wallets)) / Decimal(len(holders))
        strength = min(whale_ratio * Decimal("200"), Decimal("100"))

        signals.append(Signal(
            id=uuid4(),
            creator_id=creator.id,
            signal_type=SignalType.WHALE_BUY,
            strength=strength,
            source=SignalSource.ON_CHAIN,
            raw_metadata={
                "whale_count": len(whale_wallets),
                "total_holders": len(holders),
                "whale_ratio": float(whale_ratio),
            },
            computed_at=datetime.utcnow(),
        ))
        return signals

    def _compute_velocity_signal(
        self, creator: Creator, bags_data: dict
    ) -> list[Signal]:
        """
        Velocity surge: 24h volume is N× the 7d average daily volume.
        Indicates abnormal momentum increase.
        """
        volume_24h = Decimal(str(bags_data.get("volume_24h_usd", 0)))
        volume_7d = Decimal(str(bags_data.get("volume_7d_usd", 0)))

        if volume_7d == 0:
            return []

        daily_avg_7d = volume_7d / Decimal("7")
        if daily_avg_7d == 0:
            return []

        multiplier = volume_24h / daily_avg_7d
        if multiplier < VELOCITY_SURGE_MULTIPLIER:
            return []

        strength = min((multiplier / Decimal("5")) * Decimal("100"), Decimal("100"))
        return [Signal(
            id=uuid4(),
            creator_id=creator.id,
            signal_type=SignalType.VELOCITY_SURGE,
            strength=strength,
            source=SignalSource.BAGS_API,
            raw_metadata={
                "volume_24h": float(volume_24h),
                "daily_avg_7d": float(daily_avg_7d),
                "multiplier": float(multiplier),
            },
            computed_at=datetime.utcnow(),
        )]

    def _compute_social_signal(
        self, creator: Creator, bags_data: dict
    ) -> list[Signal]:
        """
        Social breakout: engagement velocity above threshold
        derived from Bags social data fields.
        """
        engagement_24h = bags_data.get("social_engagement_24h", 0)
        if engagement_24h < NARRATIVE_SPIKE_ENGAGEMENT_THRESHOLD:
            return []

        strength = min(
            Decimal(str(engagement_24h)) / Decimal("5000") * Decimal("100"),
            Decimal("100")
        )
        return [Signal(
            id=uuid4(),
            creator_id=creator.id,
            signal_type=SignalType.SOCIAL_BREAKOUT,
            strength=strength,
            source=SignalSource.SOCIAL,
            raw_metadata={"engagement_24h": engagement_24h},
            computed_at=datetime.utcnow(),
        )]

    async def _update_creator_scores(
        self, creator: Creator, signals: list[Signal]
    ) -> None:
        """Recompute and persist creator score from freshly computed signals."""
        whale_strength = max(
            (s.strength for s in signals if s.signal_type == SignalType.WHALE_BUY),
            default=Decimal("0"),
        )
        velocity_strength = max(
            (s.strength for s in signals if s.signal_type == SignalType.VELOCITY_SURGE),
            default=Decimal("0"),
        )
        social_strength = max(
            (s.strength for s in signals if s.signal_type == SignalType.SOCIAL_BREAKOUT),
            default=Decimal("0"),
        )
        composite = (
            whale_strength * Decimal("0.4")
            + velocity_strength * Decimal("0.35")
            + social_strength * Decimal("0.25")
        )
        await self._creator_repo.update_scores(
            creator_id=creator.id,
            narrative=composite,
            velocity=velocity_strength,
            whale_accumulation=whale_strength,
            social_momentum=social_strength,
        )

    async def _publish_actionable_signals(
        self, creator: Creator, signals: list[Signal]
    ) -> None:
        for signal in signals:
            if not signal.is_actionable():
                continue
            payload = {
                **self._signal_to_dict(signal),
                "creator_name": creator.display_name,
                "creator_bags_id": creator.bags_id,
            }
            await publish_signal(SIGNAL_CHANNEL, payload)

            if signal.signal_type == SignalType.WHALE_BUY:
                await publish_signal(WHALE_ALERT_CHANNEL, payload)
            elif signal.signal_type in (
                SignalType.VELOCITY_SURGE, SignalType.SOCIAL_BREAKOUT
            ) and signal.strength >= Decimal("75"):
                await publish_signal(BREAKOUT_CHANNEL, payload)

    @staticmethod
    def _signal_to_dict(signal: Signal) -> dict:
        return {
            "id": str(signal.id),
            "creator_id": str(signal.creator_id),
            "signal_type": signal.signal_type.value,
            "strength": float(signal.strength),
            "urgency": signal.urgency_label(),
            "source": signal.source.value,
            "computed_at": signal.computed_at.isoformat(),
            "raw_metadata": signal.raw_metadata,
        }