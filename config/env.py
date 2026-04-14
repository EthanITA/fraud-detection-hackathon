from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
LANGFUSE_PUBLIC_KEY: str = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY: str = os.environ.get("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST: str = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
TEAM_NAME: str = os.environ.get("TEAM_NAME", "reply-team")
