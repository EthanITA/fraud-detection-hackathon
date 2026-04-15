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
            "known_counterparties": sorted(cps),
            "total_sent": total_sent,
            "total_received": total_received,
            "first_seen": first_seen,
            "last_seen": last_seen,
            "is_new": txn_count < 3 or history_days < 7,
        }

    return profiles


# %% compute_temporal_profiles
def compute_temporal_profiles(txns: list[dict]) -> dict[str, dict]:
    """Per-txn profiles using only PRIOR transactions — no data leak.

    Returns {txn_id: profile_dict}. Each profile snapshot is frozen before
    the current transaction is incorporated, so the current txn cannot
    inflate its own σ, appear in known_counterparties, or skew the max.

    Includes median_amount and mad_amount for MAD-based outlier detection.
    """
    sorted_txns = sorted(txns, key=lambda t: t["timestamp"])

    # Running accumulators per sender
    senders: dict[str, dict] = {}
    received_counts: dict[str, int] = defaultdict(int)

    profiles: dict[str, dict] = {}

    for txn in sorted_txns:
        sid = txn["sender_id"]
        rid = txn["receiver_id"]

        acc = senders.get(sid)
        if acc is None:
            # First txn from this sender — empty prior history
            profiles[txn["id"]] = _empty_profile(txn, received_counts.get(sid, 0))
        else:
            profiles[txn["id"]] = _snapshot_profile(acc, txn, received_counts.get(sid, 0))

        # Update running state AFTER snapshotting
        if acc is None:
            senders[sid] = {
                "amounts": [],
                "counterparties": set(),
                "timestamps": [],
            }
            acc = senders[sid]
        acc["amounts"].append(txn["amount"])
        acc["counterparties"].add(rid)
        acc["timestamps"].append(txn["timestamp"])

        received_counts[rid] += 1

    return profiles


def _empty_profile(txn: dict, received_count: int) -> dict:
    """Profile for a sender with no prior transactions."""
    return {
        "txn_count": received_count,
        "avg_amount": 0.0,
        "std_amount": 0.0,
        "median_amount": 0.0,
        "mad_amount": 0.0,
        "min_amount": 0.0,
        "max_amount": 0.0,
        "balance": txn.get("sender_balance", 0),
        "avg_time_between_txns": 0.0,
        "unique_counterparties": 0,
        "known_counterparties": [],
        "total_sent": 0.0,
        "total_received": 0.0,
        "first_seen": 0.0,
        "last_seen": 0.0,
        "is_new": True,
    }


def _snapshot_profile(acc: dict, txn: dict, received_count: int) -> dict:
    """Freeze the sender's profile from accumulated prior-only data."""
    amounts = acc["amounts"]
    cps = acc["counterparties"]
    ts_list = acc["timestamps"]

    avg = statistics.mean(amounts) if amounts else 0.0
    std = statistics.stdev(amounts) if len(amounts) >= 2 else 0.0

    # MAD computation
    if len(amounts) >= 2:
        median = statistics.median(amounts)
        deviations = [abs(a - median) for a in amounts]
        mad = statistics.median(deviations)
    else:
        median = amounts[0] if amounts else 0.0
        mad = 0.0

    ts_sorted = sorted(ts_list)
    if len(ts_sorted) >= 2:
        gaps = [ts_sorted[i + 1] - ts_sorted[i] for i in range(len(ts_sorted) - 1)]
        avg_gap = statistics.mean(gaps)
    else:
        avg_gap = 0.0

    first_seen = ts_sorted[0] if ts_sorted else 0.0
    last_seen = ts_sorted[-1] if ts_sorted else 0.0
    history_days = (last_seen - first_seen) / 86400
    txn_count = len(amounts) + received_count

    return {
        "txn_count": txn_count,
        "avg_amount": avg,
        "std_amount": std,
        "median_amount": median,
        "mad_amount": mad,
        "min_amount": min(amounts) if amounts else 0.0,
        "max_amount": max(amounts) if amounts else 0.0,
        "balance": txn.get("sender_balance", 0),
        "avg_time_between_txns": avg_gap,
        "unique_counterparties": len(cps),
        "known_counterparties": sorted(cps),
        "total_sent": sum(amounts),
        "total_received": 0.0,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "is_new": txn_count < 3 or history_days < 7,
    }


# %% get_account_context
def get_account_context(account_id: str, txns: list[dict], n: int = 20) -> list[dict]:
    """Return the last n transactions where account_id is the sender."""
    sender_txns = [t for t in txns if t["sender_id"] == account_id]
    sender_txns.sort(key=lambda t: t["timestamp"], reverse=True)
    return sender_txns[:n]
