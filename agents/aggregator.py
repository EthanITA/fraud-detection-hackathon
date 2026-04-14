# %% imports
from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel


# %% Verdict
class Verdict(TypedDict):
    transaction_id: str
    is_fraud: bool
    confidence: float  # 0.0-1.0
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
