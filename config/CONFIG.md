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

- **`SPECIALIST_MODEL`** — The workhorse. Runs 4× per ambiguous transaction
  (velocity, amount, behavioral, relationship). Default: `gemma4:31b-cloud`.
- **`AGGREGATOR_MODEL`** — The careful judge. Runs 1× per ambiguous
  transaction. Default: `gemma4:31b-cloud`.

Also configures `TEMPERATURE` (0.0 — deterministic) and max tokens per call
(512 for both — enough headroom for reasoning models).

**`LLM_BASE_URL`** — Centralized provider endpoint. Switch between local Ollama
(`http://localhost:11434/v1`) and OpenRouter (`https://openrouter.ai/api/v1`)
by uncommenting one line. Both are OpenAI-compatible APIs.

**`COST_PER_1K_TOKENS`** centralizes $/1k-token rates for every model we use.
`utils/budget.py` reads from here — so swapping a model automatically updates
cost estimates across the pipeline. No duplicate rate tables to keep in sync.

### Tracing (`tracing.py`)

Langfuse records every LLM call: what went in, what came out, how many tokens,
how long it took. This is mandatory for the competition (judges review traces).

- `langfuse_client` — singleton Langfuse client for flushing traces on exit.
- `get_langfuse_callback()` — returns a LangChain-compatible callback handler.
  In Langfuse v3, credentials are read from env vars automatically. Session ID
  is passed via LangChain `config.metadata`, not the handler constructor.
- `generate_session_id()` — format: `{team}-{ULID}` (matches hackathon spec).
  Generated client-side, so it works even if Langfuse is down.

### `__init__.py`

Re-exports everything so consumers can write `from config import OPENROUTER_API_KEY`
instead of reaching into submodules.
