from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel

from config.models import MAX_TOKENS_SPECIALIST, SPECIALIST_MODEL, TEMPERATURE
from data import get_account_context
from prompts import (
    AMOUNT_PROMPT,
    BEHAVIORAL_PROMPT,
    RELATIONSHIP_PROMPT,
    VELOCITY_PROMPT,
)
from rules._types import RiskResult
from utils import extract_json


class SpecialistResult(TypedDict):
    agent: str              # "velocity" | "amount" | "behavioral" | "relationship"
    risk_level: str         # "high" | "medium" | "low"
    confidence: float       # 0.0-1.0
    patterns_detected: list[str]
    reasoning: str


class SpecialistOutput(BaseModel):
    """Pydantic model for structured output validation (belt-and-suspenders layer 2)."""
    risk_level: Literal["high", "medium", "low"]
    confidence: float
    patterns_detected: list[str]
    reasoning: str


def _format_rule_results(results: list[tuple[str, RiskResult]]) -> str:
    lines = []
    for name, r in results:
        if r["risk"] != "low":
            lines.append(f"- {name}: {r['risk']} -- {r['reason']}")
    return "\n".join(lines) or "No signals detected by automated rules."


def _build_specialist_context(
    specialist_name: str, state: dict, txn: dict
) -> dict:
    """Extract curated input for a specialist from the full pipeline state.

    Returns a dict with keys the prompt template expects:
    - velocity:     {txn, history, rule_results}
    - amount:       {txn, profile, rule_results}
    - behavioral:   {txn, profile, history, rule_results}
    - relationship: {txn, graph, rule_results}
    """
    txn_id = txn["id"]
    rule_results = _format_rule_results(state["rule_results"].get(txn_id, []))

    if specialist_name == "velocity":
        history = get_account_context(
            txn["sender_id"], state["transactions"], n=20
        )
        return {"txn": txn, "history": history, "rule_results": rule_results}

    if specialist_name == "amount":
        profile = state["profiles"].get(txn["sender_id"], {})
        return {"txn": txn, "profile": profile, "rule_results": rule_results}

    if specialist_name == "behavioral":
        profile = state["profiles"].get(txn["sender_id"], {})
        history = get_account_context(
            txn["sender_id"], state["transactions"], n=20
        )
        return {
            "txn": txn,
            "profile": profile,
            "history": history,
            "rule_results": rule_results,
        }

    if specialist_name == "relationship":
        graph = state.get("graph", {})
        return {"txn": txn, "graph": graph, "rule_results": rule_results}

    raise ValueError(f"Unknown specialist: {specialist_name}")


def run_velocity_specialist(state: dict) -> dict:
    """Analyze all ambiguous transactions for timing/velocity patterns.

    LangGraph node -- receives full PipelineState, returns specialist_results update.
    """
    raise NotImplementedError("velocity_specialist LLM agent")


def run_amount_specialist(state: dict) -> dict:
    """Analyze all ambiguous transactions for spending/amount patterns.

    LangGraph node -- receives full PipelineState, returns specialist_results update.
    """
    raise NotImplementedError("amount_specialist LLM agent")


def run_behavioral_specialist(state: dict) -> dict:
    """Analyze all ambiguous transactions for behavioral change patterns.

    LangGraph node -- receives full PipelineState, returns specialist_results update.
    """
    raise NotImplementedError("behavioral_specialist LLM agent")


def run_relationship_specialist(state: dict) -> dict:
    """Analyze all ambiguous transactions for network/relationship patterns.

    LangGraph node -- receives full PipelineState, returns specialist_results update.
    """
    raise NotImplementedError("relationship_specialist LLM agent")
