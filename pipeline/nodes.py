# %% imports
from __future__ import annotations

import json

from data import (
    build_relationship_graph,
    compute_account_profiles,
    get_account_context,
    parse_dataset,
)
from config.models import (
    AGGREGATOR_MODEL,
    COST_PER_1K_TOKENS,
    MAX_TOKENS_AGGREGATOR,
    MAX_TOKENS_SPECIALIST,
    SPECIALIST_MODEL,
)
from agents.aggregator import run_aggregator
from agents.specialists import (
    run_amount_specialist,
    run_behavioral_specialist,
    run_relationship_specialist,
    run_velocity_specialist,
)
from rules import RULE_TOOLS, compute_composite_risk
from .dispatch import invoke_tool
from .state import PipelineState


# %% ingest
def ingest(state: PipelineState) -> dict:
    txns = parse_dataset(state["dataset_path"])
    profiles = compute_account_profiles(txns)
    graph = build_relationship_graph(txns)
    return {"transactions": txns, "profiles": profiles, "graph": graph}


# %% run_rules
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


# %% triage
def triage(state: PipelineState) -> dict:
    auto_legit, auto_fraud = [], []
    ambiguous_scored: list[tuple[str, float, float]] = []

    for txn in state["transactions"]:
        txn_id = txn["id"]
        composite = compute_composite_risk(state["rule_results"][txn_id], txn["amount"])

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
        specialist_rate = COST_PER_1K_TOKENS[SPECIALIST_MODEL]
        aggregator_rate = COST_PER_1K_TOKENS[AGGREGATOR_MODEL]
        cost_per_txn = (4 * MAX_TOKENS_SPECIALIST * specialist_rate + MAX_TOKENS_AGGREGATOR * aggregator_rate) / 1000
        if cost_per_txn > 0:
            max_txns = int(budget.remaining() / cost_per_txn)
            ambiguous_prioritized = ambiguous_prioritized[:max_txns]

    return {
        "auto_legit": auto_legit,
        "auto_fraud": auto_fraud,
        "ambiguous_prioritized": ambiguous_prioritized,
    }


# %% velocity_specialist
def velocity_specialist(state: PipelineState) -> dict:
    """Analyze ambiguous transactions for timing/velocity patterns."""
    return run_velocity_specialist(state)


# %% amount_specialist
def amount_specialist(state: PipelineState) -> dict:
    """Analyze ambiguous transactions for spending/amount patterns."""
    return run_amount_specialist(state)


# %% behavioral_specialist
def behavioral_specialist(state: PipelineState) -> dict:
    """Analyze ambiguous transactions for behavioral change patterns."""
    return run_behavioral_specialist(state)


# %% relationship_specialist
def relationship_specialist(state: PipelineState) -> dict:
    """Analyze ambiguous transactions for network/relationship patterns."""
    return run_relationship_specialist(state)


# %% aggregate
def aggregate(state: PipelineState) -> dict:
    """Combine specialist opinions into final verdicts with economic weighting."""
    return run_aggregator(state)


# %% collect_output
def collect_output(state: PipelineState) -> dict:
    fraud_ids = list(state.get("auto_fraud", []))

    for txn_id, verdict in state.get("verdicts", {}).items():
        if verdict.get("is_fraud"):
            fraud_ids.append(txn_id)

    # Budget fallback: ambiguous txns that never reached specialists
    specialist_txn_ids = set(state.get("specialist_results", {}).keys())
    txn_by_id = {txn["id"]: txn for txn in state.get("transactions", [])}
    for txn_id, _priority in state.get("ambiguous_prioritized", []):
        if txn_id not in specialist_txn_ids and txn_id not in fraud_ids:
            rule_results = state.get("rule_results", {}).get(txn_id)
            txn = txn_by_id.get(txn_id)
            if rule_results and txn:
                composite = compute_composite_risk(rule_results, txn["amount"])
                if composite["auto_fraud"] or composite["combo_triggered"]:
                    fraud_ids.append(txn_id)

    fraud_ids = sorted(set(fraud_ids))

    ambiguous_rank = {
        txn_id: rank
        for rank, (txn_id, _) in enumerate(state.get("ambiguous_prioritized", []), 1)
    }
    auto_legit_set = set(state.get("auto_legit", []))
    auto_fraud_set = set(state.get("auto_fraud", []))
    fraud_set = set(fraud_ids)

    debug_output: list[dict] = []
    for txn in state.get("transactions", []):
        txn_id = txn["id"]
        rule_results = state.get("rule_results", {}).get(txn_id)
        composite = compute_composite_risk(rule_results, txn["amount"]) if rule_results else None

        if txn_id in auto_fraud_set:
            triage_decision = "auto_fraud"
        elif txn_id in auto_legit_set:
            triage_decision = "auto_legit"
        else:
            triage_decision = "ambiguous"

        debug_output.append({
            "txn_id": txn_id,
            "amount": txn["amount"],
            "triage": triage_decision,
            "rule_summary": composite["summary"] if composite else "no rules",
            "priority_rank": ambiguous_rank.get(txn_id),
            "specialist_results": state.get("specialist_results", {}).get(txn_id),
            "verdict": state.get("verdicts", {}).get(txn_id),
            "final": "fraud" if txn_id in fraud_set else "legit",
        })

    return {"fraud_ids": fraud_ids, "debug_output": debug_output}
