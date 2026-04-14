# %% test environment
# Import this FIRST in every debug file to avoid config/ crashes
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "test-pk")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "test-sk")
os.environ.setdefault("TEAM_NAME", "debug-team")
