# prompts/ — System Prompts

All LLM system prompts as string constants. Separated from agent logic
so prompts can be tuned independently.

## Modules

### `specialists.py` — Layer 2 Prompts

```python
VELOCITY_PROMPT: str
AMOUNT_PROMPT: str
RELATIONSHIP_PROMPT: str
```

Each prompt includes:
1. **Role definition** — "You are a fraud detection specialist focusing on {domain}"
2. **Pattern catalog** — the specific patterns this specialist looks for
3. **Layer 1 context** — "The deterministic rules already found: {rule_results}"
4. **Output schema** — enforced JSON: `{risk_level, confidence, patterns_detected, reasoning}`
5. **Calibration guidance** — what confidence 0.8 vs 0.3 means in this domain

### `aggregator.py` — Layer 3 Prompt

```python
AGGREGATOR_PROMPT: str
```

Includes:
1. **Decision rules** — 2+ high → fraud, 1 high + confidence > 0.8 → fraud
2. **Economic scaling** — threshold table by amount range
3. **Pattern combos** — always-flag combinations
4. **Output schema** — `{transaction_id, is_fraud, confidence, reasoning}`
5. **False-positive awareness** — "Consider whether the patterns have innocent explanations"
