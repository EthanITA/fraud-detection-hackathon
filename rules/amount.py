from __future__ import annotations

import json

from langchain.tools import tool

from ._types import RiskLevel


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
      MEDIUM — amount > 3× profile.max_amount

    txn_json:     Transaction (needs: amount)
    profile_json: AccountProfile (needs: max_amount, txn_count)
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})
