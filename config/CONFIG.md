# config/ — The Control Panel

Everything the pipeline needs to run: API keys, model choices, cost rates, and
observability. Change a setting here and the rest of the codebase picks it up
automatically — no shotgun surgery.

## What Lives Here

### Environment (`env.py`)

Loads your `.env` file and exposes typed constants.

**Validates on import** — if `OPENROUTER_API_KEY` is missing, the process
crashes immediately with a clear message instead of failing three layers deep
with a cryptic 401 from OpenRouter. Langfuse keys warn (not crash) because
local dev can work without tracing.

| Variable | Required | Notes |
|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** (crashes if empty) | Your token budget — `$40` for datasets 1-3, `$120` for 4-5. Non-refillable. |
| `LANGFUSE_PUBLIC_KEY` | Warns if empty | Needed for competition submission tracing. |
| `LANGFUSE_SECRET_KEY` | Warns if empty | Needed for competition submission tracing. |
| `LANGFUSE_HOST` | No (defaults to cloud) | Override for self-hosted Langfuse. |
| `TEAM_NAME` | No (defaults to `reply-team`) | Used in session IDs and output metadata. |

> **Hackathon day**: make sure `.env` has all five keys before running.

### Model Selection (`models.py`)

Two models, two roles:

- **`SPECIALIST_MODEL`** — The cheap workhorse. Runs 3x per ambiguous
  transaction. Default: `gpt-4o-mini`. Pick for speed and cost.
- **`AGGREGATOR_MODEL`** — The careful judge. Runs 1x per ambiguous
  transaction. Default: `gpt-4o`. Pick for accuracy on the final verdict.

Also configures `TEMPERATURE` (0.0 — deterministic, not creative) and max
tokens per call.

**`COST_PER_1K_TOKENS`** centralizes $/1k-token rates for every model we use.
`utils/budget.py` reads from here — so swapping a model automatically updates
cost estimates across the pipeline. No duplicate rate tables to keep in sync.

### Tracing (`langfuse.py`)

Langfuse records every LLM call: what went in, what came out, how many tokens,
how long it took. This is mandatory for the competition (judges review traces).

- `get_langfuse_callback(session_id)` — returns a LangGraph-compatible callback
  handler. Wire it into the graph's `config["callbacks"]` and every node gets
  traced automatically — no manual instrumentation per agent.
- `generate_session_id(dataset_name)` — format: `{team}-{dataset}-{timestamp}`.
  Generated client-side, so it works even if Langfuse is down.

### `__init__.py`

Re-exports everything so consumers can write `from config import OPENROUTER_API_KEY`
instead of reaching into submodules.
