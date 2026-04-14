# Reply AI Agent Challenge 2026

> **Date**: April 16, 2026 · 15:30–21:30 CEST (6 hours)
> **Team**: 3 members · **Prize**: €2,500/member (1st place)
> **Output**: `.txt` file listing fraudulent transaction IDs + source code `.zip`

---

## Competition Rules

- Input: financial transaction datasets (JSON or CSV)
- Output: `.txt` file listing fraudulent transaction IDs + source `.zip`
- **5 datasets**: 1-3 available at start; 4-5 unlock after submitting eval for 1-3
- **Token budgets**: $40 for datasets 1-3 · $120 for datasets 4-5 (OpenRouter) — non-refillable
- **Submissions**: unlimited on training · **one shot only** on evaluation
- **LLM must orchestrate**: deterministic rules must be LangChain tools the agent decides to invoke
- **Tracing**: Langfuse mandatory — session ID required in every submission

### Scoring

| Criterion | What it measures |
|---|---|
| **Count-based accuracy** | How many fraudulent txns you correctly identify |
| **Economic accuracy** | How much fraud value (€) you recover — €50k fraud >> €5 one |
| **Cost efficiency** | How sustainable your LLM token usage is |
| **Latency** | How fast your system processes transactions |
| **Architecture quality** | How well-designed your multi-agent system is |

---

## Architecture: 4-Layer Triage Funnel

The key insight: most transactions are obviously legit. Cheap filters first,
expensive LLM calls only for the ambiguous middle.

```
RAW TRANSACTIONS (100%)
        │
        ▼
┌─────────────────────────────────┐
│  Layer 0: Data Ingestion        │  $0 — parse, profiles, graph
│  data/                          │  Minimal contract + passthrough
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Layer 1: Rule Triage           │  $0 — 13 LangChain tools × 4 categories
│  rules/                         │  Weighted score + combos + amount scaling
│  ~70-85% filtered out           │  Priority ranking: score × amount
└────────────┬────────────────────┘
             │ (~15-30% ambiguous)
             ▼
┌─────────────────────────────────┐
│  Layer 2: 4 Specialists         │  ~60% budget — parallel via Send API
│  agents/specialists.py          │  velocity · amount · behavioral · relationship
│  Structured output enforced     │  Each: {risk_level, confidence, patterns, reasoning}
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Layer 3: Aggregator            │  ~40% budget — economic weighting
│  agents/aggregator.py           │  Final verdict: {is_fraud, confidence, reasoning}
└────────────┬────────────────────┘
             │
      output.txt + debug.json
```

---

## Module Map

```
reply-hackathon/
├── main.py                  # CLI entry point (18 lines)
│
├── config/                  # Environment, models, Langfuse tracing
│   ├── CONFIG.md
│   ├── env.py               # .env loading + fail-fast validation
│   ├── models.py             # Model names, token limits, cost rates
│   └── langfuse.py           # LangGraph callback handler, session IDs
│
├── data/                    # Layer 0 — parsing, profiles, graph (implemented)
│   ├── DATA.md
│   ├── ingest.py             # FIELD_MAP + passthrough (adjust on hackathon day)
│   ├── profiles.py           # O(n) precomputed account profiles
│   └── graph.py              # Relationship graph with clustering coefficients
│
├── rules/                   # Layer 1 — 13 deterministic tools (stubs)
│   ├── RULES.md
│   ├── _types.py             # RiskLevel, weights, combos, thresholds (30 constants)
│   ├── time.py               # check_velocity, check_temporal_pattern, check_card_testing
│   ├── amount.py             # check_amount_anomaly, check_balance_drain, check_first_large
│   ├── behavioral.py         # check_new_payee, check_dormant_reactivation, check_frequency_shift
│   └── graph.py              # check_fan_in, check_fan_out, check_mule_chain, check_circular_flow
│
├── prompts/                 # System prompts for all LLM agents
│   ├── PROMPTS.md
│   ├── specialists.py        # VELOCITY_PROMPT, AMOUNT_PROMPT, BEHAVIORAL_PROMPT, RELATIONSHIP_PROMPT
│   └── aggregator.py         # AGGREGATOR_PROMPT
│
├── agents/                  # Layers 2+3 — LLM specialists + aggregator (stubs)
│   ├── AGENTS.md
│   ├── specialists.py        # 4 specialist nodes + Pydantic SpecialistOutput
│   └── aggregator.py         # Aggregator node + Pydantic AggregatorOutput
│
├── pipeline/                # LangGraph state machine (implemented)
│   ├── PIPELINE.md
│   ├── state.py              # PipelineState with budget + priority + debug output
│   ├── dispatch.py           # Tool context routing for 13 rule tools
│   ├── nodes.py              # All node functions (ingest → triage → specialists → aggregate → output)
│   └── graph.py              # StateGraph wiring with Send API fan-out
│
├── utils/                   # Cross-cutting helpers
│   ├── UTILS.md
│   ├── json_repair.py        # Fallback JSON parser (structured output is primary)
│   ├── budget.py             # BudgetTracker with panic mode at 15%
│   └── logging.py            # Structured logger
│
├── requirements.txt
└── .env                     # OPENROUTER_API_KEY, LANGFUSE_*, TEAM_NAME
```

---

## Module Dependency Map

```mermaid
flowchart LR
    subgraph foundation ["Foundation (no deps)"]
        direction TB
        CONFIG["config/\n<small>env · models · langfuse</small>"]
        UTILS["utils/\n<small>budget · logging · json_repair</small>"]
        PROMPTS["prompts/\n<small>4 specialist + 1 aggregator</small>"]
    end

    subgraph layer0 ["Layer 0 — $0"]
        DATA["data/\n<small>ingest · profiles · graph</small>"]
    end

    subgraph layer1 ["Layer 1 — $0"]
        RULES["rules/\n<small>13 tools × 4 categories\n+ composite risk</small>"]
    end

    subgraph layer23 ["Layer 2+3 — LLM budget"]
        AGENTS["agents/\n<small>4 specialists + aggregator\nPydantic structured output</small>"]
    end

    subgraph orchestrator ["Orchestrator"]
        PIPELINE["pipeline/\n<small>LangGraph state machine\nSend API fan-out</small>"]
    end

    MAIN["main.py\n<small>CLI entry point</small>"]

    UTILS -.->|cost rates| CONFIG
    AGENTS -->|prompts| PROMPTS
    AGENTS -->|models, keys| CONFIG
    AGENTS -->|json fallback| UTILS
    RULES -->|thresholds| CONFIG

    PIPELINE -->|Layer 0| DATA
    PIPELINE -->|Layer 1| RULES
    PIPELINE -->|Layer 2+3| AGENTS
    PIPELINE -->|budget, logging| UTILS

    MAIN --> PIPELINE
```

### Execution Order

```mermaid
flowchart TD
    START(["python main.py dataset.csv"]) --> INGEST

    INGEST["<b>ingest</b>\n<code>data/</code>\nparse → profiles → graph"]
    INGEST --> RUN_RULES

    RUN_RULES["<b>run_rules</b>\n<code>rules/ × 13 tools</code>\neach txn → 13 risk results"]
    RUN_RULES --> TRIAGE

    TRIAGE["<b>triage</b>\n<code>rules/composite</code>\nscore + combos + amount thresholds\npriority = score × amount"]

    TRIAGE -->|"auto-legit\n~70-85%"| OUTPUT
    TRIAGE -->|"auto-fraud\n~5-10%"| OUTPUT
    TRIAGE -->|"ambiguous\ntop-N by priority"| FAN

    FAN["<b>Send API fan-out</b>"]
    FAN --> V["<b>velocity</b>\n<code>agents/</code>\ntiming patterns"]
    FAN --> A["<b>amount</b>\n<code>agents/</code>\nspending patterns"]
    FAN --> B["<b>behavioral</b>\n<code>agents/</code>\nbehavior changes"]
    FAN --> R["<b>relationship</b>\n<code>agents/</code>\nnetwork patterns"]

    V --> AGG
    A --> AGG
    B --> AGG
    R --> AGG

    AGG["<b>aggregate</b>\n<code>agents/</code>\neconomic weighting\nfinal verdict"]
    AGG --> OUTPUT

    OUTPUT["<b>output</b>\noutput.txt + debug.json"]
    OUTPUT --> DONE([done])

    style INGEST fill:#e8f5e9
    style RUN_RULES fill:#e8f5e9
    style TRIAGE fill:#e8f5e9
    style V fill:#fff3e0
    style A fill:#fff3e0
    style B fill:#fff3e0
    style R fill:#fff3e0
    style AGG fill:#fce4ec
```

---

## Key Design Decisions

### Data: Minimal Contract + Passthrough
We don't know the dataset format until hackathon day. Six guaranteed keys
(`id`, `sender_id`, `receiver_id`, `amount`, `timestamp`, `sender_balance`)
plus all raw fields preserved. On hackathon day, update `FIELD_MAP` in
`data/ingest.py` — nothing else changes.

### Rules: 4 Categories, 30 Configurable Thresholds
All magic numbers live in `rules/_types.py`. On hackathon day, see the data
distribution and adjust — no other file needs to change.

| Category | Tools | Weight |
|---|---|---|
| Time | check_velocity, check_temporal_pattern, check_card_testing | 0.5–1.5× |
| Amount | check_amount_anomaly, check_balance_drain, check_first_large | 1.0–1.5× |
| Behavioral | check_new_payee, check_dormant_reactivation, check_frequency_shift | 1.0× |
| Graph | check_fan_in, check_fan_out, check_mule_chain, check_circular_flow | 2.0× |

### Triage: Score × Amount Priority
Ambiguous transactions ranked by `composite_score × amount`. A mediocre-risk
€50k transaction gets LLM analysis before a high-risk €5 one. Budget-aware:
when tokens run low, process fewer ambiguous txns; at 15% remaining, skip LLM
entirely.

### Specialists: 4 Parallel via Send API
One specialist per rule category. LangGraph's `Send` API launches all 4
concurrently — latency = slowest specialist, not the sum. Each gets curated
context (not the full state). Structured output enforced via `response_format`
+ Pydantic validation.

### Error Handling: Amount-Aware
- Txn > €1k + specialist fails → retry once
- Txn ≤ €1k + specialist fails → skip, use remaining specialists
- All fail → fallback to rule-based verdict

### Output: txt + debug.json
`output.txt` for submission. `debug.json` with full per-txn trace (L1 scores,
specialist reasoning, aggregator verdict, priority rank, verdict source) for
tuning between dataset runs.

---

## Token Budget

**Datasets 1-3 ($40)**

| Layer | Txns | Tokens/txn | Model | Est. cost |
|---|---|---|---|---|
| 0 + 1 | all | 0 | — | $0 |
| 2 (4 specialists) | ~500 | ~300 × 4 | gpt-4o-mini | ~$8 |
| 3 (aggregator) | ~500 | ~800 | gpt-4o | ~$10 |
| **Total** | | | | **~$18** |

Safety margin: ~$22 for debugging, threshold tuning, re-runs.

**Datasets 4-5 ($120)**: same architecture, consider upgrading specialist model.

---

## Hackathon Day Playbook

### First 15 minutes — Data exploration
1. Open the dataset, inspect field names and types
2. Update `FIELD_MAP` in `data/ingest.py`
3. Run `parse_dataset()` and check output
4. Look at amount distribution, timestamp range, account count

### Next 30 minutes — Threshold tuning
1. Run Layer 0+1 on training data
2. Check triage split: what % auto-legit, auto-fraud, ambiguous?
3. Adjust thresholds in `rules/_types.py` until ~15-30% is ambiguous
4. Check `debug.json` for false positives/negatives

### Remaining time — LLM layers
1. Implement specialist stubs (wire LLM calls)
2. Test on training data, check Langfuse traces
3. Monitor budget, adjust triage if needed
4. Submit evaluation — **one shot only**

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| Token budget exhausted | BudgetTracker with panic mode. Priority ranking spends tokens where they matter most. |
| Unexpected dataset format | FIELD_MAP pattern — 1 dict to update. Passthrough preserves all fields. |
| LLM returns bad output | Belt and suspenders: response_format + Pydantic + json_repair fallback. |
| Specialist fails | Amount-aware retry (>€1k) or skip (≤€1k). All-fail → rule verdict. |
| Langfuse connection fails | Session IDs generated client-side. Log locally as backup. |
| Wrong output format | debug.json lets you inspect every verdict before submitting. |

---

## Pre-Challenge Checklist

- [x] Modular architecture: 8 packages with clean boundaries
- [x] LangGraph pipeline with Send API fan-out
- [x] 13 rule tools with 30 configurable thresholds
- [x] 4 specialist prompts + aggregator prompt
- [x] Budget tracking with panic mode
- [x] Structured output enforcement (Pydantic)
- [x] Data layer fully implemented (ingest + profiles + graph)
- [ ] `.env` configured with OpenRouter + Langfuse keys
- [ ] Langfuse integration tested with dummy session
- [ ] OpenRouter connection tested
- [ ] Rule tool stubs implemented
- [ ] Specialist LLM calls wired up
- [ ] End-to-end test on synthetic data
