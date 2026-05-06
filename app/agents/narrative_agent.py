import logging
from anthropic import AsyncAnthropic
from app.agents.agent_state import AgentState
from app.domain.creator import Creator
from app.config import get_settings

logger = logging.getLogger(__name__)


class NarrativeAgent:
    """
    Synthesizes market narrative from trending creator data and signal context.
    Produces a human-readable narrative string used by AllocationAgent
    to inform capital decisions with qualitative market intelligence.
    """

    SYSTEM_PROMPT = (
        "You are AlphaOS's narrative intelligence layer. "
        "Given a list of trending creators and their signals, produce: "
        "1) A 2-sentence market narrative summary. "
        "2) A list of 3-5 trending themes (e.g. 'AI creators surging', 'gaming tokens consolidating'). "
        "Respond ONLY with JSON: {\"narrative\": \"...\", \"themes\": [\"...\"]}"
    )

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def build_context(
        self,
        state: AgentState,
        creators: list[Creator],
    ) -> AgentState:
        if not creators:
            state.narrative_context = "Insufficient data for narrative generation."
            return state

        creator_summaries = [
            {
                "name": c.display_name,
                "tier": c.narrative_score.signal_tier(),
                "score": str(c.narrative_score.composite),
            }
            for c in creators[:15]
        ]

        try:
            response = await self._client.messages.create(
                model="claude-opus-4-5",
                max_tokens=512,
                system=self.SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": f"Breakout signals: {state.breakout_creators[:5]}\n"
                               f"Creator universe: {creator_summaries}",
                }],
            )
            import json
            raw = response.content[0].text
            parsed = json.loads(raw)
            state.narrative_context = parsed.get("narrative", "")
            state.trending_themes = parsed.get("themes", [])
            logger.info("NarrativeAgent: themes=%s", state.trending_themes)

        except Exception as exc:
            logger.error("NarrativeAgent failed: %s", exc)
            state.errors.append(f"NarrativeAgent: {exc}")
            state.narrative_context = "Narrative generation unavailable."

        return state