import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime
from app.application.portfolio_service import PortfolioService
from app.domain.portfolio import Portfolio, RebalanceStrategy


def _make_portfolio(**kwargs) -> Portfolio:
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        name="My Alpha Portfolio",
        total_value_usd=Decimal("5000"),
        allocations=[],
        rebalance_strategy=RebalanceStrategy.AI_MANAGED,
        last_rebalanced_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Portfolio(**defaults)


@pytest.mark.asyncio
async def test_create_portfolio_delegates_to_repository():
    mock_repo = AsyncMock()
    expected = _make_portfolio(name="Test")
    mock_repo.create.return_value = expected

    service = PortfolioService(
        portfolio_repo=mock_repo,
        creator_repo=AsyncMock(),
        signal_repo=AsyncMock(),
    )
    result = await service.create_portfolio(
        user_id=expected.user_id,
        name="Test",
        strategy=RebalanceStrategy.AI_MANAGED,
    )
    assert result.name == "Test"
    mock_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_rebalance_raises_on_non_ai_portfolio():
    portfolio = _make_portfolio(rebalance_strategy=RebalanceStrategy.MANUAL)
    mock_repo = AsyncMock()
    mock_repo.fetch_by_id.return_value = portfolio

    service = PortfolioService(
        portfolio_repo=mock_repo,
        creator_repo=AsyncMock(),
        signal_repo=AsyncMock(),
    )
    with pytest.raises(ValueError, match="not AI managed"):
        await service.trigger_ai_rebalance(portfolio.id)


@pytest.mark.asyncio
async def test_rebalance_raises_when_no_eligible_creators():
    portfolio = _make_portfolio(rebalance_strategy=RebalanceStrategy.AI_MANAGED)
    mock_portfolio_repo = AsyncMock()
    mock_portfolio_repo.fetch_by_id.return_value = portfolio

    mock_creator_repo = AsyncMock()
    mock_creator_repo.fetch_all_active.return_value = []

    mock_signal_repo = AsyncMock()
    mock_signal_repo.fetch_actionable_signals.return_value = []

    service = PortfolioService(
        portfolio_repo=mock_portfolio_repo,
        creator_repo=mock_creator_repo,
        signal_repo=mock_signal_repo,
    )
    with pytest.raises(ValueError, match="No eligible creators"):
        await service.trigger_ai_rebalance(portfolio.id)