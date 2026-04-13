#%% imports & shared types
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Literal, TypedDict

from langchain.tools import tool

RiskLevel = Literal["high", "medium", "low"]

class RiskResult(TypedDict):
    risk: RiskLevel
    reason: str

class CompositeResult(TypedDict):
    score: int          # 0–10
    risk_level: RiskLevel
    summary: str

_RISK_SCORES: dict[str, int] = {"high": 3, "medium": 1, "low": 0}

# Structuring thresholds: amounts just below reporting limits are suspicious
_STRUCTURING_THRESHOLDS = [4_999, 9_999, 14_999]

#%% check_velocity
@tool
def check_velocity(txn_json: str, history_json: str) -> str:
    """
    Detect anomalous transaction velocity for the sender.
    High: avg gap between recent txns < 60s.
    Medium: avg gap < 300s.

    txn_json: JSON-serialized Transaction (needs: timestamp)
    history_json: JSON-serialized list[Transaction] — last 20 from same sender
    Returns: JSON RiskResult
    """
    history = json.loads(history_json)

    if len(history) < 2:
        return json.dumps({"risk": "low", "reason": "insufficient history"})

    times = sorted(t["timestamp"] for t in history)
    gaps = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    avg_gap = sum(gaps) / len(gaps)

    if avg_gap < 60:
        return json.dumps({"risk": "high", "reason": f"burst: avg gap {avg_gap:.0f}s"})
    if avg_gap < 300:
        return json.dumps({"risk": "medium", "reason": f"high frequency: avg gap {avg_gap:.0f}s"})
    return json.dumps({"risk": "low", "reason": "normal velocity"})


#%% check_amount_anomaly
@tool
def check_amount_anomaly(txn_json: str, profile_json: str) -> str:
    """
    Detect amount-based fraud signals: statistical outlier, round number >€1k,
    or structuring near €5k / €10k / €15k reporting thresholds.

    txn_json: JSON-serialized Transaction (needs: amount)
    profile_json: JSON-serialized AccountProfile (needs: avg_amount, std_amount)
    Returns: JSON RiskResult
    """
    txn = json.loads(txn_json)
    profile = json.loads(profile_json)
    amount = txn["amount"]
    avg, std = profile["avg_amount"], profile["std_amount"]

    if std > 0 and amount > avg + 3 * std:
        return json.dumps({"risk": "high", "reason": f"outlier: €{amount} > avg+3σ (€{avg + 3 * std:.0f})"})
    if amount > 1_000 and amount % 100 == 0:
        return json.dumps({"risk": "high", "reason": f"suspiciously round: €{amount}"})
    if any(t - 200 <= amount <= t for t in _STRUCTURING_THRESHOLDS):
        return json.dumps({"risk": "medium", "reason": f"near reporting threshold: €{amount}"})
    return json.dumps({"risk": "low", "reason": "amount within normal range"})


#%% check_balance_drain
@tool
def check_balance_drain(txn_json: str, profile_json: str) -> str:
    """
    Detect balance drain: txn draining >90% of sender balance (high)
    or >70% (medium).

    txn_json: JSON-serialized Transaction (needs: amount)
    profile_json: JSON-serialized AccountProfile (needs: balance)
    Returns: JSON RiskResult
    """
    txn = json.loads(txn_json)
    profile = json.loads(profile_json)
    amount = txn["amount"]
    balance = profile.get("balance", 0)

    if balance <= 0:
        return json.dumps({"risk": "low", "reason": "balance unavailable"})

    ratio = amount / balance
    if ratio > 0.9:
        return json.dumps({"risk": "high", "reason": f"drains {ratio:.0%} of balance"})
    if ratio > 0.7:
        return json.dumps({"risk": "medium", "reason": f"drains {ratio:.0%} of balance"})
    return json.dumps({"risk": "low", "reason": f"drains {ratio:.0%} of balance"})


#%% check_counterparty
@tool
def check_counterparty(txn_json: str, graph_json: str) -> str:
    """
    Detect suspicious counterparty patterns:
    - New account receiving large amount (>€1k) → high
    - Receiver with high fan-in (many senders converging) → high

    txn_json: JSON-serialized Transaction (needs: receiver_id, amount)
    graph_json: JSON {nodes: [{id, is_new, in_degree, ...}], edges: [...]}
                — 2-hop subgraph from build_relationship_graph
    Returns: JSON RiskResult
    """
    txn = json.loads(txn_json)
    graph = json.loads(graph_json)
    receiver_id = txn["receiver_id"]
    amount = txn["amount"]

    receiver = next((n for n in graph["nodes"] if n["id"] == receiver_id), {})
    is_new = receiver.get("is_new", False)
    in_degree = receiver.get("in_degree", 0)

    if is_new and amount > 1_000:
        return json.dumps({"risk": "high", "reason": f"new account receives €{amount}"})
    if in_degree > 10:
        return json.dumps({"risk": "high", "reason": f"fan-in: {in_degree} senders → receiver"})
    return json.dumps({"risk": "low", "reason": "counterparty looks normal"})


#%% check_temporal_pattern
@tool
def check_temporal_pattern(txn_json: str) -> str:
    """
    Flag off-hours transactions (00:00–05:00 UTC) as medium risk.

    txn_json: JSON-serialized Transaction (needs: timestamp — Unix epoch)
    Returns: JSON RiskResult
    """
    txn = json.loads(txn_json)
    hour = datetime.fromtimestamp(txn["timestamp"], tz=timezone.utc).hour

    if 0 <= hour < 5:
        return json.dumps({"risk": "medium", "reason": f"off-hours: {hour:02d}:xx UTC"})
    return json.dumps({"risk": "low", "reason": "normal hours"})


#%% compute_composite_risk  (called in Python, not a LangChain tool)
def compute_composite_risk(results: list[RiskResult]) -> CompositeResult:
    """
    Aggregate 5 rule results into a 0–10 composite score.
    high=3, medium=1, low=0.
    Triage: score ≤1 → auto-legit · score ≥6 → auto-fraud · 2–5 → Layer 2
    """
    score = min(sum(_RISK_SCORES[r["risk"]] for r in results), 10)
    summary = " | ".join(r["reason"] for r in results if r["risk"] != "low")

    if score >= 6:
        risk_level: RiskLevel = "high"
    elif score >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {"score": score, "risk_level": risk_level, "summary": summary or "no signals"}


#%% all tools list (for agent binding)
RULE_TOOLS = [
    check_velocity,
    check_amount_anomaly,
    check_balance_drain,
    check_counterparty,
    check_temporal_pattern,
]
