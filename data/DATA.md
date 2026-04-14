# data/ — The Prep Kitchen

Before any fraud detection happens, we need to understand the data. This module
reads the raw dataset and prepares three things every other layer needs:

1. **Transactions** — the raw records, normalized
2. **Account profiles** — a statistical summary of each account's history
3. **Relationship graph** — who sends money to whom

**Cost**: $0 — pure computation.

## What It Builds

### Transactions (`ingest.py`)

Reads JSON or CSV and produces a clean list of dicts. Every transaction has:

```
id            →  unique identifier
sender_id     →  who sent the money
receiver_id   →  who received it
amount        →  how much (EUR)
timestamp     →  when (Unix epoch)
sender_balance → sender's balance before this transaction
```

### Account Profiles (`profiles.py`)

For every account, we compute a "fingerprint" of their normal behavior.
This is what rules like `check_amount_anomaly` compare against.

Think of it as: *"What does normal look like for this person?"*

Key fields:
- **avg_amount / std_amount** — their typical transaction size and how much it varies
- **max_amount** — the biggest thing they've ever sent (for "first large" detection)
- **balance** — current balance (for drain detection)
- **avg_time_between_txns** — how often they transact (for frequency shift detection)
- **known_counterparties** — who they've sent to before (for new payee detection)
- **last_seen** — when they last transacted (for dormant reactivation)
- **is_new** — account has < 3 txns or < 7 days old

Also provides `get_account_context(account_id, n=20)` — returns the last 20
transactions for an account, used as input to velocity and behavioral tools.

### Relationship Graph (`graph.py`)

A network where accounts are nodes and transactions are edges. This powers
the graph-based fraud signals (fan-in, fan-out, mule chains, circular flows).

Each **node** knows:
- `in_degree` — how many distinct senders send to this account
- `out_degree` — how many distinct receivers this account sends to
- `clustering_coefficient` — how interconnected this account's neighbors are

Each **edge** knows:
- How many transactions between this pair
- Total and average amount
- When all transactions happened (timestamps)

A legitimate account has a dense local cluster (friends, family, regular shops).
A mule account has low clustering — it connects otherwise-disconnected parties.
