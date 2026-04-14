# %% imports
from __future__ import annotations

from enum import Enum
from typing import TypedDict


# %% types
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


# %% risk scores
_RISK_SCORES: dict[RiskLevel, int] = {
    RiskLevel.HIGH: 3,
    RiskLevel.MEDIUM: 1,
    RiskLevel.LOW: 0,
}

# Reporting limits — amounts just below these are structuring signals
_STRUCTURING_LIMITS = [5_000, 10_000, 15_000]

# %% tool weights
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
    "check_fan_in": 2.0,
    "check_fan_out": 2.0,
    "check_mule_chain": 2.0,
    "check_circular_flow": 2.0,
    # geographic
    "check_impossible_travel": 2.0,
}

# %% always-flag combos
# ── Always-flag combos ────────────────────────────────────────────────────────
# If ALL tools in a combo set fire HIGH → auto-fraud, regardless of score.

ALWAYS_FLAG_COMBOS: list[tuple[str, set[str]]] = [
    ("BURST+BALANCE_DRAIN", {"check_velocity", "check_balance_drain"}),
    ("NEW_PAYEE+AMOUNT_ANOMALY", {"check_new_payee", "check_amount_anomaly"}),
    ("MULE_CHAIN+STRUCTURING", {"check_mule_chain", "check_amount_anomaly"}),
    ("IMPOSSIBLE_TRAVEL+BALANCE_DRAIN", {"check_impossible_travel", "check_balance_drain"}),
]

# %% amount-aware triage thresholds
# ── Amount-aware triage thresholds ────────────────────────────────────────────
# (amount_floor, legit_ceiling, fraud_floor)
# Checked top-down: first match wins.
#   legit_ceiling: weighted score ≤ this → auto-legit
#   fraud_floor:   weighted score ≥ this → auto-fraud
#   in between → ambiguous → Layer 2

AMOUNT_TRIAGE: list[tuple[float, float, float]] = [
    (10_000, 0, 4),  # >€10k: almost nothing auto-legit, cautious fraud threshold
    (1_000, 1, 5),  # €1k–€10k
    (100, 1, 6),  # €100–€1k (standard)
    (0, 2, 8),  # <€100: need very strong signals
]

# %% thresholds
# ── Thresholds ───────────────────────────────────────────────────────────────
# Every magic number the 13 tools use. Tune these on hackathon day after
# seeing the data distribution — no other file needs to change.

# Time
VELOCITY_HIGH_GAP = 60  # seconds — avg gap between recent txns → HIGH
VELOCITY_MEDIUM_GAP = 300  # seconds → MEDIUM
OFF_HOURS_START = 0  # UTC hour — suspicious window start
OFF_HOURS_END = 5  # UTC hour — suspicious window end
CARD_TEST_MICRO_LIMIT = 10  # € — max amount to count as micro test txn
CARD_TEST_LARGE_LIMIT = 500  # € — min amount for the "real" txn after tests
CARD_TEST_WINDOW = 300  # seconds — lookback for micro-txns before current
CARD_TEST_HIGH_COUNT = 3  # micro-txns in window → HIGH (fewer → MEDIUM)

# Amount
OUTLIER_SIGMA = 3  # std devs above mean → HIGH
ROUND_NUMBER_MIN = 1_000  # € — min round amount that looks suspicious
STRUCTURING_PROXIMITY = 200  # € below a reporting limit → structuring signal
DRAIN_HIGH = 0.9  # balance fraction drained → HIGH
DRAIN_MEDIUM = 0.7  # balance fraction drained → MEDIUM
FIRST_LARGE_HIGH = 5  # multiple of historical max → HIGH
FIRST_LARGE_MEDIUM = 3  # multiple of historical max → MEDIUM
FIRST_LARGE_MIN_TXNS = 5  # min txn history before HIGH can trigger

# Behavioral
NEW_PAYEE_HIGH_AMOUNT = 1_000  # € to unknown payee → HIGH
NEW_PAYEE_MEDIUM_AMOUNT = 200  # € to unknown payee → MEDIUM
DORMANT_HIGH_DAYS = 180  # days inactive → HIGH (if amount > avg)
DORMANT_MEDIUM_DAYS = 90  # days inactive → MEDIUM
FREQUENCY_SHIFT_HIGH = 10  # rate multiplier vs baseline → HIGH
FREQUENCY_SHIFT_MEDIUM = 5  # rate multiplier vs baseline → MEDIUM

# Graph
FAN_IN_HIGH = 10  # in-degree (distinct senders) → HIGH
FAN_IN_MEDIUM = 5  # in-degree → MEDIUM
FAN_OUT_HIGH = 10  # out-degree (distinct receivers in 24h) → HIGH
FAN_OUT_MEDIUM = 5  # out-degree → MEDIUM
MULE_FORWARD_HIGH = 0.7  # fraction of received amount forwarded → HIGH
MULE_FORWARD_MEDIUM = 0.5  # fraction forwarded → MEDIUM
MULE_WINDOW_HIGH = 1_800  # seconds (30 min) — forward window → HIGH
MULE_WINDOW_MEDIUM = 7_200  # seconds (2h) — forward window → MEDIUM
CIRCULAR_MAX_HOPS = 3  # max hops to detect circular flow → HIGH

# Geographic
IMPOSSIBLE_TRAVEL_DISTANCE_HIGH = 5_000  # km from home → HIGH (if > known max × 1.5)
IMPOSSIBLE_TRAVEL_DISTANCE_MEDIUM = 2_000  # km from home → MEDIUM
