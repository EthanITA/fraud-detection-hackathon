# %% imports
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import OPENROUTER_API_KEY
from config.models import LLM_BASE_URL, MAX_TOKENS_SPECIALIST, SPECIALIST_MODEL, TEMPERATURE
from config.tracing import get_langfuse_callback

_log = logging.getLogger(__name__)


# %% CitizenAssessment
class CitizenAssessment(BaseModel):
    vulnerability_level: str  # "high" | "medium" | "low"
    contradictions: list[str]
    expected_behavior: str
    risk_factors: list[str]
    summary: str


# %% prompt
CITIZEN_ANALYSIS_PROMPT = """\
You are a fraud risk analyst performing a PRE-SCREENING assessment of a citizen.

You will receive a citizen's full profile: demographics, location history, health/wellness data, and a narrative persona description.

Your job: assess this citizen's BASELINE risk profile BEFORE looking at any transactions.

ANALYZE THESE DIMENSIONS:

1. CONTRADICTIONS — Compare the persona description against the actual data:
   - Persona says "rarely travels" but location data shows foreign cities → flag it
   - Persona says "active lifestyle" but health data shows declining activity → flag it
   - Persona says "low mobility" but max_distance > 5000km → flag it

2. VULNERABILITY — Assess how susceptible this citizen is to fraud/account takeover:
   - Age 80+ with declining health = HIGH vulnerability
   - Social isolation + declining activity = HIGH vulnerability
   - Active professional with strong social network = LOW vulnerability

3. EXPECTED BEHAVIOR — What transactions would be NORMAL for this person:
   - A retired widow in rural France: small local purchases, pharmacy, bakery
   - A retail entrepreneur: business travel, supplier payments, varied merchants

4. RISK FACTORS — List specific flags:
   - impossible_travel_detected: location data contradicts persona mobility
   - elderly_vulnerable: age 80+ with health issues
   - declining_health: activity/sleep trends worsening
   - social_isolation: narrowing social circle
   - erratic_behavior: inconsistent patterns in recent data

CRITICAL: Output ONLY the JSON object below. No reasoning, no preamble, no markdown fences. Start your response with {{ and end with }}.
{{"vulnerability_level": "high"|"medium"|"low", "contradictions": [...], "expected_behavior": "...", "risk_factors": [...], "summary": "..."}}
"""

# %% LLM client
_llm = ChatOpenAI(
    model=SPECIALIST_MODEL,
    base_url=LLM_BASE_URL,
    api_key=OPENROUTER_API_KEY or "ollama",
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS_SPECIALIST,
    model_kwargs={"response_format": {"type": "json_object"}},
)


# %% analyze_citizen
def analyze_citizen(
    citizen: dict, session_id: str | None = None
) -> CitizenAssessment | None:
    """Run a single LLM call to pre-assess one citizen's risk profile."""
    from utils import extract_json

    user_data = json.dumps({
        "demographics": citizen.get("user", {}),
        "location_summary": citizen.get("location", {}),
        "health_status": citizen.get("status", {}),
        "persona": citizen.get("persona", "No persona available."),
    }, default=str)

    messages = [
        SystemMessage(content=CITIZEN_ANALYSIS_PROMPT),
        HumanMessage(content=user_data),
    ]

    invoke_config = {}
    if session_id:
        invoke_config = {
            "callbacks": [get_langfuse_callback()],
            "metadata": {"langfuse_session_id": session_id},
        }

    try:
        response = _llm.invoke(messages, config=invoke_config)
        data = extract_json(response.content)
        if "error" in data:
            _log.warning("citizen_analyst: unparseable output")
            return None
        return CitizenAssessment.model_validate(data)
    except Exception as e:
        _log.warning(f"citizen_analyst: LLM call failed: {e}")
        return None


# %% run_citizen_analysis
def run_citizen_analysis(state: dict) -> dict:
    """Analyze all citizens with available data. Returns citizen_assessments update."""
    citizens = state.get("citizens", {})
    session_id = state.get("session_id")
    assessments: dict[str, dict] = {}

    for uid, citizen in citizens.items():
        # Skip citizens with no meaningful data
        if not citizen.get("persona") and not citizen.get("location"):
            continue

        output = analyze_citizen(citizen, session_id)
        if output is not None:
            assessments[uid] = {
                "vulnerability_level": output.vulnerability_level,
                "contradictions": output.contradictions,
                "expected_behavior": output.expected_behavior,
                "risk_factors": output.risk_factors,
                "summary": output.summary,
            }
        else:
            _log.info(f"citizen_analyst: no assessment for {uid}")

    _log.info(f"citizen_analyst: assessed {len(assessments)}/{len(citizens)} citizens")
    return {"citizen_assessments": assessments}
