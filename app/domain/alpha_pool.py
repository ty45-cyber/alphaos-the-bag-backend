from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional
from enum import Enum


class PoolStrategy(str, Enum):
    MOMENTUM = "momentum"
    NARRATIVE = "narrative"
    WHALE_FOLLOW = "whale_follow"


@dataclass
class PoolStake:
    """Individual user's stake position in an AlphaPool."""
    id: UUID
    pool_id: UUID
    user_id: UUID
    staked_amount_usd: Decimal
    share_pct: Optional[Decimal]
    staked_at: datetime
    unstaked_at: Optional[datetime]

    def is_active(self) -> bool:
        return self.unstaked_at is None


@dataclass
class AlphaPool:
    """
    Aggregated capital pool managed by AI allocation agents.
    Users stake capital; agents allocate across creator tokens.
    """
    id: UUID
    pool_name: str
    strategy_type: PoolStrategy
    total_staked_usd: Decimal
    apy_7d: Optional[Decimal]
    apy_30d: Optional[Decimal]
    performance_fee_pct: Decimal = Decimal("2.00")
    is_active: bool = True
    stakes: list[PoolStake] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def active_stakes(self) -> list[PoolStake]:
        return [s for s in self.stakes if s.is_active()]

    def staker_count(self) -> int:
        return len(self.active_stakes())

    def user_share_pct(self, user_id: UUID) -> Optional[Decimal]:
        """Returns a user's ownership percentage of the pool."""
        stake = next((s for s in self.active_stakes() if s.user_id == user_id), None)
        if not stake or self.total_staked_usd == 0:
            return None
        return (stake.staked_amount_usd / self.total_staked_usd) * Decimal("100")