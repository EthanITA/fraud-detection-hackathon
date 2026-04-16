# %% imports
from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from config import OPENROUTER_API_KEY
from config.models import AGGREGATOR_MODEL, LLM_BASE_URL, MAX_TOKENS_SPECIALIST, TEMPERATURE
from config.tracing import get_langfuse_callback
from utils.llm_cache import cache_get, cache_set

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
You are a fraud risk analyst performing a PRE-SCREENING assessment of a citizen in the year 2087.

You will receive a citizen's profile: demographics (name, age, job, salary, residence), GPS location history, SMS/email communication analysis, and a narrative description.

Your job: assess this citizen's BASELINE risk profile BEFORE looking at any transactions.

ANALYZE THESE DIMENSIONS:

1. CONTRADICTIONS — Compare the description against the actual data:
   - Description says "rarely travels" but location data shows foreign cities → flag it
   - Description says "low mobility" but max_distance > 5000km → flag it
   - Salary doesn't match job type or spending patterns → flag it

2. VULNERABILITY — Assess how susceptible this citizen is to fraud/account takeover:
   - High phishing exposure (many phishing attempts in SMS/email) = HIGH vulnerability
   - Low income + low digital literacy (from description) = HIGH vulnerability
   - Professional with strong security awareness = LOW vulnerability

3. EXPECTED BEHAVIOR — What transactions would be NORMAL for this person:
   - A ride-share driver: fuel, vehicle maintenance, low-value personal purchases
   - A freelance designer: software subscriptions, coworking, varied e-commerce
   - An office clerk: routine rent, bills, modest personal spending

4. RISK FACTORS — List specific flags:
   - phishing_target: high ratio of phishing attempts in communications
   - impossible_travel: location data shows implausible movements
   - income_mismatch: spending potential vs salary inconsistency
   - high_mobility_uncharacteristic: travel patterns don't match job/description

CRITICAL: Output ONLY the JSON object below. No reasoning, no preamble, no markdown fences. Start your response with {{ and end with }}.
{{"vulnerability_level": "high"|"medium"|"low", "contradictions": [...], "expected_behavior": "...", "risk_factors": [...], "summary": "..."}}
"""

# %% LLM client
_llm = ChatOpenAI(
    model=AGGREGATOR_MODEL,
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

    # Exclude raw pings from location to save tokens
    loc = {k: v for k, v in citizen.get("location", {}).items() if k != "pings"}
    user_data = json.dumps({
        "demographics": citizen.get("user", {}),
        "location_summary": loc,
        "sms_analysis": citizen.get("sms", {}),
        "mail_analysis": citizen.get("mails", {}),
        "description": citizen.get("description", "No description available."),
    }, default=str)

    # Check cache first
    cached = cache_get(CITIZEN_ANALYSIS_PROMPT, user_data)
    if cached is not None:
        data = extract_json(cached)
        if "error" not in data:
            return CitizenAssessment.model_validate(data)

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
        print(" done")
        cache_set(CITIZEN_ANALYSIS_PROMPT, user_data, response.content)
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

    print(f"Analyzing {len(citizens)} citizens...")
    for uid, citizen in citizens.items():
        # Skip citizens with no meaningful data
        if not citizen.get("description") and not citizen.get("location"):
            continue

        name = citizen.get("user", {}).get("first_name", uid)
        print(f"  [{uid}] {name}...", end="", flush=True)
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
