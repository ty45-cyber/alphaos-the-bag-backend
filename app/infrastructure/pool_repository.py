import logging
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.pool_model import AlphaPoolModel, PoolStakeModel
from app.domain.alpha_pool import AlphaPool, PoolStake, PoolStrategy

logger = logging.getLogger(__name__)


class PoolRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_active_pools(self) -> list[AlphaPool]:
        stmt = (
            select(AlphaPoolModel)
            .options(selectinload(AlphaPoolModel.stakes))
            .where(AlphaPoolModel.is_active.is_(True))
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def fetch_by_id(self, pool_id: UUID) -> AlphaPool | None:
        stmt = (
            select(AlphaPoolModel)
            .options(selectinload(AlphaPoolModel.stakes))
            .where(AlphaPoolModel.id == str(pool_id))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def add_stake(
        self,
        pool_id: UUID,
        user_id: UUID,
        amount_usd: Decimal,
    ) -> PoolStake:
        stmt = (
            select(AlphaPoolModel)
            .options(selectinload(AlphaPoolModel.stakes))
            .where(AlphaPoolModel.id == str(pool_id))
        )
        result = await self._session.execute(stmt)
        pool_model = result.scalar_one_or_none()

        if pool_model is None:
            raise ValueError(f"Pool {pool_id} not found")
        if not pool_model.is_active:
            raise ValueError(f"Pool {pool_id} is not accepting new stakes")

        existing_stmt = select(PoolStakeModel).where(
            PoolStakeModel.pool_id == str(pool_id),
            PoolStakeModel.user_id == str(user_id),
            PoolStakeModel.unstaked_at.is_(None),
        )
        existing_result = await self._session.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            raise ValueError(f"User {user_id} already has an active stake in pool {pool_id}")

        stake_model = PoolStakeModel(
            id=str(uuid4()),
            pool_id=str(pool_id),
            user_id=str(user_id),
            staked_amount_usd=float(amount_usd),
        )
        self._session.add(stake_model)
        pool_model.total_staked_usd = float(
            Decimal(str(pool_model.total_staked_usd)) + amount_usd
        )
        await self._session.flush()

        await self._recompute_shares(pool_id)
        logger.info("Stake added: user=%s pool=%s amount=%s", user_id, pool_id, amount_usd)

        return PoolStake(
            id=UUID(stake_model.id),
            pool_id=pool_id,
            user_id=user_id,
            staked_amount_usd=amount_usd,
            share_pct=None,
            staked_at=stake_model.staked_at,
            unstaked_at=None,
        )

    async def remove_stake(self, pool_id: UUID, user_id: UUID) -> None:
        stmt = select(PoolStakeModel).where(
            PoolStakeModel.pool_id == str(pool_id),
            PoolStakeModel.user_id == str(user_id),
            PoolStakeModel.unstaked_at.is_(None),
        )
        result = await self._session.execute(stmt)
        stake = result.scalar_one_or_none()

        if stake is None:
            raise ValueError(f"No active stake found for user {user_id} in pool {pool_id}")

        pool_stmt = select(AlphaPoolModel).where(AlphaPoolModel.id == str(pool_id))
        pool_result = await self._session.execute(pool_stmt)
        pool_model = pool_result.scalar_one_or_none()

        if pool_model:
            pool_model.total_staked_usd = max(
                0.0,
                float(Decimal(str(pool_model.total_staked_usd)) - Decimal(str(stake.staked_amount_usd)))
            )

        stake.unstaked_at = datetime.utcnow()
        await self._session.flush()
        await self._recompute_shares(pool_id)
        logger.info("Stake removed: user=%s pool=%s", user_id, pool_id)

    async def _recompute_shares(self, pool_id: UUID) -> None:
        """Recalculates share percentages for all active stakers after any stake change."""
        pool_stmt = (
            select(AlphaPoolModel)
            .options(selectinload(AlphaPoolModel.stakes))
            .where(AlphaPoolModel.id == str(pool_id))
        )
        result = await self._session.execute(pool_stmt)
        pool = result.scalar_one_or_none()
        if not pool or pool.total_staked_usd == 0:
            return

        total = Decimal(str(pool.total_staked_usd))
        for stake in pool.stakes:
            if stake.unstaked_at is None:
                stake.share_pct = float(
                    (Decimal(str(stake.staked_amount_usd)) / total) * Decimal("100")
                )
        await self._session.flush()

    def _to_domain(self, model: AlphaPoolModel) -> AlphaPool:
        stakes = [
            PoolStake(
                id=UUID(s.id),
                pool_id=UUID(s.pool_id),
                user_id=UUID(s.user_id),
                staked_amount_usd=Decimal(str(s.staked_amount_usd)),
                share_pct=Decimal(str(s.share_pct)) if s.share_pct else None,
                staked_at=s.staked_at,
                unstaked_at=s.unstaked_at,
            )
            for s in (model.stakes or [])
        ]
        return AlphaPool(
            id=UUID(model.id),
            pool_name=model.pool_name,
            strategy_type=PoolStrategy(model.strategy_type),
            total_staked_usd=Decimal(str(model.total_staked_usd)),
            apy_7d=Decimal(str(model.apy_7d)) if model.apy_7d else None,
            apy_30d=Decimal(str(model.apy_30d)) if model.apy_30d else None,
            performance_fee_pct=Decimal(str(model.performance_fee_pct)),
            is_active=model.is_active,
            stakes=stakes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )