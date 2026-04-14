from __future__ import annotations

from langgraph.graph import END, StateGraph

from .nodes import (
    aggregate,
    collect_output,
    ingest,
    run_rules,
    run_specialists,
    should_run_specialists,
    triage,
)
from .state import PipelineState


def build_pipeline():
    g = StateGraph(PipelineState)

    g.add_node("ingest", ingest)
    g.add_node("run_rules", run_rules)
    g.add_node("triage", triage)
    g.add_node("specialists", run_specialists)
    g.add_node("aggregate", aggregate)
    g.add_node("output", collect_output)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "run_rules")
    g.add_edge("run_rules", "triage")
    g.add_conditional_edges(
        "triage",
        should_run_specialists,
        {"specialists": "specialists", "output": "output"},
    )
    g.add_edge("specialists", "aggregate")
    g.add_edge("aggregate", "output")
    g.add_edge("output", END)

    return g.compile()
