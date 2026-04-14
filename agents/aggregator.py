# %% imports
from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel

from config.models import AGGREGATOR_MODEL, MAX_TOKENS_AGGREGATOR, TEMPERATURE
from prompts import AGGREGATOR_PROMPT
from rules._types import RiskResult
from utils import extract_json

from .specialists import SpecialistResult


# %% Verdict
class Verdict(TypedDict):
    transaction_id: str
    is_fraud: bool
    confidence: float       # 0.0-1.0
    reasoning: str


# %% AggregatorOutput
class AggregatorOutput(BaseModel):
    """Pydantic model for structured output validation (belt-and-suspenders layer 2)."""
    is_fraud: bool
    confidence: float
    reasoning: str


# %% run_aggregator
def run_aggregator(state: dict) -> dict:
    """Combine specialist opinions into final verdicts with economic weighting.

    LangGraph node -- receives full PipelineState, returns verdicts update.
    Processes all txns that have entries in specialist_results.
    """
    raise NotImplementedError("aggregate LLM node")
