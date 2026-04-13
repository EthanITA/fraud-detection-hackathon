# Reply AI Agent Challenge 2026

> **Date**: April 16, 2026 · 15:30–21:30 CEST (6 hours)
> **Team**: 3 members · **Prize**: €2,500/member (1st place)
> **Output**: `.txt` file listing fraudulent transaction IDs + source code `.zip`

---

## Rules

- Input: financial transaction datasets (JSON or CSV)
- Output: `.txt` file listing fraudulent transaction IDs + source `.zip`
- **5 datasets**: 1-3 available at start; 4-5 unlock after submitting eval for 1-3
- **Token budgets**: $40 for datasets 1-3 · $120 for datasets 4-5 (OpenRouter) — non-refillable
- **Submissions**: unlimited on training · **one shot only** on evaluation
- **LLM must orchestrate**: deterministic rules must be LangChain tools the agent decides to invoke — not hardcoded pipeline steps
- **Tracing**: Langfuse mandatory — session ID required in every submission

### Scoring

| Criterion | What it measures |
|---|---|
| **Count-based accuracy** | How many fraudulent txns you correctly identify (each txn weighted equally) |
| **Economic accuracy** | How much fraud value (€) you recover — catching a €50k fraud >> catching a €5 one |
| **Cost efficiency** | How sustainable your LLM token usage is |
| **Latency** | How fast your system processes transactions |
| **Architecture quality** | How well-designed your multi-agent system is (judges review source code) |
---

## Part 1 — Technical Spec

### Architecture: 4-layer triage funnel

```
RAW TRANSACTIONS (100%)
        │
        ▼
┌──────────────────────────┐
│  Layer 0: Data Ingestion │  $0 tokens — parse, feature extraction, graph
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  Layer 1: Rule Triage    │  $0 tokens — deterministic LangChain tools
│  ~70-85% filtered out    │  score 0-1 → auto-legit · ≥6 → auto-fraud
└────────────┬─────────────┘
             │ (~15-30% ambiguous, score 2-5)
             ▼
┌──────────────────────────┐
│  Layer 2: Specialists    │  ~60% of budget — 3 parallel agents (cheap model)
│  velocity · amount ·     │  each returns {risk_level, confidence, reasoning}
│  relationship            │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│  Layer 3: Aggregator     │  ~40% of budget — capable model, economic weighting
│  final fraud/legit +     │  threshold scales with txn amount
│  confidence score        │
└────────────┬─────────────┘
             │
         output.txt
```

### Layer 0 — Data ingestion (`data.py`)

```
parse_dataset(path) → list[Transaction]
compute_account_profiles(txns) → dict[account_id, AccountProfile]
  AccountProfile: txn_count, avg_amount, std_amount, min/max_amount,
                  avg_time_between_txns, unique_counterparties,
                  total_sent, total_received, first_seen, last_seen, is_new
build_relationship_graph(txns) → Graph
  nodes = accounts · edges = transactions
  edge attrs: count, total_amount, avg_amount
  node attrs: in_degree, out_degree, clustering_coefficient
get_account_context(account_id, txns, n=20) → list[Transaction]
compute_risk_features(txn, profile, graph) → RiskFeatures
```

### Layer 1 — Rule tools (`rules.py`)

Each returns `{risk: "high"|"medium"|"low", reason: str}`.

| Tool | Logic |
|---|---|
| `check_velocity` | high if avg gap < 60s · medium if < 300s |
| `check_amount_anomaly` | high if > avg+3σ · high if round number >€1k · medium near €5k/€10k/€15k thresholds |
| `check_balance_drain` | high if txn > 90% of sender balance · medium if > 70% |
| `check_counterparty` | high if new account + large amount · high if receiver has fan-in pattern |
| `check_temporal_pattern` | medium if 00:00–05:00 |
| `compute_composite_risk` | high=3 · medium=1 · low=0 → score 0-10 + summary |

**Triage thresholds**: score 0–1 → auto-legit · score ≥ 6 → auto-fraud · score 2–5 → Layer 2

### Layer 2 — Specialist agents (`agents.py`)

Model: `gpt-4o-mini` (or equivalent cheap model on OpenRouter)

| Agent | Input | Focus |
|---|---|---|
| Velocity | txn + sender's last 20 txns | BURST · UNUSUAL_HOURS · CARD_TESTING · FREQUENCY_SHIFT · RAPID_ROUND_TRIP |
| Amount | txn + sender account profile | STATISTICAL_OUTLIER · ROUND_NUMBER · THRESHOLD_EVASION · STRUCTURING · BALANCE_DRAIN · FIRST_LARGE |
| Relationship | txn + 2-hop subgraph | MULE_CHAIN · NEW_PAYEE · FAN_IN · FAN_OUT · DORMANT_REACTIVATION · CIRCULAR_FLOW |

All three run in parallel. Each outputs `{risk_level, confidence, patterns_detected, reasoning}`.

Prompts live in `prompts.py`.

### Layer 3 — Verdict aggregator (`agents.py`)

Model: `gpt-4o` (or equivalent capable model)

**Decision rules**:
- 2+ specialists say high → fraud
- 1 specialist says high with confidence > 0.8 → fraud
- Economic threshold scaling:
  - > €10,000 → flag if ANY specialist says medium or above
  - €1k–€10k → flag if composite confidence > 0.5
  - < €1,000 → flag only if 2+ high
  - < €100 → flag only if all 3 high

**Pattern combos** that always flag: BURST+BALANCE_DRAIN · NEW_PAYEE+ROUND_NUMBER+LARGE · MULE_CHAIN+THRESHOLD_EVASION

Output: `{transaction_id, is_fraud, confidence, reasoning}`

### Token budget

**Datasets 1-3 ($40)**

| Layer | Txns processed | Tokens/txn | Model | Est. cost |
|---|---|---|---|---|
| 0 + 1 | 3,000 | 0 | None | $0 |
| 2 (specialists) | ~500 | ~300 × 3 | gpt-4o-mini | ~$6–8 |
| 3 (aggregator) | ~500 | ~800 | gpt-4o | ~$8–12 |
| Debugging | — | — | — | ~$15–20 |
| **Total** | | | | **~$25–35** |

Safety valve: tighten Layer 1 thresholds to pass fewer transactions to Layer 2.

**Datasets 4-5 ($120)**: same architecture — consider upgrading all layers to a more capable model.

### Fraud domain reference

**Velocity signals**: transaction burst (< 60s gaps), unusual hours (00:00–05:00), card testing (rapid small txns → large one), sudden frequency spike.

**Amount signals**: just below reporting thresholds (€4,999 / €9,999), perfectly round amounts > €1k, amount wildly inconsistent with account history, near-total balance drain.

**Behavioral/relational signals**: account draining to new payee, mule chains (A→B→C→cashout), fan-in (many senders → one account → wire out), dormant account reactivation, circular flows.

**Economic weighting**: catching a €50k fraud is worth ~1000x a €50 fraud. The aggregator's threshold must scale inversely with amount.

### Code structure

```
reply-hackathon/
├── .env                  # OPENROUTER_API_KEY, LANGFUSE_*, TEAM_NAME
├── requirements.txt
├── config.py             # Env vars, model configs, Langfuse init, session ID gen
├── data.py               # Dataset parsing, feature extraction, graph builder
├── rules.py              # Deterministic triage tools (LangChain @tool)
├── agents.py             # Orchestrator, specialists, aggregator
├── prompts.py            # All system prompts as constants
├── main.py               # CLI: load dataset → run pipeline → write output.txt
├── utils.py              # JSON parsing helpers, logging
└── README.md
```

---

### Risk mitigation

| Risk | Mitigation |
|---|---|
| Token budget exhausted | Layer 1 filters aggressively. Monitor continuously. "Budget panic" mode: skip Layer 2, rules only. |
| Unexpected dataset format | Spend first 15 min exploring data. Parser handles both JSON and CSV. |
| LLM returns unparseable output | Wrap every call in try/catch with JSON repair. Fall back to rule-based verdict. |
| Langfuse connection fails | Log locally as backup. Session IDs are generated client-side. |
| Team member goes down | Modular architecture — anyone can pick up any module. All code in shared repo. |
| Wrong evaluation output format | Triple-check against problem statement before submitting. One person dedicated to QA. |

### Pre-challenge checklist

- [ ] Codebase scaffolded: config, data, rules, agents, prompts, main
- [ ] Langfuse integration tested with dummy session
- [ ] OpenRouter connection tested with own key
