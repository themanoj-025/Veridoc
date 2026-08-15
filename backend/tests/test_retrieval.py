"""Tests for the retrieval system — BM25 search, RRF, HybridRetriever, query rewriting."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.retrieval import (
    HybridRetriever,
    bm25_search,
    reciprocal_rank_fusion,
    rewrite_query,
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
            {
                "chunk_id": "chunk-3",
                "content": "cat",
                "score": 0.85,
                "source": "vector",
            },
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

    @pytest.mark.asyncio
    async def test_rewrite_long_query_no_rewrite(self):
        """Test that long queries without demonstratives are not rewritten."""
        history = [{"role": "user", "content": "What is machine learning?"}]
        result = await rewrite_query(
            "What is deep learning and how does it work?", history
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_rewrite_short_follow_up_no_llm(self):
        """Test short query rewrite returns None when no LLM available."""
        history = [
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "Machine learning is..."},
        ]
        result = await rewrite_query("explain more", history)
        assert result is None

    @pytest.mark.asyncio
    async def test_rewrite_no_history(self):
        """Test that no history means no rewriting."""
        result = await rewrite_query("explain more", [])
        assert result is None

    @pytest.mark.asyncio
    async def test_rewrite_with_mock_llm(self):
        """Test LLM-based rewrite with a mocked LLM provider."""
        from unittest.mock import AsyncMock, patch

        mock_llm = AsyncMock()
        mock_llm.model_name = "test-model"
        mock_llm.chat = AsyncMock(
            return_value="What is machine learning? Explain more about it."
        )

        history = [
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "Machine learning is a subset of AI..."},
        ]

        with patch(
            "app.services.retrieval.query_rewrite.get_llm", return_value=mock_llm
        ):
            result = await rewrite_query("explain more about it", history)
            assert result is not None
            assert "machine learning" in result.lower()
            assert "explain" in result.lower()


# ── HybridRetriever ──────────────────────────────────────


@pytest.mark.asyncio
async def test_hybrid_retriever_retrieve():
    """Test HybridRetriever.retrieve returns results."""
    retriever = HybridRetriever()

    # Mock the dense_search to return sample chunks
    with patch("app.services.retrieval.hybrid.dense_search") as mock_dense:
        mock_dense.return_value = SAMPLE_CHUNKS

        with patch("app.services.retrieval.hybrid.bm25_search") as mock_bm25:
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

    with patch("app.services.retrieval.hybrid.dense_search") as mock_dense:
        mock_dense.return_value = SAMPLE_CHUNKS

        with patch("app.services.retrieval.hybrid.bm25_search") as mock_bm25:
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

    with patch("app.services.retrieval.hybrid.get_reranker") as mock_get:
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


# ── Session Regression (A1) ──────────────────────────────


@pytest.mark.asyncio
async def test_session_no_auto_commit_on_yield():
    """Regression test for A1: verify get_session() does NOT auto-commit
    or auto-close around the caller's business logic.

    The old behavior called commit() inside the dependency generator, which
    meant the session could be committed/closed before an SSE streaming
    generator finished writing to it. The new behavior yields the session
    raw, leaving commit/close ownership to the caller.

    This test verifies:
      1. commit() is NOT called by get_session on yield
      2. close() is NOT called by get_session on yield
      3. close() is NOT called by get_session on normal generator exit
         (the caller is responsible for closing)
      4. commit() IS called exactly once by the caller
    """
    from app.core.database import get_session

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.close = AsyncMock()
    mock_session.rollback = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.add = MagicMock()

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session

    with patch("app.core.database.async_session_factory", mock_factory):
        gen = get_session()
        session = await gen.__anext__()

        # 1. No commit/close should have been called by get_session
        mock_session.commit.assert_not_called()
        mock_session.close.assert_not_called()

        # Simulate the caller doing work
        await session.execute("SELECT 1")

        # 2. The caller commits explicitly
        await session.commit()
        mock_session.commit.assert_called_once()

        # 3. The caller closes the session explicitly
        await session.close()
        mock_session.close.assert_called_once()

        # 4. Finish the generator (mimics FastAPI dependency cleanup)
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

        # 5. close() should NOT be called BY THE GENERATOR — the caller
        #    already closed, and the generator does NOT close on exit
        #    (count should still be 1 — the caller's call)
        mock_session.close.assert_called_once()


# ── BM25 Disk Persistence (C1) ───────────────────────────


class TestBM25DiskPersistence:
    """Tests for BM25 index persistence to disk (C1).

    Verifies that indexes can be written to and loaded from disk,
    and that corrupt/missing files are handled gracefully.
    """

    def test_bm25_save_and_load_from_disk(self, tmp_path, monkeypatch):
        """Test BM25 index can be saved and reloaded from disk."""
        from app.services.retrieval.bm25 import (
            _bm25_indexes,
            _ensure_cache_dir,
            get_bm25_index,
        )

        # Point cache dir to a temp directory
        monkeypatch.setattr(
            "app.services.retrieval.bm25._BM25_CACHE_DIR",
            tmp_path / "bm25_cache",
        )
        _bm25_indexes.clear()

        chunks = [
            {"chunk_id": "c1", "content": "The quick brown fox.", "document_id": "d1"},
            {
                "chunk_id": "c2",
                "content": "Jumps over the lazy dog.",
                "document_id": "d1",
            },
        ]
        # First call: builds index, caches in memory AND writes to disk
        index1, chunks1 = get_bm25_index(chunks, document_ids=["d1"])
        assert index1 is not None
        assert len(chunks1) == 2

        # Verify disk file exists
        cache_dir = _ensure_cache_dir()
        pkl_files = list(cache_dir.glob("*.pkl"))
        assert len(pkl_files) == 1

        # Clear memory cache to simulate cold start
        _bm25_indexes.clear()

        # Second call: should load from disk (not rebuild)
        index2, chunks2 = get_bm25_index(chunks, document_ids=["d1"])
        assert index2 is not None
        assert len(chunks2) == 2

        # Both indexes should produce the same scores
        import nltk

        tokenized_query = nltk.word_tokenize("fox")
        import numpy as np

        scores1 = index1.get_scores(tokenized_query)
        scores2 = index2.get_scores(tokenized_query)
        assert np.array_equal(scores1, scores2)

    def test_bm25_disk_cache_missing_returns_none(self, tmp_path, monkeypatch):
        """Test loading a nonexistent disk cache returns None."""
        from app.services.retrieval.bm25 import _load_from_disk

        monkeypatch.setattr(
            "app.services.retrieval.bm25._BM25_CACHE_DIR",
            tmp_path / "bm25_cache",
        )

        result = _load_from_disk("nonexistent-key")
        assert result is None

    def test_bm25_corrupt_cache_falls_back_to_rebuild(self, tmp_path, monkeypatch):
        """Test that a corrupt pickle file triggers a rebuild instead of crashing."""
        from app.services.retrieval.bm25 import (
            _bm25_indexes,
            _build_cache_key,
            _disk_cache_path,
            get_bm25_index,
        )

        monkeypatch.setattr(
            "app.services.retrieval.bm25._BM25_CACHE_DIR",
            tmp_path / "bm25_cache",
        )
        _bm25_indexes.clear()

        chunks = [
            {"chunk_id": "c1", "content": "Test content.", "document_id": "d1"},
        ]
        cache_key = _build_cache_key(["d1"])

        # Write corrupt data to the cache file
        cache_path = _disk_cache_path(cache_key)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(b"this is not valid pickle data")

        # Clear memory cache
        _bm25_indexes.clear()

        # Should rebuild from scratch (not crash)
        index, loaded_chunks = get_bm25_index(chunks, document_ids=["d1"])
        assert index is not None
        assert len(loaded_chunks) == 1

    def test_bm25_invalidate_clears_disk(self, tmp_path, monkeypatch):
        """Test that invalidate_bm25_index() clears all disk cache files."""
        from app.services.retrieval.bm25 import (
            _build_cache_key,
            _ensure_cache_dir,
            _save_to_disk,
            invalidate_bm25_index,
        )

        monkeypatch.setattr(
            "app.services.retrieval.bm25._BM25_CACHE_DIR",
            tmp_path / "bm25_cache",
        )

        # Save two cache files
        chunks = [{"chunk_id": "c1", "content": "Test.", "document_id": "d1"}]
        index = MagicMock()
        _save_to_disk(_build_cache_key(["d1"]), index, chunks)
        _save_to_disk(_build_cache_key(["d2"]), index, chunks)

        cache_dir = _ensure_cache_dir()
        assert len(list(cache_dir.glob("*.pkl"))) == 2

        # Invalidate
        invalidate_bm25_index()

        # Disk cache should be empty
        assert len(list(cache_dir.glob("*.pkl"))) == 0


# ── Edge Cases ───────────────────────────────────────────


class TestRetrievalEdgeCases:
    """Tests for edge cases in retrieval."""

    def test_rrf_duplicate_chunks(self):
        """Test RRF handles duplicate chunks from different sources."""
        bm25_results = [
            {"chunk_id": "same-id", "content": "test", "score": 0.9, "source": "bm25"},
        ]
        dense_results = [
            {
                "chunk_id": "same-id",
                "content": "test",
                "score": 0.8,
                "source": "vector",
            },
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

    @pytest.mark.asyncio
    async def test_rewrite_short_no_demonstrative_no_rewrite(self):
        """Test that a short query without demonstrative does not trigger rewrite."""
        history = [
            {"role": "user", "content": "What is machine learning?"},
            {"role": "assistant", "content": "It's a subset of AI."},
        ]
        result = await rewrite_query("python", history)
        # "python" is short but has no demonstrative (this, that, it, etc.)
        # so no rewrite is triggered
        assert result is None
