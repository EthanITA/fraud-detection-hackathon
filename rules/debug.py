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

# %% resolve upstream: data
import json

from _sample import SAMPLE_TXNS
from data import build_relationship_graph, compute_account_profiles, get_account_context

profiles = compute_account_profiles(SAMPLE_TXNS)
graph = build_relationship_graph(SAMPLE_TXNS)
print(
    f"Upstream ready: {len(profiles)} profiles, " f"{len(graph['nodes'])} graph nodes"
)


# %% helper: build context for a transaction
def build_context(txn: dict) -> dict[str, str]:
    return {
        "txn": json.dumps(txn),
        "history": json.dumps(get_account_context(txn["sender_id"], SAMPLE_TXNS)),
        "profile": json.dumps(profiles.get(txn["sender_id"], {})),
        "graph": json.dumps(graph),
    }


# %% run single tool — check_velocity on burst txn (T003)
from pipeline.dispatch import invoke_tool
from rules.time import check_velocity

txn_burst = SAMPLE_TXNS[2]  # T003 — part of A003's burst
ctx = build_context(txn_burst)
result = invoke_tool(check_velocity, ctx)
print(f"check_velocity on {txn_burst['id']}: {result}")

# %% run ALL 13 tools on one transaction
from rules import RULE_TOOLS

print(f"\nAll tools on {txn_burst['id']} (burst txn):")
results_burst = []
for tool in RULE_TOOLS:
    r = invoke_tool(tool, ctx)
    results_burst.append((tool.name, r))
    flag = "⚠️" if r["risk"] != "low" else "  "
    print(f"  {flag} {tool.name}: {r['risk']} — {r['reason']}")

# %% composite risk — burst transaction
from rules import compute_composite_risk

composite = compute_composite_risk(results_burst, txn_burst["amount"])
print(f"\nComposite for {txn_burst['id']}:")
print(f"  score={composite['score']}, level={composite['risk_level']}")
print(f"  auto_fraud={composite['auto_fraud']}, auto_legit={composite['auto_legit']}")
print(f"  combo={composite['combo_triggered']}")
print(f"  summary: {composite['summary']}")

# %% run all tools on balance drain (T006)
txn_drain = SAMPLE_TXNS[5]  # T006 — 95% drain
ctx_drain = build_context(txn_drain)
results_drain = [(tool.name, invoke_tool(tool, ctx_drain)) for tool in RULE_TOOLS]
composite_drain = compute_composite_risk(results_drain, txn_drain["amount"])

print(f"\nComposite for {txn_drain['id']} (balance drain, €{txn_drain['amount']}):")
print(f"  score={composite_drain['score']}, auto_fraud={composite_drain['auto_fraud']}")
flagged = [(n, r) for n, r in results_drain if r["risk"] != "low"]
for n, r in flagged:
    print(f"  ⚠️ {n}: {r['risk']} — {r['reason']}")

# %% run all tools on structuring (T007)
txn_struct = SAMPLE_TXNS[6]  # T007 — €4,999
ctx_struct = build_context(txn_struct)
results_struct = [(tool.name, invoke_tool(tool, ctx_struct)) for tool in RULE_TOOLS]
composite_struct = compute_composite_risk(results_struct, txn_struct["amount"])

print(f"\nComposite for {txn_struct['id']} (structuring, €{txn_struct['amount']}):")
print(
    f"  score={composite_struct['score']}, auto_fraud={composite_struct['auto_fraud']}"
)

# %% triage all transactions
print("\n--- Full triage ---")
for txn in SAMPLE_TXNS:
    ctx = build_context(txn)
    results = [(tool.name, invoke_tool(tool, ctx)) for tool in RULE_TOOLS]
    c = compute_composite_risk(results, txn["amount"])
    status = "FRAUD" if c["auto_fraud"] else "LEGIT" if c["auto_legit"] else "AMBIG"
    print(f"  {txn['id']}: €{txn['amount']:>8.0f} → score={c['score']:5.1f} → {status}")
