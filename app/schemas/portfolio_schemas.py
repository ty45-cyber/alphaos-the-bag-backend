from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field
from app.domain.portfolio import RebalanceStrategy


class AllocationResponse(BaseModel):
    id: UUID
    creator_id: UUID
    allocation_pct: Decimal
    entry_price_usd: Decimal | None
    current_price_usd: Decimal | None
    unrealized_pnl_usd: Decimal
    pnl_pct: Decimal | None

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    total_value_usd: Decimal
    rebalance_strategy: RebalanceStrategy
    allocations: list[AllocationResponse]
    total_unrealized_pnl: Decimal
    last_rebalanced_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreatePortfolioRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    strategy: RebalanceStrategy = RebalanceStrategy.AI_MANAGED


class RebalanceResponse(BaseModel):
    portfolio_id: UUID
    positions_set: int
    strategy_used: str
    narrative_context: str
    message: str