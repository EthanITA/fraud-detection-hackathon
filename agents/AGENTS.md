# agents/ — The Expert Panel

Layer 1 handled the obvious cases. What's left are the ambiguous transactions —
the ones where the alarms went off a bit, but not enough to be certain.

This is where we bring in the experts.

## The Metaphor

Imagine a fraud review meeting. Four specialists each look at the same
suspicious transaction from their own angle:

- **The Timing Expert** — "This account normally transacts twice a week. Today it
  did 12 transactions in 2 hours. The deterministic rules flagged a burst, but
  I see it's also card-testing: five €1 charges, then this €2,000 one."

- **The Money Expert** — "This is €4,800 — just under the €5,000 reporting
  threshold. The account averages €150 transactions. That's 32× their norm."

- **The Behavior Expert** — "This account was dormant for 3 months, reactivated
  yesterday, and is now sending money to a payee it's never transacted with
  before. That's two behavioral red flags stacking up."

- **The Network Expert** — "The receiver was created 3 days ago and has already
  received money from 8 different accounts. Classic mule aggregation pattern."

Then a **senior analyst** (the aggregator) hears all four opinions and makes
the final call, weighing how much money is at stake.

## Architecture

```
triage
  │
  ├── Send("velocity_specialist", state)     ─┐
  ├── Send("amount_specialist", state)        │
  ├── Send("behavioral_specialist", state)    ├── parallel (LangGraph Send API)
  └── Send("relationship_specialist", state)  ─┘
                                                │
                                            aggregate
```

All 4 specialists are separate LangGraph nodes launched in parallel via
`Send()`. Each writes to the same `specialist_results` state key, which uses a
`_merge_dicts` reducer in `PipelineState` to merge all branches:

```python
# After all 4 complete, state contains:
specialist_results = {
    "TXN001": {
        "velocity":     {"risk_level": "high", "confidence": 0.85, ...},
        "amount":       {"risk_level": "medium", "confidence": 0.6, ...},
        "behavioral":   {"risk_level": "high", "confidence": 0.78, ...},
        "relationship": {"risk_level": "low", "confidence": 0.2, ...},
    },
    "TXN002": { ... },
}
```

## Layer 2 — Four Specialists (`specialists.py`)

Each specialist iterates over `ambiguous_prioritized` and analyzes every
transaction from its domain perspective. Each gets a **curated subset** of
state — not the full pipeline state.

### Specialist Input — Curated Subset

| Specialist       | Gets                                                    |
|------------------|---------------------------------------------------------|
| **Velocity**     | txn (guaranteed keys) + history (last 20) + L1 rules   |
| **Amount**       | txn (guaranteed keys) + profile + L1 rules              |
| **Behavioral**   | txn (guaranteed keys) + profile + history + L1 rules    |
| **Relationship** | txn (guaranteed keys) + graph subgraph + L1 rules       |

The `_build_specialist_context()` helper extracts exactly what each specialist
needs from the full pipeline state — nothing more.

### What Each Specialist Looks For

**Velocity Specialist** — *"How does the timing feel?"*
- Patterns: BURST, UNUSUAL_HOURS, CARD_TESTING, FREQUENCY_SHIFT, RAPID_ROUND_TRIP
- Model: gpt-4o-mini (~300 tokens)

**Amount Specialist** — *"Does the money make sense?"*
- Patterns: STATISTICAL_OUTLIER, ROUND_NUMBER, THRESHOLD_EVASION, STRUCTURING, BALANCE_DRAIN, FIRST_LARGE
- Model: gpt-4o-mini (~300 tokens)

**Behavioral Specialist** — *"Has the account's behavior changed?"*
- Patterns: NEW_PAYEE, DORMANT_REACTIVATION, FREQUENCY_SHIFT
- Model: gpt-4o-mini (~300 tokens)

**Relationship Specialist** — *"Who is this money going to?"*
- Patterns: MULE_CHAIN, FAN_IN, FAN_OUT, CIRCULAR_FLOW
- Model: gpt-4o-mini (~300 tokens)

### Why They Get Layer 1 Results

Like a doctor receiving lab results before examining a patient. The specialist
doesn't re-run the tests — they use the results as context and focus on nuance
that rules can't capture:

- Rules found "new payee + large" → specialist investigates *whether this is
  actually unusual* for this type of account
- Rules found "balance drain" → specialist checks if this account regularly
  makes large wire transfers

### State Write Pattern

Each specialist node returns a dict that the `_merge_dicts` reducer merges:

```python
# velocity_specialist returns:
{
    "specialist_results": {
        "TXN001": {"velocity": {"risk_level": "high", "confidence": 0.85, "patterns_detected": ["BURST"], "reasoning": "..."}},
        "TXN002": {"velocity": {"risk_level": "low", "confidence": 0.2, "patterns_detected": [], "reasoning": "..."}},
    }
}

# After all 4 merge → specialist_results["TXN001"] has all 4 keys
```

## Structured Output Flow

Belt and suspenders — three layers ensure we always get valid JSON:

1. **API level**: `response_format: {"type": "json_object"}` on the OpenRouter
   request forces the model to produce valid JSON.
2. **Schema level**: Pydantic models (`SpecialistOutput`, `AggregatorOutput`)
   with LangChain's `with_structured_output()` validate the shape.
3. **Fallback**: `utils.extract_json()` as a last-resort parser if the above
   layers fail (e.g., model wraps JSON in markdown).

### Pydantic Models

```python
# specialists.py
class SpecialistOutput(BaseModel):
    risk_level: Literal["high", "medium", "low"]
    confidence: float               # 0.0–1.0
    patterns_detected: list[str]
    reasoning: str

# aggregator.py
class AggregatorOutput(BaseModel):
    is_fraud: bool
    confidence: float               # 0.0–1.0
    reasoning: str
```

## Prompt Construction Recipe

Every specialist call follows this 5-step recipe:

1. **Extract** relevant data from pipeline state (`_build_specialist_context`)
2. **Format** Layer 1 rule results as human-readable summary (`_format_rule_results`)
3. **Inject** into the prompt template (from `prompts/` module)
4. **Call** LLM with structured output enforcement (`with_structured_output`)
5. **Parse & validate** response via Pydantic model, fallback to `extract_json`

## Error / Retry Contract

Specialist failures are handled based on transaction amount:

| Condition | Behavior |
|---|---|
| **Amount > €1,000** and specialist fails | Retry once |
| **Amount ≤ €1,000** and specialist fails | Skip that specialist |
| **All 4 specialists fail** for a txn | Fall back to rule-based verdict |

This is amount-aware: we invest more effort protecting high-value transactions.

## Layer 3 — The Aggregator (`aggregator.py`)

One capable model makes the final fraud/legit decision.

**Input**: All specialist results for a transaction + the transaction + L1 rules

**Output**:
```python
AggregatorOutput(is_fraud=True, confidence=0.87, reasoning="Two specialists flagged high risk...")
```

### Decision Logic

The aggregator's prompt encodes these rules:

**Specialist consensus:**
- 2+ say HIGH → fraud
- 1 says HIGH with confidence > 0.8 → fraud

**Economic scaling** (the amount changes how cautious we are):
- €10k+ → flag if ANY specialist says medium or above
- €1k–€10k → flag if average confidence > 0.5
- < €1k → only if 2+ HIGH
- < €100 → only if ALL say HIGH

**Pattern combos that always flag:**
- BURST + BALANCE_DRAIN
- NEW_PAYEE + ROUND_NUMBER + LARGE
- MULE_CHAIN + THRESHOLD_EVASION

### Why a Separate Aggregator?

The specialists are biased by design — each one only sees one dimension. The
velocity specialist doesn't know the amount is suspicious; the amount specialist
doesn't know the receiver is a mule. Only the aggregator sees the full picture
and can reason about cross-domain correlations.

## Token Budget Per Call

| What | Tokens/call | Model | Cost/call |
|---|---|---|---|
| Specialist (×4) | ~300 each | gpt-4o-mini | ~$0.004 |
| Aggregator (×1) | ~800 | gpt-4o | ~$0.020 |
| **Per ambiguous txn** | **~2,000** | | **~$0.036** |

For ~500 ambiguous txns across datasets 1-3: **~$18** (within $40 budget).
All costs tracked via `BudgetTracker` in pipeline state.

## Implementation Status

| Component | Status |
|---|---|
| `SpecialistResult` TypedDict | Done |
| `SpecialistOutput` Pydantic model | Done |
| `AggregatorOutput` Pydantic model | Done |
| `Verdict` TypedDict | Done |
| `_format_rule_results()` | Done |
| `_build_specialist_context()` | Done |
| `run_velocity_specialist(state)` | **Stub** |
| `run_amount_specialist(state)` | **Stub** |
| `run_behavioral_specialist(state)` | **Stub** |
| `run_relationship_specialist(state)` | **Stub** |
| `run_aggregator(state)` | **Stub** |
| Prompt templates | Done (in `prompts/`) |
| LangGraph wiring | Done (in `pipeline/graph.py`) |
