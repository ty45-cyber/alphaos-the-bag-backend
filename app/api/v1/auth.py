import logging
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database import get_db
from app.infrastructure.user_repository import UserRepository
from app.schemas.auth_schema import WalletAuthRequest, TokenResponse, UserProfileResponse
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer()


def _create_access_token(user_id: str, wallet: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user_id,
        "wallet": wallet,
        "exp": datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        ),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        return user_id
    except JWTError as exc:
        logger.warning("JWT decode failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


@router.post("/connect", response_model=TokenResponse)
async def connect_wallet(
    payload: WalletAuthRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Wallet-based auth: accepts a wallet address and signed message.
    In production, verify the signature against the wallet's public key.
    Returns a JWT for subsequent API calls.
    """
    user_repo = UserRepository(session)
    hunter = await user_repo.get_or_create(payload.wallet_address)
    token = _create_access_token(str(hunter.id), hunter.wallet_address)
    return TokenResponse(
        access_token=token,
        user_id=str(hunter.id),
        wallet_address=hunter.wallet_address,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db),
):
    from uuid import UUID
    user_repo = UserRepository(session)
    hunter = await user_repo.fetch_by_id(UUID(user_id))
    if hunter is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserProfileResponse(
        user_id=str(hunter.id),
        wallet_address=hunter.wallet_address,
        username=hunter.username,
        alpha_reputation_score=str(hunter.alpha_reputation_score),
        total_pnl_usd=str(hunter.total_pnl_usd),
        win_rate=str(hunter.win_rate),
        streak_days=hunter.streak_days,
        tier=hunter.tier(),
        is_public_portfolio=hunter.is_public_portfolio,
    )