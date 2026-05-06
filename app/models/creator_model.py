from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Numeric, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base


class CreatorModel(Base):
    __tablename__ = "creators"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    bags_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    wallet_address: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    token_mint: Mapped[str] = mapped_column(String(64), nullable=False)

    narrative_score: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.00, nullable=False
    )
    velocity_score: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.00, nullable=False
    )
    whale_accumulation_score: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.00, nullable=False
    )
    social_momentum_score: Mapped[float] = mapped_column(
        Numeric(6, 2), default=0.00, nullable=False
    )

    market_cap_usd: Mapped[float | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    volume_24h_usd: Mapped[float | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    holder_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_signal_computed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    signals: Mapped[list["SignalModel"]] = relationship(  # noqa: F821
        "SignalModel", back_populates="creator", lazy="select", cascade="all, delete-orphan"
    )