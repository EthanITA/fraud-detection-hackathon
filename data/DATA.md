# data/ — The Prep Kitchen

Imagine a restaurant kitchen. Before a single dish goes out, the prep cooks wash vegetables, portion proteins, and organize everything into containers. That's what this module does for fraud detection — it takes raw transaction data and prepares three things every downstream layer needs:

1. **Transactions** — the raw records, normalized to a common shape
2. **Account profiles** — a statistical fingerprint of each account's behavior
3. **Relationship graph** — a network of who sends money to whom

**Cost**: $0 — pure computation, no LLM calls.

---

## Why "Minimal Contract + Passthrough"?

We don't know the exact dataset format until hackathon day. It might be a CSV with 10 columns or a JSON with 50 fields. So instead of defining a rigid schema that breaks when reality hits, we take a different approach:

- **6 guaranteed keys** that all downstream code can rely on (the "contract")
- **Every other field preserved as-is** (the "passthrough")

This means rules, agents, and tools always find the 6 keys they need. But if the dataset has extra fields like `location`, `device_id`, or `ip_address`, those ride along too — and LLM agents can reason about them without any code changes.

**What's fixed**: The 6 guaranteed keys and their types. Every module depends on these.
**What's flexible**: Everything else — field name mappings, extra columns, file format.

---

## Guaranteed Keys

Every transaction dict has at least these 6 fields:

| Key | Type | Description |
|---|---|---|
| `id` | `str` | Unique transaction identifier |
| `sender_id` | `str` | Who sent the money |
| `receiver_id` | `str` | Who received it |
| `amount` | `float` | Transaction amount in EUR |
| `timestamp` | `float` | When it happened (Unix epoch) |
| `sender_balance` | `float \| None` | Sender's balance before this txn — `None` if the dataset doesn't provide it |

Plus **all original fields** from the raw dataset, preserved alongside these.

---

## Modules

### `ingest.py` — Parse and Normalize

`parse_dataset(path: str) -> list[dict]`

Reads JSON or CSV and produces a list of transaction dicts. The heavy lifting is a **field name mapping** — a simple dict at the top of the file that translates whatever the dataset calls its columns into our 6 guaranteed keys:

```python
FIELD_MAP = {
    "transaction_id": "id",
    "from_account": "sender_id",
    "to_account": "receiver_id",
    # ... adjust on hackathon day
}
```

On hackathon day, you open `ingest.py`, update `FIELD_MAP`, and you're done.

**Key behavior**:
- If the dataset has a balance field, it becomes `sender_balance`
- If not, `sender_balance` is set to `None` (profiles.py will estimate it later)
- All original fields are kept — nothing is dropped

---

### `profiles.py` — Account Fingerprints

**Why precompute?** Every rule needs to ask "what's normal for this account?" If we computed that on the fly for each transaction, we'd scan the full history each time — O(n) per transaction, O(n²) total. Instead, we do one upfront pass over all transactions and cache the result. O(n) once, O(1) lookups forever.

#### `compute_account_profiles(txns: list[dict]) -> dict[str, dict]`

Single O(n) pass. Builds a profile per account with:

| Field | What it tells you |
|---|---|
| `txn_count` | How active this account is |
| `avg_amount` / `std_amount` | Typical transaction size and how much it varies |
| `min_amount` / `max_amount` | Range of transaction sizes |
| `balance` | Current balance (from `sender_balance` or estimated as `received - sent`) |
| `avg_time_between_txns` | How often they transact |
| `unique_counterparties` | Number of distinct accounts they interact with |
| `known_counterparties` | Set of account IDs they've transacted with before |
| `total_sent` / `total_received` | Aggregate flow |
| `first_seen` / `last_seen` | Activity window |
| `is_new` | Account has fewer than 3 txns or less than 7 days of history |

#### `get_account_context(account_id, txns, n=20) -> list[dict]`

Returns the last `n` transactions where this account is the **sender**, sorted by timestamp descending. Used as input for velocity checks and behavioral analysis.

---

### `graph.py` — Relationship Network

#### `build_relationship_graph(txns: list[dict]) -> dict`

Single upfront pass. Returns:

```python
{
    "nodes": [{"id", "in_degree", "out_degree", "clustering_coefficient", "is_new"}],
    "edges": [{"source", "target", "count", "total_amount", "avg_amount", "timestamps"}]
}
```

**Nodes** = accounts. A node's `clustering_coefficient` measures how interconnected its neighbors are. Legitimate accounts tend to cluster (friends, family, regular shops). Mule accounts have low clustering — they bridge otherwise-disconnected groups.

**Edges** = transaction relationships between two accounts. Each edge aggregates all transactions between a pair: how many, how much total, average size, and when they happened.

---

### `citizens.py` — Multi-Modal Citizen Context

Loads supplementary data from the dataset directory alongside transactions.

#### `build_citizen_profiles(dir_path: str) -> dict[str, dict]`

Master function that loads and merges all supplementary files:

| File | Loader | Output |
|---|---|---|
| `users.json` | `load_users()` | Demographics: age, job, residence, lat/lng |
| `locations.json` | `load_locations()` | Location summary: home city, visited cities, max distance, travel frequency |
| `status.csv` | `load_statuses()` | Health summary: activity/sleep/exposure trends, specialist visits |
| `personas.md` | `load_personas()` | Full natural-language persona description |

Each citizen profile contains:
- **`summary`** — compact one-liner (e.g., "95yo, Retired, lives in Detroit, high mobility/travel") — included in ALL specialist contexts
- **`location`** — pre-computed: home city, visited cities, max distance from home (km), travel pings count
- **`status`** — pre-computed: activity/sleep/exposure trends (increasing/declining/stable), specialist visit flag
- **`persona`** — full text — included only in behavioral specialist + aggregator contexts
- **`user`** — raw demographics

Gracefully returns `{}` if the path is a file (not a directory) or if supplementary files are missing.

## Quick Reference

```
parse_dataset("dataset_dir/")          # or a single file path
    → list[dict]  (each dict has 6 guaranteed keys + all raw fields)

compute_account_profiles(txns)
    → {"ACC001": {txn_count, avg_amount, ...}, ...}

get_account_context("ACC001", txns, n=20)
    → [last 20 sent txns for ACC001]

build_relationship_graph(txns)
    → {nodes: [...], edges: [...]}

build_citizen_profiles("dataset_dir/")
    → {"IAFGUHCK": {user, location, status, persona, summary}, ...}
```
