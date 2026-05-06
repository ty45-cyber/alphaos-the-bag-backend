from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field
from app.domain.alpha_pool import PoolStrategy


class PoolResponse(BaseModel):
    id: UUID
    pool_name: str
    strategy_type: PoolStrategy
    total_staked_usd: Decimal
    apy_7d: Decimal | None
    apy_30d: Decimal | None
    performance_fee_pct: Decimal
    staker_count: int
    is_active: bool

    model_config = {"from_attributes": True}


class StakeRequest(BaseModel):
    amount_usd: Decimal = Field(gt=0, description="Amount in USD to stake")


class StakeResponse(BaseModel):
    stake_id: UUID
    pool_id: UUID
    user_id: UUID
    staked_amount_usd: Decimal
    staked_at: datetime
    message: str


class UserShareResponse(BaseModel):
    pool_id: UUID
    user_id: UUID
    share_pct: Decimal | None
    total_pool_usd: Decimal