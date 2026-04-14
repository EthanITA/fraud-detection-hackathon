from __future__ import annotations

from typing import TypedDict

from config.models import AGGREGATOR_MODEL, MAX_TOKENS_AGGREGATOR, TEMPERATURE
from prompts import AGGREGATOR_PROMPT
from rules._types import RiskResult
from utils import extract_json

from .specialists import SpecialistResult


class Verdict(TypedDict):
    transaction_id: str
    is_fraud: bool
    confidence: float       # 0.0–1.0
    reasoning: str


def run_aggregator(
    txn: dict,
    specialist_results: list[SpecialistResult],
    rule_results: list[tuple[str, RiskResult]],
) -> Verdict:
    """
    Final fraud/legit decision. Combines 3 specialist opinions
    with economic weighting and pattern combo detection.
    """
    raise NotImplementedError
