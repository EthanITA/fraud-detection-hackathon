# rules/ — The Alarm System

These are 13 fast, cheap alarms. Like a building's fire detection system: smoke
detectors, heat sensors, motion detectors. Each one is simple and sometimes wrong
alone, but together they paint a picture.

**Cost**: $0 — pure Python, no LLM calls.

## The Three Questions

Every rule answers one of three questions about a transaction:

### 1. "Is the timing suspicious?" → `time.py`

Fraudsters race the clock. They drain accounts in minutes, often at 3am when
the real owner is asleep.

- **`check_velocity`** — Are transactions happening unusually fast? (< 60s gap = alarm)
- **`check_temporal_pattern`** — Is this happening at 3am? (00:00–05:00 UTC)
- **`check_card_testing`** — Did tiny test transactions (€0.50, €1, €2) happen right before this big one?

### 2. "Is the amount suspicious?" → `amount.py`

Fraudsters either go all-in (drain the account) or carefully stay below reporting
thresholds (€4,999 instead of €5,000).

- **`check_amount_anomaly`** — Is this amount wildly different from this account's history? Is it a suspiciously round number?
- **`check_balance_drain`** — Is this transaction wiping out the account? (>90% of balance)
- **`check_first_large`** — Has this account *never* sent this much before?

### 3a. "Is the behavior suspicious?" → `behavioral.py`

Account-level patterns that don't fit the profile.

- **`check_new_payee`** — Sending a lot of money to someone you've never transacted with
- **`check_dormant_reactivation`** — Account was dead for 6 months, suddenly active with big amounts
- **`check_frequency_shift`** — Normally 2 txns/week, suddenly 30 in one day

### 3b. "Is the network suspicious?" → `graph.py`

The most powerful signals. Individual transactions look clean, but the *network*
reveals the scheme.

- **`check_fan_in`** — Many accounts sending to one "collector" account (mule aggregation)
- **`check_fan_out`** — One account distributing to many recipients (mule payout)
- **`check_mule_chain`** — Money hops A→B→C within minutes (laundering chain)
- **`check_circular_flow`** — Money loops back to where it started (wash trading)

## How Alarms Combine

Each alarm says HIGH (3 pts), MEDIUM (1 pt), or LOW (0 pts).
But not all alarms are equal:

| Alarm type | Weight | Why |
|---|---|---|
| Off-hours | 0.5× | Lots of innocent reasons to transact at night |
| Standard signals | 1.0× | Baseline |
| Drain / card testing | 1.5× | Strong behavioral indicators |
| **Graph patterns** | **2.0×** | **Hardest to fake, most indicative of organized fraud** |

### Auto-Pilot Decisions

Some combinations are so clear that we skip the LLM entirely:

**Always fraud** (combo triggered):
- Burst + Balance drain (account being emptied fast)
- New payee + Suspicious amount (sending a weird amount to a stranger)
- Mule chain + Structuring (laundering + hiding from reporting)

**Depends on how much money is involved**:

| Amount | "Clearly legit" if score ≤ | "Clearly fraud" if score ≥ |
|---|---|---|
| > €10,000 | 0 (almost nothing is safe) | 4 |
| €1k–€10k | 1 | 5 |
| €100–€1k | 1 | 6 |
| < €100 | 2 (most things are fine) | 8 (need overwhelming evidence) |

Everything in between → ambiguous → goes to the LLM specialists.
