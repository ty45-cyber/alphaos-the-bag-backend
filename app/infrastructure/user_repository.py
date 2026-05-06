import logging
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user_model import UserModel
from app.domain.alpha_hunter import AlphaHunter

logger = logging.getLogger(__name__)


class UserRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_by_wallet(self, wallet_address: str) -> AlphaHunter | None:
        stmt = select(UserModel).where(UserModel.wallet_address == wallet_address)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def fetch_by_id(self, user_id: UUID) -> AlphaHunter | None:
        stmt = select(UserModel).where(UserModel.id == str(user_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_or_create(self, wallet_address: str) -> AlphaHunter:
        existing = await self.fetch_by_wallet(wallet_address)
        if existing:
            return existing
        model = UserModel(
            id=str(uuid4()),
            wallet_address=wallet_address,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("Created new user for wallet=%s", wallet_address)
        return self._to_domain(model)

    async def fetch_leaderboard(self, limit: int = 50) -> list[AlphaHunter]:
        """Fetch users ordered by total PnL for leaderboard display."""
        stmt = (
            select(UserModel)
            .where(UserModel.is_public_portfolio.is_(True))
            .order_by(desc(UserModel.total_pnl_usd))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def update_performance(
        self,
        user_id: UUID,
        pnl_delta: Decimal,
        won: bool,
    ) -> None:
        """
        Atomically updates PnL, win rate, streak, and reputation score
        after a position is closed.
        """
        stmt = select(UserModel).where(UserModel.id == str(user_id))
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            logger.warning("update_performance: user %s not found", user_id)
            return

        model.total_pnl_usd = float(
            Decimal(str(model.total_pnl_usd)) + pnl_delta
        )
        if won:
            model.streak_days += 1
            model.alpha_reputation_score = min(
                float(Decimal(str(model.alpha_reputation_score)) + Decimal("5")),
                1000.0,
            )
        else:
            model.streak_days = 0
            model.alpha_reputation_score = max(
                float(Decimal(str(model.alpha_reputation_score)) - Decimal("2")),
                0.0,
            )

        await self._session.flush()

    def _to_domain(self, model: UserModel) -> AlphaHunter:
        return AlphaHunter(
            id=UUID(model.id),
            wallet_address=model.wallet_address,
            username=model.username,
            alpha_reputation_score=Decimal(str(model.alpha_reputation_score)),
            total_pnl_usd=Decimal(str(model.total_pnl_usd)),
            win_rate=Decimal(str(model.win_rate)),
            streak_days=model.streak_days,
            is_public_portfolio=model.is_public_portfolio,
            alpha_tokens_staked=Decimal(str(model.alpha_tokens_staked)),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )