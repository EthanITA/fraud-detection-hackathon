# %% model selection
from __future__ import annotations

SPECIALIST_MODEL = "openai/gpt-4o-mini"
AGGREGATOR_MODEL = "openai/gpt-4o-mini"

# %% generation params
TEMPERATURE = 0.0
MAX_TOKENS_SPECIALIST = 512
MAX_TOKENS_AGGREGATOR = 512

# %% cost table
COST_PER_1K_TOKENS: dict[str, float] = {
    "openai/gpt-4o-mini": 0.00015,
    "openai/gpt-4o": 0.005,
}
