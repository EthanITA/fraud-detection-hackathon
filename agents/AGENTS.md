# agents/ — The Expert Panel

Layer 1 handled the obvious cases. What's left are the ambiguous transactions —
the ones where the alarms went off a bit, but not enough to be certain.

This is where we bring in the experts.

## The Metaphor

Imagine a fraud review meeting. Five specialists each look at the same
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

- **The Geographic/Identity Expert** — "This citizen is a 95-year-old retiree
  who lives in Detroit and rarely travels. But this transaction originated from
  a merchant in Tokyo — 10,000km from home. That's physically implausible."

Then a **senior analyst** (the aggregator) hears all five opinions and makes
the final call, weighing how much money is at stake.

## Architecture

```
triage
  │
  ├── Send("velocity_specialist", state)     ─┐
  ├── Send("amount_specialist", state)        │
  ├── Send("behavioral_specialist", state)    ├── parallel (LangGraph Send API)
  ├── Send("relationship_specialist", state)  │
  └── Send("geographic_specialist", state)    ─┘
                                                │
                                            aggregate
```

All 5 specialists are separate LangGraph nodes launched in parallel via
`Send()`. Each writes to the same `specialist_results` state key, which uses a
`_merge_dicts` reducer in `PipelineState` to merge all branches:

```python
# After all 5 complete, state contains:
specialist_results = {
    "TXN001": {
        "velocity":     {"risk_level": "high", "confidence": 0.85, ...},
        "amount":       {"risk_level": "medium", "confidence": 0.6, ...},
        "behavioral":   {"risk_level": "high", "confidence": 0.78, ...},
        "relationship": {"risk_level": "low", "confidence": 0.2, ...},
        "geographic":   {"risk_level": "high", "confidence": 0.9, ...},
    },
    "TXN002": { ... },
}
```

## Layer 2 — Five Specialists (`specialists.py`)

Each specialist iterates over `ambiguous_prioritized` and analyzes every
transaction from its domain perspective. Each gets a **curated subset** of
state — not the full pipeline state.

### Specialist Input — Curated Subset

| Specialist       | Gets                                                                  |
|------------------|-----------------------------------------------------------------------|
| **Velocity**     | txn + history (last 20) + L1 rules + citizen summary + location       |
| **Amount**       | txn + profile + L1 rules + citizen summary + location                 |
| **Behavioral**   | txn + profile + history + L1 rules + citizen summary + **full persona** |
| **Relationship** | txn + graph subgraph + L1 rules + citizen summary + location          |
| **Geographic**   | txn + L1 rules + citizen summary + location + status + **full persona** |

The `_build_specialist_context()` helper extracts exactly what each specialist
needs from the full pipeline state — nothing more.

### What Each Specialist Looks For

**Velocity Specialist** — *"How does the timing feel?"*
- Patterns: BURST, UNUSUAL_HOURS, CARD_TESTING, FREQUENCY_SHIFT, RAPID_ROUND_TRIP
- Model: configurable via `config/models.py` (~512 tokens)

**Amount Specialist** — *"Does the money make sense?"*
- Patterns: STATISTICAL_OUTLIER, ROUND_NUMBER, THRESHOLD_EVASION, STRUCTURING, BALANCE_DRAIN, FIRST_LARGE
- Model: configurable via `config/models.py` (~512 tokens)

**Behavioral Specialist** — *"Has the account's behavior changed?"*
- Patterns: NEW_PAYEE, DORMANT_REACTIVATION, FREQUENCY_SHIFT
- Model: configurable via `config/models.py` (~512 tokens)

**Relationship Specialist** — *"Who is this money going to?"*
- Patterns: MULE_CHAIN, FAN_IN, FAN_OUT, CIRCULAR_FLOW
- Model: configurable via `config/models.py` (~512 tokens)

**Geographic/Identity Specialist** — *"Is this plausible for THIS person?"*
- Patterns: IMPOSSIBLE_TRAVEL, LIFESTYLE_MISMATCH, MOBILITY_VIOLATION, VULNERABILITY_EXPLOITATION
- Model: configurable via `config/models.py` (~512 tokens)

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

# After all 5 merge → specialist_results["TXN001"] has all 5 keys
```

## Structured Output Flow

Belt and suspenders — three layers ensure we always get valid JSON:

1. **API level**: `response_format: {"type": "json_object"}` on the LLM request
   forces the model to produce valid JSON (suppresses chain-of-thought on
   reasoning models like Nemotron).
2. **Schema level**: Pydantic models (`SpecialistOutput`, `AggregatorOutput`)
   validate the shape after parsing.
3. **Fallback**: `utils.extract_json()` as a last-resort parser — prefers JSON
   objects containing expected keys (`risk_level`, `is_fraud`, `confidence`) over
   random JSON fragments that may appear in reasoning text.

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
| **All 5 specialists fail** for a txn | Fall back to rule-based verdict |

This is amount-aware: we invest more effort protecting high-value transactions.

## Layer 3 — The Aggregator (`aggregator.py`)

One capable model makes the final fraud/legit decision.

**Input**: All 5 specialist results for a transaction + the transaction + L1 rules + citizen persona

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
- IMPOSSIBLE_TRAVEL + BALANCE_DRAIN

### Why a Separate Aggregator?

The specialists are biased by design — each one only sees one dimension. The
velocity specialist doesn't know the amount is suspicious; the amount specialist
doesn't know the receiver is a mule; the geographic specialist doesn't know
about the network patterns. Only the aggregator sees the full picture and can
reason about cross-domain correlations.

## Token Budget Per Call

| What | Max tokens | Model | Cost/call |
|---|---|---|---|
| Specialist (×5) | 512 each | configurable | depends on provider |
| Aggregator (×1) | 512 | configurable | depends on provider |
| **Per ambiguous txn** | **~3,584** | | **varies** |

With local Ollama: $0.00 per call.
All costs tracked via `BudgetTracker` in pipeline state.

## Layer 0.5 — Citizen Pre-Analysis (`citizen_analyst.py`)

Before any transaction analysis, the citizen analyst runs **once per citizen**
with available supplementary data. It receives the full citizen profile (persona,
location history, health status, demographics) and outputs a structured
assessment.

**Input**: citizen profile (demographics + location summary + health status + persona text)

**Output**:
```python
CitizenAssessment(
    vulnerability_level="high",
    contradictions=["persona says homebound but location shows Kuala Lumpur"],
    expected_behavior="Small local purchases, pharmacy, bakery. No international.",
    risk_factors=["elderly_vulnerable", "impossible_travel_detected"],
    summary="95yo homebound retiree with impossible travel pings — likely compromised."
)
```

**Why a separate pre-analysis step?** Without it, every specialist must
independently reason about "is this transaction plausible for this person?" from
raw data. With pre-analysis, the specialists receive a pre-computed assessment
that surfaces the key contradictions and risk factors. This improves both quality
(consistent citizen interpretation across all 5 specialists) and efficiency
(citizen reasoning is done once and cached, not repeated 5× per transaction).

## LLM Inference Cache

All LLM calls (specialists, aggregator, citizen analyst) are cached locally
in `.llm_cache/responses.json`. Cache key = SHA-256 of (system prompt + user
prompt). On cache hit, the response is returned instantly (~0ms vs ~5s).

This is critical for the hackathon workflow: tune thresholds in `_types.py`,
re-run the pipeline, and only fresh inputs trigger new LLM calls. Citizen
pre-analysis runs once ever. Specialist calls for unchanged transactions are
free on re-run.

Clear the cache by deleting `.llm_cache/responses.json`.

## Implementation Status

| Component | Status |
|---|---|
| `SpecialistResult` TypedDict | Done |
| `SpecialistOutput` Pydantic model | Done |
| `AggregatorOutput` Pydantic model | Done |
| `CitizenAssessment` Pydantic model | Done |
| `Verdict` TypedDict | Done |
| `_format_rule_results()` | Done |
| `_build_specialist_context()` | Done |
| `run_citizen_analysis(state)` | Done |
| `run_velocity_specialist(state)` | Done |
| `run_amount_specialist(state)` | Done |
| `run_behavioral_specialist(state)` | Done |
| `run_relationship_specialist(state)` | Done |
| `run_geographic_specialist(state)` | Done |
| `run_aggregator(state)` | Done |
| LLM inference cache | Done (in `utils/llm_cache.py`) |
| Prompt templates | Done (in `prompts/`) |
| LangGraph wiring | Done (in `pipeline/graph.py`) |
