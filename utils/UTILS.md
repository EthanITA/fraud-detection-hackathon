# utils/ — Cross-Cutting Helpers

## Modules

### `json_repair.py` — Robust LLM Output Parsing

```python
extract_json(raw: str) → dict
```

LLMs frequently return JSON wrapped in markdown fences, with trailing commas,
or with commentary before/after. This module:
1. Strips markdown code fences (` ```json ... ``` `)
2. Attempts `json.loads()`
3. Falls back to regex extraction of the outermost `{...}`
4. Last resort: returns a fallback dict with `{"error": "parse_failed", "raw": raw}`

### `budget.py` — Token Budget Tracking

```python
BudgetTracker:
    __init__(limit: float)        # e.g. 40.0 for datasets 1-3
    record(tokens: int, model: str) → float  # returns remaining budget
    remaining() → float
    is_panic() → bool             # True when < 15% budget remains

BUDGET_PANIC_THRESHOLD: float = 0.15
```

When `is_panic()` is True, the pipeline switches to "budget panic" mode:
- Skip Layer 2+3 entirely
- Use only Layer 1 rule-based verdicts
- Log warning to Langfuse
