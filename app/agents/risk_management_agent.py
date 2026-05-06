import logging
from decimal import Decimal
from app.agents.agent_state import AgentState

logger = logging.getLogger(__name__)


class RiskManagementAgent:
    """
    Enforces position sizing limits and portfolio-level risk controls.
    Runs before allocation execution to prevent over-concentration.
    """

    DEFAULT_MAX_SINGLE_PCT = Decimal("20.00")
    HIGH_CONVICTION_MAX_PCT = Decimal("30.00")
    CONCENTRATION_ALERT_THRESHOLD = Decimal("50.00")  # Top 3 positions

    async def enforce_risk_limits(self, state: AgentState) -> AgentState:
        """
        Reviews proposed allocations and applies hard limits.
        Overrides any allocation that violates risk rules.
        """
        if not state.allocation_decisions:
            return state

        total_top_3 = sum(
            d.recommended_pct
            for d in sorted(
                state.allocation_decisions,
                key=lambda d: d.recommended_pct,
                reverse=True
            )[:3]
        )

        if total_top_3 > self.CONCENTRATION_ALERT_THRESHOLD:
            logger.warning(
                "RiskManagementAgent: top-3 concentration at %.2f%%, redistributing",
                total_top_3
            )
            state = self._redistribute_concentration(state)

        for decision in state.allocation_decisions:
            if decision.recommended_pct > state.max_single_allocation_pct:
                excess = decision.recommended_pct - state.max_single_allocation_pct
                decision.recommended_pct = state.max_single_allocation_pct
                state.risk_override_triggered = True
                state.risk_override_reason = (
                    f"Capped {decision.creator_id} at {state.max_single_allocation_pct}%"
                    f" (was {decision.recommended_pct + excess}%)"
                )

        return state

    def _redistribute_concentration(self, state: AgentState) -> AgentState:
        """
        Flattens over-concentrated allocations by normalizing
        toward equal-weight with a momentum tilt.
        """
        n = len(state.allocation_decisions)
        if n == 0:
            return state

        equal_weight = Decimal("100.00") / Decimal(n)
        for decision in state.allocation_decisions:
            decision.recommended_pct = (
                decision.recommended_pct * Decimal("0.7")
                + equal_weight * Decimal("0.3")
            )

        # Re-normalize to exactly 100
        total = sum(d.recommended_pct for d in state.allocation_decisions)
        if total > 0:
            for decision in state.allocation_decisions:
                decision.recommended_pct = (
                    decision.recommended_pct / total * Decimal("100")
                ).quantize(Decimal("0.01"))

        return state