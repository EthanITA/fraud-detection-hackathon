# %% imports
from __future__ import annotations

import json

from langchain.tools import tool

from ._types import (
    DRAIN_HIGH,
    DRAIN_MEDIUM,
    FIRST_LARGE_HIGH,
    FIRST_LARGE_MEDIUM,
    FIRST_LARGE_MIN_TXNS,
    MAD_CONSISTENCY,
    MAD_MULTIPLIER,
    OUTLIER_SIGMA,
    ROUND_NUMBER_MIN,
    STRUCTURING_PROXIMITY,
    RiskLevel,
    _STRUCTURING_LIMITS,
)


# %% check_amount_anomaly
@tool
def check_amount_anomaly(txn_json: str, profile_json: str) -> str:
    """
    Detect amount-based fraud signals.
      HIGH   — MAD outlier (modified Z-score > 3.5) or amount > avg + 3σ
      MEDIUM — round number ≥€1k, or within €200 below reporting limit (€5k/€10k/€15k)

    txn_json:     Transaction (needs: amount)
    profile_json: AccountProfile (needs: avg_amount, std_amount, median_amount, mad_amount)
    """
    txn = json.loads(txn_json)
    profile = json.loads(profile_json)
    amount = txn.get("amount", 0)
    avg = profile.get("avg_amount", 0)
    std = profile.get("std_amount", 0)
    median = profile.get("median_amount", 0)
    mad = profile.get("mad_amount", 0)

    # 1. MAD-based outlier (preferred — robust to skew and single-outlier masking)
    if mad > 0:
        modified_mad = MAD_CONSISTENCY * mad
        z = (amount - median) / modified_mad
        if z > MAD_MULTIPLIER:
            return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Amount {amount} is a MAD outlier (z={z:.1f}, median={median:.0f}, MAD={mad:.0f})"})

    # 2. 3σ fallback (when MAD unavailable — e.g. all prior amounts identical)
    if std > 0 and amount > avg + OUTLIER_SIGMA * std:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Amount {amount} exceeds {OUTLIER_SIGMA}σ above mean ({avg:.0f} + {OUTLIER_SIGMA}×{std:.0f})"})

    # 2. Round number
    is_round = amount >= ROUND_NUMBER_MIN and amount % 1000 == 0
    # 3. Structuring
    is_structuring = any(0 < (limit - amount) <= STRUCTURING_PROXIMITY for limit in _STRUCTURING_LIMITS)

    if is_round or is_structuring:
        reasons = []
        if is_round:
            reasons.append(f"round number ({amount})")
        if is_structuring:
            reasons.append(f"just below reporting limit")
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Suspicious amount pattern: {', '.join(reasons)}"})

    return json.dumps({"risk": RiskLevel.LOW, "reason": "Amount within normal range"})


# %% check_balance_drain
@tool
def check_balance_drain(txn_json: str, profile_json: str) -> str:
    """
    Detect near-total balance wipeout in a single transaction.
      HIGH   — drains >90% of sender balance
      MEDIUM — drains >70% of sender balance

    txn_json:     Transaction (needs: amount)
    profile_json: AccountProfile (needs: balance)
    """
    txn = json.loads(txn_json)
    profile = json.loads(profile_json)
    amount = txn.get("amount", 0)
    balance = profile.get("balance") or 0

    if balance <= 0:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "No positive balance to assess"})

    drain_ratio = amount / balance

    if drain_ratio > DRAIN_HIGH:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Transaction drains {drain_ratio:.0%} of account balance"})
    if drain_ratio > DRAIN_MEDIUM:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Transaction drains {drain_ratio:.0%} of account balance"})

    return json.dumps({"risk": RiskLevel.LOW, "reason": "Balance drain within normal range"})


# %% check_first_large
@tool
def check_first_large(txn_json: str, profile_json: str) -> str:
    """
    Flag an account's first-ever unusually large transaction.
      HIGH   — amount >5× historical max AND ≥6 prior txns
      MEDIUM — amount >3× historical max

    txn_json:     Transaction (needs: amount)
    profile_json: AccountProfile (needs: max_amount, txn_count)
    """
    txn = json.loads(txn_json)
    profile = json.loads(profile_json)
    amount = txn.get("amount", 0)
    max_amount = profile.get("max_amount", 0)
    txn_count = profile.get("txn_count", 0)

    if max_amount <= 0 or txn_count < 2:
        return json.dumps({"risk": RiskLevel.LOW, "reason": "Insufficient transaction history"})

    ratio = amount / max_amount

    if ratio > FIRST_LARGE_HIGH and txn_count > FIRST_LARGE_MIN_TXNS:
        return json.dumps({"risk": RiskLevel.HIGH, "reason": f"Amount is {ratio:.1f}x the historical max with {txn_count} prior transactions"})
    if ratio > FIRST_LARGE_MEDIUM:
        return json.dumps({"risk": RiskLevel.MEDIUM, "reason": f"Amount is {ratio:.1f}x the historical max"})

    return json.dumps({"risk": RiskLevel.LOW, "reason": "Amount consistent with transaction history"})
