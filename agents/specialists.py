# %% imports
from __future__ import annotations

import json
import logging
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import OPENROUTER_API_KEY
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

_log = logging.getLogger(__name__)


# %% SpecialistResult
class SpecialistResult(TypedDict):
    agent: str  # "velocity" | "amount" | "behavioral" | "relationship"
    risk_level: str  # "high" | "medium" | "low"
    confidence: float  # 0.0-1.0
    patterns_detected: list[str]
    reasoning: str


# %% SpecialistOutput
class SpecialistOutput(BaseModel):
    """Pydantic model for structured output validation (belt-and-suspenders layer 2)."""

    risk_level: Literal["high", "medium", "low"]
    confidence: float
    patterns_detected: list[str]
    reasoning: str


# %% prompt map
_PROMPTS = {
    "velocity": VELOCITY_PROMPT,
    "amount": AMOUNT_PROMPT,
    "behavioral": BEHAVIORAL_PROMPT,
    "relationship": RELATIONSHIP_PROMPT,
}


# %% LLM client
_llm = ChatOpenAI(
    model=SPECIALIST_MODEL,
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS_SPECIALIST,
)


# %% _format_rule_results
def _format_rule_results(results: list[tuple[str, RiskResult]]) -> str:
    lines = []
    for name, r in results:
        if r["risk"] != "low":
            lines.append(f"- {name}: {r['risk']} -- {r['reason']}")
    return "\n".join(lines) or "No signals detected by automated rules."


# %% _build_specialist_context
def _build_specialist_context(specialist_name: str, state: dict, txn: dict) -> dict:
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
        history = get_account_context(txn["sender_id"], state["transactions"], n=20)
        return {"txn": txn, "history": history, "rule_results": rule_results}

    if specialist_name == "amount":
        profile = state["profiles"].get(txn["sender_id"], {})
        return {"txn": txn, "profile": profile, "rule_results": rule_results}

    if specialist_name == "behavioral":
        profile = state["profiles"].get(txn["sender_id"], {})
        history = get_account_context(txn["sender_id"], state["transactions"], n=20)
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


# %% _call_specialist
def _call_specialist(name: str, context: dict) -> SpecialistOutput | None:
    """Single LLM call for one specialist on one transaction."""
    rule_results = context["rule_results"]
    system = _PROMPTS[name].format(rule_results=rule_results)
    user_data = {k: v for k, v in context.items() if k != "rule_results"}
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=json.dumps(user_data, default=str)),
    ]
    try:
        response = _llm.invoke(messages)
        data = extract_json(response.content)
        if "error" in data:
            _log.warning(f"{name}: LLM returned unparseable output")
            return None
        return SpecialistOutput.model_validate(data)
    except Exception as e:
        _log.warning(f"{name}: LLM call failed: {e}")
        return None


# %% _run_specialist
def _run_specialist(name: str, state: dict) -> dict:
    """Shared logic for all 4 specialists — loop over ambiguous txns."""
    results: dict[str, dict] = {}
    txn_by_id = {t["id"]: t for t in state.get("transactions", [])}

    for txn_id, _priority in state.get("ambiguous_prioritized", []):
        txn = txn_by_id.get(txn_id)
        if not txn:
            continue

        context = _build_specialist_context(name, state, txn)
        output = _call_specialist(name, context)

        # Retry once for high-value txns (>€1k)
        if output is None and txn["amount"] > 1000:
            _log.info(f"{name}: retrying high-value txn {txn_id} (€{txn['amount']})")
            context = _build_specialist_context(name, state, txn)
            output = _call_specialist(name, context)

        if output is not None:
            results[txn_id] = {
                name: {
                    "agent": name,
                    "risk_level": output.risk_level,
                    "confidence": output.confidence,
                    "patterns_detected": output.patterns_detected,
                    "reasoning": output.reasoning,
                }
            }

    return {"specialist_results": results}


# %% run_velocity_specialist
def run_velocity_specialist(state: dict) -> dict:
    """Analyze all ambiguous transactions for timing/velocity patterns."""
    return _run_specialist("velocity", state)


# %% run_amount_specialist
def run_amount_specialist(state: dict) -> dict:
    """Analyze all ambiguous transactions for spending/amount patterns."""
    return _run_specialist("amount", state)


# %% run_behavioral_specialist
def run_behavioral_specialist(state: dict) -> dict:
    """Analyze all ambiguous transactions for behavioral change patterns."""
    return _run_specialist("behavioral", state)


# %% run_relationship_specialist
def run_relationship_specialist(state: dict) -> dict:
    """Analyze all ambiguous transactions for network/relationship patterns."""
    return _run_specialist("relationship", state)
