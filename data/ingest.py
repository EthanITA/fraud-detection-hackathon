# %% imports
from __future__ import annotations

import csv
import json

# %% field mapping
# Adjust on hackathon day: map raw field names → guaranteed keys.
FIELD_MAP: dict[str, str] = {
    "transaction_id": "id",
    "from_account": "sender_id",
    "to_account": "receiver_id",
    "amount": "amount",
    "timestamp": "timestamp",
    "balance": "sender_balance",
}

GUARANTEED_KEYS = {
    "id",
    "sender_id",
    "receiver_id",
    "amount",
    "timestamp",
    "sender_balance",
}


# %% _normalize
def _normalize(raw: dict) -> dict:
    txn = dict(raw)
    for src, dst in FIELD_MAP.items():
        if src in txn:
            val = txn[src]
            if src != dst:
                txn[dst] = val
            if dst in ("amount", "timestamp", "sender_balance"):
                txn[dst] = float(val) if val is not None else None
            elif dst in ("id", "sender_id", "receiver_id"):
                txn[dst] = str(val)
    if "sender_balance" not in txn:
        txn["sender_balance"] = None
    return txn


# %% parse_dataset
def parse_dataset(path: str) -> list[dict]:
    """Parse a JSON or CSV dataset into a list of transaction dicts.

    Each dict contains the 6 guaranteed keys plus all original fields.
    """
    if path.endswith(".json"):
        with open(path) as f:
            rows = json.load(f)
    elif path.endswith(".csv"):
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
    else:
        raise ValueError(f"Unsupported file format: {path}")

    return [_normalize(row) for row in rows]
