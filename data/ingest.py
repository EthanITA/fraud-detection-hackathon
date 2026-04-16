# %% imports
from __future__ import annotations

import csv
import json
from pathlib import Path

# %% field mapping — official Reply Mirror challenge format
FIELD_MAP: dict[str, str] = {
    "transaction_id": "id",
    "sender_id": "sender_id",
    "recipient_id": "receiver_id",
    "amount": "amount",
    "timestamp": "timestamp",
    "balance_after": "sender_balance",
    # New fields kept as-is
    "transaction_type": "transaction_type",
    "location": "location",
    "payment_method": "payment_method",
    "sender_iban": "sender_iban",
    "recipient_iban": "recipient_iban",
    "description": "description",
}

FLOAT_KEYS = {"amount", "sender_balance"}
STR_KEYS = {"id", "sender_id", "receiver_id", "transaction_type", "location",
            "payment_method", "sender_iban", "recipient_iban", "description"}


# %% _parse_timestamp
def _parse_timestamp(val: str) -> float:
    """Parse ISO timestamp string to epoch seconds."""
    from datetime import datetime
    if not val:
        return 0.0
    try:
        return datetime.fromisoformat(val).timestamp()
    except (ValueError, TypeError):
        return float(val) if val else 0.0


# %% _normalize
def _normalize(raw: dict) -> dict:
    txn = dict(raw)
    for src, dst in FIELD_MAP.items():
        if src in txn:
            val = txn[src]
            if src != dst:
                txn[dst] = val
            if dst in FLOAT_KEYS:
                try:
                    txn[dst] = float(val) if val not in (None, "") else None
                except (ValueError, TypeError):
                    txn[dst] = None
            elif dst == "timestamp":
                txn[dst] = _parse_timestamp(val)
                txn["timestamp_raw"] = val  # keep original for display
            elif dst in STR_KEYS:
                txn[dst] = str(val) if val is not None else ""
    if "sender_balance" not in txn:
        txn["sender_balance"] = None
    return txn


# %% find_transactions_file
def find_transactions_file(dir_path: str) -> str:
    """Find the transactions file in a dataset directory.

    Looks for JSON/CSV files whose name contains 'transaction'.
    Falls back to the first JSON/CSV file that isn't a known supplementary file.
    """
    d = Path(dir_path)
    skip = {"users.json", "locations.json", "status.csv", "personas.md"}

    # Priority: files with "transaction" in the name
    for ext in ("*.json", "*.csv"):
        for f in d.glob(ext):
            if "transaction" in f.name.lower() and f.name not in skip:
                return str(f)

    # Fallback: first JSON/CSV not in the skip list
    for ext in ("*.json", "*.csv"):
        for f in d.glob(ext):
            if f.name not in skip:
                return str(f)

    raise FileNotFoundError(f"No transactions file found in {dir_path}")


# %% parse_dataset
def parse_dataset(path: str) -> list[dict]:
    """Parse a JSON or CSV dataset into a list of transaction dicts.

    Accepts either a file path or a directory path.
    Each dict contains the 6 guaranteed keys plus all original fields.
    """
    p = Path(path)
    if p.is_dir():
        path = find_transactions_file(path)

    if path.endswith(".json"):
        with open(path) as f:
            rows = json.load(f)
    elif path.endswith(".csv"):
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
    else:
        raise ValueError(f"Unsupported file format: {path}")

    return [_normalize(row) for row in rows]
