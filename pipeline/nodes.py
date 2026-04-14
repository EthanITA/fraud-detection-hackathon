from __future__ import annotations

import json

from data import (
    build_relationship_graph,
    compute_account_profiles,
    get_account_context,
    parse_dataset,
)
from rules import RULE_TOOLS, compute_composite_risk

from .dispatch import invoke_tool
from .state import PipelineState


# ── Layer 0 ───────────────────────────────────────────────────────────────────

def ingest(state: PipelineState) -> dict:
    txns = parse_dataset(state["dataset_path"])
    profiles = compute_account_profiles(txns)
    graph = build_relationship_graph(txns)
    return {"transactions": txns, "profiles": profiles, "graph": graph}


# ── Layer 1 ───────────────────────────────────────────────────────────────────

def run_rules(state: PipelineState) -> dict:
    all_results = {}

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
        all_results[txn["id"]] = [
            (tool.name, invoke_tool(tool, context)) for tool in RULE_TOOLS
        ]

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


# ── Layer 2 ───────────────────────────────────────────────────────────────────

def run_specialists(state: PipelineState) -> dict:
    # TODO: 3 parallel LLM agents (velocity, amount, relationship)
    return {"specialist_results": {}}


# ── Layer 3 ───────────────────────────────────────────────────────────────────

def aggregate(state: PipelineState) -> dict:
    # TODO: LLM aggregator with economic weighting
    return {"verdicts": {}}


# ── Output ────────────────────────────────────────────────────────────────────

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
