# %% imports
from __future__ import annotations

from typing import Annotated, TypedDict

from rules._types import RiskResult
from utils import BudgetTracker


# %% _merge_dicts
def _merge_dicts(a: dict, b: dict) -> dict:
    merged = dict(a)
    for key, val in b.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(val, dict):
            merged[key] = {**merged[key], **val}
        else:
            merged[key] = val
    return merged


# %% PipelineState
class PipelineState(TypedDict, total=False):
    dataset_path: str
    session_id: str
    budget: BudgetTracker
    transactions: list[dict]
    profiles: dict  # account_id → AccountProfile (full dataset, for specialists)
    temporal_profiles: dict  # txn_id → AccountProfile (prior-only, for rules)
    graph: dict  # relationship graph
    citizens: dict  # user_id → citizen profile (demographics, location, status, persona)
    citizen_assessments: dict  # user_id → LLM pre-analysis (vulnerability, contradictions, expected behavior)
    rule_results: dict[
        str, list[tuple[str, RiskResult]]
    ]  # txn_id → [(tool_name, result)]
    auto_legit: list[str]
    auto_fraud: list[str]
    ambiguous_prioritized: list[
        tuple[str, float]
    ]  # [(txn_id, score*amount)] sorted desc
    specialist_results: Annotated[dict, _merge_dicts]  # txn_id → {specialist → result}
    verdicts: dict  # txn_id → Verdict
    fraud_ids: list[str]
    debug_output: list[dict]
