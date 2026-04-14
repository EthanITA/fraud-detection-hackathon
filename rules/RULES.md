# rules/ — Layer 1: Deterministic Triage

13 LangChain `@tool` functions across 4 signal categories. Each returns `{risk, reason}`.
All tools cost $0 tokens — pure Python logic.

## Tool Registry

### Time Signals (`time.py`)

| Tool | HIGH | MEDIUM |
|---|---|---|
| `check_velocity` | avg gap < 60s | avg gap < 300s |
| `check_temporal_pattern` | — | hour in [0, 5) |
| `check_card_testing` | 3+ micro-txns → large | 1–2 micro-txns → large |

### Amount Signals (`amount.py`)

| Tool | HIGH | MEDIUM |
|---|---|---|
| `check_amount_anomaly` | > avg+3σ; round >€1k | within €200 of reporting limit |
| `check_balance_drain` | drains > 90% balance | drains > 70% balance |
| `check_first_large` | > 5× max_amount | > 3× max_amount |

### Behavioral Signals (`behavioral.py`)

| Tool | HIGH | MEDIUM |
|---|---|---|
| `check_new_payee` | new receiver + amount >€1k | new receiver + amount >€200 |
| `check_dormant_reactivation` | >180 days silent + large | >90 days silent |
| `check_frequency_shift` | rate >10× baseline | rate >5× baseline |

### Graph Flow Signals (`graph.py`)

| Tool | HIGH | MEDIUM |
|---|---|---|
| `check_fan_in` | receiver in_degree > 10 | > 5 |
| `check_fan_out` | sender out_degree > 10 (24h) | > 5 |
| `check_mule_chain` | ≥70% forwarded in 30min | ≥50% in 2h |
| `check_circular_flow` | path back to sender ≤3 hops | — |

## Composite Risk (`__init__.py`)

```
compute_composite_risk(results: [(tool_name, RiskResult)], amount: float) → CompositeResult
```

### Weighted Scoring

| Category | Weight | Rationale |
|---|---|---|
| Temporal | 0.5× | Weak alone — legitimate users travel, work late |
| Standard | 1.0× | Baseline signals |
| Drain/testing | 1.5× | Strong behavioral indicators |
| Graph flow | 2.0× | Hardest to fake, most indicative of organized fraud |

### Always-Flag Combos

| Combo | Tools (all must be HIGH) |
|---|---|
| BURST + BALANCE_DRAIN | `check_velocity` + `check_balance_drain` |
| NEW_PAYEE + AMOUNT_ANOMALY | `check_new_payee` + `check_amount_anomaly` |
| MULE_CHAIN + STRUCTURING | `check_mule_chain` + `check_amount_anomaly` |

### Amount-Aware Triage

| Amount | Auto-legit ≤ | Auto-fraud ≥ | Rationale |
|---|---|---|---|
| > €10,000 | 0 | 4 | False negative cost is huge |
| €1k–€10k | 1 | 5 | Moderate caution |
| €100–€1k | 1 | 6 | Standard |
| < €100 | 2 | 8 | False positive cost outweighs fraud value |
