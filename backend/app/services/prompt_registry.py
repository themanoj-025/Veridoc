"""G2: Prompt version registry — loads templates from ``prompts/registry.json``.

Every system/RAG prompt template is versioned in the registry file. When a
message is generated, ``get_prompt_version()`` returns the version of the
template that was used, and the value is stored on the ``Message`` row so
every answer is traceable to the exact prompt that produced it.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_REGISTRY_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent / "prompts" / "registry.json"
)


@lru_cache(maxsize=1)
def _load_registry() -> dict:
    """Load and parse the prompt registry (cached after first read)."""
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_prompt_version(name: str) -> str:
    """Return the version string of the named prompt template.

    Falls back to ``"unknown"`` (never raises) so a missing registry entry
    cannot break message persistence.
    """
    for prompt in _load_registry().get("prompts", []):
        if prompt.get("name") == name:
            return str(prompt.get("version", "unknown"))
    return "unknown"


def get_prompt_template(name: str) -> str | None:
    """Return the template body for the named prompt, or ``None`` if missing."""
    for prompt in _load_registry().get("prompts", []):
        if prompt.get("name") == name:
            return str(prompt.get("template", ""))
    return None


def invalidate_cache() -> None:
    """Clear the registry cache (used by tests after editing registry.json)."""
    _load_registry.cache_clear()
