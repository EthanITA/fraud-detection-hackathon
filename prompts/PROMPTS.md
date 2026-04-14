# prompts/ — The Playbooks

System prompts are the instructions we give to each LLM agent. They define what
the agent looks for, how it thinks, and what format it responds in.

**Why a separate module?** Prompt tuning is the #1 lever for improving accuracy.
You want to iterate on prompts without touching agent logic — change the playbook
without rewiring the factory.

## What Lives Here

### Specialist Prompts (`specialists.py`)

Three constants: `VELOCITY_PROMPT`, `AMOUNT_PROMPT`, `RELATIONSHIP_PROMPT`.

Each prompt follows the same structure:

1. **Role** — "You are a fraud detection specialist focusing on {domain}."
2. **Pattern catalog** — The specific patterns to look for, with examples of what
   each looks like in real data.
3. **Context framing** — "The automated rules already found these signals: {results}.
   Use them as starting context, but form your own assessment."
4. **Output format** — Strict JSON schema. No prose, no markdown — just the struct.
5. **Confidence calibration** — "0.9 means you'd bet money on it. 0.5 means it
   could go either way. 0.2 means probably fine but something feels off."

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

- **Be explicit about the output schema.** LLMs return better JSON when you show
  them the exact shape with example values.
- **Include the rule results in the prompt.** This grounds the LLM — it doesn't
  hallucinate patterns that the deterministic checks already disproved.
- **Calibrate confidence with examples.** "0.9 = account emptied at 3am to a new
  mule account" vs "0.3 = slightly high amount to a known payee."
