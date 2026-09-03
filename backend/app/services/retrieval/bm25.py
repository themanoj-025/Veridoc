"""BM25 keyword search — lexical retrieval with cached and disk-persisted indexes.

The BM25 index is built once per unique set of document IDs and cached
in-memory AND persisted to disk (as JSON).  On cold start, the
persisted index is loaded from disk instead of rebuilding from scratch,
eliminating the ~500ms warmup on first query (C1).

The cache is invalidated when documents are added, deleted, or re-indexed
by calling ``invalidate_bm25_index()``.

Security: Uses JSON serialization instead of pickle to prevent arbitrary
code execution (CWE-502). The BM25Okapi index is reconstructed from the
saved tokenized corpus on load.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import nltk
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Cached BM25 indexes: cache_key -> (BM25Okapi, list_of_chunks).
#
# This is intentionally a module-level dict (NOT a service singleton).
# It is a **performance cache** that:
#   - Avoids O(chunks) BM25 index rebuild on every query
#   - Is persisted to disk for cold-start recovery
#   - Is invalidated via invalidate_bm25_index() when documents change
#
# Unlike _vector_store / _provider / etc., this cache does not represent
# an injectable service dependency — it is an internal implementation
# detail of the BM25 retrieval module.  The surrounding getter functions
# (get_vector_store, get_llm, etc.) are already container-aware via DI.
_bm25_indexes: dict[str, Any] = {}

# Sentinel to detect first-call NLTK download requests
_NLTK_ATTEMPTED = False

# Disk persistence directory
_BM25_CACHE_DIR = Path(settings.data_dir) / "bm25_cache"


def _ensure_cache_dir() -> Path:
    """Ensure the BM25 disk cache directory exists."""
    _BM25_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _BM25_CACHE_DIR


def _disk_cache_path(cache_key: str) -> Path:
    """Get the disk cache path for a given cache key."""
    return _ensure_cache_dir() / f"{cache_key}.json"


def _save_to_disk(cache_key: str, index: Any, chunks: list[dict]) -> None:
    """Persist BM25 index and chunk data to disk as JSON.

    Instead of pickling the BM25Okapi object (which allows arbitrary code
    execution), we save the tokenized corpus that built it. On load, we
    reconstruct the BM25Okapi instance from the saved corpus.
    """
    try:
        path = _disk_cache_path(cache_key)
        # Extract the tokenized corpus from the BM25 index internals.
        # rank_bm25.BM25Okapi stores the corpus in self.corpus after __init__.
        tokenized_corpus = getattr(index, "corpus", None)
        if tokenized_corpus is None:
            logger.warning("BM25 index has no corpus attribute — skipping disk persist")
            return

        data = {
            "version": 2,
            "tokenized_corpus": tokenized_corpus,
            "chunks": chunks,
            "key": cache_key,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        logger.debug("BM25 index persisted to disk (JSON): %s", path.name)
    except (OSError, ValueError, TypeError) as e:
        logger.warning("BM25 disk persistence failed: %s", e)


def _load_from_disk(cache_key: str) -> tuple[Any, list[dict]] | None:
    """Load a persisted BM25 index from disk (JSON format).

    Reconstructs the BM25Okapi instance from the saved tokenized corpus.
    """
    path = _disk_cache_path(cache_key)
    if not path.exists():
        # Also check for legacy pickle format and clean it up
        legacy_path = _ensure_cache_dir() / f"{cache_key}.pkl"
        if legacy_path.exists():
            try:
                legacy_path.unlink()
                logger.debug("Removed legacy pickle cache: %s", legacy_path.name)
            except OSError:
                pass
        return None

    try:
        from rank_bm25 import BM25Okapi

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tokenized_corpus = data["tokenized_corpus"]
        chunks = data["chunks"]

        # Reconstruct BM25Okapi from the saved tokenized corpus
        index = BM25Okapi(tokenized_corpus)

        logger.info(
            "BM25 index loaded from disk (JSON): %s (%d chunks)",
            path.name,
            len(chunks),
        )
        return index, chunks
    except (json.JSONDecodeError, EOFError, OSError, ValueError, KeyError) as e:
        logger.warning("BM25 disk load failed, will rebuild: %s", e)
        path.unlink(missing_ok=True)
        return None


def _ensure_nltk_data() -> None:
    """Download NLTK punkt tokenizer data once at first BM25 call.

    This avoids the network/filesystem call during query-time scoring.
    """
    global _NLTK_ATTEMPTED
    if not _NLTK_ATTEMPTED:
        try:
            nltk.download("punkt", quiet=True)
            nltk.download("punkt_tab", quiet=True)
        except (OSError, ImportError):
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
    """Build or retrieve a cached BM25 index (in-memory + disk-persisted).

    The cache key is derived from ``document_ids`` (sorted, deduplicated).
    If the document set has been indexed before the cached ``BM25Okapi``
    instance is returned; otherwise a new index is trained on ``chunks``
    and cached (both in-memory and on disk).

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

    # 1. Check in-memory cache first
    if cache_key in _bm25_indexes:
        cached_index, cached_chunks = _bm25_indexes[cache_key]
        logger.debug(
            "BM25 cache HIT (memory) for key=%s (%d chunks)",
            cache_key,
            len(cached_chunks),
        )
        return cached_index, cached_chunks

    # 2. Try disk cache (JSON format)
    disk_cached = _load_from_disk(cache_key)
    if disk_cached is not None:
        _bm25_indexes[cache_key] = disk_cached
        return disk_cached

    # 3. Build from scratch
    logger.info(
        "BM25 cache MISS for key=%s — training on %d chunks",
        cache_key,
        len(chunks),
    )

    tokenized = [nltk.word_tokenize(c["content"].lower()) for c in chunks]
    index = BM25Okapi(tokenized)
    _bm25_indexes[cache_key] = (index, chunks)

    # 4. Persist to disk for next cold start (JSON, not pickle)
    _save_to_disk(cache_key, index, chunks)

    return index, chunks


def invalidate_bm25_index() -> None:
    """Clear all cached BM25 indexes (call when documents change)."""
    _bm25_indexes.clear()
    # Also clear disk cache
    try:
        cache_dir = _ensure_cache_dir()
        cache_files = list(cache_dir.glob("*.json"))
        # Also clean up any legacy pickle files
        legacy_files = list(cache_dir.glob("*.pkl"))
        all_files = cache_files + legacy_files
        count = len(all_files)
        for f in all_files:
            f.unlink()
        logger.debug("BM25 disk cache cleared: %d files", count)
    except (OSError, ValueError) as e:
        logger.warning("BM25 disk cache clear failed: %s", e)
    logger.debug("BM25 indexes invalidated (memory + disk)")


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
        is cached per unique set of document IDs and persisted to disk.

    Returns
    -------
    list[dict]
        Top-k results sorted by BM25 score descending.
    """
    if not chunks:
        return []

    tokenized_query = nltk.word_tokenize(query.lower())

    # Get or build cached index (keyed by document set, disk-persisted)
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
