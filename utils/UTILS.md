# utils/ — The Safety Net

Cross-cutting helpers that keep the pipeline running even when things go wrong.
Think of these as the seatbelts — you design the car to not crash, but you still
wear them.

## What Lives Here

### JSON Repair (`json_repair.py`)

**Why does this exist if we use structured output?**

The primary strategy for getting valid JSON from LLMs is structured output,
enforced at the API level in `agents/`. That approach works the vast majority of
the time. But LLMs are unpredictable — a model update, an edge-case prompt, or a
provider hiccup can still produce malformed output.

`extract_json()` is the fallback. It tries a 4-step cascade:

1. Direct `json.loads()` — works when structured output did its job
2. Strip markdown fences (`` ```json ... ``` ``) and retry
3. Regex-extract the outermost `{...}` and retry
4. Give up gracefully: `{"error": "parse_failed", "raw": ...}`

The key property: **it never raises**. A specialist returning garbled JSON doesn't
crash the pipeline — it gets a fallback verdict based on rule scores alone.

### Budget Tracking (`budget.py`)

**Why centralized tracking?**

The token budget is non-refillable ($40 for datasets 1-3). Running out mid-pipeline
means you can't process remaining transactions — a worse outcome than reduced
accuracy. Centralized tracking gives us a single place to answer "can we afford
another LLM call?"

`BudgetTracker` reads cost rates from `config.models.COST_PER_1K_TOKENS` so
pricing stays in one place. For unknown models, it falls back to a conservative
default rate.

**Budget panic mode**: When < 15% budget remains, `is_panic()` returns `True` and
the pipeline skips LLM layers entirely, relying on Layer 1 rule-based verdicts.
You lose accuracy but you don't lose the ability to submit.

Think of it as: always keep enough fuel to land the plane.

### Structured Logging (`logging.py`)

**Why structured logging?**

When you're debugging why Dataset 2 flagged transaction #847 differently than
Dataset 1, you need to trace through the pipeline's decisions. Unstructured
print statements make this painful — structured logs make it searchable.

`get_logger(name)` returns a configured logger with a consistent format:

```
14:32:01 | INFO    | triage | auto_legit=412 auto_fraud=23 ambiguous=65
14:32:05 | INFO    | budget | remaining=$31.20 panic=False
```

Key events to log across the pipeline:
- **Pipeline start**: dataset path, transaction count
- **Triage results**: auto_legit / auto_fraud / ambiguous counts
- **Budget status**: remaining dollars, panic mode flag
- **Specialist results**: per-transaction risk levels and confidence
- **Final output**: fraud count, output file path
