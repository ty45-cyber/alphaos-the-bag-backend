import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.infrastructure.portfolio_repository import PortfolioRepository
from app.infrastructure.creator_repository import CreatorRepository
from app.infrastructure.signal_repository import SignalRepository
from app.application.portfolio_service import PortfolioService
from app.api.v1.auth import get_current_user_id
from app.schemas.portfolio_schema import (
    PortfolioResponse,
    AllocationResponse,
    CreatePortfolioRequest,
    RebalanceResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portfolios", tags=["Portfolios"])


def _build_service(session: AsyncSession) -> PortfolioService:
    return PortfolioService(
        portfolio_repo=PortfolioRepository(session),
        creator_repo=CreatorRepository(session),
        signal_repo=SignalRepository(session),
    )


def _to_response(portfolio) -> PortfolioResponse:
    return PortfolioResponse(
        id=portfolio.id,
        user_id=portfolio.user_id,
        name=portfolio.name,
        total_value_usd=portfolio.total_value_usd,
        rebalance_strategy=portfolio.rebalance_strategy,
        allocations=[
            AllocationResponse(
                id=a.id,
                creator_id=a.creator_id,
                allocation_pct=a.allocation_pct,
                entry_price_usd=a.entry_price_usd,
                current_price_usd=a.current_price_usd,
                unrealized_pnl_usd=a.unrealized_pnl_usd,
                pnl_pct=a.pnl_pct(),
            )
            for a in portfolio.allocations
        ],
        total_unrealized_pnl=portfolio.total_unrealized_pnl(),
        last_rebalanced_at=portfolio.last_rebalanced_at,
        created_at=portfolio.created_at,
    )


@router.post("", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    payload: CreatePortfolioRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = _build_service(session)
    portfolio = await service.create_portfolio(
        user_id=UUID(user_id),
        name=payload.name,
        strategy=payload.strategy,
    )
    return _to_response(portfolio)


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = _build_service(session)
    portfolios = await service.fetch_user_portfolios(UUID(user_id))
    return [_to_response(p) for p in portfolios]


@router.get("/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio(
    portfolio_id: UUID,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = _build_service(session)
    portfolio = await service.fetch_portfolio(portfolio_id)
    if portfolio is None or str(portfolio.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found",
        )
    return _to_response(portfolio)


@router.post("/{portfolio_id}/rebalance", response_model=RebalanceResponse)
async def rebalance_portfolio(
    portfolio_id: UUID,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    """Triggers the AI allocation pipeline and applies results to the portfolio."""
    service = _build_service(session)
    portfolio = await service.fetch_portfolio(portfolio_id)
    if portfolio is None or str(portfolio.user_id) != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found")

    try:
        updated = await service.trigger_ai_rebalance(portfolio_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return RebalanceResponse(
        portfolio_id=updated.id,
        positions_set=len(updated.allocations),
        strategy_used="ai_managed",
        narrative_context="Agent pipeline executed successfully",
        message=f"Portfolio rebalanced across {len(updated.allocations)} creator positions",
    )