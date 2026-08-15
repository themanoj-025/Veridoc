"""Query rewriting — transforms vague follow-ups into standalone queries using the LLM.

When a follow-up query is short or ambiguous (e.g. "what about section 3?"),
the configured LLM is prompted to produce a standalone, well-formed query
that incorporates context from the chat history.

Falls back to simple string concatenation if the LLM call times out or errors.
"""

from __future__ import annotations

import asyncio

import structlog

from app.services.llm_provider import get_llm

logger = structlog.get_logger(__name__)

_REWRITE_SYSTEM_PROMPT = (
    "You are a query-rewriting assistant. Your job is to rewrite a user's "
    "follow-up question into a standalone, self-contained search query that "
    "can be used to find relevant information in a document collection.\n\n"
    "Rules:\n"
    "1. A follow-up question may refer to the previous conversation context.\n"
    "2. Rewrite it so it makes sense on its own, without needing the history.\n"
    "3. Preserve all key entities, dates, numbers, and technical terms.\n"
    "4. Output ONLY the rewritten query — no explanations, no prefixes.\n"
    "5. Do NOT answer the question; just rewrite it for search.\n"
    "6. If the question is already standalone, return it unchanged.\n"
)


async def rewrite_query(query: str, history: list[dict]) -> str | None:
    """Rewrite a follow-up query into a standalone query using the LLM.

    Returns a rewritten query string, or ``None`` if no rewriting is needed
    or the LLM call failed (in which case the original query should be used).

    The LLM-based rewrite is triggered when:
    - The query is short (≤ 5 words) AND there's prior history, OR
    - The query contains a demonstrative reference (this, that, these, those, it)
    """
    is_short = len(query.split()) <= 5
    has_demonstrative = any(
        kw in query.lower().split()
        for kw in ["this", "that", "these", "those", "it", "they", "them"]
    )

    if not is_short and not has_demonstrative:
        return None

    if not history or len(history) < 2:
        return None

    # Build a concise history summary (last user + last assistant turns)
    history_summary = []
    for msg in history[-4:]:  # last 4 messages (2 turns)
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"][:500]  # truncate long messages
        history_summary.append(f"{role}: {content}")

    history_text = "\n".join(history_summary)
    prompt = (
        f"Conversation history:\n{history_text}\n\n"
        f"Follow-up question: {query}\n\n"
        f"Rewritten standalone query:"
    )

    try:
        llm = get_llm()
        rewritten = await asyncio.wait_for(
            llm.chat(
                system_prompt=_REWRITE_SYSTEM_PROMPT,
                history=[],
                message=prompt,
            ),
            timeout=10.0,  # short timeout for rewrite
        )
        result = rewritten.strip().strip('"').strip("'")
        if result:
            logger.info(
                "Query rewritten",
                original=query[:50],
                rewritten=result[:50],
            )
            return result
    except TimeoutError:
        logger.warning("Query rewrite timed out, using original query")
    except Exception as e:
        logger.warning("Query rewrite failed, using original query", error=str(e))

    return None
