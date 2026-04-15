# %% imports
from __future__ import annotations

import json
import logging
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import OPENROUTER_API_KEY
from config.tracing import get_langfuse_callback
from config.models import LLM_BASE_URL, MAX_TOKENS_SPECIALIST, SPECIALIST_MODEL, TEMPERATURE
from data import get_account_context
from prompts import (
    AMOUNT_PROMPT,
    BEHAVIORAL_PROMPT,
    GEOGRAPHIC_PROMPT,
    RELATIONSHIP_PROMPT,
    VELOCITY_PROMPT,
)
from rules._types import RiskResult
from utils import extract_json
from utils.llm_cache import cache_get, cache_set

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
    "geographic": GEOGRAPHIC_PROMPT,
}


# %% LLM client
_llm = ChatOpenAI(
    model=SPECIALIST_MODEL,
    base_url=LLM_BASE_URL,
    api_key=OPENROUTER_API_KEY or "ollama",
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS_SPECIALIST,
    model_kwargs={"response_format": {"type": "json_object"}},
)


# %% _format_rule_results
def _format_rule_results(results: list[tuple[str, RiskResult]]) -> str:
    lines = []
    for name, r in results:
        if r["risk"] != "low":
            lines.append(f"- {name}: {r['risk']} -- {r['reason']}")
    return "\n".join(lines) or "No signals detected by automated rules."


# %% _get_citizen_context
def _get_citizen_context(state: dict, user_id: str, include_persona: bool = False) -> dict:
    """Extract citizen context for a user. Returns compact summary for most specialists,
    full persona text only when include_persona=True (behavioral + aggregator).
    Includes LLM pre-analysis if available."""
    citizen = state.get("citizens", {}).get(user_id, {})
    if not citizen:
        return {}
    ctx = {
        "citizen_summary": citizen.get("summary", "no citizen data"),
        "location": citizen.get("location", {}),
        "status": citizen.get("status", {}),
    }
    # Include LLM pre-analysis if available
    assessment = state.get("citizen_assessments", {}).get(user_id)
    if assessment:
        ctx["pre_assessment"] = assessment
    if include_persona and citizen.get("persona"):
        ctx["persona"] = citizen["persona"]
    return ctx


# %% _build_specialist_context
def _build_specialist_context(specialist_name: str, state: dict, txn: dict) -> dict:
    """Extract curated input for a specialist from the full pipeline state.

    Returns a dict with keys the prompt template expects:
    - velocity:     {txn, history, rule_results, citizen}
    - amount:       {txn, profile, rule_results, citizen}
    - behavioral:   {txn, profile, history, rule_results, citizen+persona}
    - relationship: {txn, graph, rule_results, citizen}
    """
    txn_id = txn["id"]
    sender_id = txn["sender_id"]
    rule_results = _format_rule_results(state["rule_results"].get(txn_id, []))

    if specialist_name == "velocity":
        history = get_account_context(sender_id, state["transactions"], n=20)
        citizen = _get_citizen_context(state, sender_id)
        return {"txn": txn, "history": history, "citizen": citizen, "rule_results": rule_results}

    if specialist_name == "amount":
        profile = state["profiles"].get(sender_id, {})
        citizen = _get_citizen_context(state, sender_id)
        return {"txn": txn, "profile": profile, "citizen": citizen, "rule_results": rule_results}

    if specialist_name == "behavioral":
        profile = state["profiles"].get(sender_id, {})
        history = get_account_context(sender_id, state["transactions"], n=20)
        citizen = _get_citizen_context(state, sender_id, include_persona=True)
        return {
            "txn": txn,
            "profile": profile,
            "history": history,
            "citizen": citizen,
            "rule_results": rule_results,
        }

    if specialist_name == "relationship":
        graph = state.get("graph", {})
        citizen = _get_citizen_context(state, sender_id)
        return {"txn": txn, "graph": graph, "citizen": citizen, "rule_results": rule_results}

    if specialist_name == "geographic":
        citizen = _get_citizen_context(state, sender_id, include_persona=True)
        return {"txn": txn, "citizen": citizen, "rule_results": rule_results}

    raise ValueError(f"Unknown specialist: {specialist_name}")


# %% _call_specialist
def _call_specialist(
    name: str, context: dict, session_id: str | None = None
) -> SpecialistOutput | None:
    """Single LLM call for one specialist on one transaction."""
    rule_results = context["rule_results"]
    system = _PROMPTS[name].format(rule_results=rule_results)
    user_data = {k: v for k, v in context.items() if k != "rule_results"}
    user_content = json.dumps(user_data, default=str)

    # Check cache first
    cached = cache_get(system, user_content)
    if cached is not None:
        data = extract_json(cached)
        if "error" not in data:
            print(f"  [{name}] cached")
            return SpecialistOutput.model_validate(data)

    print(f"  [{name}] calling LLM...", end="", flush=True)
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=user_content),
    ]
    invoke_config = {}
    if session_id:
        invoke_config = {
            "callbacks": [get_langfuse_callback()],
            "metadata": {"langfuse_session_id": session_id},
        }
    try:
        response = _llm.invoke(messages, config=invoke_config)
        print(" done")
        cache_set(system, user_content, response.content)
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
    """Shared logic for all 5 specialists — loop over ambiguous txns."""
    results: dict[str, dict] = {}
    txn_by_id = {t["id"]: t for t in state.get("transactions", [])}
    session_id = state.get("session_id")

    ambiguous = state.get("ambiguous_prioritized", [])
    print(f"[{name}] processing {len(ambiguous)} txns")
    for i, (txn_id, _priority) in enumerate(ambiguous, 1):
        txn = txn_by_id.get(txn_id)
        if not txn:
            continue

        print(f"  ({i}/{len(ambiguous)}) {txn_id} €{txn['amount']:.0f}")
        context = _build_specialist_context(name, state, txn)
        output = _call_specialist(name, context, session_id)

        # Retry once for high-value txns (>€1k)
        if output is None and txn["amount"] > 1000:
            _log.info(f"{name}: retrying high-value txn {txn_id} (€{txn['amount']})")
            context = _build_specialist_context(name, state, txn)
            output = _call_specialist(name, context, session_id)

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


# %% run_geographic_specialist
def run_geographic_specialist(state: dict) -> dict:
    """Analyze all ambiguous transactions for geographic/identity consistency."""
    return _run_specialist("geographic", state)
