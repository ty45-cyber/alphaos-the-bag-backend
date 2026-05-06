from dataclasses import asdict
from decimal import Decimal
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.infrastructure.database import get_db
from app.infrastructure.user_repository import UserRepository
from app.application.leaderboard_service import LeaderboardService, LeaderboardEntry

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


class LeaderboardEntryResponse(BaseModel):
    rank: int
    user_id: str
    username: str | None
    wallet_address: str
    tier: str
    total_pnl_usd: str
    win_rate: str
    streak_days: int
    alpha_reputation_score: str
    rank_score: str


@router.get("", response_model=list[LeaderboardEntryResponse])
async def get_leaderboard(
    limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns the top Alpha Hunters ranked by composite performance score.
    Only users with public portfolios appear on the leaderboard.
    Cached for 2 minutes.
    """
    service = LeaderboardService(UserRepository(session))
    entries = await service.fetch_leaderboard(limit)
    return [
        LeaderboardEntryResponse(
            rank=e.rank,
            user_id=e.user_id,
            username=e.username,
            wallet_address=e.wallet_address,
            tier=e.tier,
            total_pnl_usd=str(e.total_pnl_usd),
            win_rate=str(e.win_rate),
            streak_days=e.streak_days,
            alpha_reputation_score=str(e.alpha_reputation_score),
            rank_score=str(e.rank_score),
        )
        for e in entries
    ]