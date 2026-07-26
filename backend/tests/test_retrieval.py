"""Tests for the retrieval system — BM25 search, RRF, HybridRetriever, query rewriting."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.retrieval import (
    bm25_search,
    reciprocal_rank_fusion,
    HybridRetriever,
    rewrite_query,
    query_rewrite,
)


# ── Sample test data ─────────────────────────────────────

SAMPLE_CHUNKS = [
    {
        "chunk_id": "chunk-1",
        "content": "The quick brown fox jumps over the lazy dog.",
        "document_id": "doc-1",
        "document_title": "Animal Document",
        "page_number": 1,
        "score": 0.9,
    },
    {
        "chunk_id": "chunk-2",
        "content": "Machine learning is a subset of artificial intelligence.",
        "document_id": "doc-1",
        "document_title": "Animal Document",
        "page_number": 2,
        "score": 0.8,
    },
    {
        "chunk_id": "chunk-3",
        "content": "The lazy dog sleeps all day in the sun.",
        "document_id": "doc-2",
        "document_title": "Pet Care Guide",
        "page_number": None,
        "score": 0.7,
    },
    {
        "chunk_id": "chunk-4",
        "content": "Python is a versatile programming language for AI and ML.",
        "document_id": "doc-2",
        "document_title": "Pet Care Guide",
        "page_number": 3,
        "score": 0.6,
    },
    {
        "chunk_id": "chunk-5",
        "content": "Artificial intelligence transforms how we interact with technology.",
        "document_id": "doc-3",
        "document_title": "Tech Overview",
        "page_number": 1,
        "score": 0.5,
    },
]


# ── BM25 Search ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_bm25_search_empty_chunks():
    """Test BM25 search with empty chunk list returns empty results."""
    results = await bm25_search("test query", [])
    assert results == []


@pytest.mark.asyncio
async def test_bm25_search_basic(mock_bm25_builder):
    """Test BM25 search returns scored results sorted by relevance."""
    results = await bm25_search("lazy dog", SAMPLE_CHUNKS)

    assert len(results) > 0
    assert all("score" in r for r in results)
    assert all("source" in r for r in results)
    assert all(r["source"] == "bm25" for r in results)
    # Results should be sorted by score descending
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_bm25_search_top_k(mock_bm25_builder):
    """Test BM25 search respects top_k parameter."""
    results = await bm25_search("test query", SAMPLE_CHUNKS, top_k=3)
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_bm25_search_preserves_fields(mock_bm25_builder):
    """Test BM25 search preserves original chunk fields."""
    results = await bm25_search("lazy dog", SAMPLE_CHUNKS)

    assert len(results) > 0
    result = results[0]
    assert "chunk_id" in result
    assert "content" in result
    assert "document_id" in result
    assert "document_title" in result


# ── Reciprocal Rank Fusion ───────────────────────────────

class TestReciprocalRankFusion:
    """Tests for Reciprocal Rank Fusion algorithm."""

    def test_rrf_merges_results(self):
        """Test RRF merges two result sets correctly."""
        bm25_results = [
            {"chunk_id": "chunk-1", "content": "fox", "score": 0.9, "source": "bm25"},
            {"chunk_id": "chunk-2", "content": "dog", "score": 0.8, "source": "bm25"},
        ]
        dense_results = [
            {"chunk_id": "chunk-3", "content": "cat", "score": 0.85, "source": "vector"},
            {"chunk_id": "chunk-1", "content": "fox", "score": 0.7, "source": "vector"},
        ]

        merged = reciprocal_rank_fusion(bm25_results, dense_results)

        # Should include all unique chunks
        chunk_ids = {r["chunk_id"] for r in merged}
        assert "chunk-1" in chunk_ids
        assert "chunk-2" in chunk_ids
        assert "chunk-3" in chunk_ids

    def test_rrf_has_scores(self):
        """Test RRF results have rrf_score field."""
        bm25_results = [
            {"chunk_id": "chunk-1", "content": "test", "score": 0.9},
        ]
        dense_results = [
            {"chunk_id": "chunk-2", "content": "test", "score": 0.8},
        ]

        merged = reciprocal_rank_fusion(bm25_results, dense_results)
        assert all("rrf_score" in r for r in merged)

    def test_rrf_empty_bm25(self):
        """Test RRF with empty BM25 results still returns dense results."""
        merged = reciprocal_rank_fusion([], SAMPLE_CHUNKS)
        assert len(merged) > 0
        assert len(merged) <= 20

    def test_rrf_empty_dense(self):
        """Test RRF with empty dense results still returns BM25 results."""
        merged = reciprocal_rank_fusion(SAMPLE_CHUNKS, [])
        assert len(merged) > 0

    def test_rrf_both_empty(self):
        """Test RRF with both empty returns empty."""
        merged = reciprocal_rank_fusion([], [])
        assert merged == []

    def test_rrf_respects_top_k(self):
        """Test RRF respects the top_k parameter."""
        chunks = [{"chunk_id": f"chunk-{i}", "content": f"test {i}"} for i in range(10)]
        merged = reciprocal_rank_fusion(chunks, chunks, top_k=3)
        assert len(merged) <= 3


# ── Query Rewriting ──────────────────────────────────────

class TestQueryRewrite:
    """Tests for query rewriting logic."""

    def test_rewrite_long_query_no_change(self):
        """Test that long queries are not rewritten."""
        history = [{"role": "user", "content": "What is machine learning?"}]
        result = rewrite_query("What is deep learning?", history)
        assert result is None  # Not rewritten because it's long enough

    def test_rewrite_short_follow_up(self):
        """Test that short follow-ups get context prepended."""
        history = [{"role": "user", "content": "What is machine learning?"}]
        result = rewrite_query("explain more", history)
        assert result == "What is machine learning? explain more"

    def test_rewrite_no_history(self):
        """Test that no history means no rewriting."""
        result = rewrite_query("explain more", [])
        assert result is None

    def test_rewrite_with_question_word(self):
        """Test that short queries with question words are not rewritten."""
        history = [{"role": "user", "content": "Tell me about AI"}]
        result = rewrite_query("What is it?", history)
        assert result is None  # Has question word, not a vague follow-up

    def test_query_rewrite_function(self):
        """Test the static query_rewrite function."""
        history = [{"role": "user", "content": "What is machine learning?"}]
        result = query_rewrite("tell more", history)
        assert "machine learning" in result


# ── HybridRetriever ──────────────────────────────────────

@pytest.mark.asyncio
async def test_hybrid_retriever_retrieve():
    """Test HybridRetriever.retrieve returns results."""
    retriever = HybridRetriever()

    # Mock the dense_search to return sample chunks
    with patch("app.services.retrieval.dense_search") as mock_dense:
        mock_dense.return_value = SAMPLE_CHUNKS

        with patch("app.services.retrieval.bm25_search") as mock_bm25:
            mock_bm25.return_value = SAMPLE_CHUNKS[:3]

            results = await retriever.retrieve(
                query="test query",
                document_ids=["doc-1", "doc-2"],
                top_k=5,
            )

    assert len(results) > 0
    assert len(results) <= 5


@pytest.mark.asyncio
async def test_hybrid_retriever_retrieve_no_docs():
    """Test HybridRetriever.retrieve with no document IDs."""
    retriever = HybridRetriever()

    with patch("app.services.retrieval.dense_search") as mock_dense:
        mock_dense.return_value = SAMPLE_CHUNKS

        with patch("app.services.retrieval.bm25_search") as mock_bm25:
            mock_bm25.return_value = []

            results = await retriever.retrieve(
                query="test query",
                document_ids=None,
                top_k=5,
            )

    assert len(results) > 0


@pytest.mark.asyncio
async def test_hybrid_retriever_rerank_fallback():
    """Test rerank falls back to score-based sort when reranker is None."""
    retriever = HybridRetriever()

    with patch("app.services.retrieval.get_reranker") as mock_get:
        mock_get.return_value = None  # Reranker unavailable

        results = await retriever.rerank("test query", SAMPLE_CHUNKS, top_k=3)

    assert len(results) == 3
    # Results should be sorted by score
    scores = [r.get("score", 0) for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_hybrid_retriever_rerank_empty():
    """Test rerank with empty chunks returns empty."""
    retriever = HybridRetriever()
    results = await retriever.rerank("test query", [])
    assert results == []


# ── Edge Cases ───────────────────────────────────────────

class TestRetrievalEdgeCases:
    """Tests for edge cases in retrieval."""

    def test_rrf_duplicate_chunks(self):
        """Test RRF handles duplicate chunks from different sources."""
        bm25_results = [
            {"chunk_id": "same-id", "content": "test", "score": 0.9, "source": "bm25"},
        ]
        dense_results = [
            {"chunk_id": "same-id", "content": "test", "score": 0.8, "source": "vector"},
        ]

        merged = reciprocal_rank_fusion(bm25_results, dense_results)

        # Same chunk ID should appear only once
        chunk_ids = [r["chunk_id"] for r in merged]
        assert chunk_ids.count("same-id") == 1

    def test_rrf_k_parameter(self):
        """Test RRF with different k values."""
        chunks_a = [{"chunk_id": "A", "content": "test"}]
        chunks_b = [{"chunk_id": "B", "content": "test"}]

        merged_small_k = reciprocal_rank_fusion(chunks_a, chunks_b, k=1)
        merged_large_k = reciprocal_rank_fusion(chunks_a, chunks_b, k=100)

        assert len(merged_small_k) == 2
        assert len(merged_large_k) == 2

    def test_query_rewrite_empty_history(self):
        """Test query_rewrite with empty history returns original query."""
        result = query_rewrite("test", [])
        assert result == "test"
