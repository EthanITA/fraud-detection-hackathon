# %% model selection
from __future__ import annotations

# %% provider
LLM_BASE_URL = "https://openrouter.ai/api/v1"

# Quality model (slow, costly) — citizen analysis + aggregator
QUALITY_MODEL = "google/gemini-3.1-flash-lite-preview"
# Speed model (fast, cheap) — specialists
SPEED_MODEL = "google/gemini-2.5-flash-lite-preview-09-2025"

SPECIALIST_MODEL = SPEED_MODEL
AGGREGATOR_MODEL = QUALITY_MODEL

# %% generation params
TEMPERATURE = 0.0
MAX_TOKENS_SPECIALIST = 512
MAX_TOKENS_AGGREGATOR = 512

# %% cost table (per 1K tokens, approximate)
COST_PER_1K_TOKENS: dict[str, float] = {
    QUALITY_MODEL: 0.00015,
    SPEED_MODEL: 0.0001,
    # legacy
    "gemma4:31b-cloud": 0.0,
    "gemma3:27b-cloud": 0.000125,
    "openai/gpt-4o-mini": 0.00015,
    "openai/gpt-4o": 0.005,
}
