"""Hybrid retrieval — BM25 + dense vector search with RRF and cross-encoder reranking."""

from __future__ import annotations

import logging
from typing import Any

from app.services.vector_store import get_vector_store
from app.services.ingestion import get_embedding_model

logger = logging.getLogger(__name__)

# Global BM25 index (lazy-loaded per document set)
_bm25_indexes: dict[str, Any] = {}
_bm25_chunks: dict[str, list[dict]] = {}

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


def _build_bm25_index(chunks: list[dict]) -> Any:
    """Build or retrieve a BM25 index for a set of chunks."""
    from rank_bm25 import BM25Okapi
    import nltk

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)

    tokenized = [nltk.word_tokenize(c["content"].lower()) for c in chunks]
    return BM25Okapi(tokenized)


async def bm25_search(
    query: str,
    chunks: list[dict],
    top_k: int = 20,
) -> list[dict]:
    """Search chunks using BM25 (lexical search)."""
    if not chunks:
        return []

    import nltk

    try:
        nltk.data.find("tokenizers/punkt")
    except LookupError:
        nltk.download("punkt", quiet=True)

    # Build index
    bm25 = _build_bm25_index(chunks)

    # Search
    tokenized_query = nltk.word_tokenize(query.lower())
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


async def dense_search(
    query: str,
    document_ids: list[str] | None = None,
    top_k: int = 20,
) -> list[dict]:
    """Search chunks using dense vector embeddings."""
    model = get_embedding_model()
    query_embedding = model.encode(query).tolist()

    vs = get_vector_store()
    results = await vs.search(
        query_embedding=query_embedding,
        document_ids=document_ids,
        top_k=top_k,
    )

    return results


def reciprocal_rank_fusion(
    bm25_results: list[dict],
    dense_results: list[dict],
    k: int = 60,
    top_k: int = 20,
) -> list[dict]:
    """Merge BM25 and dense results using Reciprocal Rank Fusion."""
    scores: dict[str, dict] = {}

    for rank, result in enumerate(bm25_results):
        chunk_id = result.get("chunk_id", result.get("content", ""))
        if chunk_id not in scores:
            scores[chunk_id] = {**result, "rrf_score": 0.0}
        scores[chunk_id]["rrf_score"] += 1.0 / (k + rank + 1)

    for rank, result in enumerate(dense_results):
        chunk_id = result.get("chunk_id", result.get("content", ""))
        if chunk_id not in scores:
            scores[chunk_id] = {**result, "rrf_score": 0.0}
        scores[chunk_id]["rrf_score"] += 1.0 / (k + rank + 1)

    # Sort by RRF score
    sorted_results = sorted(
        scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )

    return sorted_results[:top_k]


async def query_rewrite(
    query: str,
    history: list[dict],
) -> str:
    """Rewrite a vague follow-up query using chat history context."""
    # Simple heuristic: if query is short, prepend context from last user message
    if len(query.split()) <= 3 and history:
        for h in reversed(history):
            if h["role"] == "user":
                # Use the last user message as context
                return f"{h['content']} {query}"
    return query


class HybridRetriever:
    """Combined hybrid retriever with BM25 + dense + RRF + reranking."""

    async def retrieve(
        self,
        query: str,
        document_ids: list[str] | None = None,
        top_k: int = 20,
    ) -> list[dict]:
        """Run hybrid retrieval (BM25 + dense, merged via RRF).

        Attempts BM25 lexical search first using chunks loaded from the vector store.
        Falls back to dense-only if chunks are unavailable.
        """
        # Dense search (always run)
        dense_results = await dense_search(query, document_ids, top_k=top_k * 2)

        # BM25 search — uses dense results as corpus for simplicity
        # In a full implementation, chunks would be loaded from the database
        bm25_results = []
        if dense_results:
            # Use the dense search results as BM25 corpus for hybrid fusion
            # This gives us lexical matching on top of semantic matches
            bm25_results = await bm25_search(query, dense_results, top_k=top_k)

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

        # Add rerank scores
        for i, c in enumerate(chunks):
            c["rerank_score"] = float(scores[i])
            c["source"] = "reranked"

        # Sort by rerank score
        chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

        return chunks[:top_k]


async def rewrite_query(query: str, history: list[dict]) -> str | None:
    """Optional query rewriting for vague follow-ups."""
    if len(query.split()) <= 3 and history:
        # Find the last user query in history
        for h in reversed(history):
            if h["role"] == "user":
                last_user = h["content"]
                # If the new query looks like a follow-up, combine
                if not any(kw in query.lower() for kw in ["what", "how", "why", "who", "where", "when"]):
                    return f"{last_user} {query}"
    return None
