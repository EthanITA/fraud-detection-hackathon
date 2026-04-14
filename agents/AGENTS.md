# agents/ — Layers 2 + 3: LLM Agents

## Architecture

```
ambiguous txns (score 2–5 from Layer 1)
        │
        ▼
┌─────────────────────────────────────────┐
│  Layer 2: 3 Specialists (parallel)      │
│                                         │
│  ┌───────────┐ ┌──────────┐ ┌────────┐ │
│  │ Velocity  │ │  Amount  │ │ Relat. │ │
│  │ gpt-4o-   │ │ gpt-4o-  │ │ gpt-4o-│ │
│  │ mini      │ │ mini     │ │ mini   │ │
│  └─────┬─────┘ └────┬─────┘ └───┬────┘ │
│        └─────────────┼───────────┘      │
└──────────────────────┼──────────────────┘
                       ▼
┌──────────────────────────────────────────┐
│  Layer 3: Aggregator                     │
│  gpt-4o — economic weighting             │
│  → {is_fraud, confidence, reasoning}     │
└──────────────────────────────────────────┘
```

## Modules

### `specialists.py` — Layer 2

```python
run_all_specialists(
    txn: dict,
    history: list[dict],
    profile: dict,
    graph: dict,
    rule_results: list[tuple[str, RiskResult]],
) → list[SpecialistResult]
```

Runs 3 specialists in parallel. Each receives:
- The transaction
- Domain-specific context (history OR profile OR subgraph)
- Layer 1 rule results (so it doesn't re-derive what rules already found)

**SpecialistResult schema:**
```
{
  agent:              str       # "velocity" | "amount" | "relationship"
  risk_level:         str       # "high" | "medium" | "low"
  confidence:         float     # 0.0–1.0
  patterns_detected:  list[str] # e.g. ["BURST", "CARD_TESTING"]
  reasoning:          str       # human-readable explanation
}
```

#### Specialist Focus Areas

| Agent | Context | Patterns |
|---|---|---|
| **Velocity** | txn + last 20 txns | BURST, UNUSUAL_HOURS, CARD_TESTING, FREQUENCY_SHIFT, RAPID_ROUND_TRIP |
| **Amount** | txn + account profile | STATISTICAL_OUTLIER, ROUND_NUMBER, THRESHOLD_EVASION, STRUCTURING, BALANCE_DRAIN, FIRST_LARGE |
| **Relationship** | txn + 2-hop subgraph | MULE_CHAIN, NEW_PAYEE, FAN_IN, FAN_OUT, DORMANT_REACTIVATION, CIRCULAR_FLOW |

### `aggregator.py` — Layer 3

```python
run_aggregator(
    txn: dict,
    specialist_results: list[SpecialistResult],
    rule_results: list[tuple[str, RiskResult]],
) → Verdict
```

**Verdict schema:**
```
{
  transaction_id: str
  is_fraud:       bool
  confidence:     float    # 0.0–1.0
  reasoning:      str
}
```

**Decision rules (encoded in prompt + post-processing):**

| Condition | Verdict |
|---|---|
| 2+ specialists say HIGH | fraud |
| 1 specialist HIGH + confidence > 0.8 | fraud |
| amount > €10k + ANY specialist ≥ MEDIUM | fraud |
| amount €1k–€10k + composite confidence > 0.5 | fraud |
| amount < €1k + only if 2+ HIGH | fraud |
| amount < €100 + only if all 3 HIGH | fraud |

**Always-flag pattern combos:**
- BURST + BALANCE_DRAIN
- NEW_PAYEE + ROUND_NUMBER + LARGE
- MULE_CHAIN + THRESHOLD_EVASION

## Token Budget

| Component | Tokens/txn | Model | Cost/txn |
|---|---|---|---|
| 3 specialists | ~300 × 3 | gpt-4o-mini | ~$0.012 |
| Aggregator | ~800 | gpt-4o | ~$0.020 |
| **Total per txn** | ~1,700 | | **~$0.032** |

For ~500 ambiguous txns: ~$16 total (within $40 budget for datasets 1-3).
