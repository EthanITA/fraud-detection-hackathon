# %% imports
from __future__ import annotations

import json

from rules._types import RiskResult

# %% _TOOL_CONTEXT
_TOOL_CONTEXT: dict[str, tuple[str, ...]] = {
    "check_velocity":             ("txn", "history"),
    "check_temporal_pattern":     ("txn",),
    "check_card_testing":         ("txn", "history"),
    "check_amount_anomaly":       ("txn", "profile"),
    "check_balance_drain":        ("txn", "profile"),
    "check_first_large":          ("txn", "profile"),
    "check_new_payee":            ("txn", "profile"),
    "check_dormant_reactivation": ("txn", "profile"),
    "check_frequency_shift":      ("txn", "history", "profile"),
    "check_fan_in":               ("txn", "graph"),
    "check_fan_out":              ("txn", "graph"),
    "check_mule_chain":           ("txn", "graph"),
    "check_circular_flow":        ("txn", "graph"),
    "check_impossible_travel":    ("txn", "citizen"),
}


# %% invoke_tool
def invoke_tool(tool, context: dict[str, str]) -> RiskResult:
    """Call a rule tool with the subset of context it needs.

    If a required context key is missing (e.g., citizen data not loaded),
    the tool gets '{}' as a graceful fallback — it will return LOW risk.
    """
    keys = _TOOL_CONTEXT[tool.name]
    args = {f"{k}_json": context.get(k, "{}") for k in keys}
    return json.loads(tool.invoke(args))
