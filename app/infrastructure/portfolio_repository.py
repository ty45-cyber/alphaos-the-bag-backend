import logging
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.portfolio_model import PortfolioModel, AllocationModel
from app.domain.portfolio import Portfolio, Allocation, RebalanceStrategy

logger = logging.getLogger(__name__)


class PortfolioRepository:

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def fetch_by_id(self, portfolio_id: UUID) -> Portfolio | None:
        stmt = (
            select(PortfolioModel)
            .options(selectinload(PortfolioModel.allocations))
            .where(PortfolioModel.id == str(portfolio_id))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def fetch_by_user(self, user_id: UUID) -> list[Portfolio]:
        stmt = (
            select(PortfolioModel)
            .options(selectinload(PortfolioModel.allocations))
            .where(PortfolioModel.user_id == str(user_id))
        )
        result = await self._session.execute(stmt)
        return [self._to_domain(m) for m in result.scalars().all()]

    async def create(self, user_id: UUID, name: str, strategy: RebalanceStrategy) -> Portfolio:
        model = PortfolioModel(
            id=str(uuid4()),
            user_id=str(user_id),
            name=name,
            rebalance_strategy=strategy.value,
        )
        self._session.add(model)
        await self._session.flush()
        logger.info("Created portfolio %s for user %s", model.id, user_id)
        return self._to_domain(model)

    async def apply_allocations(
        self,
        portfolio_id: UUID,
        decisions: list[dict],
    ) -> Portfolio:
        """
        Replaces all existing allocations with the agent's new decisions.
        Each decision: {creator_id, allocation_pct, entry_price_usd}
        """
        stmt = (
            select(PortfolioModel)
            .options(selectinload(PortfolioModel.allocations))
            .where(PortfolioModel.id == str(portfolio_id))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()

        if model is None:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        for existing in model.allocations:
            await self._session.delete(existing)

        await self._session.flush()

        for decision in decisions:
            alloc = AllocationModel(
                id=str(uuid4()),
                portfolio_id=str(portfolio_id),
                creator_id=str(decision["creator_id"]),
                allocation_pct=float(decision["allocation_pct"]),
                entry_price_usd=float(decision.get("entry_price_usd", 0)) or None,
            )
            self._session.add(alloc)

        model.last_rebalanced_at = datetime.utcnow()
        await self._session.flush()

        return await self.fetch_by_id(portfolio_id)

    def _to_domain(self, model: PortfolioModel) -> Portfolio:
        allocations = [
            Allocation(
                id=UUID(a.id),
                portfolio_id=UUID(a.portfolio_id),
                creator_id=UUID(a.creator_id),
                allocation_pct=Decimal(str(a.allocation_pct)),
                entry_price_usd=Decimal(str(a.entry_price_usd)) if a.entry_price_usd else None,
                current_price_usd=Decimal(str(a.current_price_usd)) if a.current_price_usd else None,
                unrealized_pnl_usd=Decimal(str(a.unrealized_pnl_usd)),
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in (model.allocations or [])
        ]
        return Portfolio(
            id=UUID(model.id),
            user_id=UUID(model.user_id),
            name=model.name,
            total_value_usd=Decimal(str(model.total_value_usd)),
            allocations=allocations,
            rebalance_strategy=RebalanceStrategy(model.rebalance_strategy),
            last_rebalanced_at=model.last_rebalanced_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )