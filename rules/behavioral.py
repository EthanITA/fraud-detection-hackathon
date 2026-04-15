# %% imports
from __future__ import annotations

import json

from langchain.tools import tool

from ._types import (
    DORMANT_HIGH_DAYS,
    DORMANT_MEDIUM_DAYS,
    FREQUENCY_SHIFT_HIGH,
    FREQUENCY_SHIFT_MEDIUM,
    NEW_PAYEE_HIGH_AMOUNT,
    NEW_PAYEE_MEDIUM_AMOUNT,
    RiskLevel,
)


# %% check_new_payee
@tool
def check_new_payee(txn_json: str, profile_json: str) -> str:
    """
    Detect a large transaction sent to a counterparty never seen before.
      HIGH   — unknown receiver AND amount >€1,000
      MEDIUM — unknown receiver AND amount >€200

    txn_json:     Transaction (needs: receiver_id, amount)
    profile_json: AccountProfile (needs: known_counterparties: list[str])
    """
    txn = json.loads(txn_json)
    profile = json.loads(profile_json)
    receiver_id = txn.get("receiver_id")
    amount = txn.get("amount", 0)
    known = profile.get("known_counterparties", [])

    if not receiver_id or receiver_id in known:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "Known payee."})

    if amount > NEW_PAYEE_HIGH_AMOUNT:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"New payee with large amount (€{amount})."})
    if amount > NEW_PAYEE_MEDIUM_AMOUNT:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"New payee with moderate amount (€{amount})."})
    return json.dumps({"risk": RiskLevel.LOW, "reason": "New payee but small amount."})


# %% check_dormant_reactivation
@tool
def check_dormant_reactivation(txn_json: str, profile_json: str) -> str:
    """
    Flag an account that was silent for a long period and suddenly transacts.
      HIGH   — inactive >180 days AND amount > account average
      MEDIUM — inactive >90 days

    txn_json:     Transaction (needs: timestamp)
    profile_json: AccountProfile (needs: last_seen — Unix epoch)
    """
    txn = json.loads(txn_json)
    profile = json.loads(profile_json)
    last_seen = profile.get("last_seen", 0)

    if not last_seen:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No last_seen data to determine dormancy."})

    timestamp = txn.get("timestamp", 0)
    amount = txn.get("amount", 0)
    avg_amount = profile.get("avg_amount", 0)
    days_inactive = (timestamp - last_seen) / 86400

    if days_inactive > DORMANT_HIGH_DAYS and amount > avg_amount:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Dormant {int(days_inactive)}d, amount exceeds average."})
    if days_inactive > DORMANT_MEDIUM_DAYS:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Dormant {int(days_inactive)}d, reactivated."})
    return json.dumps({"risk": RiskLevel.LOW, "reason": "Account not dormant."})


# %% check_frequency_shift
@tool
def check_frequency_shift(txn_json: str, history_json: str, profile_json: str) -> str:
    """
    Detect a sudden spike in transaction rate vs. the account's historical baseline.
      HIGH   — recent rate (last 1h) >10× baseline rate
      MEDIUM — recent rate >5× baseline rate

    txn_json:     Transaction (needs: timestamp)
    history_json: list[Transaction] — last 20 from same sender
    profile_json: AccountProfile (needs: avg_time_between_txns)
    """
    txn = json.loads(txn_json)
    history = json.loads(history_json) if history_json else []
    profile = json.loads(profile_json)

    avg_time = profile.get("avg_time_between_txns", 0)
    if avg_time <= 0:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No baseline frequency data."})

    ts = txn.get("timestamp", 0)
    cutoff = ts - 3600
    # Only count history txns in the 1h window BEFORE the current txn (not future or self)
    recent_count = sum(
        1 for h in history
        if cutoff < h.get("timestamp", 0) < ts
    )

    if recent_count == 0:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No recent transactions in last hour."})

    recent_rate = recent_count  # txns per hour
    baseline_rate = 3600 / avg_time
    if baseline_rate <= 0:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "Invalid baseline rate."})

    rate_multiplier = recent_rate / baseline_rate

    if rate_multiplier > FREQUENCY_SHIFT_HIGH:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Frequency spike: {rate_multiplier:.1f}x baseline."})
    if rate_multiplier > FREQUENCY_SHIFT_MEDIUM:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Elevated frequency: {rate_multiplier:.1f}x baseline."})
    return json.dumps({"risk": RiskLevel.LOW, "reason": "Transaction frequency within normal range."})
