import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.infrastructure.signal_repository import SignalRepository
from app.infrastructure.creator_repository import CreatorRepository
from app.infrastructure.bags_client import BagsClient, BagsAPIError
from app.application.signal_service import SignalService
from app.schemas.signal_schema import (
    SignalResponse,
    SignalFeedResponse,
    SignalIngestRequest,
    SignalIngestResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/signals", tags=["Signals"])


def _build_signal_service(session: AsyncSession) -> SignalService:
    return SignalService(
        signal_repo=SignalRepository(session),
        creator_repo=CreatorRepository(session),
        bags_client=BagsClient(),
    )


@router.get("/feed", response_model=SignalFeedResponse)
async def get_signal_feed(
    min_strength: float = Query(default=65.0, ge=0.0, le=100.0),
    since_hours: int = Query(default=24, ge=1, le=168),
    session: AsyncSession = Depends(get_db),
):
    """
    Returns all actionable signals above min_strength threshold
    within the last N hours. Primary feed for the dashboard.
    """
    service = _build_signal_service(session)
    signals = await service.fetch_live_signals(
        min_strength=min_strength,
        since_hours=since_hours,
    )
    return SignalFeedResponse(
        signals=[
            SignalResponse(
                id=s.id,
                creator_id=s.creator_id,
                signal_type=s.signal_type,
                strength=s.strength,
                urgency=s.urgency_label(),
                source=s.source,
                computed_at=s.computed_at,
                raw_metadata=s.raw_metadata,
            )
            for s in signals
        ],
        total=len(signals),
        since_hours=since_hours,
    )


@router.get("/creator/{creator_id}", response_model=list[SignalResponse])
async def get_creator_signals(
    creator_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    """Returns the most recent signals for a specific creator."""
    service = _build_signal_service(session)
    signals = await service.fetch_signals_for_creator(creator_id, limit)
    if not signals:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No signals found for creator {creator_id}",
        )
    return [
        SignalResponse(
            id=s.id,
            creator_id=s.creator_id,
            signal_type=s.signal_type,
            strength=s.strength,
            urgency=s.urgency_label(),
            source=s.source,
            computed_at=s.computed_at,
            raw_metadata=s.raw_metadata,
        )
        for s in signals
    ]


@router.post("/ingest", response_model=SignalIngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest_creator_signals(
    payload: SignalIngestRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
):
    """
    Triggers fresh signal ingestion for a creator from Bags API.
    Runs synchronously and returns the computed signal count.
    """
    service = _build_signal_service(session)
    try:
        signals = await service.ingest_and_compute_signals(payload.bags_id)
    except BagsAPIError as exc:
        logger.error("Signal ingest failed for bags_id=%s: %s", payload.bags_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Bags API error: {exc}",
        )

    actionable = sum(1 for s in signals if s.is_actionable())
    return SignalIngestResponse(
        bags_id=payload.bags_id,
        signals_computed=len(signals),
        actionable_count=actionable,
        message=f"Computed {len(signals)} signals, {actionable} actionable — published to live feed",
    )