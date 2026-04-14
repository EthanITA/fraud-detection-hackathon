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


# -- Layer 0 ------------------------------------------------------------------

def ingest(state: PipelineState) -> dict:
    txns = parse_dataset(state["dataset_path"])
    profiles = compute_account_profiles(txns)
    graph = build_relationship_graph(txns)
    return {"transactions": txns, "profiles": profiles, "graph": graph}


# -- Layer 1 ------------------------------------------------------------------

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
    auto_legit, auto_fraud = [], []
    ambiguous_scored: list[tuple[str, float, float]] = []

    for txn in state["transactions"]:
        txn_id = txn["id"]
        composite = compute_composite_risk(
            state["rule_results"][txn_id], txn["amount"]
        )

        if composite["combo_triggered"] is not None:
            auto_fraud.append(txn_id)
        elif composite["auto_fraud"]:
            auto_fraud.append(txn_id)
        elif composite["auto_legit"]:
            auto_legit.append(txn_id)
        else:
            ambiguous_scored.append((txn_id, composite["score"], txn["amount"]))

    # Priority ranking: score * amount descending (expected-value heuristic)
    ambiguous_prioritized = sorted(
        [(txn_id, score * amount) for txn_id, score, amount in ambiguous_scored],
        key=lambda x: x[1],
        reverse=True,
    )

    # Budget check: estimate how many ambiguous txns we can afford
    budget = state.get("budget")
    if budget and budget.is_panic():
        ambiguous_prioritized = []
    elif budget:
        # TODO: estimate cost per txn and cap ambiguous_prioritized to top-N
        pass

    return {
        "auto_legit": auto_legit,
        "auto_fraud": auto_fraud,
        "ambiguous_prioritized": ambiguous_prioritized,
    }


# -- Layer 2 — Specialists (parallel via Send) --------------------------------

def velocity_specialist(state: PipelineState) -> dict:
    """Analyze ambiguous transactions for timing/velocity patterns."""
    raise NotImplementedError("velocity_specialist LLM agent")


def amount_specialist(state: PipelineState) -> dict:
    """Analyze ambiguous transactions for spending/amount patterns."""
    raise NotImplementedError("amount_specialist LLM agent")


def behavioral_specialist(state: PipelineState) -> dict:
    """Analyze ambiguous transactions for behavioral change patterns."""
    raise NotImplementedError("behavioral_specialist LLM agent")


def relationship_specialist(state: PipelineState) -> dict:
    """Analyze ambiguous transactions for network/relationship patterns."""
    raise NotImplementedError("relationship_specialist LLM agent")


# -- Layer 3 ------------------------------------------------------------------

def aggregate(state: PipelineState) -> dict:
    """Combine specialist opinions into final verdicts with economic weighting."""
    raise NotImplementedError("aggregate LLM node")


# -- Output --------------------------------------------------------------------

def collect_output(state: PipelineState) -> dict:
    fraud_ids = list(state.get("auto_fraud", []))

    for txn_id, verdict in state.get("verdicts", {}).items():
        if verdict.get("is_fraud"):
            fraud_ids.append(txn_id)

    # Budget fallback: ambiguous txns that never reached specialists
    specialist_txn_ids = set(state.get("specialist_results", {}).keys())
    for txn_id, _priority in state.get("ambiguous_prioritized", []):
        if txn_id not in specialist_txn_ids and txn_id not in fraud_ids:
            # TODO: rule-based fallback verdict for budget-skipped txns
            pass

    fraud_ids = sorted(set(fraud_ids))

    # TODO: build debug_output list[dict] with full per-txn trace
    debug_output: list[dict] = []

    return {"fraud_ids": fraud_ids, "debug_output": debug_output}
