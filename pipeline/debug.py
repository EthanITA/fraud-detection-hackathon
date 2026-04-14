# %% env setup
import sys, os  # noqa: E401
try:
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
except NameError:
    sys.path.insert(0, os.getcwd())
import _env  # noqa: F401

# %% resolve upstream: write sample data to temp file
import json
import tempfile

from _sample import SAMPLE_TXNS

tmpfile = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
json.dump(SAMPLE_TXNS, tmpfile)
tmpfile.close()
print(f"Sample data written to: {tmpfile.name}")

# %% build pipeline
from pipeline import build_pipeline

pipeline = build_pipeline()
graph = pipeline.get_graph()
print(f"Pipeline nodes: {[n for n in graph.nodes if not n.startswith('__')]}")

# %% inspect pipeline state type
from pipeline.state import PipelineState

print("\nPipelineState fields:")
for field, annotation in PipelineState.__annotations__.items():
    print(f"  {field}: {annotation}")

# %% run Layer 0 only — ingest
from pipeline.nodes import ingest

state_after_ingest = ingest({"dataset_path": tmpfile.name})
txns = state_after_ingest["transactions"]
profiles = state_after_ingest["profiles"]
graph_data = state_after_ingest["graph"]

print(f"\nAfter ingest:")
print(f"  {len(txns)} transactions")
print(f"  {len(profiles)} profiles")
print(f"  {len(graph_data['nodes'])} graph nodes, {len(graph_data['edges'])} edges")

# %% run Layer 1 — rules
from pipeline.nodes import run_rules

state_after_rules = {**state_after_ingest}
state_after_rules.update(run_rules(state_after_ingest))
rule_results = state_after_rules["rule_results"]

print(f"\nAfter run_rules:")
print(f"  {len(rule_results)} transactions scored")
for txn_id, results in list(rule_results.items())[:3]:
    flagged = [(n, r) for n, r in results if r["risk"] != "low"]
    print(f"  {txn_id}: {len(flagged)} flags")

# %% run triage
from pipeline.nodes import triage

state_after_triage = {**state_after_rules}
state_after_triage.update(triage(state_after_rules))

auto_legit = state_after_triage.get("auto_legit", [])
auto_fraud = state_after_triage.get("auto_fraud", [])
ambiguous = state_after_triage.get("ambiguous_prioritized", [])

print(f"\nAfter triage:")
print(f"  auto_legit: {len(auto_legit)} txns — {auto_legit}")
print(f"  auto_fraud: {len(auto_fraud)} txns — {auto_fraud}")
print(f"  ambiguous:  {len(ambiguous)} txns (by priority):")
for txn_id, priority in ambiguous:
    txn = next(t for t in txns if t["id"] == txn_id)
    print(f"    {txn_id}: priority={priority:.0f} (€{txn['amount']} × score)")

# %% Layer 2+3 are stubs — inspect what specialists would receive
print("\n--- What specialists would process ---")
for txn_id, priority in ambiguous[:5]:
    txn = next(t for t in txns if t["id"] == txn_id)
    rule_res = rule_results[txn_id]
    flagged = [f"{n}:{r['risk']}" for n, r in rule_res if r["risk"] != "low"]
    print(f"  {txn_id}: €{txn['amount']:>8.0f} | priority={priority:>10.0f} | flags: {', '.join(flagged)}")

# %% collect output (with stubs, only auto_fraud appears)
from pipeline.nodes import collect_output

final = collect_output(state_after_triage)
print(f"\nFinal fraud IDs: {final['fraud_ids']}")
print(f"Debug entries: {len(final['debug_output'])}")

# %% cleanup
import os

os.unlink(tmpfile.name)
print(f"\nCleaned up {tmpfile.name}")
