# %% imports
from __future__ import annotations

from typing import Any

import ulid
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from .env import LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, TEAM_NAME

# %% langfuse client (singleton for flush)
langfuse_client = Langfuse(
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
    host=LANGFUSE_HOST,
)


# %% get_langfuse_callback
def get_langfuse_callback() -> Any:
    """Return a LangChain-compatible Langfuse callback handler.

    In v3, credentials are read from env vars automatically.
    Session ID is passed via LangChain config metadata, not here.
    """
    return CallbackHandler()


# %% generate_session_id
def generate_session_id() -> str:
    """Session ID format: {team}-{ULID} (matches hackathon tracing spec)."""
    return f"{TEAM_NAME}-{ulid.new().str}"
