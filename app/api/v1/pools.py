import logging
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.infrastructure.pool_repository import PoolRepository
from app.application.pool_service import PoolService
from app.api.v1.auth import get_current_user_id
from app.schemas.pool_schema import (
    PoolResponse,
    StakeRequest,
    StakeResponse,
    UserShareResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pools", tags=["AlphaPools"])


def _build_service(session: AsyncSession) -> PoolService:
    return PoolService(pool_repo=PoolRepository(session))


def _to_response(pool) -> PoolResponse:
    return PoolResponse(
        id=pool.id,
        pool_name=pool.pool_name,
        strategy_type=pool.strategy_type,
        total_staked_usd=pool.total_staked_usd,
        apy_7d=pool.apy_7d,
        apy_30d=pool.apy_30d,
        performance_fee_pct=pool.performance_fee_pct,
        staker_count=pool.staker_count(),
        is_active=pool.is_active,
    )


@router.get("", response_model=list[PoolResponse])
async def list_pools(session: AsyncSession = Depends(get_db)):
    service = _build_service(session)
    pools = await service.list_active_pools()
    return [_to_response(p) for p in pools]


@router.get("/{pool_id}", response_model=PoolResponse)
async def get_pool(pool_id: UUID, session: AsyncSession = Depends(get_db)):
    service = _build_service(session)
    pool = await service.fetch_pool(pool_id)
    if pool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")
    return _to_response(pool)


@router.post("/{pool_id}/stake", response_model=StakeResponse, status_code=status.HTTP_201_CREATED)
async def stake_in_pool(
    pool_id: UUID,
    payload: StakeRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = _build_service(session)
    try:
        stake = await service.stake(pool_id, UUID(user_id), payload.amount_usd)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    return StakeResponse(
        stake_id=stake.id,
        pool_id=stake.pool_id,
        user_id=stake.user_id,
        staked_amount_usd=stake.staked_amount_usd,
        staked_at=stake.staked_at,
        message=f"Successfully staked ${stake.staked_amount_usd} in pool",
    )


@router.delete("/{pool_id}/stake", status_code=status.HTTP_204_NO_CONTENT)
async def unstake_from_pool(
    pool_id: UUID,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = _build_service(session)
    try:
        await service.unstake(pool_id, UUID(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/{pool_id}/my-share", response_model=UserShareResponse)
async def get_my_pool_share(
    pool_id: UUID,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    service = _build_service(session)
    pool = await service.fetch_pool(pool_id)
    if pool is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pool not found")

    share = await service.get_user_share(pool_id, UUID(user_id))
    return UserShareResponse(
        pool_id=pool_id,
        user_id=UUID(user_id),
        share_pct=share,
        total_pool_usd=pool.total_staked_usd,
    )