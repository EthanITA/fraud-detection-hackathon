# %% imports
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

_log = logging.getLogger(__name__)

# %% cache config
CACHE_DIR = Path(__file__).resolve().parent.parent / ".llm_cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "responses.json"


# %% _load_cache
def _load_cache() -> dict[str, str]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


# %% _save_cache
def _save_cache(cache: dict[str, str]) -> None:
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False))


# %% _make_key
def _make_key(system_prompt: str, user_prompt: str) -> str:
    """Hash system + user prompt to create a deterministic cache key."""
    content = f"{system_prompt}\n---\n{user_prompt}"
    return hashlib.sha256(content.encode()).hexdigest()


# %% cache_get
def cache_get(system_prompt: str, user_prompt: str) -> str | None:
    """Look up a cached LLM response. Returns None on miss."""
    key = _make_key(system_prompt, user_prompt)
    cache = _load_cache()
    result = cache.get(key)
    if result is not None:
        _log.debug(f"llm_cache: HIT {key[:12]}...")
    return result


# %% cache_set
def cache_set(system_prompt: str, user_prompt: str, response: str) -> None:
    """Store an LLM response in the cache."""
    key = _make_key(system_prompt, user_prompt)
    cache = _load_cache()
    cache[key] = response
    _save_cache(cache)
    _log.debug(f"llm_cache: SET {key[:12]}...")
