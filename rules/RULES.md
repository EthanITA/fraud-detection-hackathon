# rules/ — The Alarm System

These are 14 fast, cheap alarms across 5 categories. Like a building's fire
detection system: smoke detectors, heat sensors, motion detectors. Each one is
simple and sometimes wrong alone, but together they paint a picture.

**Cost**: $0 — pure Python, no LLM calls.

## The Five Questions

Every rule answers one of five questions about a transaction:

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

### 4. "Is the location plausible?" --> `geographic.py`

Cross-references transaction location with the citizen's known home and travel
history. A transaction from Tokyo by a homebound retiree in Detroit is
physically implausible.

- **`check_impossible_travel`** — Is this transaction from a location the citizen has never visited and couldn't plausibly reach? Compares haversine distance from home to the transaction's lat/lng against the citizen's max known travel distance.

## How Alarms Combine

Each alarm says HIGH (3 pts), MEDIUM (1 pt), or LOW (0 pts).
But not all alarms are equal:

| Alarm type | Weight | Why |
|---|---|---|
| Off-hours | 0.5x | Lots of innocent reasons to transact at night |
| Standard signals | 1.0x | Baseline |
| Drain / card testing | 1.5x | Strong behavioral indicators |
| **Graph patterns** | **2.0x** | **Hardest to fake, most indicative of organized fraud** |
| **Geographic** | **2.0x** | **Physical implausibility is hard to explain away** |

### Auto-Pilot Decisions

Some combinations are so clear that we skip the LLM entirely:

**Always fraud** (combo triggered):
- Burst + Balance drain (account being emptied fast)
- New payee + Suspicious amount (sending a weird amount to a stranger)
- Mule chain + Structuring (laundering + hiding from reporting)
- Impossible travel + Balance drain (draining from an implausible location)

**Depends on how much money is involved**:

| Amount | "Clearly legit" if score ≤ | "Clearly fraud" if score ≥ |
|---|---|---|
| > €10,000 | 0 (almost nothing is safe) | 4 |
| €1k–€10k | 1 | 5 |
| €100–€1k | 1 | 6 |
| < €100 | 2 (most things are fine) | 8 (need overwhelming evidence) |

Everything in between → ambiguous → goes to the LLM specialists.

## Threshold Tuning Guide

Every magic number in the rules lives in one place: `_types.py`. On hackathon day,
open that file, look at the data distribution, adjust the numbers. No other file
needs to change — every tool reads its thresholds from there.

### Time thresholds

| Constant | Default | Controls | Used by |
|---|---|---|---|
| `VELOCITY_HIGH_GAP` | 60 | Avg gap (seconds) between recent txns → HIGH | `check_velocity` |
| `VELOCITY_MEDIUM_GAP` | 300 | Avg gap (seconds) → MEDIUM | `check_velocity` |
| `OFF_HOURS_START` | 0 | Start of suspicious window (UTC hour) | `check_temporal_pattern` |
| `OFF_HOURS_END` | 5 | End of suspicious window (UTC hour) | `check_temporal_pattern` |
| `CARD_TEST_MICRO_LIMIT` | 10 | Max amount (€) to count as a "micro" test txn | `check_card_testing` |
| `CARD_TEST_LARGE_LIMIT` | 500 | Min amount (€) for the "real" txn after tests | `check_card_testing` |
| `CARD_TEST_WINDOW` | 300 | Lookback window (seconds) for micro-txns | `check_card_testing` |
| `CARD_TEST_HIGH_COUNT` | 3 | Micro-txn count in window → HIGH | `check_card_testing` |

### Amount thresholds

| Constant | Default | Controls | Used by |
|---|---|---|---|
| `OUTLIER_SIGMA` | 3 | Standard deviations above mean → HIGH | `check_amount_anomaly` |
| `ROUND_NUMBER_MIN` | 1000 | Min round amount (€) that looks suspicious | `check_amount_anomaly` |
| `STRUCTURING_PROXIMITY` | 200 | € below a reporting limit to flag as structuring | `check_amount_anomaly` |
| `DRAIN_HIGH` | 0.9 | Balance fraction drained → HIGH | `check_balance_drain` |
| `DRAIN_MEDIUM` | 0.7 | Balance fraction drained → MEDIUM | `check_balance_drain` |
| `FIRST_LARGE_HIGH` | 5 | Multiple of max historical amount → HIGH | `check_first_large` |
| `FIRST_LARGE_MEDIUM` | 3 | Multiple of max historical amount → MEDIUM | `check_first_large` |
| `FIRST_LARGE_MIN_TXNS` | 5 | Min historical txns before HIGH can trigger | `check_first_large` |

### Behavioral thresholds

| Constant | Default | Controls | Used by |
|---|---|---|---|
| `NEW_PAYEE_HIGH_AMOUNT` | 1000 | Amount (€) to unknown payee → HIGH | `check_new_payee` |
| `NEW_PAYEE_MEDIUM_AMOUNT` | 200 | Amount (€) to unknown payee → MEDIUM | `check_new_payee` |
| `DORMANT_HIGH_DAYS` | 180 | Days inactive → HIGH (if amount > avg) | `check_dormant_reactivation` |
| `DORMANT_MEDIUM_DAYS` | 90 | Days inactive → MEDIUM | `check_dormant_reactivation` |
| `FREQUENCY_SHIFT_HIGH` | 10 | Rate multiplier vs. baseline → HIGH | `check_frequency_shift` |
| `FREQUENCY_SHIFT_MEDIUM` | 5 | Rate multiplier vs. baseline → MEDIUM | `check_frequency_shift` |

### Graph thresholds

| Constant | Default | Controls | Used by |
|---|---|---|---|
| `FAN_IN_HIGH` | 10 | In-degree (distinct senders) → HIGH | `check_fan_in` |
| `FAN_IN_MEDIUM` | 5 | In-degree → MEDIUM | `check_fan_in` |
| `FAN_OUT_HIGH` | 10 | Out-degree (distinct receivers in 24h) → HIGH | `check_fan_out` |
| `FAN_OUT_MEDIUM` | 5 | Out-degree → MEDIUM | `check_fan_out` |
| `MULE_FORWARD_HIGH` | 0.7 | Fraction of received amount forwarded → HIGH | `check_mule_chain` |
| `MULE_FORWARD_MEDIUM` | 0.5 | Fraction forwarded → MEDIUM | `check_mule_chain` |
| `MULE_WINDOW_HIGH` | 1800 | Forward window (seconds, 30 min) → HIGH | `check_mule_chain` |
| `MULE_WINDOW_MEDIUM` | 7200 | Forward window (seconds, 2h) → MEDIUM | `check_mule_chain` |
| `CIRCULAR_MAX_HOPS` | 3 | Max hops to detect circular flow → HIGH | `check_circular_flow` |

### Geographic thresholds

| Constant | Default | Controls | Used by |
|---|---|---|---|
| `IMPOSSIBLE_TRAVEL_DISTANCE_HIGH` | 5000 | km from home → HIGH (if also > known max × 1.5) | `check_impossible_travel` |
| `IMPOSSIBLE_TRAVEL_DISTANCE_MEDIUM` | 2000 | km from home → MEDIUM | `check_impossible_travel` |

---

## Decision Flowcharts

Visual reference for every rule's decision logic. Each node shows the exact
threshold from `_types.py` and the resulting risk level with its point value.

### 1. Time-Based Rules

#### `check_velocity` (weight: 1.0x)

```mermaid
flowchart TD
    A["check_velocity<br/><i>Weight: 1.0x</i>"] --> B{"history.length < 2?"}
    B -->|Yes| LOW1["LOW<br/>Not enough history"]
    B -->|No| C["Sort timestamps<br/>Compute gaps between txns<br/>avg_gap = mean(gaps)"]
    C --> D{"avg_gap < 60s?"}
    D -->|Yes| HIGH["HIGH (3 pts)<br/>Burst activity"]
    D -->|No| E{"avg_gap < 300s?"}
    E -->|Yes| MED["MEDIUM (1 pt)<br/>Elevated velocity"]
    E -->|No| LOW2["LOW (0 pts)<br/>Normal range"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
```

#### `check_temporal_pattern` (weight: 0.5x)

```mermaid
flowchart TD
    A["check_temporal_pattern<br/><i>Weight: 0.5x (weakest)</i>"] --> B["Extract UTC hour<br/>from txn.timestamp"]
    B --> C{"hour in [0, 7) UTC?"}
    C -->|Yes| MED["MEDIUM (1 pt)<br/>Off-hours activity"]
    C -->|No| LOW["LOW (0 pts)<br/>Normal hours"]

    style MED fill:#ff9900,color:#fff
    style LOW fill:#44aa44,color:#fff
```

#### `check_card_testing` (weight: 1.5x)

```mermaid
flowchart TD
    A["check_card_testing<br/><i>Weight: 1.5x</i>"] --> B{"txn.amount < 5?<br/>(is micro itself)"}
    B -->|Yes| LOW1["LOW<br/>Current txn is micro"]
    B -->|No| C["Count micro-txns in<br/>last 300s window"]
    C --> D{"txn.amount > 500?<br/>(is large)"}
    D -->|No| LOW2["LOW<br/>No large txn follows"]
    D -->|Yes| E{"micro_count >= 3?"}
    E -->|Yes| HIGH["HIGH (3 pts)<br/>Card-testing pattern:<br/>3+ micro-txns then large txn"]
    E -->|No| F{"micro_count >= 1?"}
    F -->|Yes| MED["MEDIUM (1 pt)<br/>1-2 micro-txns<br/>before large txn"]
    F -->|No| LOW3["LOW (0 pts)<br/>No pattern"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
    style LOW3 fill:#44aa44,color:#fff
```

### 2. Amount-Based Rules

#### `check_amount_anomaly` (weight: 1.0x)

```mermaid
flowchart TD
    A["check_amount_anomaly<br/><i>Weight: 1.0x</i>"] --> B{"MAD > 0?"}
    B -->|Yes| C["z = (amount - median) / (MAD x 1.4826)"]
    C --> D{"z > 3.5?"}
    D -->|Yes| HIGH1["HIGH (3 pts)<br/>MAD outlier"]
    D -->|No| F
    B -->|No| F{"std > 0 AND<br/>amount > avg + 3 sigma?"}
    F -->|Yes| HIGH2["HIGH (3 pts)<br/>3-sigma outlier"]
    F -->|No| G["Check secondary signals"]
    G --> H{"amount >= 1k AND<br/>divisible by 1000?"}
    G --> I{"Within 200 below<br/>5k / 10k / 15k?"}
    H -->|Yes| MED["MEDIUM (1 pt)<br/>Round number /<br/>Structuring"]
    I -->|Yes| MED
    H -->|No| J{"neither?"}
    I -->|No| J
    J -->|Both No| LOW["LOW (0 pts)<br/>Normal range"]

    style HIGH1 fill:#ff4444,color:#fff
    style HIGH2 fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW fill:#44aa44,color:#fff
```

#### `check_balance_drain` (weight: 1.5x)

```mermaid
flowchart TD
    A["check_balance_drain<br/><i>Weight: 1.5x</i>"] --> B{"balance <= 0?"}
    B -->|Yes| LOW1["LOW<br/>No balance to assess"]
    B -->|No| C["drain_ratio = amount / balance"]
    C --> D{"ratio > 90%?"}
    D -->|Yes| HIGH["HIGH (3 pts)<br/>Near-total wipeout"]
    D -->|No| E{"ratio > 70%?"}
    E -->|Yes| MED["MEDIUM (1 pt)<br/>Significant drain"]
    E -->|No| LOW2["LOW (0 pts)<br/>Normal range"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
```

#### `check_first_large` (weight: 1.0x)

```mermaid
flowchart TD
    A["check_first_large<br/><i>Weight: 1.0x</i>"] --> B{"max_amount <= 0 OR<br/>txn_count < 2?"}
    B -->|Yes| LOW1["LOW<br/>Insufficient history"]
    B -->|No| C["ratio = amount / max_amount"]
    C --> D{"ratio > 5x AND<br/>txn_count > 5?"}
    D -->|Yes| HIGH["HIGH (3 pts)<br/>Unprecedented large txn<br/>with established history"]
    D -->|No| E{"ratio > 3x?"}
    E -->|Yes| MED["MEDIUM (1 pt)<br/>Unusually large for account"]
    E -->|No| LOW2["LOW (0 pts)<br/>Consistent with history"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
```

### 3. Behavioral Rules

#### `check_new_payee` (weight: 1.0x)

```mermaid
flowchart TD
    A["check_new_payee<br/><i>Weight: 1.0x</i>"] --> B{"receiver_id in<br/>known_counterparties?"}
    B -->|Yes| LOW1["LOW<br/>Known payee"]
    B -->|No| C{"amount > 1,000?"}
    C -->|Yes| HIGH["HIGH (3 pts)<br/>Large payment to<br/>unknown payee"]
    C -->|No| D{"amount > 200?"}
    D -->|Yes| MED["MEDIUM (1 pt)<br/>Moderate payment to<br/>unknown payee"]
    D -->|No| LOW2["LOW (0 pts)<br/>Small amount, new payee"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
```

#### `check_dormant_reactivation` (weight: 1.0x)

```mermaid
flowchart TD
    A["check_dormant_reactivation<br/><i>Weight: 1.0x</i>"] --> B{"last_seen exists?"}
    B -->|No| LOW1["LOW<br/>No dormancy data"]
    B -->|Yes| C["days_inactive =<br/>(timestamp - last_seen) / 86400"]
    C --> D{"inactive > 180 days<br/>AND amount > avg?"}
    D -->|Yes| HIGH["HIGH (3 pts)<br/>Long-dormant account<br/>+ above-average txn"]
    D -->|No| E{"inactive > 90 days?"}
    E -->|Yes| MED["MEDIUM (1 pt)<br/>Dormant reactivation"]
    E -->|No| LOW2["LOW (0 pts)<br/>Not dormant"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
```

#### `check_frequency_shift` (weight: 1.0x)

```mermaid
flowchart TD
    A["check_frequency_shift<br/><i>Weight: 1.0x</i>"] --> B{"avg_time_between_txns > 0?"}
    B -->|No| LOW1["LOW<br/>No baseline"]
    B -->|Yes| C["Count txns in 1h window<br/>before current txn"]
    C --> D{"recent_count == 0?"}
    D -->|Yes| LOW2["LOW<br/>No recent activity"]
    D -->|No| E["baseline_rate = 3600 / avg_time<br/>rate_multiplier = recent_count / baseline_rate"]
    E --> F{"multiplier > 10x?"}
    F -->|Yes| HIGH["HIGH (3 pts)<br/>Frequency spike"]
    F -->|No| G{"multiplier > 5x?"}
    G -->|Yes| MED["MEDIUM (1 pt)<br/>Elevated frequency"]
    G -->|No| LOW3["LOW (0 pts)<br/>Normal frequency"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
    style LOW3 fill:#44aa44,color:#fff
```

### 4. Graph / Network Rules

#### `check_fan_in` (weight: 2.0x)

```mermaid
flowchart TD
    A["check_fan_in<br/><i>Weight: 2.0x</i>"] --> B["Look up receiver_id<br/>in graph nodes"]
    B --> C{"node found?"}
    C -->|No| LOW1["LOW<br/>Not in graph"]
    C -->|Yes| D{"in_degree > 10?"}
    D -->|Yes| HIGH["HIGH (3 x 2.0 = 6.0)<br/>Aggregation node:<br/>>10 distinct senders"]
    D -->|No| E{"in_degree > 5?"}
    E -->|Yes| MED["MEDIUM (1 x 2.0 = 2.0)<br/>Elevated fan-in"]
    E -->|No| LOW2["LOW (0 pts)<br/>Normal"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
```

#### `check_fan_out` (weight: 2.0x)

```mermaid
flowchart TD
    A["check_fan_out<br/><i>Weight: 2.0x</i>"] --> B["Look up sender_id<br/>in graph nodes"]
    B --> C{"node found?"}
    C -->|No| LOW1["LOW<br/>Not in graph"]
    C -->|Yes| D{"out_degree > 10?"}
    D -->|Yes| HIGH["HIGH (3 x 2.0 = 6.0)<br/>Payout node:<br/>>10 distinct recipients"]
    D -->|No| E{"out_degree > 5?"}
    E -->|Yes| MED["MEDIUM (1 x 2.0 = 2.0)<br/>Elevated fan-out"]
    E -->|No| LOW2["LOW (0 pts)<br/>Normal"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
```

#### `check_mule_chain` (weight: 2.0x)

```mermaid
flowchart TD
    A["check_mule_chain<br/><i>Weight: 2.0x</i>"] --> B{"txn_amount > 0?"}
    B -->|No| LOW1["LOW<br/>Zero amount"]
    B -->|Yes| C["Find outgoing edges<br/>from receiver_id"]
    C --> D{"outgoing edges exist?"}
    D -->|No| LOW2["LOW<br/>No forwarding"]
    D -->|Yes| E["For each outgoing edge:<br/>Sum amounts forwarded<br/>within 30min and 2h windows"]
    E --> F["ratio_high = fwd_30min / txn_amount<br/>ratio_medium = fwd_2h / txn_amount"]
    F --> G{"ratio_high >= 70%?"}
    G -->|Yes| HIGH["HIGH (3 x 2.0 = 6.0)<br/>Rapid forwarding:<br/>A -> B -> C within 30min"]
    G -->|No| H{"ratio_medium >= 50%?"}
    H -->|Yes| MED["MEDIUM (1 x 2.0 = 2.0)<br/>Forwarding within 2h"]
    H -->|No| LOW3["LOW (0 pts)<br/>No rapid forwarding"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
    style LOW3 fill:#44aa44,color:#fff
```

#### `check_circular_flow` (weight: 2.0x)

```mermaid
flowchart TD
    A["check_circular_flow<br/><i>Weight: 2.0x</i>"] --> B{"sender == receiver?<br/>(self-loop)"}
    B -->|Yes| HIGH1["HIGH<br/>Self-loop detected"]
    B -->|No| C["Build adjacency list<br/>from graph edges"]
    C --> D["BFS from receiver_id<br/>max depth = 3 hops"]
    D --> E{"Path back to<br/>sender_id found?"}
    E -->|Yes| HIGH2["HIGH (3 x 2.0 = 6.0)<br/>Circular flow within 3 hops"]
    E -->|No| LOW["LOW (0 pts)<br/>No circular flow"]

    style HIGH1 fill:#ff4444,color:#fff
    style HIGH2 fill:#ff4444,color:#fff
    style LOW fill:#44aa44,color:#fff
```

### 5. Geographic Rule

#### `check_impossible_travel` (weight: 2.0x)

```mermaid
flowchart TD
    A["check_impossible_travel<br/><i>Weight: 2.0x</i>"] --> B{"citizen home<br/>location known?"}
    B -->|No| LOW1["LOW<br/>No citizen location"]
    B -->|Yes| C{"txn location<br/>(lat/lng) present?"}
    C -->|No| LOW2["LOW<br/>No txn location"]
    C -->|Yes| D["distance = haversine(<br/>  home -> txn location<br/>)"]
    D --> E{"distance > 5000km AND<br/>distance > max_known x 1.5?"}
    E -->|Yes| HIGH["HIGH (3 x 2.0 = 6.0)<br/>Impossible travel"]
    E -->|No| F{"distance > 2000km?"}
    F -->|Yes| MED["MEDIUM (1 x 2.0 = 2.0)<br/>Distant transaction"]
    F -->|No| LOW3["LOW (0 pts)<br/>Within normal range"]

    style HIGH fill:#ff4444,color:#fff
    style MED fill:#ff9900,color:#fff
    style LOW1 fill:#44aa44,color:#fff
    style LOW2 fill:#44aa44,color:#fff
    style LOW3 fill:#44aa44,color:#fff
```

### 6. Composite Scoring Engine

#### `compute_composite_risk`

```mermaid
flowchart TD
    A["compute_composite_risk"] --> B["1. Weighted Score<br/>score = sum of risk_pts x weight"]
    B --> C["2. Combo Detection<br/>Check dangerous rule pairs"]
    C --> D{"Combo triggered?"}
    D -->|Yes| FRAUD1["AUTO-FRAUD"]

    D -->|No| E["3. Amount-Aware Thresholds"]
    E --> F{"txn > 10k?"}
    F -->|Yes| G["legit <= 0 | fraud >= 4"]
    F -->|No| H{"txn > 1k?"}
    H -->|Yes| I["legit <= 1 | fraud >= 5"]
    H -->|No| J{"txn > 100?"}
    J -->|Yes| K["legit <= 1 | fraud >= 6"]
    J -->|No| L["legit <= 2 | fraud >= 8"]

    G --> M{"score >= fraud_floor?"}
    I --> M
    K --> M
    L --> M

    M -->|Yes| FRAUD2["AUTO-FRAUD"]
    M -->|No| N{"score <= legit_ceiling?"}
    N -->|Yes| LEGIT["AUTO-LEGIT"]
    N -->|No| AMBIG["MEDIUM -> Layer 2"]

    style FRAUD1 fill:#ff4444,color:#fff
    style FRAUD2 fill:#ff4444,color:#fff
    style LEGIT fill:#44aa44,color:#fff
    style AMBIG fill:#ff9900,color:#fff
```

#### Always-Flag Combo Pairs

```mermaid
flowchart LR
    subgraph "Both HIGH = auto-fraud"
        direction TB
        C1["BURST + BALANCE_DRAIN<br/><i>Account takeover</i>"]
        C2["NEW_PAYEE + AMOUNT_ANOMALY<br/><i>Social engineering</i>"]
        C3["MULE_CHAIN + STRUCTURING<br/><i>Organized laundering</i>"]
        C4["IMPOSSIBLE_TRAVEL + BALANCE_DRAIN<br/><i>Stolen credentials</i>"]
    end

    style C1 fill:#cc0000,color:#fff
    style C2 fill:#cc0000,color:#fff
    style C3 fill:#cc0000,color:#fff
    style C4 fill:#cc0000,color:#fff
```
