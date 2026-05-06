import logging
from uuid import uuid4
from langgraph.graph import StateGraph, END
from app.agents.agent_state import AgentState
from app.agents.signal_analysis_agent import SignalAnalysisAgent
from app.agents.risk_management_agent import RiskManagementAgent
from app.agents.allocation_agent import AllocationAgent
from app.agents.narrative_agent import NarrativeAgent
from app.domain.signal import Signal
from app.domain.creator import Creator

logger = logging.getLogger(__name__)

signal_analysis = SignalAnalysisAgent()
risk_management = RiskManagementAgent()
allocation = AllocationAgent()
narrative = NarrativeAgent()


def build_allocation_graph(
    signals: list[Signal],
    eligible_creators: list[Creator],
):
    """
    Constructs and compiles the LangGraph allocation pipeline.
    Nodes: signal_analysis → narrative → risk → allocate → END
    """

    async def run_signal_analysis(state: AgentState) -> AgentState:
        return await signal_analysis.analyze(state, signals)

    async def run_narrative(state: AgentState) -> AgentState:
        return await narrative.build_context(state, eligible_creators)

    async def run_risk(state: AgentState) -> AgentState:
        return await risk_management.enforce_risk_limits(state)

    async def run_allocation(state: AgentState) -> AgentState:
        return await allocation.decide_allocations(state, eligible_creators)

    def should_proceed_to_allocation(state: AgentState) -> str:
        if state.risk_override_triggered:
            logger.warning("Risk override active: %s", state.risk_override_reason)
        if state.errors:
            return "end"
        return "allocate"

    graph = StateGraph(AgentState)
    graph.add_node("signal_analysis", run_signal_analysis)
    graph.add_node("narrative", run_narrative)
    graph.add_node("risk", run_risk)
    graph.add_node("allocate", run_allocation)

    graph.set_entry_point("signal_analysis")
    graph.add_edge("signal_analysis", "narrative")
    graph.add_edge("narrative", "risk")
    graph.add_conditional_edges(
        "risk",
        should_proceed_to_allocation,
        {"allocate": "allocate", "end": END},
    )
    graph.add_edge("allocate", END)

    return graph.compile()


async def run_allocation_pipeline(
    signals: list[Signal],
    eligible_creators: list[Creator],
    portfolio_id=None,
    pool_id=None,
) -> AgentState:
    """Entry point for the full allocation agent pipeline."""
    initial_state = AgentState(
        portfolio_id=portfolio_id,
        pool_id=pool_id,
        agent_run_id=str(uuid4()),
    )
    compiled = build_allocation_graph(signals, eligible_creators)
    final_state = await compiled.ainvoke(initial_state)
    return final_state