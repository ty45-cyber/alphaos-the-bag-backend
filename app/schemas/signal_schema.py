from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field
from app.domain.signal import SignalType, SignalSource


class SignalResponse(BaseModel):
    id: UUID
    creator_id: UUID
    signal_type: SignalType
    strength: Decimal = Field(ge=0, le=100)
    urgency: str
    source: SignalSource
    computed_at: datetime
    raw_metadata: dict | None = None

    model_config = {"from_attributes": True}


class SignalFeedResponse(BaseModel):
    signals: list[SignalResponse]
    total: int
    since_hours: int


class SignalIngestRequest(BaseModel):
    bags_id: str = Field(min_length=1, max_length=64)


class SignalIngestResponse(BaseModel):
    bags_id: str
    signals_computed: int
    actionable_count: int
    message: str


class CreatorSignalSummary(BaseModel):
    creator_id: UUID
    creator_name: str
    bags_id: str
    signal_count: int
    max_strength: Decimal
    dominant_signal_type: SignalType
    latest_signal_at: datetime