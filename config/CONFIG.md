# config/ — Environment & Observability

## Modules

### `env.py` — Environment Variables

Loads `.env` and exposes typed constants:

```python
OPENROUTER_API_KEY: str    # LLM API access (non-refillable budget)
LANGFUSE_PUBLIC_KEY: str   # Tracing (mandatory for submission)
LANGFUSE_SECRET_KEY: str
LANGFUSE_HOST: str
TEAM_NAME: str             # Used in session IDs and output metadata
```

### `models.py` — Model Configuration

Centralized model selection so switching models is a one-line change:

```python
SPECIALIST_MODEL: str      # cheap model for Layer 2 (e.g. "gpt-4o-mini")
AGGREGATOR_MODEL: str      # capable model for Layer 3 (e.g. "gpt-4o")
TEMPERATURE: float         # 0.0 for deterministic fraud detection
MAX_TOKENS_SPECIALIST: int # ~300 per call
MAX_TOKENS_AGGREGATOR: int # ~800 per call
```

### `langfuse.py` — Tracing & Session Management

```python
init_langfuse() → LangfuseClient
generate_session_id() → str   # required in every submission
trace_call(session_id, node_name, input, output, tokens_used)
```

Session ID format: `{TEAM_NAME}-{dataset_name}-{timestamp}`
