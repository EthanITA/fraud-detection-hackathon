# %% env setup
import os  # noqa: E401
import sys

try:
    sys.path.insert(
        0, str(__import__("pathlib").Path(__file__).resolve().parent.parent)
    )
except NameError:
    sys.path.insert(0, os.getcwd())
import _env  # noqa: F401

# %% resolve upstream: data + rules
import json

from _sample import SAMPLE_TXNS
from data import build_relationship_graph, compute_account_profiles, get_account_context
from pipeline.dispatch import invoke_tool
from rules import RULE_TOOLS

profiles = compute_account_profiles(SAMPLE_TXNS)
graph = build_relationship_graph(SAMPLE_TXNS)

# Run rules on all txns
rule_results = {}
for txn in SAMPLE_TXNS:
    ctx = {
        "txn": json.dumps(txn),
        "history": json.dumps(get_account_context(txn["sender_id"], SAMPLE_TXNS)),
        "profile": json.dumps(profiles.get(txn["sender_id"], {})),
        "graph": json.dumps(graph),
    }
    rule_results[txn["id"]] = [
        (tool.name, invoke_tool(tool, ctx)) for tool in RULE_TOOLS
    ]

print(f"Upstream ready: {len(rule_results)} txns scored")

# %% simulate pipeline state (what specialists receive)
state = {
    "transactions": SAMPLE_TXNS,
    "profiles": profiles,
    "graph": graph,
    "rule_results": rule_results,
    "ambiguous_prioritized": [("T006", 4.5 * 9500), ("T003", 3.0 * 500)],
}

# %% inspect specialist context — velocity
from agents.specialists import _build_specialist_context

txn_t006 = next(t for t in SAMPLE_TXNS if t["id"] == "T006")
velocity_ctx = _build_specialist_context("velocity", state, txn_t006)
print("Velocity context for T006:")
print(f"  txn: {velocity_ctx['txn']['id']} €{velocity_ctx['txn']['amount']}")
print(f"  history: {len(velocity_ctx['history'])} txns")
print(f"  rule_results:\n{velocity_ctx['rule_results']}")

# %% inspect specialist context — amount
amount_ctx = _build_specialist_context("amount", state, txn_t006)
print("\nAmount context for T006:")
print(f"  txn: {amount_ctx['txn']['id']}")
print(f"  profile balance: €{amount_ctx['profile'].get('balance', '?')}")
print(f"  profile avg: €{amount_ctx['profile'].get('avg_amount', '?')}")

# %% inspect specialist context — behavioral
behavioral_ctx = _build_specialist_context("behavioral", state, txn_t006)
print("\nBehavioral context for T006:")
print(f"  txn: {behavioral_ctx['txn']['id']}")
print(f"  profile: {list(behavioral_ctx['profile'].keys())}")
print(f"  history: {len(behavioral_ctx['history'])} txns")

# %% inspect specialist context — relationship
rel_ctx = _build_specialist_context("relationship", state, txn_t006)
print("\nRelationship context for T006:")
print(f"  txn: {rel_ctx['txn']['id']}")
print(f"  graph nodes: {len(rel_ctx['graph'].get('nodes', []))}")
print(f"  graph edges: {len(rel_ctx['graph'].get('edges', []))}")

# %% inspect formatted rule results
from agents.specialists import _format_rule_results

formatted = _format_rule_results(rule_results["T006"])
print("\nFormatted rule results for T006:")
print(formatted)

# %% Pydantic models — test validation
from agents.specialists import SpecialistOutput

valid = SpecialistOutput(
    risk_level="high",
    confidence=0.85,
    patterns_detected=["BALANCE_DRAIN"],
    reasoning="Account drained 95% of balance in single txn",
)
print(f"\nValid SpecialistOutput: {valid.model_dump()}")

# %% Pydantic — test invalid
try:
    invalid = SpecialistOutput(
        risk_level="extreme",  # not in literal
        confidence=0.5,
        patterns_detected=[],
        reasoning="test",
    )
except Exception as e:
    print(f"Expected validation error: {type(e).__name__}: {e}")

# %% AggregatorOutput
from agents.aggregator import AggregatorOutput

verdict = AggregatorOutput(
    is_fraud=True, confidence=0.87, reasoning="2 specialists flagged high"
)
print(f"\nAggregatorOutput: {verdict.model_dump()}")
