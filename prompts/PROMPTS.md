# prompts/ — The Playbooks

System prompts are the instructions we give to each LLM agent. They define what
the agent looks for, how it thinks, and what format it responds in.

**Why a separate module?** Prompt tuning is the #1 lever for improving accuracy.
You want to iterate on prompts without touching agent logic — change the playbook
without rewiring the factory.

## What Lives Here

### Specialist Prompts (`specialists.py`)

Five constants, one per specialist: `VELOCITY_PROMPT`, `AMOUNT_PROMPT`,
`BEHAVIORAL_PROMPT`, `RELATIONSHIP_PROMPT`, `GEOGRAPHIC_PROMPT`.

Each prompt follows the same structure:

1. **Role** — "You are a fraud detection specialist focusing on {domain}."
2. **Pattern catalog** — The specific patterns to look for, with examples of what
   each looks like in real data.
3. **Context framing** — "The automated rules already found these signals: {results}.
   Use them as starting context, but form your own assessment."
4. **Output format** — Strict JSON schema. No prose, no markdown — just the struct.
5. **Confidence calibration** — "0.9 means you'd bet money on it. 0.5 means it
   could go either way. 0.2 means probably fine but something feels off."

### Citizen Analysis Prompt (`citizen_analyst.py`)

One constant: `CITIZEN_ANALYSIS_PROMPT` (defined in `agents/citizen_analyst.py`,
not in `prompts/`, since it's tightly coupled to the analyst agent).

This prompt asks the LLM to pre-screen a citizen's risk profile before any
transaction analysis. It explicitly instructs the LLM to:
1. Compare the persona text against actual data and flag contradictions
2. Assess vulnerability (age, health trends, social isolation)
3. Describe expected transaction behavior
4. List specific risk factors as tags

### Aggregator Prompt (`aggregator.py`)

One constant: `AGGREGATOR_PROMPT`.

This is the most important prompt in the system. It includes:

1. **Decision rules** — The explicit thresholds (2+ high → fraud, etc.)
2. **Economic context** — "A €50k fraud costs the bank 1000× more than a €50 one.
   Scale your caution with the amount."
3. **False-positive awareness** — "Before flagging, consider: is there an innocent
   explanation? International transfers, business payments, and first-time large
   purchases are often legitimate."
4. **Output format** — `{is_fraud, confidence, reasoning}`

## Prompt Engineering Tips for the Hackathon

- **Enforce JSON at two levels.** The prompt says "CRITICAL: Output ONLY the
  JSON object" and the LLM client sets `response_format: {"type": "json_object"}`.
  Both are needed — some models (e.g., Nemotron reasoning models) ignore prompt
  instructions but obey API-level format constraints.
- **Include the rule results in the prompt.** This grounds the LLM — it doesn't
  hallucinate patterns that the deterministic checks already disproved.
- **Calibrate confidence with examples.** "0.9 = account emptied at 3am to a new
  mule account" vs "0.3 = slightly high amount to a known payee."
- **Watch token budgets on reasoning models.** Models like Nemotron spend most of
  their token budget on chain-of-thought before producing output. The
  `response_format` constraint suppresses this; `max_tokens: 512` provides
  headroom.
