# data/ — Layer 0: Data Ingestion

Parses datasets, builds account profiles, and constructs the relationship graph.
All outputs are plain dicts (JSON-serializable) for rule tool consumption.
$0 tokens — pure computation.

## Modules

### `ingest.py` — Dataset Parsing

```
parse_dataset(path: str) → list[Transaction]
```

Handles both JSON and CSV. Normalizes field names, types, and timestamps.

**Transaction schema:**
```
{
  id:              str
  sender_id:       str
  receiver_id:     str
  amount:          float        # EUR
  timestamp:       float        # Unix epoch
  sender_balance:  float        # Balance before this txn
}
```

### `profiles.py` — Account Profiles

```
compute_account_profiles(txns) → dict[account_id, AccountProfile]
get_account_context(account_id, txns, n=20) → list[Transaction]
```

**AccountProfile schema:**
```
{
  txn_count:                int
  avg_amount:               float
  std_amount:               float
  min_amount:               float
  max_amount:               float
  balance:                  float
  avg_time_between_txns:    float     # seconds
  unique_counterparties:    int
  known_counterparties:     list[str] # receiver IDs seen before
  total_sent:               float
  total_received:           float
  first_seen:               float     # Unix epoch
  last_seen:                float     # Unix epoch
  is_new:                   bool      # < 3 txns or < 7 days old
}
```

### `graph.py` — Relationship Graph

```
build_relationship_graph(txns) → Graph
```

**Graph schema (serializable dict):**
```
{
  nodes: [
    {
      id:                       str
      in_degree:                int
      out_degree:               int
      clustering_coefficient:   float
      is_new:                   bool
    }
  ],
  edges: [
    {
      source:       str
      target:       str
      count:        int
      total_amount: float
      avg_amount:   float
      timestamps:   list[float]
    }
  ]
}
```
