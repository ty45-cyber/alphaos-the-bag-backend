import logging
from decimal import Decimal
from anthropic import AsyncAnthropic
from app.agents.agent_state import AgentState, AllocationDecision
from app.config import get_settings
from app.domain.creator import Creator

logger = logging.getLogger(__name__)


class AllocationAgent:
    """
    AI agent that determines optimal capital allocation across creators
    based on signal strength, narrative momentum, and risk constraints.
    """

    SYSTEM_PROMPT = """You are AlphaOS's capital allocation intelligence.
    
    Your role: Given a set of creator signals and market context, 
    recommend portfolio allocations (percentages) that maximize 
    risk-adjusted returns in the creator token economy.
    
    Rules:
    - Total allocations must sum to exactly 100%
    - Never allocate more than {max_single_pct}% to one creator
    - Prioritize creators with whale accumulation + narrative momentum
    - Respond ONLY with valid JSON: {"allocations": [{"creator_id": "...", "pct": 0.0, "reasoning": "..."}]}
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def decide_allocations(
        self,
        state: AgentState,
        eligible_creators: list[Creator],
    ) -> AgentState:
        """
        Core allocation decision: calls Claude to produce allocation percentages.
        Writes AllocationDecision objects back to shared state.
        """
        if not eligible_creators:
            logger.warning("AllocationAgent: no eligible creators, skipping")
            return state

        creator_context = [
            {
                "id": str(c.id),
                "name": c.display_name,
                "narrative_score": str(c.narrative_score.composite),
                "tier": c.narrative_score.signal_tier(),
                "market_cap_usd": str(c.market_cap_usd or 0),
                "holder_count": c.holder_count,
            }
            for c in eligible_creators
        ]

        prompt = (
            f"Narrative context: {state.narrative_context}\n"
            f"Bearish signals on: {state.bearish_creators}\n"
            f"Creators to allocate across:\n{creator_context}\n"
            f"Max single allocation: {state.max_single_allocation_pct}%\n"
            "Produce allocation JSON now."
        )

        try:
            response = await self._client.messages.create(
                model="claude-opus-4-5",
                max_tokens=1024,
                system=self.SYSTEM_PROMPT.format(
                    max_single_pct=state.max_single_allocation_pct
                ),
                messages=[{"role": "user", "content": prompt}],
            )

            import json
            raw = response.content[0].text
            parsed = json.loads(raw)

            state.allocation_decisions = [
                AllocationDecision(
                    creator_id=next(
                        c.id for c in eligible_creators
                        if str(c.id) == a["creator_id"]
                    ),
                    recommended_pct=Decimal(str(a["pct"])),
                    reasoning=a.get("reasoning", ""),
                    confidence=Decimal("0.85"),
                )
                for a in parsed.get("allocations", [])
            ]
            logger.info(
                "AllocationAgent: produced %d decisions",
                len(state.allocation_decisions)
            )

        except Exception as exc:
            logger.error("AllocationAgent decision failed: %s", exc)
            state.errors.append(f"AllocationAgent: {exc}")

        return state