from __future__ import annotations

import time

from .env import LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, TEAM_NAME


def init_langfuse():
    """Create and return a Langfuse client for tracing LLM calls."""
    raise NotImplementedError


def generate_session_id(dataset_name: str) -> str:
    """Session ID format: {team}-{dataset}-{timestamp}."""
    ts = int(time.time())
    return f"{TEAM_NAME}-{dataset_name}-{ts}"
