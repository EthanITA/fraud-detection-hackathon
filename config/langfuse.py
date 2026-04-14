from __future__ import annotations

import time
from typing import Any

from .env import LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, TEAM_NAME


def get_langfuse_callback(session_id: str | None = None) -> Any:
    """Return a LangGraph-compatible Langfuse callback handler."""
    from langfuse.callback import CallbackHandler

    return CallbackHandler(
        public_key=LANGFUSE_PUBLIC_KEY,
        secret_key=LANGFUSE_SECRET_KEY,
        host=LANGFUSE_HOST,
        session_id=session_id,
    )


def generate_session_id(dataset_name: str) -> str:
    """Session ID format: {team}-{dataset}-{timestamp}."""
    ts = int(time.time())
    return f"{TEAM_NAME}-{dataset_name}-{ts}"
