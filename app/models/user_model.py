from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Numeric, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    wallet_address: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    alpha_reputation_score: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.00, nullable=False
    )
    total_pnl_usd: Mapped[float] = mapped_column(
        Numeric(20, 2), default=0.00, nullable=False
    )
    win_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0.00, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_public_portfolio: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alpha_tokens_staked: Mapped[float] = mapped_column(
        Numeric(20, 8), default=0.00, nullable=False
    )
    hashed_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    portfolios: Mapped[list["PortfolioModel"]] = relationship(  # noqa: F821
        "PortfolioModel", back_populates="user", lazy="select"
    )