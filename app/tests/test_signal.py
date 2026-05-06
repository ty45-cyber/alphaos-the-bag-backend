import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime
from app.application.signal_service import SignalService
from app.domain.creator import Creator, NarrativeScore
from app.domain.signal import SignalType


def _make_creator(**kwargs) -> Creator:
    defaults = dict(
        id=uuid4(),
        bags_id="creator_001",
        wallet_address="wallet123",
        display_name="Test Creator",
        token_mint="mint123",
        narrative_score=NarrativeScore(
            velocity=Decimal("50"),
            whale_accumulation=Decimal("60"),
            social_momentum=Decimal("40"),
            composite=Decimal("52"),
        ),
        market_cap_usd=Decimal("500000"),
        volume_24h_usd=Decimal("80000"),
        holder_count=200,
        last_signal_computed_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return Creator(**defaults)


@pytest.mark.asyncio
async def test_whale_signal_detected_when_threshold_met():
    service = SignalService(
        signal_repo=AsyncMock(),
        creator_repo=AsyncMock(),
        bags_client=AsyncMock(),
    )
    creator = _make_creator(market_cap_usd=Decimal("1000000"), holder_count=100)
    holders = [
        {"balance": "10000", "wallet": f"whale_{i}"}
        for i in range(10)
    ]
    signals = service._compute_whale_signals(creator, holders)
    assert len(signals) == 1
    assert signals[0].signal_type == SignalType.WHALE_BUY
    assert signals[0].strength > Decimal("0")


@pytest.mark.asyncio
async def test_velocity_signal_not_triggered_below_multiplier():
    service = SignalService(
        signal_repo=AsyncMock(),
        creator_repo=AsyncMock(),
        bags_client=AsyncMock(),
    )
    creator = _make_creator()
    bags_data = {"volume_24h_usd": 10000, "volume_7d_usd": 70000}
    signals = service._compute_velocity_signal(creator, bags_data)
    assert len(signals) == 0


@pytest.mark.asyncio
async def test_velocity_signal_triggered_on_surge():
    service = SignalService(
        signal_repo=AsyncMock(),
        creator_repo=AsyncMock(),
        bags_client=AsyncMock(),
    )
    creator = _make_creator()
    bags_data = {"volume_24h_usd": 100000, "volume_7d_usd": 70000}
    signals = service._compute_velocity_signal(creator, bags_data)
    assert len(signals) == 1
    assert signals[0].signal_type == SignalType.VELOCITY_SURGE


@pytest.mark.asyncio
async def test_social_signal_not_triggered_below_threshold():
    service = SignalService(
        signal_repo=AsyncMock(),
        creator_repo=AsyncMock(),
        bags_client=AsyncMock(),
    )
    creator = _make_creator()
    bags_data = {"social_engagement_24h": 100}
    signals = service._compute_social_signal(creator, bags_data)
    assert len(signals) == 0