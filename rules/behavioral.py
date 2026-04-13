from __future__ import annotations

import json

from langchain.tools import tool

from ._types import RiskLevel


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
      HIGH   — recent rate (last 1h) > 10× profile.avg_time_between_txns
      MEDIUM — recent rate > 5× baseline

    txn_json:     Transaction (needs: timestamp)
    history_json: list[Transaction] — last 20 from same sender
    profile_json: AccountProfile (needs: avg_time_between_txns)
    """
    return json.dumps({"risk": RiskLevel.LOW, "reason": "TODO"})
