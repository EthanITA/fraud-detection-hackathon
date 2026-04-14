# %% imports
from __future__ import annotations

import json
import logging
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import OPENROUTER_API_KEY
from config.tracing import get_langfuse_callback
from config.models import AGGREGATOR_MODEL, LLM_BASE_URL, MAX_TOKENS_AGGREGATOR, TEMPERATURE
from prompts import AGGREGATOR_PROMPT
from rules._types import RiskResult
from utils import extract_json
from utils.llm_cache import cache_get, cache_set

_log = logging.getLogger(__name__)


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


# %% LLM client
_llm = ChatOpenAI(
    model=AGGREGATOR_MODEL,
    base_url=LLM_BASE_URL,
    api_key=OPENROUTER_API_KEY or "ollama",
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS_AGGREGATOR,
    model_kwargs={"response_format": {"type": "json_object"}},
)


# %% _format_specialist_opinions
def _format_specialist_opinions(specialist_results: dict) -> str:
    """Format the 5 specialist outputs into a readable block for the aggregator."""
    lines = []
    for name, result in specialist_results.items():
        lines.append(
            f"[{name.upper()}] risk={result['risk_level']} "
            f"confidence={result['confidence']:.2f} "
            f"patterns={result['patterns_detected']} "
            f"reasoning=\"{result['reasoning']}\""
        )
    return "\n".join(lines) or "No specialist assessments available."


# %% _format_rule_results
def _format_rule_results(results: list[tuple[str, RiskResult]]) -> str:
    lines = []
    for name, r in results:
        if r["risk"] != "low":
            lines.append(f"- {name}: {r['risk']} -- {r['reason']}")
    return "\n".join(lines) or "No signals detected by automated rules."


# %% run_aggregator
def run_aggregator(state: dict) -> dict:
    """Combine specialist opinions into final verdicts with economic weighting.

    LangGraph node -- receives full PipelineState, returns verdicts update.
    Processes all txns that have entries in specialist_results.
    """
    verdicts: dict[str, Verdict] = {}
    txn_by_id = {t["id"]: t for t in state.get("transactions", [])}
    specialist_results = state.get("specialist_results", {})
    session_id = state.get("session_id")

    for txn_id, sp_results in specialist_results.items():
        txn = txn_by_id.get(txn_id)
        if not txn:
            continue

        rule_results = _format_rule_results(
            state.get("rule_results", {}).get(txn_id, [])
        )
        specialist_summary = _format_specialist_opinions(sp_results)

        # Citizen context: full persona + pre-analysis for aggregator
        sender_id = txn["sender_id"]
        citizen = state.get("citizens", {}).get(sender_id, {})
        citizen_context = citizen.get("persona") or citizen.get("summary", "")
        citizen_assessment = state.get("citizen_assessments", {}).get(sender_id, {})

        user_content = json.dumps({
            "transaction": txn,
            "citizen_context": citizen_context,
            "citizen_pre_assessment": citizen_assessment,
            "specialist_assessments": specialist_summary,
            "rule_results": rule_results,
        }, default=str)

        messages = [
            SystemMessage(content=AGGREGATOR_PROMPT),
            HumanMessage(content=user_content),
        ]

        output = _call_aggregator(messages, session_id)

        # Retry once for high-value txns
        if output is None and txn["amount"] > 1000:
            _log.info(f"aggregator: retrying high-value txn {txn_id} (€{txn['amount']})")
            output = _call_aggregator(messages, session_id)

        if output is not None:
            verdicts[txn_id] = {
                "transaction_id": txn_id,
                "is_fraud": output.is_fraud,
                "confidence": output.confidence,
                "reasoning": output.reasoning,
            }
        else:
            _log.warning(f"aggregator: no verdict for {txn_id}, skipping")

    return {"verdicts": verdicts}


# %% _call_aggregator
def _call_aggregator(
    messages: list, session_id: str | None = None
) -> AggregatorOutput | None:
    """Single LLM call for the aggregator."""
    system_content = messages[0].content
    user_content = messages[1].content

    # Check cache first
    cached = cache_get(system_content, user_content)
    if cached is not None:
        data = extract_json(cached)
        if "error" not in data:
            return AggregatorOutput.model_validate(data)

    invoke_config = {}
    if session_id:
        invoke_config = {
            "callbacks": [get_langfuse_callback()],
            "metadata": {"langfuse_session_id": session_id},
        }
    try:
        response = _llm.invoke(messages, config=invoke_config)
        cache_set(system_content, user_content, response.content)
        data = extract_json(response.content)
        if "error" in data:
            _log.warning("aggregator: LLM returned unparseable output")
            return None
        return AggregatorOutput.model_validate(data)
    except Exception as e:
        _log.warning(f"aggregator: LLM call failed: {e}")
        return None
