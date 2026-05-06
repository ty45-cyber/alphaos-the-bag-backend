import logging
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.portfolio_repository import PortfolioRepository
from app.infrastructure.creator_repository import CreatorRepository
from app.infrastructure.signal_repository import SignalRepository
from app.infrastructure.redis_client import cache_delete
from app.domain.portfolio import Portfolio, RebalanceStrategy
from app.agents.graph import run_allocation_pipeline

logger = logging.getLogger(__name__)

MIN_PORTFOLIO_VALUE_USD = Decimal("100.00")


class PortfolioService:
    """
    Manages portfolio lifecycle: creation, AI-driven rebalancing,
    manual allocation updates, and PnL computation.
    """

    def __init__(
        self,
        portfolio_repo: PortfolioRepository,
        creator_repo: CreatorRepository,
        signal_repo: SignalRepository,
    ) -> None:
        self._portfolio_repo = portfolio_repo
        self._creator_repo = creator_repo
        self._signal_repo = signal_repo

    async def create_portfolio(
        self,
        user_id: UUID,
        name: str,
        strategy: RebalanceStrategy = RebalanceStrategy.AI_MANAGED,
    ) -> Portfolio:
        return await self._portfolio_repo.create(user_id, name, strategy)

    async def fetch_user_portfolios(self, user_id: UUID) -> list[Portfolio]:
        return await self._portfolio_repo.fetch_by_user(user_id)

    async def fetch_portfolio(self, portfolio_id: UUID) -> Portfolio | None:
        return await self._portfolio_repo.fetch_by_id(portfolio_id)

    async def trigger_ai_rebalance(self, portfolio_id: UUID) -> Portfolio:
        """
        Runs the full LangGraph allocation pipeline and applies
        the resulting decisions to the portfolio.
        """
        portfolio = await self._portfolio_repo.fetch_by_id(portfolio_id)
        if portfolio is None:
            raise ValueError(f"Portfolio {portfolio_id} not found")

        if portfolio.rebalance_strategy != RebalanceStrategy.AI_MANAGED:
            raise ValueError(
                f"Portfolio {portfolio_id} is not AI managed "
                f"(strategy={portfolio.rebalance_strategy.value})"
            )

        signals = await self._signal_repo.fetch_actionable_signals(
            min_strength=60.0, since_hours=48
        )
        eligible_creators = await self._creator_repo.fetch_all_active(limit=30)
        eligible_creators = [
            c for c in eligible_creators
            if c.is_eligible_for_pool_allocation()
        ]

        if not eligible_creators:
            raise ValueError("No eligible creators available for allocation")

        final_state = await run_allocation_pipeline(
            signals=signals,
            eligible_creators=eligible_creators,
            portfolio_id=portfolio_id,
        )

        if final_state.errors:
            logger.error("Allocation pipeline errors: %s", final_state.errors)
            raise RuntimeError(f"Agent pipeline failed: {final_state.errors}")

        decisions = [
            {
                "creator_id": d.creator_id,
                "allocation_pct": d.recommended_pct,
                "entry_price_usd": None,
            }
            for d in final_state.allocation_decisions
        ]

        updated = await self._portfolio_repo.apply_allocations(portfolio_id, decisions)
        await cache_delete(f"portfolio:{portfolio_id}")
        logger.info(
            "AI rebalance complete for portfolio %s: %d positions",
            portfolio_id, len(decisions)
        )
        return updated

    async def compute_total_pnl(self, portfolio: Portfolio) -> Decimal:
        return portfolio.total_unrealized_pnl()