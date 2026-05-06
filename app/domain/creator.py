from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass(frozen=True)
class NarrativeScore:
    """Composite score capturing creator market momentum."""
    velocity: Decimal       # Growth rate of holder count + volume
    whale_accumulation: Decimal  # Large wallet buy pressure
    social_momentum: Decimal     # Twitter/Discord engagement velocity
    composite: Decimal           # Weighted composite: 0.00–100.00

    def is_breakout(self) -> bool:
        """True when composite score exceeds breakout threshold."""
        return self.composite >= Decimal("75.00")

    def signal_tier(self) -> str:
        """Human-readable tier for UI display."""
        if self.composite >= 80:
            return "ALPHA"
        elif self.composite >= 60:
            return "RISING"
        elif self.composite >= 40:
            return "WATCH"
        return "COLD"


@dataclass
class Creator:
    """
    Core domain entity representing a Bags-listed creator
    with an associated token in the creator economy.
    """
    id: UUID
    bags_id: str
    wallet_address: str
    display_name: str
    token_mint: str
    narrative_score: NarrativeScore
    market_cap_usd: Optional[Decimal]
    volume_24h_usd: Optional[Decimal]
    holder_count: int
    last_signal_computed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    def fundability_score(self) -> Decimal:
        """
        Public score used on creator score page.
        Combines narrative score with liquidity indicators.
        """
        if not self.market_cap_usd or self.market_cap_usd == 0:
            return self.narrative_score.composite * Decimal("0.5")

        liquidity_factor = min(
            Decimal("1.0"),
            (self.volume_24h_usd or Decimal("0")) / self.market_cap_usd
        )
        return (self.narrative_score.composite * Decimal("0.7")) + (
            liquidity_factor * Decimal("30")
        )

    def is_eligible_for_pool_allocation(self) -> bool:
        """
        Minimum thresholds for AI pool to allocate capital to this creator.
        Protects against rug-pull risk on micro-cap illiquid tokens.
        """
        return (
            self.holder_count >= 50
            and (self.market_cap_usd or Decimal("0")) >= Decimal("10000")
            and self.narrative_score.composite >= Decimal("40.00")
        )