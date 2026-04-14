# Pipeline Graph

```mermaid
stateDiagram-v2
    [*] --> ingest

    state "Layer 0" as L0 {
        ingest: Ingest
        note right of ingest
            parse_dataset()
            compute_account_profiles()
            build_relationship_graph()
        end note
    }

    state "Layer 1 — $0 tokens" as L1 {
        run_rules: Run 13 Rule Tools
        triage: Triage (composite score)
        note right of triage
            weighted score + combo detection
            + amount-aware thresholds
        end note
    }

    state "Layer 2 — ~60% budget" as L2 {
        specialists: 3 Specialist Agents
        note right of specialists
            velocity · amount · relationship
            model: gpt-4o-mini
        end note
    }

    state "Layer 3 — ~40% budget" as L3 {
        aggregate: Aggregator Agent
        note right of aggregate
            economic weighting
            pattern combos
            model: gpt-4o
        end note
    }

    output: Collect Output → output.txt

    ingest --> run_rules
    run_rules --> triage

    triage --> output: score ≤ legit_ceiling\n→ auto-legit
    triage --> output: score ≥ fraud_floor\nor combo triggered\n→ auto-fraud
    triage --> specialists: score in between\n→ ambiguous

    specialists --> aggregate
    aggregate --> output
    output --> [*]
```

## Nodes

| Node | Module | Layer | Tokens |
|---|---|---|---|
| `ingest` | `pipeline/nodes.py` → `data/` | 0 | $0 |
| `run_rules` | `pipeline/nodes.py` → `rules/` | 1 | $0 |
| `triage` | `pipeline/nodes.py` → `rules.compute_composite_risk` | 1 | $0 |
| `specialists` | `pipeline/nodes.py` (TODO) | 2 | ~$6–8 |
| `aggregate` | `pipeline/nodes.py` (TODO) | 3 | ~$8–12 |
| `output` | `pipeline/nodes.py` | — | $0 |

## Routing

`triage` → conditional edge:
- **Has ambiguous txns** → `specialists` → `aggregate` → `output`
- **No ambiguous txns** → `output` (skip LLM layers entirely)
