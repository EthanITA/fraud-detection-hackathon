# %% env setup
import sys, os  # noqa: E401
try:
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
except NameError:
    sys.path.insert(0, os.getcwd())
import _env  # noqa: F401

# %% load sample transactions
from _sample import SAMPLE_TXNS

print(f"Loaded {len(SAMPLE_TXNS)} sample transactions")
for t in SAMPLE_TXNS[:3]:
    print(f"  {t['id']}: {t['sender_id']} → {t['receiver_id']} €{t['amount']}")

# %% compute account profiles
from data import compute_account_profiles

profiles = compute_account_profiles(SAMPLE_TXNS)
print(f"\n{len(profiles)} account profiles:")
for aid, p in sorted(profiles.items()):
    print(f"  {aid}: txns={p['txn_count']}, avg=€{p['avg_amount']:.0f}, "
          f"balance=€{p['balance']:.0f}, new={p['is_new']}")

# %% inspect one profile in detail
a001 = profiles["A001"]
print("\nA001 full profile:")
for k, v in a001.items():
    print(f"  {k}: {v}")

# %% get account context (last 20 sent txns)
from data import get_account_context

history = get_account_context("A003", SAMPLE_TXNS, n=20)
print(f"\nA003 history ({len(history)} txns):")
for t in history:
    print(f"  {t['id']}: €{t['amount']} @ {t['timestamp']}")

# %% build relationship graph
from data import build_relationship_graph

graph = build_relationship_graph(SAMPLE_TXNS)
print(f"\nGraph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")

# %% inspect nodes
print("\nNodes:")
for n in sorted(graph["nodes"], key=lambda x: x["id"]):
    print(f"  {n['id']}: in={n['in_degree']} out={n['out_degree']} "
          f"cluster={n['clustering_coefficient']:.2f} new={n['is_new']}")

# %% inspect edges
print("\nEdges:")
for e in graph["edges"]:
    print(f"  {e['source']} → {e['target']}: {e['count']}× "
          f"total=€{e['total_amount']:.0f} avg=€{e['avg_amount']:.0f}")

# %% fan-in check — A011 should have high in-degree
a011 = next(n for n in graph["nodes"] if n["id"] == "A011")
print(f"\nA011 (fan-in target): in_degree={a011['in_degree']}, "
      f"out_degree={a011['out_degree']}")
