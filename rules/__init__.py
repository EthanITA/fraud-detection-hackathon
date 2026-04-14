from __future__ import annotations

from ._types import (
    ALWAYS_FLAG_COMBOS,
    AMOUNT_TRIAGE,
    TOOL_WEIGHTS,
    CompositeResult,
    RiskLevel,
    RiskResult,
    _RISK_SCORES,
)
from .amount import check_amount_anomaly, check_balance_drain, check_first_large
from .behavioral import (
    check_dormant_reactivation,
    check_frequency_shift,
    check_new_payee,
)
from .graph import check_circular_flow, check_fan_in, check_fan_out, check_mule_chain
from .time import check_card_testing, check_temporal_pattern, check_velocity


def compute_composite_risk(
    results: list[tuple[str, RiskResult]],
    amount: float,
) -> CompositeResult:
    """
    Aggregate rule results into a weighted composite score.

    Inputs:
      results — list of (tool.name, RiskResult) pairs from all 13 rule tools
      amount  — transaction amount in EUR for economic threshold scaling

    Logic:
      1. Weighted sum: each tool's risk score (HIGH=3, MED=1, LOW=0) × tool weight
      2. Combo check: if a known dangerous pattern fires, auto-fraud regardless of score
      3. Amount-aware thresholds: high-value txns get stricter legit/fraud cutoffs
    """
    # 1. weighted score
    score = 0.0
    for tool_name, result in results:
        weight = TOOL_WEIGHTS.get(tool_name, 1.0)
        score += _RISK_SCORES[RiskLevel(result["risk"])] * weight

    # 2. combo detection
    high_tools = {name for name, r in results if RiskLevel(r["risk"]) == RiskLevel.HIGH}
    combo_triggered = None
    for combo_name, combo_set in ALWAYS_FLAG_COMBOS:
        if combo_set.issubset(high_tools):
            combo_triggered = combo_name
            break

    # 3. amount-aware thresholds
    legit_ceiling, fraud_floor = 1.0, 6.0
    for floor, lc, ff in AMOUNT_TRIAGE:
        if amount >= floor:
            legit_ceiling, fraud_floor = lc, ff
            break

    # 4. triage decision
    auto_fraud = combo_triggered is not None or score >= fraud_floor
    auto_legit = not auto_fraud and score <= legit_ceiling

    # 5. build result
    flagged = [
        (name, r) for name, r in results if RiskLevel(r["risk"]) != RiskLevel.LOW
    ]
    summary = " | ".join(f"{name}: {r['reason']}" for name, r in flagged)

    if auto_fraud:
        risk_level = RiskLevel.HIGH
    elif auto_legit:
        risk_level = RiskLevel.LOW
    else:
        risk_level = RiskLevel.MEDIUM

    return {
        "score": score,
        "risk_level": risk_level,
        "summary": summary or "no signals",
        "auto_legit": auto_legit,
        "auto_fraud": auto_fraud,
        "combo_triggered": combo_triggered,
    }


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
