import logging
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.creator_model import CreatorModel
from app.domain.creator import Creator, NarrativeScore

logger = logging.getLogger(__name__)


class CreatorRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_by_bags_id(self, bags_id: str) -> Creator | None:
        stmt = select(CreatorModel).where(CreatorModel.bags_id == bags_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def fetch_by_id(self, creator_id: UUID) -> Creator | None:
        stmt = select(CreatorModel).where(CreatorModel.id == str(creator_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def fetch_all_active(self, limit: int = 100) -> list[Creator]:
        """Fetch creators ordered by composite narrative score."""
        stmt = (
            select(CreatorModel)
            .order_by(desc(CreatorModel.narrative_score))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def upsert_from_bags(self, bags_data: dict) -> Creator:
        """
        Upsert a creator record from raw Bags API response.
        Creates if new, updates market data if existing.
        """
        bags_id = bags_data["id"]
        stmt = select(CreatorModel).where(CreatorModel.bags_id == bags_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            model = CreatorModel(
                bags_id=bags_id,
                wallet_address=bags_data.get("wallet_address", ""),
                display_name=bags_data.get("display_name", bags_id),
                token_mint=bags_data.get("token_mint", ""),
            )
            self._session.add(model)
            logger.info("Created new creator record for bags_id=%s", bags_id)
        else:
            model.market_cap_usd = bags_data.get("market_cap_usd")
            model.volume_24h_usd = bags_data.get("volume_24h_usd")
            model.holder_count = bags_data.get("holder_count", model.holder_count)
            logger.debug("Updated market data for bags_id=%s", bags_id)

        await self._session.flush()
        return self._to_domain(model)

    async def update_scores(
        self,
        creator_id: UUID,
        narrative: Decimal,
        velocity: Decimal,
        whale_accumulation: Decimal,
        social_momentum: Decimal,
    ) -> None:
        from datetime import datetime
        stmt = select(CreatorModel).where(CreatorModel.id == str(creator_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            logger.warning("update_scores: creator %s not found", creator_id)
            return
        model.narrative_score = float(narrative)
        model.velocity_score = float(velocity)
        model.whale_accumulation_score = float(whale_accumulation)
        model.social_momentum_score = float(social_momentum)
        model.last_signal_computed_at = datetime.utcnow()
        await self._session.flush()

    def _to_domain(self, model: CreatorModel) -> Creator:
        from datetime import datetime
        composite = Decimal(str(model.narrative_score or 0))
        return Creator(
            id=UUID(model.id),
            bags_id=model.bags_id,
            wallet_address=model.wallet_address,
            display_name=model.display_name,
            token_mint=model.token_mint,
            narrative_score=NarrativeScore(
                velocity=Decimal(str(model.velocity_score or 0)),
                whale_accumulation=Decimal(str(model.whale_accumulation_score or 0)),
                social_momentum=Decimal(str(model.social_momentum_score or 0)),
                composite=composite,
            ),
            market_cap_usd=Decimal(str(model.market_cap_usd)) if model.market_cap_usd else None,
            volume_24h_usd=Decimal(str(model.volume_24h_usd)) if model.volume_24h_usd else None,
            holder_count=model.holder_count,
            last_signal_computed_at=model.last_signal_computed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )