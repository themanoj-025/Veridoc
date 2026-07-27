"""HybridRetriever — orchestrates BM25 + dense + RRF + cross-encoder reranking."""

from __future__ import annotations

from typing import Any

import structlog

from app.services.retrieval.bm25 import bm25_search
from app.services.retrieval.dense import dense_search
from app.services.retrieval.rrf import reciprocal_rank_fusion

logger = structlog.get_logger(__name__)

# Cross-encoder re-ranker (lazy-loaded)
_reranker = None


def get_reranker():
    """Lazy-load the cross-encoder re-ranker model."""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder

            logger.info("Loading cross-encoder re-ranker: ms-marco-MiniLM-L-6-v2")
            _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        except Exception as e:
            logger.warning(f"Failed to load cross-encoder: {e}")
            _reranker = None
    return _reranker


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
    ) -> list[dict]:
        """Re-rank chunks using a cross-encoder model."""
        reranker = get_reranker()
        if reranker is None or not chunks:
            # Fallback: sort by existing score
            chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
            return chunks[:top_k]

        pairs = [(query, c["content"]) for c in chunks]
        scores = reranker.predict(pairs)

        for i, c in enumerate(chunks):
            c["rerank_score"] = float(scores[i])
            c["source"] = "reranked"

        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        return chunks[:top_k]
