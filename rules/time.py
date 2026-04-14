# %% imports
from __future__ import annotations

import json

from langchain.tools import tool

from ._types import RiskLevel


# %% check_velocity
@tool
def check_velocity(txn_json: str, history_json: str) -> str:
    """
    Detect anomalous transaction burst rate for the sender.
      HIGH   — avg gap between recent txns < 60s
      MEDIUM — avg gap < 300s

    txn_json:     Transaction (needs: timestamp)
    history_json: list[Transaction] — last 20 from same sender
    """
    # TODO: parse txn_json/history_json, compute avg gap between recent txns,
    #   HIGH if avg_gap < VELOCITY_HIGH_GAP, MEDIUM if < VELOCITY_MEDIUM_GAP
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


# %% check_temporal_pattern
@tool
def check_temporal_pattern(txn_json: str) -> str:
    """
    Flag off-hours activity (00:00–05:00 UTC) as medium risk.
      MEDIUM — transaction hour in [0, 5)

    txn_json: Transaction (needs: timestamp — Unix epoch)
    """
    # TODO: parse txn_json, extract hour from timestamp (UTC),
    #   MEDIUM if hour in [OFF_HOURS_START, OFF_HOURS_END)
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


# %% check_card_testing
@tool
def check_card_testing(txn_json: str, history_json: str) -> str:
    """
    Detect card-testing pattern: rapid micro-transactions (< €10) immediately
    preceding a large transaction.
      HIGH   — 3+ micro-txns in last 5 min followed by current large txn (> €500)
      MEDIUM — 1–2 micro-txns before a large txn

    txn_json:     Transaction (needs: amount, timestamp)
    history_json: list[Transaction] — last 20 from same sender
    """
    # TODO: parse txn_json/history_json, count micro-txns (< CARD_TEST_MICRO_LIMIT)
    #   in last CARD_TEST_WINDOW seconds. HIGH if count >= CARD_TEST_HIGH_COUNT
    #   and current amount > CARD_TEST_LARGE_LIMIT, MEDIUM if 1-2 micro-txns
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})
