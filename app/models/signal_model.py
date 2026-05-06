from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base


class SignalModel(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    creator_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("creators.id", ondelete="CASCADE"),
        nullable=False,
    )
    signal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    strength: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    creator: Mapped["CreatorModel"] = relationship(  # noqa: F821
        "CreatorModel", back_populates="signals", lazy="select"
    )

    __table_args__ = (
        Index("idx_signals_creator_computed", "creator_id", "computed_at"),
        Index("idx_signals_type_strength", "signal_type", "strength"),
    )