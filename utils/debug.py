# %% env setup
import sys, os  # noqa: E401
try:
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))
except NameError:
    sys.path.insert(0, os.getcwd())
import _env  # noqa: F401

# %% json_repair — valid JSON
from utils import extract_json

result = extract_json('{"risk": "high", "reason": "burst"}')
print("direct:", result)

# %% json_repair — markdown-wrapped
result = extract_json('```json\n{"risk": "medium", "reason": "off-hours"}\n```')
print("markdown:", result)

# %% json_repair — garbled
result = extract_json("Sure! Here's the analysis: {\"risk\": \"low\"}")
print("garbled:", result)

# %% json_repair — total failure
result = extract_json("I cannot process this request")
print("failed:", result)

# %% budget tracker
from utils import BudgetTracker

budget = BudgetTracker(limit=40.0)
print(f"Start: ${budget.remaining():.2f}, panic={budget.is_panic()}")

budget.record(tokens=1000, model="openai/gpt-4o-mini")
print(f"After 1k mini tokens: ${budget.remaining():.2f}")

budget.record(tokens=5000, model="openai/gpt-4o")
print(f"After 5k gpt-4o tokens: ${budget.remaining():.2f}")

budget.record(tokens=100_000, model="openai/gpt-4o")
print(f"After heavy use: ${budget.remaining():.2f}, panic={budget.is_panic()}")

# %% logger
from utils import get_logger

log = get_logger("debug_test")
log.info("triage auto_legit=412 auto_fraud=23 ambiguous=65")
log.warning("budget remaining=$3.20 panic=True")
