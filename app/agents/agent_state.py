from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID


@dataclass
class AllocationDecision:
    creator_id: UUID
    recommended_pct: Decimal
    reasoning: str
    confidence: Decimal  # 0.00–1.00


@dataclass
class AgentState:
    """
    Shared mutable state passed between LangGraph agent nodes.
    Each agent reads from and writes to this state.
    """
    portfolio_id: Optional[UUID] = None
    pool_id: Optional[UUID] = None

    # Signal analysis outputs
    top_signals: list[dict[str, Any]] = field(default_factory=list)
    breakout_creators: list[str] = field(default_factory=list)  # bags_ids
    bearish_creators: list[str] = field(default_factory=list)

    # Allocation agent outputs
    allocation_decisions: list[AllocationDecision] = field(default_factory=list)

    # Risk management outputs
    max_single_allocation_pct: Decimal = Decimal("20.00")
    risk_override_triggered: bool = False
    risk_override_reason: Optional[str] = None

    # Narrative agent outputs
    narrative_context: str = ""
    trending_themes: list[str] = field(default_factory=list)

    # Execution metadata
    agent_run_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)