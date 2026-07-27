"""Query rewriting — transforms vague follow-ups into standalone queries."""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


async def query_rewrite(
    query: str,
    history: list[dict],
) -> str:
    """Rewrite a vague follow-up query using chat history context.

    Uses a simple heuristic: if query is short, prepend context from
    the last user message to form a standalone query.
    """
    if len(query.split()) <= 3 and history:
        for h in reversed(history):
            if h["role"] == "user":
                return f"{h['content']} {query}"
    return query


async def rewrite_query(query: str, history: list[dict]) -> str | None:
    """Optional query rewriting for vague follow-ups.

    Returns a rewritten query string or None if no rewriting is needed.
    """
    if len(query.split()) <= 3 and history:
        for h in reversed(history):
            if h["role"] == "user":
                last_user = h["content"]
                if not any(kw in query.lower() for kw in ["what", "how", "why", "who", "where", "when"]):
                    return f"{last_user} {query}"
    return None
