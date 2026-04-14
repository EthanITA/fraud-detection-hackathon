# %% env setup
import sys; sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))  # noqa: E702
import _env  # noqa: F401

# %% inspect env vars
from config import OPENROUTER_API_KEY, LANGFUSE_PUBLIC_KEY, TEAM_NAME

print(f"API key: {OPENROUTER_API_KEY[:8]}...")
print(f"Langfuse: {LANGFUSE_PUBLIC_KEY[:8]}...")
print(f"Team: {TEAM_NAME}")

# %% inspect model config
from config import SPECIALIST_MODEL, AGGREGATOR_MODEL, COST_PER_1K_TOKENS, TEMPERATURE

print(f"Specialist: {SPECIALIST_MODEL} (${COST_PER_1K_TOKENS.get(SPECIALIST_MODEL, '?')}/1k)")
print(f"Aggregator: {AGGREGATOR_MODEL} (${COST_PER_1K_TOKENS.get(AGGREGATOR_MODEL, '?')}/1k)")
print(f"Temperature: {TEMPERATURE}")

# %% session ID
from config import generate_session_id

session = generate_session_id("dataset-1")
print(f"Session ID: {session}")
