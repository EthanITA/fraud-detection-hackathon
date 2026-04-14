from __future__ import annotations

from langgraph.constants import Send
from langgraph.graph import END, StateGraph

from .nodes import (
    aggregate,
    amount_specialist,
    behavioral_specialist,
    collect_output,
    ingest,
    relationship_specialist,
    run_rules,
    triage,
    velocity_specialist,
)
from .state import PipelineState


def _fan_out_to_specialists(state: PipelineState) -> list:
    """Route triage output: ambiguous txns fan-out to 4 specialists, rest skip to output."""
    if state.get("ambiguous_prioritized"):
        return [
            Send("velocity_specialist", state),
            Send("amount_specialist", state),
            Send("behavioral_specialist", state),
            Send("relationship_specialist", state),
        ]
    return [Send("output", state)]


def build_pipeline():
    g = StateGraph(PipelineState)

    g.add_node("ingest", ingest)
    g.add_node("run_rules", run_rules)
    g.add_node("triage", triage)
    g.add_node("velocity_specialist", velocity_specialist)
    g.add_node("amount_specialist", amount_specialist)
    g.add_node("behavioral_specialist", behavioral_specialist)
    g.add_node("relationship_specialist", relationship_specialist)
    g.add_node("aggregate", aggregate)
    g.add_node("output", collect_output)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "run_rules")
    g.add_edge("run_rules", "triage")
    g.add_conditional_edges("triage", _fan_out_to_specialists)
    g.add_edge("velocity_specialist", "aggregate")
    g.add_edge("amount_specialist", "aggregate")
    g.add_edge("behavioral_specialist", "aggregate")
    g.add_edge("relationship_specialist", "aggregate")
    g.add_edge("aggregate", "output")
    g.add_edge("output", END)

    return g.compile()
