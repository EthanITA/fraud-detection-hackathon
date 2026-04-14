# %% imports
from __future__ import annotations

import statistics
from collections import defaultdict


# %% compute_account_profiles
def compute_account_profiles(txns: list[dict]) -> dict[str, dict]:
    """Single O(n) pass over all transactions. Builds an AccountProfile per account.

    Profile keys: txn_count, avg_amount, std_amount, min_amount, max_amount,
    balance, avg_time_between_txns, unique_counterparties, known_counterparties,
    total_sent, total_received, first_seen, last_seen, is_new
    """
    sent: dict[str, list[dict]] = defaultdict(list)
    received: dict[str, list[float]] = defaultdict(list)
    counterparties: dict[str, set[str]] = defaultdict(set)
    timestamps: dict[str, list[float]] = defaultdict(list)
    balances: dict[str, float | None] = {}

    for txn in txns:
        sid, rid = txn["sender_id"], txn["receiver_id"]
        amt, ts = txn["amount"], txn["timestamp"]

        sent[sid].append(txn)
        received[rid].append(amt)
        counterparties[sid].add(rid)
        counterparties[rid].add(sid)
        timestamps[sid].append(ts)
        timestamps[rid].append(ts)

        if txn.get("sender_balance") is not None:
            balances[sid] = txn["sender_balance"]

    all_ids = set(sent) | set(received)
    profiles: dict[str, dict] = {}

    for aid in all_ids:
        amounts = [t["amount"] for t in sent.get(aid, [])]
        total_sent = sum(amounts)
        total_received = sum(received.get(aid, []))
        txn_count = len(sent.get(aid, [])) + len(received.get(aid, []))

        ts_sorted = sorted(timestamps.get(aid, []))
        if len(ts_sorted) >= 2:
            gaps = [ts_sorted[i + 1] - ts_sorted[i] for i in range(len(ts_sorted) - 1)]
            avg_gap = statistics.mean(gaps)
        else:
            avg_gap = 0.0

        first_seen = ts_sorted[0] if ts_sorted else 0.0
        last_seen = ts_sorted[-1] if ts_sorted else 0.0
        history_days = (last_seen - first_seen) / 86400

        balance = balances.get(aid)
        if balance is None:
            balance = total_received - total_sent

        cps = counterparties.get(aid, set())

        profiles[aid] = {
            "txn_count": txn_count,
            "avg_amount": statistics.mean(amounts) if amounts else 0.0,
            "std_amount": statistics.stdev(amounts) if len(amounts) >= 2 else 0.0,
            "min_amount": min(amounts) if amounts else 0.0,
            "max_amount": max(amounts) if amounts else 0.0,
            "balance": balance,
            "avg_time_between_txns": avg_gap,
            "unique_counterparties": len(cps),
            "known_counterparties": cps,
            "total_sent": total_sent,
            "total_received": total_received,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "is_new": txn_count < 3 or history_days < 7,
        }

    return profiles


# %% get_account_context
def get_account_context(
    account_id: str, txns: list[dict], n: int = 20
) -> list[dict]:
    """Return the last n transactions where account_id is the sender."""
    sender_txns = [t for t in txns if t["sender_id"] == account_id]
    sender_txns.sort(key=lambda t: t["timestamp"], reverse=True)
    return sender_txns[:n]
