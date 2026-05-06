import logging
from dataclasses import dataclass
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.user_repository import UserRepository
from app.infrastructure.redis_client import cache_set, cache_get
from app.domain.alpha_hunter import AlphaHunter

logger = logging.getLogger(__name__)

LEADERBOARD_CACHE_KEY = "leaderboard:top50"
LEADERBOARD_CACHE_TTL = 120  # 2 minutes


@dataclass
class LeaderboardEntry:
    rank: int
    user_id: str
    username: str | None
    wallet_address: str
    tier: str
    total_pnl_usd: Decimal
    win_rate: Decimal
    streak_days: int
    alpha_reputation_score: Decimal
    rank_score: Decimal


class LeaderboardService:
    """
    Computes and caches the AlphaHunter leaderboard.
    Ranking uses the composite rank score from the AlphaHunter domain.
    """

    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def fetch_leaderboard(self, limit: int = 50) -> list[LeaderboardEntry]:
        cached = await cache_get(LEADERBOARD_CACHE_KEY)
        if cached:
            logger.debug("Leaderboard cache hit")
            return [LeaderboardEntry(**e) for e in cached]

        hunters = await self._user_repo.fetch_leaderboard(limit)
        ranked = self._rank(hunters)

        await cache_set(
            LEADERBOARD_CACHE_KEY,
            [
                {
                    "rank": e.rank,
                    "user_id": e.user_id,
                    "username": e.username,
                    "wallet_address": e.wallet_address,
                    "tier": e.tier,
                    "total_pnl_usd": str(e.total_pnl_usd),
                    "win_rate": str(e.win_rate),
                    "streak_days": e.streak_days,
                    "alpha_reputation_score": str(e.alpha_reputation_score),
                    "rank_score": str(e.rank_score),
                }
                for e in ranked
            ],
            ttl_seconds=LEADERBOARD_CACHE_TTL,
        )
        return ranked

    def _rank(self, hunters: list[AlphaHunter]) -> list[LeaderboardEntry]:
        scored = sorted(
            hunters,
            key=lambda h: h.leaderboard_rank_score(),
            reverse=True,
        )
        return [
            LeaderboardEntry(
                rank=idx + 1,
                user_id=str(h.id),
                username=h.username,
                wallet_address=h.wallet_address,
                tier=h.tier(),
                total_pnl_usd=h.total_pnl_usd,
                win_rate=h.win_rate,
                streak_days=h.streak_days,
                alpha_reputation_score=h.alpha_reputation_score,
                rank_score=h.leaderboard_rank_score(),
            )
            for idx, h in enumerate(scored)
        ]