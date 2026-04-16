# %% imports
from __future__ import annotations

from langgraph.constants import Send
from langgraph.graph import END, StateGraph

from .nodes import (
    aggregate,
    amount_specialist,
    analyze_citizens,
    behavioral_specialist,
    collect_output,
    geographic_specialist,
    ingest,
    relationship_specialist,
    run_rules,
    triage,
    velocity_specialist,
)
from .state import PipelineState


# %% LLM toggle — set to False to skip all LLM inference (rules-only mode)
ENABLE_LLM = True


# %% _fan_out_to_specialists
def _fan_out_to_specialists(state: PipelineState) -> list:
    """Route triage output: ambiguous txns fan-out to 5 specialists, rest skip to output."""
    if not ENABLE_LLM:
        return [Send("output", state)]
    if state.get("ambiguous_prioritized"):
        return [
            Send("velocity_specialist", state),
            Send("amount_specialist", state),
            Send("behavioral_specialist", state),
            Send("relationship_specialist", state),
            Send("geographic_specialist", state),
        ]
    return [Send("output", state)]


# %% _skip_citizen_analysis
def _skip_citizen_analysis(state: PipelineState) -> dict:
    """No-op when LLM is disabled."""
    return {}


# %% build_pipeline
def build_pipeline():
    g = StateGraph(PipelineState)

    g.add_node("ingest", ingest)
    g.add_node("analyze_citizens", analyze_citizens if ENABLE_LLM else _skip_citizen_analysis)
    g.add_node("run_rules", run_rules)
    g.add_node("triage", triage)
    g.add_node("velocity_specialist", velocity_specialist)
    g.add_node("amount_specialist", amount_specialist)
    g.add_node("behavioral_specialist", behavioral_specialist)
    g.add_node("relationship_specialist", relationship_specialist)
    g.add_node("geographic_specialist", geographic_specialist)
    g.add_node("aggregate", aggregate)
    g.add_node("output", collect_output)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "analyze_citizens")
    g.add_edge("analyze_citizens", "run_rules")
    g.add_edge("run_rules", "triage")
    g.add_conditional_edges("triage", _fan_out_to_specialists)
    g.add_edge("velocity_specialist", "aggregate")
    g.add_edge("amount_specialist", "aggregate")
    g.add_edge("behavioral_specialist", "aggregate")
    g.add_edge("relationship_specialist", "aggregate")
    g.add_edge("geographic_specialist", "aggregate")
    g.add_edge("aggregate", "output")
    g.add_edge("output", END)

    return g.compile()
