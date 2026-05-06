from pydantic import BaseModel, Field


class WalletAuthRequest(BaseModel):
    wallet_address: str = Field(min_length=32, max_length=64)
    signed_message: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    wallet_address: str


class UserProfileResponse(BaseModel):
    user_id: str
    wallet_address: str
    username: str | None
    alpha_reputation_score: str
    total_pnl_usd: str
    win_rate: str
    streak_days: int
    tier: str
    is_public_portfolio: bool