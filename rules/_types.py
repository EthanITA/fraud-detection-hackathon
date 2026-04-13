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
    score: int  # 0–10
    risk_level: RiskLevel
    summary: str


_RISK_SCORES: dict[RiskLevel, int] = {
    RiskLevel.HIGH: 3,
    RiskLevel.MEDIUM: 1,
    RiskLevel.LOW: 0,
}

# Reporting limits — amounts just below these are structuring signals
_STRUCTURING_LIMITS = [5_000, 10_000, 15_000]
