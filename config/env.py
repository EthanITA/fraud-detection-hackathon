# %% imports
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

# %% load env
load_dotenv()

# %% env vars
OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
LANGFUSE_PUBLIC_KEY: str = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY: str = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST: str = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
TEAM_NAME: str = os.environ.get("TEAM_NAME", "reply-team")

# %% validation
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not set. Check your .env file.")

_log = logging.getLogger(__name__)

if not LANGFUSE_PUBLIC_KEY:
    _log.warning("LANGFUSE_PUBLIC_KEY not set — tracing will be disabled.")
if not LANGFUSE_SECRET_KEY:
    _log.warning("LANGFUSE_SECRET_KEY not set — tracing will be disabled.")
