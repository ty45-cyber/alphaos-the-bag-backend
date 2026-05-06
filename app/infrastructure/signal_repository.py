import logging
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.signal_model import SignalModel
from app.domain.signal import Signal, SignalType, SignalSource

logger = logging.getLogger(__name__)


class SignalRepository:
    """
    Data access layer for Signal persistence and retrieval.
    All queries return domain objects, not ORM models.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, signal: Signal) -> Signal:
        model = SignalModel(
            id=str(signal.id),
            creator_id=str(signal.creator_id),
            signal_type=signal.signal_type.value,
            strength=float(signal.strength),
            source=signal.source.value,
            raw_metadata=signal.raw_metadata,
            computed_at=signal.computed_at,
        )
        self._session.add(model)
        await self._session.flush()
        logger.debug("Persisted signal %s for creator %s", signal.id, signal.creator_id)
        return signal

    async def save_batch(self, signals: list[Signal]) -> list[Signal]:
        """Bulk insert signals for efficiency during ingestion runs."""
        models = [
            SignalModel(
                id=str(s.id),
                creator_id=str(s.creator_id),
                signal_type=s.signal_type.value,
                strength=float(s.strength),
                source=s.source.value,
                raw_metadata=s.raw_metadata,
                computed_at=s.computed_at,
            )
            for s in signals
        ]
        self._session.add_all(models)
        await self._session.flush()
        logger.info("Bulk persisted %d signals", len(models))
        return signals

    async def fetch_latest_for_creator(
        self,
        creator_id: UUID,
        limit: int = 20,
    ) -> list[Signal]:
        stmt = (
            select(SignalModel)
            .where(SignalModel.creator_id == str(creator_id))
            .order_by(desc(SignalModel.computed_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def fetch_actionable_signals(
        self,
        min_strength: float = 65.0,
        since_hours: int = 24,
    ) -> list[Signal]:
        """Fetch all actionable signals from the last N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        stmt = (
            select(SignalModel)
            .where(
                and_(
                    SignalModel.strength >= min_strength,
                    SignalModel.computed_at >= cutoff,
                )
            )
            .order_by(desc(SignalModel.strength))
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def fetch_by_type(
        self,
        signal_type: SignalType,
        limit: int = 50,
    ) -> list[Signal]:
        stmt = (
            select(SignalModel)
            .where(SignalModel.signal_type == signal_type.value)
            .order_by(desc(SignalModel.computed_at))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    def _to_domain(self, model: SignalModel) -> Signal:
        return Signal(
            id=UUID(model.id),
            creator_id=UUID(model.creator_id),
            signal_type=SignalType(model.signal_type),
            strength=Decimal(str(model.strength)),
            source=SignalSource(model.source),
            raw_metadata=model.raw_metadata,
            computed_at=model.computed_at,
        )