# %% imports
from __future__ import annotations

import json
import re


# %% extract_json
def extract_json(raw: str) -> dict:
    """
    Fallback JSON parser for LLM output.

    Primary JSON enforcement is via structured output in agents/.
    This function is the defensive safety net for when structured output
    fails or isn't available.

    Cascade:
      1. Direct json.loads
      2. Strip markdown fences and retry
      3. Regex-extract outermost {...} and retry
      4. Give up: {"error": "parse_failed", "raw": <first 200 chars>}
    """
    # 1. direct
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. strip markdown fences
    stripped = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    stripped = re.sub(r"\s*```$", "", stripped)
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, TypeError):
        pass

    # 3. regex outermost braces
    match = re.search(r"\{.*}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    # 4. give up
    return {"error": "parse_failed", "raw": raw[:200]}
