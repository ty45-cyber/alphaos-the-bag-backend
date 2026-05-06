from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Numeric, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base


class AlphaPoolModel(Base):
    __tablename__ = "alpha_pools"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    pool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(64), nullable=False)
    total_staked_usd: Mapped[float] = mapped_column(
        Numeric(20, 2), default=0.00, nullable=False
    )
    apy_7d: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    apy_30d: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    performance_fee_pct: Mapped[float] = mapped_column(
        Numeric(4, 2), default=2.00, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    stakes: Mapped[list["PoolStakeModel"]] = relationship(  # noqa: F821
        "PoolStakeModel", back_populates="pool",
        lazy="select", cascade="all, delete-orphan"
    )


class PoolStakeModel(Base):
    __tablename__ = "pool_stakes"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    pool_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("alpha_pools.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    staked_amount_usd: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    share_pct: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    staked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    unstaked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    pool: Mapped["AlphaPoolModel"] = relationship("AlphaPoolModel", back_populates="stakes")