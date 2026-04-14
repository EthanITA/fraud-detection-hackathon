"""
Fraud detection pipeline — LangGraph state machine.

Layer 0: Ingest → parse dataset, compute profiles, build graph
Layer 1: Rules  → run 13 deterministic tools, triage by composite score
Layer 2: Specialists → 3 parallel LLM agents (velocity, amount, relationship)
Layer 3: Aggregator  → final verdict with economic weighting
"""

from __future__ import annotations

import json
import sys
from typing import TypedDict

from langgraph.graph import END, StateGraph

from data import (
    build_relationship_graph,
    compute_account_profiles,
    get_account_context,
    parse_dataset,
)
from rules import RULE_TOOLS, compute_composite_risk
from rules._types import RiskResult


# ── State ─────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict, total=False):
    dataset_path: str
    transactions: list[dict]
    profiles: dict
    graph: dict
    rule_results: dict          # txn_id → [(tool_name, RiskResult)]
    auto_legit: list[str]
    auto_fraud: list[str]
    ambiguous: list[str]
    specialist_results: dict    # txn_id → [specialist outputs]
    verdicts: dict              # txn_id → {is_fraud, confidence, reasoning}
    fraud_ids: list[str]


# ── Tool dispatch ─────────────────────────────────────────────────────────────
# Maps each tool.name to the context keys it needs.
# Keys are resolved to f"{key}_json" parameter names at call time.

_TOOL_CONTEXT: dict[str, tuple[str, ...]] = {
    "check_velocity":             ("txn", "history"),
    "check_temporal_pattern":     ("txn",),
    "check_card_testing":         ("txn", "history"),
    "check_amount_anomaly":       ("txn", "profile"),
    "check_balance_drain":        ("txn", "profile"),
    "check_first_large":          ("txn", "profile"),
    "check_new_payee":            ("txn", "profile"),
    "check_dormant_reactivation": ("txn", "profile"),
    "check_frequency_shift":      ("txn", "history", "profile"),
    "check_fan_in":               ("txn", "graph"),
    "check_fan_out":              ("txn", "graph"),
    "check_mule_chain":           ("txn", "graph"),
    "check_circular_flow":        ("txn", "graph"),
}


def _invoke_tool(tool, context: dict[str, str]) -> RiskResult:
    keys = _TOOL_CONTEXT[tool.name]
    args = {f"{k}_json": context[k] for k in keys}
    return json.loads(tool.invoke(args))


# ── Layer 0: Ingest ───────────────────────────────────────────────────────────

def ingest(state: PipelineState) -> dict:
    txns = parse_dataset(state["dataset_path"])
    profiles = compute_account_profiles(txns)
    graph = build_relationship_graph(txns)
    return {"transactions": txns, "profiles": profiles, "graph": graph}


# ── Layer 1: Run all rule tools + triage ──────────────────────────────────────

def run_rules(state: PipelineState) -> dict:
    all_results: dict[str, list[tuple[str, RiskResult]]] = {}

    for txn in state["transactions"]:
        sender_id = txn["sender_id"]

        context = {
            "txn": json.dumps(txn),
            "history": json.dumps(
                get_account_context(sender_id, state["transactions"])
            ),
            "profile": json.dumps(state["profiles"].get(sender_id, {})),
            "graph": json.dumps(state["graph"]),
        }

        txn_results = [(tool.name, _invoke_tool(tool, context)) for tool in RULE_TOOLS]
        all_results[txn["id"]] = txn_results

    return {"rule_results": all_results}


def triage(state: PipelineState) -> dict:
    auto_legit, auto_fraud, ambiguous = [], [], []

    for txn in state["transactions"]:
        txn_id = txn["id"]
        composite = compute_composite_risk(
            state["rule_results"][txn_id], txn["amount"]
        )

        if composite["auto_fraud"]:
            auto_fraud.append(txn_id)
        elif composite["auto_legit"]:
            auto_legit.append(txn_id)
        else:
            ambiguous.append(txn_id)

    return {"auto_legit": auto_legit, "auto_fraud": auto_fraud, "ambiguous": ambiguous}


# ── Layer 2: Specialist agents ────────────────────────────────────────────────

def run_specialists(state: PipelineState) -> dict:
    # TODO: 3 parallel LLM agents (velocity, amount, relationship)
    # Each returns {risk_level, confidence, patterns_detected, reasoning}
    return {"specialist_results": {}}


# ── Layer 3: Aggregator ───────────────────────────────────────────────────────

def aggregate(state: PipelineState) -> dict:
    # TODO: LLM aggregator with economic weighting + pattern combos
    # Returns {transaction_id, is_fraud, confidence, reasoning}
    return {"verdicts": {}}


# ── Output collector ──────────────────────────────────────────────────────────

def collect_output(state: PipelineState) -> dict:
    fraud_ids = list(state.get("auto_fraud", []))
    for txn_id, verdict in state.get("verdicts", {}).items():
        if verdict.get("is_fraud"):
            fraud_ids.append(txn_id)
    return {"fraud_ids": sorted(set(fraud_ids))}


# ── Routing ───────────────────────────────────────────────────────────────────

def should_run_specialists(state: PipelineState) -> str:
    if state.get("ambiguous"):
        return "specialists"
    return "output"


# ── Graph ─────────────────────────────────────────────────────────────────────

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


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pipeline = build_pipeline()
    result = pipeline.invoke({"dataset_path": sys.argv[1]})

    with open("output.txt", "w") as f:
        for txn_id in result["fraud_ids"]:
            f.write(f"{txn_id}\n")

    print(f"Found {len(result['fraud_ids'])} fraudulent transactions")
