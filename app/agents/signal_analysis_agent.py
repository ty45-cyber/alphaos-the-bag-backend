import logging
from decimal import Decimal
from app.agents.agent_state import AgentState
from app.domain.signal import Signal, SignalType

logger = logging.getLogger(__name__)


class SignalAnalysisAgent:
    """
    Processes raw signals and extracts actionable intelligence:
    breakout creators, bearish flags, and top signal list.
    """

    BREAKOUT_STRENGTH_THRESHOLD = Decimal("65.00")
    BEARISH_STRENGTH_THRESHOLD = Decimal("60.00")

    async def analyze(
        self,
        state: AgentState,
        signals: list[Signal],
    ) -> AgentState:
        """
        Classifies signals into breakout and bearish buckets.
        Populates state with processed signal intelligence.
        """
        if not signals:
            logger.info("SignalAnalysisAgent: no signals to process")
            return state

        breakout_ids: set[str] = set()
        bearish_ids: set[str] = set()
        top_signals = []

        for signal in signals:
            creator_id_str = str(signal.creator_id)

            if signal.is_actionable() and not signal.is_bearish():
                breakout_ids.add(creator_id_str)
                top_signals.append({
                    "creator_id": creator_id_str,
                    "type": signal.signal_type.value,
                    "strength": float(signal.strength),
                    "urgency": signal.urgency_label(),
                    "source": signal.source.value,
                })

            elif (
                signal.is_bearish()
                and signal.strength >= self.BEARISH_STRENGTH_THRESHOLD
            ):
                bearish_ids.add(creator_id_str)

        state.breakout_creators = list(breakout_ids)
        state.bearish_creators = list(bearish_ids)
        state.top_signals = sorted(
            top_signals,
            key=lambda s: s["strength"],
            reverse=True
        )[:10]

        logger.info(
            "SignalAnalysisAgent: %d breakouts, %d bearish",
            len(breakout_ids),
            len(bearish_ids),
        )
        return state