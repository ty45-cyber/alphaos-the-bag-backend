from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional, Any
from enum import Enum


class SignalType(str, Enum):
    WHALE_BUY = "whale_buy"
    WHALE_SELL = "whale_sell"
    NARRATIVE_SPIKE = "narrative_spike"
    VELOCITY_SURGE = "velocity_surge"
    SOCIAL_BREAKOUT = "social_breakout"
    HOLDER_ACCUMULATION = "holder_accumulation"


class SignalSource(str, Enum):
    ON_CHAIN = "on_chain"
    SOCIAL = "social"
    BAGS_API = "bags_api"


@dataclass(frozen=True)
class Signal:
    """
    Immutable domain event representing a detected market signal
    for a specific creator. Strength is normalized 0–100.
    """
    id: UUID
    creator_id: UUID
    signal_type: SignalType
    strength: Decimal       # 0.00–100.00
    source: SignalSource
    raw_metadata: Optional[dict[str, Any]]
    computed_at: datetime

    def is_actionable(self) -> bool:
        """Signal is strong enough to trigger portfolio rebalance consideration."""
        return self.strength >= Decimal("65.00")

    def is_bearish(self) -> bool:
        return self.signal_type == SignalType.WHALE_SELL

    def urgency_label(self) -> str:
        if self.strength >= 85:
            return "URGENT"
        elif self.strength >= 65:
            return "HIGH"
        elif self.strength >= 45:
            return "MEDIUM"
        return "LOW"