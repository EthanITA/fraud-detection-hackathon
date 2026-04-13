from __future__ import annotations

from ._types import CompositeResult, RiskLevel, RiskResult, _RISK_SCORES
from .amount import check_amount_anomaly, check_balance_drain, check_first_large
from .behavioral import check_dormant_reactivation, check_frequency_shift, check_new_payee
from .graph import check_circular_flow, check_fan_in, check_fan_out, check_mule_chain
from .time import check_card_testing, check_temporal_pattern, check_velocity


def compute_composite_risk(results: list[RiskResult]) -> CompositeResult:
    """
    Aggregate rule results into a 0–10 composite score.
    high=3, medium=1, low=0.
    Triage: score ≤1 → auto-legit · score ≥6 → auto-fraud · 2–5 → Layer 2
    """
    score = min(sum(_RISK_SCORES[RiskLevel(r["risk"])] for r in results), 10)
    summary = " | ".join(r["reason"] for r in results if r["risk"] != RiskLevel.LOW)

    if score >= 6:
        risk_level = RiskLevel.HIGH
    elif score >= 2:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    return {"score": score, "risk_level": risk_level, "summary": summary or "no signals"}


RULE_TOOLS = [
    # time
    check_velocity,
    check_temporal_pattern,
    check_card_testing,
    # amount
    check_amount_anomaly,
    check_balance_drain,
    check_first_large,
    # behavioral
    check_new_payee,
    check_dormant_reactivation,
    check_frequency_shift,
    # graph flow
    check_fan_in,
    check_fan_out,
    check_mule_chain,
    check_circular_flow,
]
