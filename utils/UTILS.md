# utils/ — The Safety Net

Cross-cutting helpers that keep the pipeline running even when things go wrong.

## What Lives Here

### JSON Repair (`json_repair.py`)

LLMs are unreliable JSON producers. They wrap output in markdown fences, add
trailing commas, or sprinkle commentary around the JSON. This module handles it.

```
extract_json(raw: str) → dict
```

Tries, in order:
1. Direct `json.loads()` — works ~70% of the time
2. Strip markdown fences (` ```json ... ``` `) and retry
3. Regex extract the outermost `{...}` and retry
4. Last resort: return `{"error": "parse_failed", "raw": raw}`

The pipeline wraps every LLM call with this. A specialist returning garbled JSON
doesn't crash the system — it gets a fallback verdict based on rule scores alone.

### Budget Tracking (`budget.py`)

The token budget is non-refillable ($40 for datasets 1-3). Running out mid-pipeline
means you can't process remaining transactions. This module tracks spend.

```
BudgetTracker:
    record(tokens, model) → remaining $
    is_panic() → bool
```

**Budget panic mode**: When < 15% budget remains, the pipeline skips Layers 2+3
entirely and uses only Layer 1 rule-based verdicts. You lose accuracy but you
don't lose the ability to submit.

Think of it as: always keep enough fuel to land the plane.
