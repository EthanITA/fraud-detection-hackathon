# config/ — The Control Panel

Everything you need to configure before running the pipeline. API keys, model
choices, and observability setup.

## What Lives Here

### Environment (`env.py`)

Loads your `.env` file and exposes typed constants:

- **`OPENROUTER_API_KEY`** — Your token budget. $40 for datasets 1-3, $120 for 4-5.
  Non-refillable. Treat it like cash.
- **`LANGFUSE_*`** keys — Mandatory tracing. Every submission needs a session ID,
  and Langfuse records every LLM call for the judges.
- **`TEAM_NAME`** — Used in session IDs and output metadata.

### Model Selection (`models.py`)

Two models, two roles:

- **`SPECIALIST_MODEL`** — The cheap workhorse. Runs 3× per ambiguous transaction.
  Default: `gpt-4o-mini`. Pick for speed and cost.
- **`AGGREGATOR_MODEL`** — The careful judge. Runs 1× per ambiguous transaction.
  Default: `gpt-4o`. Pick for accuracy on the final verdict.

Also configures temperature (0.0 — we want deterministic, not creative) and
max tokens per call.

Changing models is a one-line edit here. Nothing else in the codebase knows
or cares which specific model is running.

### Tracing (`langfuse.py`)

Langfuse records every LLM call: what went in, what came out, how many tokens,
how long it took. This is mandatory for the competition (judges review traces).

- `init_langfuse()` — creates the client
- `generate_session_id()` — format: `{team}-{dataset}-{timestamp}`

Session IDs are generated client-side, so they work even if Langfuse is down.
