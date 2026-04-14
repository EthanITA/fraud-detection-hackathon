# %% env setup
import os  # noqa: E401
import sys

try:
    sys.path.insert(
        0, str(__import__("pathlib").Path(__file__).resolve().parent.parent)
    )
except NameError:
    sys.path.insert(0, os.getcwd())
import _env  # noqa: F401

# %% load all prompts
from prompts import (
    AGGREGATOR_PROMPT,
    AMOUNT_PROMPT,
    BEHAVIORAL_PROMPT,
    RELATIONSHIP_PROMPT,
    VELOCITY_PROMPT,
)

prompts = {
    "velocity": VELOCITY_PROMPT,
    "amount": AMOUNT_PROMPT,
    "behavioral": BEHAVIORAL_PROMPT,
    "relationship": RELATIONSHIP_PROMPT,
    "aggregator": AGGREGATOR_PROMPT,
}

print("Prompt lengths:")
for name, p in prompts.items():
    print(f"  {name}: {len(p)} chars, {len(p.split())} words")

# %% inspect velocity prompt structure
print("\n--- VELOCITY_PROMPT ---")
print(VELOCITY_PROMPT[:500])
print("...")

# %% format a specialist prompt with sample rule results
sample_rule_results = """- check_velocity: high -- burst: avg gap 30s
- check_balance_drain: high -- drains 95% of balance
- check_temporal_pattern: medium -- off-hours: 03:xx UTC"""

formatted = VELOCITY_PROMPT.format(rule_results=sample_rule_results)
print("\n--- Formatted VELOCITY_PROMPT ---")
print(formatted)

# %% inspect aggregator prompt
print("\n--- AGGREGATOR_PROMPT ---")
print(AGGREGATOR_PROMPT[:600])
print("...")

# %% check all prompts have {rule_results} placeholder
for name, p in prompts.items():
    has_placeholder = "{rule_results}" in p
    print(f"  {name}: has {{rule_results}} = {has_placeholder}")
