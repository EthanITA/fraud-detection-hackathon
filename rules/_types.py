from __future__ import annotations

from enum import Enum
from typing import TypedDict


class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskResult(TypedDict):
    risk: RiskLevel
    reason: str


class CompositeResult(TypedDict):
    score: float
    risk_level: RiskLevel
    summary: str
    auto_legit: bool
    auto_fraud: bool
    combo_triggered: str | None


_RISK_SCORES: dict[RiskLevel, int] = {
    RiskLevel.HIGH: 3,
    RiskLevel.MEDIUM: 1,
    RiskLevel.LOW: 0,
}

# Reporting limits — amounts just below these are structuring signals
_STRUCTURING_LIMITS = [5_000, 10_000, 15_000]

# ── Tool weights ──────────────────────────────────────────────────────────────
# Graph/mule signals are harder to fake and more indicative → higher weight.
# Temporal alone is weak (legitimate users travel, work late) → lower weight.

TOOL_WEIGHTS: dict[str, float] = {
    # time
    "check_velocity": 1.0,
    "check_temporal_pattern": 0.5,
    "check_card_testing": 1.5,
    # amount
    "check_amount_anomaly": 1.0,
    "check_balance_drain": 1.5,
    "check_first_large": 1.0,
    # behavioral
    "check_new_payee": 1.0,
    "check_dormant_reactivation": 1.0,
    "check_frequency_shift": 1.0,
    # graph flow
    "check_fan_in": 1.5,
    "check_fan_out": 1.5,
    "check_mule_chain": 2.0,
    "check_circular_flow": 2.0,
}

# ── Always-flag combos ────────────────────────────────────────────────────────
# If ALL tools in a combo set fire HIGH → auto-fraud, regardless of score.

ALWAYS_FLAG_COMBOS: list[tuple[str, set[str]]] = [
    ("BURST+BALANCE_DRAIN", {"check_velocity", "check_balance_drain"}),
    ("NEW_PAYEE+AMOUNT_ANOMALY", {"check_new_payee", "check_amount_anomaly"}),
    ("MULE_CHAIN+STRUCTURING", {"check_mule_chain", "check_amount_anomaly"}),
]

# ── Amount-aware triage thresholds ────────────────────────────────────────────
# (amount_floor, legit_ceiling, fraud_floor)
# Checked top-down: first match wins.
#   legit_ceiling: weighted score ≤ this → auto-legit
#   fraud_floor:   weighted score ≥ this → auto-fraud
#   in between → ambiguous → Layer 2

AMOUNT_TRIAGE: list[tuple[float, float, float]] = [
    (10_000, 0, 4),  # >€10k: almost nothing auto-legit, cautious fraud threshold
    (1_000, 1, 5),   # €1k–€10k
    (100, 1, 6),     # €100–€1k (standard)
    (0, 2, 8),       # <€100: need very strong signals
]
