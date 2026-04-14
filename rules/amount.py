# %% imports
from __future__ import annotations

import json

from langchain.tools import tool

from ._types import RiskLevel


# %% check_amount_anomaly
@tool
def check_amount_anomaly(txn_json: str, profile_json: str) -> str:
    """
    Detect amount-based fraud signals.
      HIGH   — amount > avg + 3σ (statistical outlier)
      HIGH   — round number > €1k (e.g. €5,000.00)
      MEDIUM — amount within €200 below a reporting limit (structuring)

    txn_json:     Transaction (needs: amount)
    profile_json: AccountProfile (needs: avg_amount, std_amount)
    """
    # TODO: parse txn_json/profile_json, check three signals:
    #   1. Statistical outlier: amount > avg + OUTLIER_SIGMA * std → HIGH
    #   2. Round number: amount >= ROUND_NUMBER_MIN and amount % 1000 == 0 → bump
    #   3. Structuring: amount within STRUCTURING_PROXIMITY below a _STRUCTURING_LIMITS entry → bump
    #   Return highest triggered level
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


# %% check_balance_drain
@tool
def check_balance_drain(txn_json: str, profile_json: str) -> str:
    """
    Detect near-total balance wipeout.
      HIGH   — txn drains > 90% of sender balance
      MEDIUM — txn drains > 70% of sender balance

    txn_json:     Transaction (needs: amount)
    profile_json: AccountProfile (needs: balance)
    """
    # TODO: parse txn_json/profile_json, compute drain_ratio = amount / balance,
    #   HIGH if drain_ratio > DRAIN_HIGH, MEDIUM if > DRAIN_MEDIUM
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})


# %% check_first_large
@tool
def check_first_large(txn_json: str, profile_json: str) -> str:
    """
    Flag an account's first-ever unusually large transaction.
      HIGH   — amount > 5× profile.max_amount AND txn_count > 5
      MEDIUM — amount > 3× profile.max_amount

    txn_json:     Transaction (needs: amount)
    profile_json: AccountProfile (needs: max_amount, txn_count)
    """
    # TODO: parse txn_json/profile_json, compute ratio = amount / max_amount,
    #   HIGH if ratio > FIRST_LARGE_HIGH and txn_count > FIRST_LARGE_MIN_TXNS,
    #   MEDIUM if ratio > FIRST_LARGE_MEDIUM
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})
