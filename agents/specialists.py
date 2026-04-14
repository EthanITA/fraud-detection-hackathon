from __future__ import annotations

import json
from typing import TypedDict

from config.models import MAX_TOKENS_SPECIALIST, SPECIALIST_MODEL, TEMPERATURE
from prompts import AMOUNT_PROMPT, RELATIONSHIP_PROMPT, VELOCITY_PROMPT
from rules._types import RiskResult
from utils import extract_json


class SpecialistResult(TypedDict):
    agent: str              # "velocity" | "amount" | "relationship"
    risk_level: str         # "high" | "medium" | "low"
    confidence: float       # 0.0–1.0
    patterns_detected: list[str]
    reasoning: str


def _format_rule_results(results: list[tuple[str, RiskResult]]) -> str:
    lines = []
    for name, r in results:
        if r["risk"] != "low":
            lines.append(f"- {name}: {r['risk']} — {r['reason']}")
    return "\n".join(lines) or "No signals detected by automated rules."


def run_velocity_specialist(
    txn: dict,
    history: list[dict],
    rule_results: list[tuple[str, RiskResult]],
) -> SpecialistResult:
    """Analyze timing patterns. Input: txn + sender's last 20 txns."""
    raise NotImplementedError


def run_amount_specialist(
    txn: dict,
    profile: dict,
    rule_results: list[tuple[str, RiskResult]],
) -> SpecialistResult:
    """Analyze amount patterns. Input: txn + sender account profile."""
    raise NotImplementedError


def run_relationship_specialist(
    txn: dict,
    graph: dict,
    rule_results: list[tuple[str, RiskResult]],
) -> SpecialistResult:
    """Analyze network patterns. Input: txn + 2-hop subgraph."""
    raise NotImplementedError


def run_all_specialists(
    txn: dict,
    history: list[dict],
    profile: dict,
    graph: dict,
    rule_results: list[tuple[str, RiskResult]],
) -> list[SpecialistResult]:
    """Run all 3 specialists in parallel and return their assessments."""
    raise NotImplementedError
