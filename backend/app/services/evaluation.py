"""Evaluation harness — runs gold Q&A through pipeline and reports metrics."""

from __future__ import annotations

import re
import time
from typing import Any

import structlog

from app.core.database import async_session_factory
from app.services.llm_provider import get_llm
from app.services.retrieval.hybrid import HybridRetriever

logger = structlog.get_logger(__name__)


# Cache resolved slug → document UUIDs so each gold slug is only resolved
# against the DB once per process.
_SLUG_CACHE: dict[str, list[str] | None] = {}


def _normalize_slug(value: str) -> str:
    """Lowercase and strip non-alphanumeric characters for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _slug_matches(needle: str, candidate: str | None) -> bool:
    """Fuzzy-match a normalized slug against a filename or title.

    Uses bidirectional substring matching after stripping the file
    extension, so gold slugs like ``synthetic_contract_001`` still resolve
    to ``synthetic_contract.txt``.
    """
    if not candidate:
        return False
    hay = _normalize_slug(candidate.rsplit(".", 1)[0])
    if not needle or not hay:
        return False
    return needle in hay or hay in needle


async def resolve_document_ids(doc_id: str) -> list[str] | None:
    """Resolve a gold-set document slug to real DB document UUIDs.

    The gold Q&A set uses human-readable slugs (e.g. ``gutenberg_132``,
    ``arxiv_*``) but the vector store filters by the actual document UUID
    stored in Chroma metadata. Passing a slug through verbatim would
    silently return zero chunks for every filtered question, corrupting
    the metrics.

    Wildcards (``*``, empty, and slugs ending in ``_*``) return ``None`` →
    search all docs. Concrete slugs are matched against the documents table
    (normalized filename/title substring match); when nothing matches or the
    DB is unreachable we warn and fall back to ``None`` (search all) so a
    resolution failure degrades gracefully instead of silently scoring every
    question as unanswerable.
    """
    if not doc_id or doc_id == "*" or doc_id.endswith("_*"):
        return None

    if doc_id in _SLUG_CACHE:
        return _SLUG_CACHE[doc_id]

    matched: list[str] = []
    try:
        from sqlalchemy import select

        from app.models.document import Document

        async with async_session_factory() as session:
            result = await session.execute(
                select(Document.id, Document.filename, Document.title)
            )
            rows = result.all()

        needle = _normalize_slug(doc_id)
        matched = [
            str(row[0])
            for row in rows
            if _slug_matches(needle, row[1]) or _slug_matches(needle, row[2])
        ]
    except (OSError, ValueError) as exc:
        logger.warning(
            "could_not_resolve_slug",
            slug=doc_id,
            error=str(exc),
            fallback="searching all documents",
        )

    if not matched:
        logger.warning(
            "no_document_matched_slug",
            slug=doc_id,
            fallback="searching all documents",
        )
        _SLUG_CACHE[doc_id] = None
        return None

    _SLUG_CACHE[doc_id] = matched
    return matched


async def faithfulness_check(
    query: str,
    answer: str,
    context: str,
) -> float:
    """
    Check if the answer is faithful to the provided context.
    Uses an NLI-like approach with the LLM as a judge.
    Returns a score from 0.0 (not faithful) to 1.0 (fully faithful).
    """
    llm = get_llm()

    prompt = (
        "You are a faithfulness evaluator. Given a question, a context, and an answer, "
        "determine whether the answer is fully supported by the context. "
        "Rate the answer on a scale of 0 to 100, where:\n"
        "- 100 = All claims in the answer are directly supported by the context\n"
        "- 75 = Most claims are supported, with minor extrapolation\n"
        "- 50 = Some claims supported, some unsupported\n"
        "- 25 = Most claims are not supported\n"
        "- 0 = No claims are supported by the context\n\n"
        "Return ONLY a number between 0 and 100.\n\n"
        f"=== QUESTION ===\n{query}\n\n"
        f"=== CONTEXT ===\n{context}\n\n"
        f"=== ANSWER ===\n{answer}\n\n"
        "Faithfulness score (0-100):"
    )

    try:
        result = await llm.chat(
            system_prompt="You are a precise faithfulness evaluator. Return only a number.",
            history=[],
            message=prompt,
        )
        # Extract numeric score
        score_str = result.strip()
        # Find first number in the response
        for word in score_str.split():
            try:
                score = int(word.strip(".,:;"))
                return max(0.0, min(1.0, score / 100.0))
            except ValueError:
                continue
        return 0.5  # Default if parsing fails
    except (RuntimeError, ValueError, TimeoutError) as e:
        logger.warning(f"Faithfulness check failed: {e}")
        return 0.5


async def run_single_eval(
    question: str,
    gold_answer: str,
    document_ids: list[str] | None = None,
    use_hybrid: bool = True,
) -> dict[str, Any]:
    """Run a single evaluation query through the pipeline."""
    start = time.time()

    # Retrieve
    if use_hybrid:
        # Hybrid+rerank: BM25 + dense via RRF, then cross-encoder rerank
        retriever = HybridRetriever()
        retrieved = await retriever.retrieve(
            query=question,
            document_ids=document_ids,
            top_k=20,
        )
        # Rerank
        reranked = await retriever.rerank(question, retrieved, top_k=5)
    else:
        # Naive dense-only path (used by `--compare`): no BM25/RRF, no rerank.
        # Previously this flag was a no-op — both runs used the identical
        # hybrid pipeline, making the head-to-head table meaningless.
        from app.services.retrieval.dense import dense_search

        retrieved = await dense_search(
            query=question,
            document_ids=document_ids,
            top_k=20,
        )
        reranked = retrieved[:5]

    # Build context
    context = "\n\n".join(
        [
            f"[Doc: {c.get('document_title', 'unknown')}] {c['content']}"
            for c in reranked
        ]
    )

    # Generate answer
    llm = get_llm()

    system_prompt = (
        "You are Veridoc, a precise document Q&A assistant. "
        "Answer the question based ONLY on the provided context. "
        "If the context doesn't contain enough information, say so clearly."
        f"\n\nCONTEXT:\n{context}"
    )

    answer = await llm.chat(system_prompt, [], question)

    # Faithfulness
    faith_score = await faithfulness_check(question, answer, context)

    total_time = (time.time() - start) * 1000

    return {
        "question": question,
        "generated_answer": answer,
        "gold_answer": gold_answer,
        "faithfulness_score": faith_score,
        "latency_ms": total_time,
        "retrieved_chunks": len(retrieved),
        "n_chunks_used": len(reranked),
    }


def compute_metrics(
    results: list[dict[str, Any]],
    unanswerable_indices: set[int] | None = None,
) -> dict[str, Any]:
    """Compute evaluation metrics from results."""
    unanswerable_indices = unanswerable_indices or set()

    total = len(results)
    faithfulness_scores = []
    latencies = []
    correct_count = 0
    correct_refusal = 0
    total_unanswerable = len(unanswerable_indices)

    for i, r in enumerate(results):
        faithfulness_scores.append(r.get("faithfulness_score", 0))
        latencies.append(r.get("latency_ms", 0))

        # Simple answer correctness heuristic
        gen_answer = r.get("generated_answer", "").lower()
        gold_answer = r.get("gold_answer", "").lower()

        if i in unanswerable_indices:
            # Check if model refused
            refusal_phrases = [
                "cannot answer",
                "cannot determine",
                "don't have enough",
                "not enough information",
                "not provided",
                "no information",
                "cannot",
                "unable to",
                "not found in",
                "not mentioned",
                "does not contain",
                "isn't mentioned",
                "aren't provided",
            ]
            refused = any(phrase in gen_answer for phrase in refusal_phrases)
            if refused:
                correct_refusal += 1
        else:
            # Simple keyword overlap (in production, use LLM judge)
            gold_keywords = set(gold_answer.split())
            gen_keywords = set(gen_answer.split())
            if len(gold_keywords) > 0:
                overlap = len(gold_keywords & gen_keywords) / len(gold_keywords)
                if overlap > 0.3:
                    correct_count += 1

    # Metrics
    faithfulness_scores.sort()
    latencies.sort()

    return {
        "total_questions": total,
        "answer_accuracy": correct_count / max(total - total_unanswerable, 1),
        "refusal_accuracy": correct_refusal / max(total_unanswerable, 1),
        "mean_faithfulness": sum(faithfulness_scores)
        / max(len(faithfulness_scores), 1),
        "p50_latency_ms": latencies[len(latencies) // 2] if latencies else 0,
        "p95_latency_ms": latencies[int(len(latencies) * 0.95)] if latencies else 0,
        "mean_latency_ms": sum(latencies) / max(len(latencies), 1),
        "faithfulness_scores": faithfulness_scores,
        "latencies_ms": latencies,
    }
