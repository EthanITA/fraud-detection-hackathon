from __future__ import annotations

from typing import TypedDict

from rules._types import RiskResult


class PipelineState(TypedDict, total=False):
    dataset_path: str
    transactions: list[dict]
    profiles: dict                                    # account_id → AccountProfile
    graph: dict                                       # relationship graph
    rule_results: dict[str, list[tuple[str, RiskResult]]]  # txn_id → [(tool_name, result)]
    auto_legit: list[str]
    auto_fraud: list[str]
    ambiguous: list[str]
    specialist_results: dict                          # txn_id → [specialist outputs]
    verdicts: dict                                    # txn_id → {is_fraud, confidence, reasoning}
    fraud_ids: list[str]
