#%% imports & shared types
from __future__ import annotations
import json
from typing import TypedDict
from enum import Enum

from langchain.tools import tool


class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskResult(TypedDict):
    risk: RiskLevel
    reason: str


class CompositeResult(TypedDict):
    score: int          # 0–10
    risk_level: RiskLevel
    summary: str


_RISK_SCORES: dict[RiskLevel, int] = {RiskLevel.HIGH: 3, RiskLevel.MEDIUM: 1, RiskLevel.LOW: 0}

# Reporting limits — amounts just below these are structuring signals
_STRUCTURING_LIMITS = [5_000, 10_000, 15_000]


#%% ── TIME SIGNALS ────────────────────────────────────────────────────────────

@tool
def check_velocity(txn_json: str, history_json: str) -> str:
    """
    Detect anomalous transaction burst rate for the sender.
      HIGH   — avg gap between recent txns < 60s
      MEDIUM — avg gap < 300s

    txn_json:     Transaction (needs: timestamp)
    history_json: list[Transaction] — last 20 from same sender
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


@tool
def check_temporal_pattern(txn_json: str) -> str:
    """
    Flag off-hours activity (00:00–05:00 UTC) as medium risk.
      MEDIUM — transaction hour in [0, 5)

    txn_json: Transaction (needs: timestamp — Unix epoch)
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


@tool
def check_card_testing(txn_json: str, history_json: str) -> str:
    """
    Detect card-testing pattern: a sequence of rapid micro-transactions
    (< €10) immediately preceding a large transaction.
      HIGH   — 3+ micro-txns in last 5 min followed by current large txn (> €500)
      MEDIUM — 1–2 micro-txns before a large txn

    txn_json:     Transaction (needs: amount, timestamp)
    history_json: list[Transaction] — last 20 from same sender
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


#%% ── AMOUNT SIGNALS ──────────────────────────────────────────────────────────

@tool
def check_amount_anomaly(txn_json: str, profile_json: str) -> str:
    """
    Detect amount-based fraud signals.
      HIGH   — amount > avg + 3σ (statistical outlier)
      HIGH   — round number > €1k (e.g. €5,000.00)
      MEDIUM — amount within €200 below a reporting limit (structuring)

    txn_json:    Transaction (needs: amount)
    profile_json: AccountProfile (needs: avg_amount, std_amount)
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


@tool
def check_balance_drain(txn_json: str, profile_json: str) -> str:
    """
    Detect near-total balance wipeout.
      HIGH   — txn drains > 90% of sender balance
      MEDIUM — txn drains > 70% of sender balance

    txn_json:     Transaction (needs: amount)
    profile_json: AccountProfile (needs: balance)
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


@tool
def check_first_large(txn_json: str, profile_json: str) -> str:
    """
    Flag an account's first-ever unusually large transaction.
      HIGH   — amount > 5× profile.max_amount AND txn_count > 5
               (enough history to establish a baseline, then sudden spike)
      MEDIUM — amount > 3× profile.max_amount

    txn_json:     Transaction (needs: amount)
    profile_json: AccountProfile (needs: max_amount, txn_count)
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


#%% ── BEHAVIORAL SIGNALS ──────────────────────────────────────────────────────

@tool
def check_new_payee(txn_json: str, profile_json: str) -> str:
    """
    Detect a large transaction sent to a counterparty never seen before.
      HIGH   — receiver not in profile.known_counterparties AND amount > €1k
      MEDIUM — receiver not in known_counterparties AND amount > €200

    txn_json:     Transaction (needs: receiver_id, amount)
    profile_json: AccountProfile (needs: known_counterparties: list[str])
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


@tool
def check_dormant_reactivation(txn_json: str, profile_json: str) -> str:
    """
    Flag an account that was silent for a long period and suddenly transacts.
      HIGH   — days since last txn > 180 AND amount > profile.avg_amount
      MEDIUM — days since last txn > 90

    txn_json:     Transaction (needs: timestamp)
    profile_json: AccountProfile (needs: last_seen — Unix epoch)
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


@tool
def check_frequency_shift(txn_json: str, history_json: str, profile_json: str) -> str:
    """
    Detect a sudden spike in transaction rate vs. the account's historical baseline.
      HIGH   — recent rate (last 1h) > 10× profile.avg_time_between_txns baseline
      MEDIUM — recent rate > 5× baseline

    txn_json:     Transaction (needs: timestamp)
    history_json: list[Transaction] — last 20 from same sender
    profile_json: AccountProfile (needs: avg_time_between_txns)
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


#%% ── GRAPH FLOW SIGNALS ──────────────────────────────────────────────────────

@tool
def check_fan_in(txn_json: str, graph_json: str) -> str:
    """
    Detect a money-mule aggregation node: many distinct senders converging
    on one receiver account.
      HIGH   — receiver.in_degree > 10
      MEDIUM — receiver.in_degree > 5

    txn_json:  Transaction (needs: receiver_id)
    graph_json: subgraph {nodes: [{id, in_degree, ...}], edges: [...]}
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


@tool
def check_fan_out(txn_json: str, graph_json: str) -> str:
    """
    Detect rapid distribution from one account to many recipients
    (money-mule payout node).
      HIGH   — sender.out_degree > 10 in last 24h
      MEDIUM — sender.out_degree > 5

    txn_json:   Transaction (needs: sender_id)
    graph_json: subgraph {nodes: [{id, out_degree, ...}], edges: [...]}
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


@tool
def check_mule_chain(txn_json: str, graph_json: str) -> str:
    """
    Detect a mule-chain hop: A→B→C where the intermediate node B
    forwarded funds within a short window after receiving them.
      HIGH   — receiver forwarded ≥ 70% of received amount within 30 min
      MEDIUM — receiver forwarded ≥ 50% within 2h

    txn_json:   Transaction (needs: receiver_id, amount, timestamp)
    graph_json: 2-hop subgraph with edge timestamps and amounts
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


@tool
def check_circular_flow(txn_json: str, graph_json: str) -> str:
    """
    Detect circular money flow where funds eventually return to the origin
    account (wash trading / network testing).
      HIGH   — a path from receiver back to sender exists within 3 hops

    txn_json:   Transaction (needs: sender_id, receiver_id)
    graph_json: 3-hop subgraph as adjacency list
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


#%% ── AGGREGATOR (pure Python, not a LangChain tool) ─────────────────────────

def compute_composite_risk(results: list[RiskResult]) -> CompositeResult:
    """
    Aggregate rule results into a 0–10 composite score.
    high=3, medium=1, low=0.
    Triage: score ≤1 → auto-legit · score ≥6 → auto-fraud · 2–5 → Layer 2
    """
    score = min(sum(_RISK_SCORES[RiskLevel(r["risk"])] for r in results), 10)
    summary = " | ".join(r["reason"] for r in results if r["risk"] != RiskLevel.LOW)

    if score >= 6:
        risk_level = RiskLevel.HIGH
    elif score >= 2:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    return {"score": score, "risk_level": risk_level, "summary": summary or "no signals"}


#%% ── TOOL REGISTRY (bind to agent) ──────────────────────────────────────────

RULE_TOOLS = [
    # time
    check_velocity,
    check_temporal_pattern,
    check_card_testing,
    # amount
    check_amount_anomaly,
    check_balance_drain,
    check_first_large,
    # behavioral
    check_new_payee,
    check_dormant_reactivation,
    check_frequency_shift,
    # graph flow
    check_fan_in,
    check_fan_out,
    check_mule_chain,
    check_circular_flow,
]
