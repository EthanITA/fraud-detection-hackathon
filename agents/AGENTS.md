# agents/ — The Expert Panel

Layer 1 handled the obvious cases. What's left are the ambiguous transactions —
the ones where the alarms went off a bit, but not enough to be certain.

This is where we bring in the experts.

## The Metaphor

Imagine a fraud review meeting. Three specialists each look at the same
suspicious transaction from their own angle:

- **The Timing Expert** — "This account normally transacts twice a week. Today it
  did 12 transactions in 2 hours. The deterministic rules flagged a burst, but
  I see it's also card-testing: five €1 charges, then this €2,000 one."

- **The Money Expert** — "This is €4,800 — just under the €5,000 reporting
  threshold. The account averages €150 transactions. That's 32× their norm."

- **The Network Expert** — "The receiver was created 3 days ago and has already
  received money from 8 different accounts. Classic mule aggregation pattern."

Then a **senior analyst** (the aggregator) hears all three opinions and makes
the final call, weighing how much money is at stake.

## Layer 2 — Three Specialists (`specialists.py`)

All three run **in parallel** on the same transaction. Each gets:
1. The transaction itself
2. Context specific to their domain (history / profile / subgraph)
3. What Layer 1's rules already found (so they don't repeat work)

Each returns:

```
{
  agent:             "velocity" | "amount" | "relationship"
  risk_level:        "high" | "medium" | "low"
  confidence:        0.0–1.0
  patterns_detected: ["BURST", "CARD_TESTING", ...]
  reasoning:         "The rapid micro-transactions followed by..."
}
```

### What Each Specialist Looks For

**Velocity Specialist** — *"How does the timing feel?"*
- Receives: txn + sender's last 20 transactions
- Patterns: BURST, UNUSUAL_HOURS, CARD_TESTING, FREQUENCY_SHIFT, RAPID_ROUND_TRIP
- Model: gpt-4o-mini (~300 tokens)

**Amount Specialist** — *"Does the money make sense?"*
- Receives: txn + sender's account profile
- Patterns: STATISTICAL_OUTLIER, ROUND_NUMBER, THRESHOLD_EVASION, STRUCTURING, BALANCE_DRAIN, FIRST_LARGE
- Model: gpt-4o-mini (~300 tokens)

**Relationship Specialist** — *"Who is this money going to?"*
- Receives: txn + 2-hop subgraph around sender/receiver
- Patterns: MULE_CHAIN, NEW_PAYEE, FAN_IN, FAN_OUT, DORMANT_REACTIVATION, CIRCULAR_FLOW
- Model: gpt-4o-mini (~300 tokens)

### Why They Get Layer 1 Results

Like a doctor receiving lab results before examining a patient. The specialist
doesn't re-run the tests — they use the results as context and focus on nuance
that rules can't capture:

- Rules found "new payee + large" → specialist investigates *whether this is
  actually unusual* for this type of account
- Rules found "balance drain" → specialist checks if this account regularly
  makes large wire transfers

## Layer 3 — The Aggregator (`aggregator.py`)

One capable model makes the final fraud/legit decision.

**Input**: 3 specialist opinions + the transaction + Layer 1 rule results

**Output**:
```
{
  transaction_id: str
  is_fraud:       true | false
  confidence:     0.0–1.0
  reasoning:      "Two specialists flagged high risk..."
}
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
- < €100 → only if ALL 3 say HIGH

**Pattern combos that always flag:**
- BURST + BALANCE_DRAIN
- NEW_PAYEE + ROUND_NUMBER + LARGE
- MULE_CHAIN + THRESHOLD_EVASION

### Why a Separate Aggregator?

The specialists are biased by design — each one only sees one dimension. The
velocity specialist doesn't know the amount is suspicious; the amount specialist
doesn't know the receiver is a mule. Only the aggregator sees the full picture
and can reason about cross-domain correlations.

## Budget

| What | Tokens/txn | Model | Cost/txn |
|---|---|---|---|
| 3 specialists | ~900 total | gpt-4o-mini | ~$0.012 |
| Aggregator | ~800 | gpt-4o | ~$0.020 |
| **Per transaction** | **~1,700** | | **~$0.032** |

For ~500 ambiguous txns across datasets 1-3: **~$16** (within $40 budget).
