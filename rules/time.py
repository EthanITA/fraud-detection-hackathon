# %% imports
from __future__ import annotations

import json
from datetime import datetime, timezone

from langchain.tools import tool

from ._types import (
    CARD_TEST_HIGH_COUNT,
    CARD_TEST_LARGE_LIMIT,
    CARD_TEST_MICRO_LIMIT,
    CARD_TEST_WINDOW,
    OFF_HOURS_END,
    OFF_HOURS_START,
    VELOCITY_HIGH_GAP,
    VELOCITY_MEDIUM_GAP,
    RiskLevel,
)


# %% check_velocity
@tool
def check_velocity(txn_json: str, history_json: str) -> str:
    """
    Detect anomalous transaction burst rate for the sender.
      HIGH   — avg gap < 60s (VELOCITY_HIGH_GAP)
      MEDIUM — avg gap < 5min (VELOCITY_MEDIUM_GAP=300s)

    txn_json:     Transaction (needs: timestamp)
    history_json: list[Transaction] — last 20 from same sender
    """
    history = json.loads(history_json)
    if len(history) < 2:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "Not enough history to compute velocity."})

    timestamps = sorted(t["timestamp"] for t in history)
    gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    avg_gap = sum(gaps) / len(gaps)

    if avg_gap < VELOCITY_HIGH_GAP:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Avg gap {avg_gap:.0f}s between recent txns indicates burst activity."})
    if avg_gap < VELOCITY_MEDIUM_GAP:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Avg gap {avg_gap:.0f}s between recent txns is elevated."})
    return json.dumps({"risk": RiskLevel.LOW, "reason": "Transaction velocity is within normal range."})


# %% check_temporal_pattern
@tool
def check_temporal_pattern(txn_json: str) -> str:
    """
    Flag off-hours activity as medium risk.
      MEDIUM — transaction hour in [0:00, 7:00) UTC

    txn_json: Transaction (needs: timestamp — Unix epoch)
    """
    txn = json.loads(txn_json)
    hour = datetime.fromtimestamp(txn["timestamp"], tz=timezone.utc).hour

    if OFF_HOURS_START <= hour < OFF_HOURS_END:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Transaction at {hour}:00 UTC falls in off-hours window."})
    return json.dumps({"risk": RiskLevel.LOW, "reason": "Transaction occurred during normal hours."})


# %% check_card_testing
@tool
def check_card_testing(txn_json: str, history_json: str) -> str:
    """
    Detect card-testing pattern: rapid micro-transactions preceding a large one.
      HIGH   — ≥3 micro-txns (<€5) in last 5min before a large txn (>€500)
      MEDIUM — 1–2 micro-txns before a large txn

    txn_json:     Transaction (needs: amount, timestamp)
    history_json: list[Transaction] — last 20 from same sender
    """
    txn = json.loads(txn_json)
    history = json.loads(history_json)

    if txn.get("amount", 0) < CARD_TEST_MICRO_LIMIT:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "Current transaction is itself a micro-transaction."})

    ts = txn["timestamp"]
    micro_count = sum(
        1 for h in history
        if h.get("amount", 0) < CARD_TEST_MICRO_LIMIT and 0 < ts - h["timestamp"] <= CARD_TEST_WINDOW
    )

    is_large = txn.get("amount", 0) > CARD_TEST_LARGE_LIMIT

    if micro_count >= CARD_TEST_HIGH_COUNT and is_large:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"{micro_count} micro-txns in last {CARD_TEST_WINDOW}s before a large transaction — card-testing pattern."})
    if micro_count >= 1 and is_large:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"{micro_count} micro-txn(s) preceding a large transaction."})
    return json.dumps({"risk": RiskLevel.LOW, "reason": "No card-testing pattern detected."})
