from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional
from enum import Enum


class RebalanceStrategy(str, Enum):
    AI_MANAGED = "ai_managed"
    MANUAL = "manual"
    COPY_TRADE = "copy_trade"


@dataclass
class Allocation:
    """A single creator position within a portfolio."""
    id: UUID
    portfolio_id: UUID
    creator_id: UUID
    allocation_pct: Decimal       # 0.00–100.00
    entry_price_usd: Optional[Decimal]
    current_price_usd: Optional[Decimal]
    unrealized_pnl_usd: Decimal
    created_at: datetime
    updated_at: datetime

    def pnl_pct(self) -> Optional[Decimal]:
        if not self.entry_price_usd or self.entry_price_usd == 0:
            return None
        return (
            (self.current_price_usd - self.entry_price_usd)
            / self.entry_price_usd
        ) * Decimal("100")


@dataclass
class Portfolio:
    """
    User's capital allocation across creators.
    Total allocation_pct across all allocations must equal 100.
    """
    id: UUID
    user_id: UUID
    name: str
    total_value_usd: Decimal
    allocations: list[Allocation] = field(default_factory=list)
    rebalance_strategy: RebalanceStrategy = RebalanceStrategy.AI_MANAGED
    last_rebalanced_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def validate_allocations(self) -> bool:
        """Ensures portfolio allocations sum to exactly 100%."""
        if not self.allocations:
            return True
        total = sum(a.allocation_pct for a in self.allocations)
        return abs(total - Decimal("100.00")) < Decimal("0.01")

    def top_positions(self, n: int = 5) -> list[Allocation]:
        return sorted(
            self.allocations,
            key=lambda a: a.allocation_pct,
            reverse=True
        )[:n]

    def total_unrealized_pnl(self) -> Decimal:
        return sum(a.unrealized_pnl_usd for a in self.allocations)