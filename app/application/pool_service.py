import logging
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.pool_repository import PoolRepository
from app.domain.alpha_pool import AlphaPool, PoolStake

logger = logging.getLogger(__name__)

MIN_STAKE_USD = Decimal("10.00")
MAX_STAKE_USD = Decimal("1000000.00")


class PoolService:
    """
    Manages AlphaPool staking lifecycle: listing pools, staking,
    unstaking, and share computation.
    """

    def __init__(self, pool_repo: PoolRepository) -> None:
        self._pool_repo = pool_repo

    async def list_active_pools(self) -> list[AlphaPool]:
        return await self._pool_repo.fetch_active_pools()

    async def fetch_pool(self, pool_id: UUID) -> AlphaPool | None:
        return await self._pool_repo.fetch_by_id(pool_id)

    async def stake(
        self,
        pool_id: UUID,
        user_id: UUID,
        amount_usd: Decimal,
    ) -> PoolStake:
        if amount_usd < MIN_STAKE_USD:
            raise ValueError(
                f"Minimum stake is ${MIN_STAKE_USD}. Received ${amount_usd}."
            )
        if amount_usd > MAX_STAKE_USD:
            raise ValueError(
                f"Maximum stake is ${MAX_STAKE_USD}. Received ${amount_usd}."
            )

        pool = await self._pool_repo.fetch_by_id(pool_id)
        if pool is None:
            raise ValueError(f"Pool {pool_id} does not exist")
        if not pool.is_active:
            raise ValueError(f"Pool {pool_id} is closed to new stakes")

        stake = await self._pool_repo.add_stake(pool_id, user_id, amount_usd)
        logger.info("User %s staked $%s in pool %s", user_id, amount_usd, pool_id)
        return stake

    async def unstake(self, pool_id: UUID, user_id: UUID) -> None:
        pool = await self._pool_repo.fetch_by_id(pool_id)
        if pool is None:
            raise ValueError(f"Pool {pool_id} does not exist")

        await self._pool_repo.remove_stake(pool_id, user_id)
        logger.info("User %s unstaked from pool %s", user_id, pool_id)

    async def get_user_share(
        self, pool_id: UUID, user_id: UUID
    ) -> Decimal | None:
        pool = await self._pool_repo.fetch_by_id(pool_id)
        if pool is None:
            return None
        return pool.user_share_pct(user_id)