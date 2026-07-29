"""HybridRetriever — orchestrates BM25 + dense + RRF + cross-encoder reranking."""

from __future__ import annotations

from typing import Any

import structlog

from app.services.retrieval.bm25 import bm25_search
from app.services.retrieval.dense import dense_search
from app.services.retrieval.rrf import reciprocal_rank_fusion

logger = structlog.get_logger(__name__)


def get_reranker():
    """Get the cross-encoder re-ranker model.

    Checks the DI container first (see :class:`app.core.di.DIContainer`).
    Falls back to an uncached instance when no container is active.
    """
    from app.core.di import get_di_container

    container = get_di_container()
    if container is not None:
        return container.get_or_create_reranker()
    # Direct fallback (no caching)
    try:
        from sentence_transformers import CrossEncoder
        logger.info("Loading cross-encoder (standalone): ms-marco-MiniLM-L-6-v2")
        return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    except Exception as e:
        logger.warning(f"Failed to load cross-encoder: {e}")
        return None


class HybridRetriever:
    """Combined hybrid retriever with BM25 + dense + RRF + reranking.

    The BM25 index is built once per unique set of document IDs and cached
    in-memory.  When the same documents are queried again, the cached
    index is reused — eliminating the O(chunks) rebuild cost on every
    query (item B5).
    """

    async def retrieve(
        self,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int = 20,
    ) -> list[dict]:
        """Run hybrid retrieval (BM25 + dense, merged via RRF).

        Unlike the v1 pipeline which only ran BM25 over the top-K dense
        results, this version loads the **full chunk corpus** for the
        relevant documents and builds a proper BM25 index over all of
        them.  The index is cached per unique set of document IDs.
        """
        # Dense search (always run)
        dense_results = await dense_search(query, document_ids, top_k=top_k * 2)

        # Load full chunk corpus for BM25 indexing (cached by document set)
        # get_all_chunks is sync (ChromaDB get() is synchronous)
        full_corpus = []
        try:
            from app.services.vector_store import get_vector_store as _get_vs  # type: ignore[import]
            vs = _get_vs()
            full_corpus = vs.get_all_chunks(document_ids=document_ids)
        except Exception as exc:
            logger.warning("Full corpus load failed — falling back to dense-only: %s", exc)

        # BM25 search — uses the full corpus, cached per document set
        bm25_results = []
        if full_corpus:
            bm25_results = await bm25_search(
                query,
                full_corpus,
                top_k=top_k,
                document_ids=document_ids,
            )

        # RRF merge
        merged = reciprocal_rank_fusion(bm25_results, dense_results, top_k=top_k)

        return merged

    async def rerank(
        self,
        query: str,
        chunks: list[dict],
        top_k: int = 5,
        batch_size: int = 0,
    ) -> list[dict]:
        """Re-rank chunks using a cross-encoder model with batched prediction.

        Parameters
        ----------
        query : str
            The original search query.
        chunks : list[dict]
            Candidate chunks to re-rank (typically top-20 from hybrid retrieval).
        top_k : int
            Number of top chunks to return after re-ranking.
        batch_size : int
            Batch size for the cross-encoder predict call.  ``0`` means "let
            the underlying ``CrossEncoder.predict`` decide" (typically defaults
            to batch_size=32 internally).  Explicitly setting it to the chunk
            count ensures a single batch — good for small candidate sets.

        Returns
        -------
        list[dict]
            Top-k chunks sorted by cross-encoder score descending.
        """
        reranker = get_reranker()
        if reranker is None or not chunks:
            # Fallback: sort by existing score
            chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
            return chunks[:top_k]

        import time

        pairs = [(query, c["content"]) for c in chunks]

        # Use explicit batch_size if provided, otherwise let the model decide
        predict_kwargs: dict[str, Any] = {"batch_size": batch_size} if batch_size > 0 else {}

        start = time.time()
        scores = reranker.predict(pairs, **predict_kwargs)
        elapsed_ms = (time.time() - start) * 1000

        logger.info(
            "Cross-encoder reranked %d pairs in %.1fms (batch_size=%s)",
            len(pairs),
            elapsed_ms,
            str(batch_size) if batch_size > 0 else "default",
        )

        for i, c in enumerate(chunks):
            c["rerank_score"] = float(scores[i])
            c["source"] = "reranked"
            c["rerank_latency_ms"] = elapsed_ms

        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        return chunks[:top_k]
