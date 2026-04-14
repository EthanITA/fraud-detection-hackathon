# %% model selection
from __future__ import annotations

# %% provider — switch between local Ollama and OpenRouter
LLM_BASE_URL = "http://localhost:11434/v1"  # Ollama (local)
# LLM_BASE_URL = "https://openrouter.ai/api/v1"  # OpenRouter (remote)

SPECIALIST_MODEL = "gemma3:27b-cloud"
AGGREGATOR_MODEL = "gemma3:27b-cloud"

# %% generation params
TEMPERATURE = 0.0
MAX_TOKENS_SPECIALIST = 512
MAX_TOKENS_AGGREGATOR = 512

# %% cost table
COST_PER_1K_TOKENS: dict[str, float] = {
    "gemma4:31b-cloud": 0.0,
    "gemma3:27b-cloud": 0.000125,
    "openai/gpt-4o-mini": 0.00015,
    "openai/gpt-4o": 0.005,
}
