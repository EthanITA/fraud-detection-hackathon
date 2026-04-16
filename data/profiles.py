# %% imports
from __future__ import annotations

import statistics
from collections import defaultdict


# %% transaction type categories
TXN_CATEGORIES = {
    "transfer": "within_system",
    "direct debit": "within_system",
    "e-commerce": "external",
    "in-person payment": "external",
    "withdrawal": "cash_out",
}

ALL_CATEGORIES = ["within_system", "external", "cash_out"]


# %% _categorize
def _categorize(txn: dict) -> str:
    return TXN_CATEGORIES.get(txn.get("transaction_type", ""), "external")


# %% _compute_subprofile
def _compute_subprofile(
    sent_txns: list[dict],
    received_amounts: list[float],
    all_timestamps: list[float],
    counterparties: set[str],
    balance: float | None,
    dataset_start: float,
) -> dict:
    """Compute a profile from a subset of transactions."""
    amounts = [t["amount"] for t in sent_txns]
    total_sent = sum(amounts)
    total_received = sum(received_amounts)
    txn_count = len(sent_txns) + len(received_amounts)

    ts_sorted = sorted(all_timestamps)
    if len(ts_sorted) >= 2:
        gaps = [ts_sorted[i + 1] - ts_sorted[i] for i in range(len(ts_sorted) - 1)]
        avg_gap = statistics.mean(gaps)
    else:
        avg_gap = 0.0

    first_seen = ts_sorted[0] if ts_sorted else 0.0
    last_seen = ts_sorted[-1] if ts_sorted else 0.0
    history_span_days = (last_seen - first_seen) / 86400 if first_seen else 0.0

    # "new" = first seen in last 20% of dataset OR fewer than 3 transactions
    time_since_start = first_seen - dataset_start if dataset_start else 0.0
    is_new = txn_count < 3

    return {
        "txn_count": txn_count,
        "sent_count": len(sent_txns),
        "received_count": len(received_amounts),
        "avg_amount": statistics.mean(amounts) if amounts else 0.0,
        "std_amount": statistics.stdev(amounts) if len(amounts) >= 2 else 0.0,
        "min_amount": min(amounts) if amounts else 0.0,
        "max_amount": max(amounts) if amounts else 0.0,
        "balance": balance,
        "avg_time_between_txns": avg_gap,
        "unique_counterparties": len(counterparties),
        "known_counterparties": sorted(counterparties),
        "total_sent": total_sent,
        "total_received": total_received,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "history_span_days": round(history_span_days, 1),
        "is_new": is_new,
    }


# %% compute_account_profiles
def compute_account_profiles(txns: list[dict]) -> dict[str, dict]:
    """Single O(n) pass. Builds per-account profiles with category breakdowns.

    Each profile has:
    - overall: aggregated across all transaction types
    - within_system: transfers + direct debits
    - external: e-commerce + in-person payments
    - cash_out: withdrawals
    """
    # Collect per-account, per-category data
    sent: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    received: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    counterparties: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    timestamps: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    balances: dict[str, float | None] = {}

    for txn in txns:
        sid, rid = txn["sender_id"], txn["receiver_id"]
        amt, ts = txn["amount"], txn["timestamp"]
        cat = _categorize(txn)

        sent[sid][cat].append(txn)
        sent[sid]["_all"].append(txn)
        if rid:
            received[rid][cat].append(amt)
            received[rid]["_all"].append(amt)
            counterparties[sid][cat].add(rid)
            counterparties[sid]["_all"].add(rid)
            counterparties[rid][cat].add(sid)
            counterparties[rid]["_all"].add(sid)

        timestamps[sid][cat].append(ts)
        timestamps[sid]["_all"].append(ts)
        if rid:
            timestamps[rid][cat].append(ts)
            timestamps[rid]["_all"].append(ts)

        if txn.get("sender_balance") is not None:
            balances[sid] = txn["sender_balance"]

    all_ids = set(sent) | set(received)
    all_timestamps_flat = [t["timestamp"] for t in txns]
    dataset_start = min(all_timestamps_flat) if all_timestamps_flat else 0.0

    profiles: dict[str, dict] = {}
    for aid in all_ids:
        balance = balances.get(aid)
        if balance is None:
            balance = sum(received.get(aid, {}).get("_all", [])) - sum(
                t["amount"] for t in sent.get(aid, {}).get("_all", [])
            )

        profile: dict = {}

        # Overall
        profile["overall"] = _compute_subprofile(
            sent.get(aid, {}).get("_all", []),
            received.get(aid, {}).get("_all", []),
            timestamps.get(aid, {}).get("_all", []),
            counterparties.get(aid, {}).get("_all", set()),
            balance,
            dataset_start,
        )

        # Per-category
        for cat in ALL_CATEGORIES:
            profile[cat] = _compute_subprofile(
                sent.get(aid, {}).get(cat, []),
                received.get(aid, {}).get(cat, []),
                timestamps.get(aid, {}).get(cat, []),
                counterparties.get(aid, {}).get(cat, set()),
                None,  # balance only meaningful at overall level
                dataset_start,
            )

        profiles[aid] = profile

    return profiles


# %% compute_temporal_profiles
def compute_temporal_profiles(txns: list[dict]) -> dict[str, dict]:
    """Per-txn profiles using only PRIOR transactions — no data leak.

    Returns {txn_id: profile_dict} with category breakdowns.
    Each profile snapshot is frozen before the current transaction.
    """
    sorted_txns = sorted(txns, key=lambda t: t["timestamp"])
    dataset_start = sorted_txns[0]["timestamp"] if sorted_txns else 0.0

    # Running accumulators per sender, per category
    senders: dict[str, dict[str, dict]] = {}
    received_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    profiles: dict[str, dict] = {}

    for txn in sorted_txns:
        sid = txn["sender_id"]
        rid = txn["receiver_id"]
        cat = _categorize(txn)

        acc = senders.get(sid)
        if acc is None:
            profiles[txn["id"]] = _empty_temporal_profile()
        else:
            profiles[txn["id"]] = _snapshot_temporal_profile(
                acc, txn, received_counts.get(sid, {}), dataset_start,
            )

        # Update running state AFTER snapshotting
        if acc is None:
            senders[sid] = {}
            acc = senders[sid]

        for key in [cat, "_all"]:
            if key not in acc:
                acc[key] = {"amounts": [], "counterparties": set(), "timestamps": []}
            acc[key]["amounts"].append(txn["amount"])
            if rid:
                acc[key]["counterparties"].add(rid)
            acc[key]["timestamps"].append(txn["timestamp"])

        if rid:
            received_counts[rid][cat] += 1
            received_counts[rid]["_all"] += 1

    return profiles


def _empty_temporal_profile() -> dict:
    """Profile for a sender with no prior transactions."""
    empty = {
        "txn_count": 0, "sent_count": 0, "received_count": 0,
        "avg_amount": 0.0, "std_amount": 0.0,
        "median_amount": 0.0, "mad_amount": 0.0,
        "min_amount": 0.0, "max_amount": 0.0,
        "balance": None, "avg_time_between_txns": 0.0,
        "unique_counterparties": 0, "known_counterparties": [],
        "total_sent": 0.0, "total_received": 0.0,
        "first_seen": 0.0, "last_seen": 0.0,
        "history_span_days": 0.0, "is_new": True,
    }
    return {
        "overall": dict(empty),
        "within_system": dict(empty),
        "external": dict(empty),
        "cash_out": dict(empty),
    }


def _snapshot_from_accumulator(
    acc_cat: dict | None,
    received_count: int,
    balance: float | None,
    dataset_start: float,
) -> dict:
    """Build one sub-profile from accumulated prior-only data."""
    if not acc_cat or not acc_cat["amounts"]:
        return {
            "txn_count": received_count, "sent_count": 0,
            "received_count": received_count,
            "avg_amount": 0.0, "std_amount": 0.0,
            "median_amount": 0.0, "mad_amount": 0.0,
            "min_amount": 0.0, "max_amount": 0.0,
            "balance": balance, "avg_time_between_txns": 0.0,
            "unique_counterparties": 0, "known_counterparties": [],
            "total_sent": 0.0, "total_received": 0.0,
            "first_seen": 0.0, "last_seen": 0.0,
            "history_span_days": 0.0, "is_new": True,
        }

    amounts = acc_cat["amounts"]
    cps = acc_cat["counterparties"]
    ts_list = acc_cat["timestamps"]

    avg = statistics.mean(amounts)
    std = statistics.stdev(amounts) if len(amounts) >= 2 else 0.0

    if len(amounts) >= 2:
        median = statistics.median(amounts)
        mad = statistics.median([abs(a - median) for a in amounts])
    else:
        median = amounts[0]
        mad = 0.0

    ts_sorted = sorted(ts_list)
    if len(ts_sorted) >= 2:
        gaps = [ts_sorted[i + 1] - ts_sorted[i] for i in range(len(ts_sorted) - 1)]
        avg_gap = statistics.mean(gaps)
    else:
        avg_gap = 0.0

    first_seen = ts_sorted[0] if ts_sorted else 0.0
    last_seen = ts_sorted[-1] if ts_sorted else 0.0
    history_span_days = (last_seen - first_seen) / 86400 if first_seen else 0.0
    txn_count = len(amounts) + received_count

    return {
        "txn_count": txn_count,
        "sent_count": len(amounts),
        "received_count": received_count,
        "avg_amount": avg,
        "std_amount": std,
        "median_amount": median,
        "mad_amount": mad,
        "min_amount": min(amounts),
        "max_amount": max(amounts),
        "balance": balance,
        "avg_time_between_txns": avg_gap,
        "unique_counterparties": len(cps),
        "known_counterparties": sorted(cps),
        "total_sent": sum(amounts),
        "total_received": 0.0,
        "first_seen": first_seen,
        "last_seen": last_seen,
        "history_span_days": round(history_span_days, 1),
        "is_new": txn_count < 3,
    }


def _snapshot_temporal_profile(
    acc: dict,
    txn: dict,
    received_counts: dict[str, int],
    dataset_start: float,
) -> dict:
    """Build full temporal profile with category breakdowns."""
    balance = txn.get("sender_balance")
    result = {}
    result["overall"] = _snapshot_from_accumulator(
        acc.get("_all"), received_counts.get("_all", 0), balance, dataset_start,
    )
    for cat in ALL_CATEGORIES:
        result[cat] = _snapshot_from_accumulator(
            acc.get(cat), received_counts.get(cat, 0), None, dataset_start,
        )
    return result


# %% get_account_context
def get_account_context(account_id: str, txns: list[dict], n: int = 20) -> list[dict]:
    """Return the last n transactions where account_id is the sender."""
    sender_txns = [t for t in txns if t["sender_id"] == account_id]
    sender_txns.sort(key=lambda t: t["timestamp"], reverse=True)
    return sender_txns[:n]
