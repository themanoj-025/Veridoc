"""BM25 keyword search — lexical retrieval with cached per-collection indexes.

The BM25 index is built once per unique set of document IDs and cached
in-memory.  When the same documents are queried again, the cached index
is reused, eliminating the O(chunks) rebuild cost on every query.

The cache is invalidated when documents are added, deleted, or re-indexed
by calling ``invalidate_bm25_index()``.
"""

from __future__ import annotations

import hashlib
from typing import Any

import nltk
import structlog

logger = structlog.get_logger(__name__)

# Cached BM25 indexes: cache_key -> (BM25Okapi, list_of_chunks)
_bm25_indexes: dict[str, Any] = {}

# Sentinel to detect first-call NLTK download requests
_NLTK_ATTEMPTED = False


def _ensure_nltk_data() -> None:
    """Download NLTK punkt tokenizer data once at first BM25 call.

    This avoids the network/filesystem call during query-time scoring.
    """
    global _NLTK_ATTEMPTED
    if not _NLTK_ATTEMPTED:
        try:
            nltk.download("punkt", quiet=True)
            nltk.download("punkt_tab", quiet=True)
        except Exception:
            logger.warning("NLTK punkt download failed, BM25 may degrade")
        _NLTK_ATTEMPTED = True


def _build_cache_key(document_ids: list[str] | None) -> str:
    """Create a deterministic cache key from sorted document IDs."""
    if not document_ids:
        return "__all_documents__"
    normalized = sorted(set(document_ids))
    raw = ":".join(normalized)
    return hashlib.md5(raw.encode()).hexdigest()


def get_bm25_index(
    chunks: list[dict],
    document_ids: list[str] | None = None,
) -> tuple[Any, list[dict]]:
    """Build or retrieve a cached BM25 index.

    The cache key is derived from ``document_ids`` (sorted, deduplicated).
    If the document set has been indexed before the cached ``BM25Okapi``
    instance is returned; otherwise a new index is trained on ``chunks``
    and cached.

    Parameters
    ----------
    chunks : list[dict]
        The full chunk corpus to index (only used when cache misses).
    document_ids : list[str] | None
        Document IDs that define the cache scope.  When ``None``, a
        single global cache slot is used (``__all_documents__``).

    Returns
    -------
    tuple[BM25Okapi, list[dict]]
        The BM25 index and the (possibly cached) chunk list.
    """
    from rank_bm25 import BM25Okapi

    _ensure_nltk_data()

    cache_key = _build_cache_key(document_ids)

    if cache_key in _bm25_indexes:
        cached_index, cached_chunks = _bm25_indexes[cache_key]
        logger.debug("BM25 cache HIT for key=%s (%d chunks)", cache_key, len(cached_chunks))
        return cached_index, cached_chunks

    logger.info(
        "BM25 cache MISS for key=%s — training on %d chunks",
        cache_key,
        len(chunks),
    )

    tokenized = [nltk.word_tokenize(c["content"].lower()) for c in chunks]
    index = BM25Okapi(tokenized)
    _bm25_indexes[cache_key] = (index, chunks)
    return index, chunks


def invalidate_bm25_index() -> None:
    """Clear all cached BM25 indexes (call when documents change)."""
    _bm25_indexes.clear()
    logger.debug("BM25 indexes invalidated (%d entries cleared)", len(_bm25_indexes))


async def bm25_search(
    query: str,
    chunks: list[dict],
    top_k: int = 20,
    document_ids: list[str] | None = None,
) -> list[dict]:
    """Search chunks using BM25 (lexical search).

    Parameters
    ----------
    query : str
        The search query.
    chunks : list[dict]
        Full chunk corpus (only used when cache misses).
    top_k : int
        Number of results to return.
    document_ids : list[str] | None
        Document IDs for cache scoping.  When provided the BM25 index
        is cached per unique set of document IDs.

    Returns
    -------
    list[dict]
        Top-k results sorted by BM25 score descending.
    """
    if not chunks:
        return []

    _ensure_nltk_data()
    tokenized_query = nltk.word_tokenize(query.lower())

    # Get or build cached index (keyed by document set)
    bm25, _ = get_bm25_index(chunks, document_ids=document_ids)
    scores = bm25.get_scores(tokenized_query)

    # Sort by score
    scored = list(enumerate(scores))
    scored.sort(key=lambda x: x[1], reverse=True)

    results = []
    for idx, score in scored[:top_k]:
        chunk = chunks[idx].copy()
        chunk["score"] = float(score)
        chunk["source"] = "bm25"
        results.append(chunk)

    return results
