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

# %% config
PROJECT_ROOT = str(__import__("pathlib").Path(__file__).resolve().parent.parent)
_default = os.path.join(PROJECT_ROOT, "challenges", "1. The Truman Show - train")
DATASET = sys.argv[1] if len(sys.argv) > 1 else _default

# %% load transactions
from data import parse_dataset

txns = parse_dataset(DATASET)
print(f"Loaded {len(txns)} transactions from {DATASET}")
for t in txns[:3]:
    print(f"  {t['id'][:12]}.. {t['sender_id']} → {t['receiver_id']} €{t['amount']} ({t.get('transaction_type', '?')})")

# %% compute account profiles
from data import compute_account_profiles

profiles = compute_account_profiles(txns)
print(f"\n{len(profiles)} account profiles:")
for aid, p in sorted(profiles.items()):
    o = p["overall"]
    print(
        f"  {aid}: txns={o['txn_count']}(sent={o['sent_count']},recv={o['received_count']}), "
        f"avg=€{o['avg_amount']:.0f}, balance=€{o['balance']:.0f}, "
        f"span={o['history_span_days']}d, new={o['is_new']}"
    )

# %% inspect citizen profiles with category breakdown
citizen_ids = sorted([aid for aid in profiles if "-" in aid])
for cid in citizen_ids:
    p = profiles[cid]
    print(f"\n{'='*60}")
    print(f"{cid}")
    print(f"{'='*60}")
    for cat_name, label in [
        ("overall", "OVERALL"),
        ("within_system", "WITHIN SYSTEM (transfer + direct debit)"),
        ("external", "EXTERNAL (e-commerce + in-person)"),
        ("cash_out", "CASH OUT (withdrawal)"),
    ]:
        c = p[cat_name]
        if c["txn_count"] == 0:
            print(f"  {label}: (none)")
            continue
        print(
            f"  {label}: txns={c['txn_count']}(s={c['sent_count']},r={c['received_count']}), "
            f"avg=€{c['avg_amount']:.0f}, std=€{c['std_amount']:.0f}, "
            f"range=[€{c['min_amount']:.0f}–€{c['max_amount']:.0f}], "
            f"span={c['history_span_days']}d, new={c['is_new']}"
        )

# %% get account context (last 20 sent txns)
from data import get_account_context

if citizen_ids:
    cid = citizen_ids[0]
    history = get_account_context(cid, txns, n=20)
    print(f"\n{cid} history ({len(history)} txns):")
    for t in history[:5]:
        print(f"  {t['id'][:12]}.. €{t['amount']} @ {t.get('timestamp_raw', t['timestamp'])}")

# %% build relationship graph
from data import build_relationship_graph

graph = build_relationship_graph(txns)
print(f"\nGraph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")

# %% inspect nodes
print("\nNodes (top 10 by in-degree):")
for n in sorted(graph["nodes"], key=lambda x: x["in_degree"], reverse=True)[:10]:
    print(
        f"  {n['id']}: in={n['in_degree']} out={n['out_degree']} "
        f"cluster={n['clustering_coefficient']:.2f} new={n['is_new']}"
    )

# %% citizen profiles
from data import build_citizen_profiles

citizens = build_citizen_profiles(DATASET)
print(f"\n{len(citizens)} citizen profiles:")
for biotag, c in citizens.items():
    print(f"  {biotag}: {c['summary']}")
