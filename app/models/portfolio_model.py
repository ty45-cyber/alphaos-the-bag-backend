from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base


class PortfolioModel(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    total_value_usd: Mapped[float] = mapped_column(
        Numeric(20, 2), default=0.00, nullable=False
    )
    rebalance_strategy: Mapped[str] = mapped_column(
        String(32), default="ai_managed", nullable=False
    )
    last_rebalanced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="portfolios", lazy="select")  # noqa: F821
    allocations: Mapped[list["AllocationModel"]] = relationship(  # noqa: F821
        "AllocationModel", back_populates="portfolio",
        lazy="select", cascade="all, delete-orphan"
    )


class AllocationModel(Base):
    __tablename__ = "portfolio_allocations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    portfolio_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    creator_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("creators.id"),
        nullable=False,
    )
    allocation_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    entry_price_usd: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    current_price_usd: Mapped[float | None] = mapped_column(Numeric(20, 8), nullable=True)
    unrealized_pnl_usd: Mapped[float] = mapped_column(
        Numeric(20, 2), default=0.00, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        default=datetime.utcnow, onupdate=datetime.utcnow
    )

    portfolio: Mapped["PortfolioModel"] = relationship(
        "PortfolioModel", back_populates="allocations"
    )