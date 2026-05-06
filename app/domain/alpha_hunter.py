from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class AlphaHunter:
    """
    A user with a public reputation in the AlphaOS ecosystem.
    Reputation compounds through correct calls and pool performance.
    """
    id: UUID
    wallet_address: str
    username: Optional[str]
    alpha_reputation_score: Decimal   # 0–1000, compounding
    total_pnl_usd: Decimal
    win_rate: Decimal                 # 0.00–100.00 pct
    streak_days: int
    is_public_portfolio: bool
    alpha_tokens_staked: Decimal
    created_at: datetime
    updated_at: datetime

    def leaderboard_rank_score(self) -> Decimal:
        """
        Composite score for leaderboard ranking.
        Weights: PnL (40%), win_rate (30%), reputation (20%), streak (10%).
        """
        normalized_pnl = min(self.total_pnl_usd / Decimal("100000"), Decimal("1.0"))
        normalized_streak = min(Decimal(self.streak_days) / Decimal("30"), Decimal("1.0"))
        return (
            normalized_pnl * Decimal("40")
            + (self.win_rate / Decimal("100")) * Decimal("30")
            + (self.alpha_reputation_score / Decimal("1000")) * Decimal("20")
            + normalized_streak * Decimal("10")
        )

    def tier(self) -> str:
        score = self.leaderboard_rank_score()
        if score >= 70:
            return "WHALE"
        elif score >= 50:
            return "ALPHA"
        elif score >= 30:
            return "HUNTER"
        return "ROOKIE"