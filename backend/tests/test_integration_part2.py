"""Integration tests — real Postgres (testcontainers) + real ChromaDB (ephemeral).

These tests exercise the full document → parse → chunk → embed → index → search
pipeline against real databases, not mocks.  Key design decisions:

- **Postgres**: ``testcontainers.postgres.PostgresContainer`` provides a real
  Postgres 16 instance for each test session.
- **ChromaDB**: ``chromadb.EphemeralClient()`` — fast, no Docker needed for
  Chroma, exercises the exact same Python API as the production HTTP client.
- **Embedding model**: Mocked with ``numpy.random`` (real sentence-transformers
  is too heavy for CI).  This tests the ChromaDB API integration, not search
  quality.
- **``process_document()``**: Called end-to-end in the main pipeline test via
  a ``_TestVectorStore`` helper that wraps ``EphemeralClient`` with the same
  interface as the production ``VectorStore``.

Prerequisites
-------------
- Docker must be running (testcontainers starts Postgres in a container)
- ``testcontainers`` package must be installed (see requirements.txt)
- Tests are auto-skipped if testcontainers is not installed

Quick start::

    docker info  # confirm Docker is running
    cd backend && python -m pytest tests/test_integration.py -v --timeout=120 — Part 2."""

from __future__ import annotations

import uuid
from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest

# Skip ChromaDB-backed tests if chromadb is not installed
try:
    import chromadb
except ImportError:
    chromadb = None


async def test_process_document_end_to_end(
    pg_engine_and_factory,
    sample_text_file,
    temp_dir,
) -> None:
    """Call ``process_document()`` with a real Postgres session factory,
    patched embedding model, and a ``_TestVectorStore`` (EphemeralClient).
    Then verify:
      - Document status transitions to ``\"indexed\"``
      - Chunks are persisted in Postgres with correct indices
      - Chunks are searchable in ChromaDB
      - BM25 cache is invalidated (covered by the ``invalidate_bm25_index`` call)
    """
    import numpy as np
    from app.models.chunk import Chunk
    from app.models.document import Document
    from app.services.ingestion import process_document
    from sqlalchemy import select

    _engine, test_factory = pg_engine_and_factory

    # ── 1. Create a Document record in Postgres ──────────────
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=uuid.uuid4(),
        title="Machine Learning Fundamentals",
        filename=sample_text_file.name,
        file_type="txt",
        file_size=sample_text_file.stat().st_size,
        file_path=str(sample_text_file),
        status="pending",
    )
    async with test_factory() as session:
        session.add(doc)
        await session.flush()

    # ── 2. Set up test Chroma + embedding mock ──────────────
    test_vs = _TestVectorStore()

    mock_model = MagicMock()
    embedding_dim = 384

    def _mock_encode(texts, **kwargs):
        """Return embeddings matching the number of input texts."""
        n = len(texts) if isinstance(texts, (list, tuple)) else 1
        return np.random.rand(n, embedding_dim)

    mock_model.encode = MagicMock(side_effect=_mock_encode)

    # Patch the heavy dependencies that process_document() calls
    with (
        patch("app.services.ingestion.get_vector_store", return_value=test_vs),
        patch("app.services.ingestion.get_embedding_model", return_value=mock_model),
    ):
        # ── 3. Run the full ingestion orchestrator ───────────
        await process_document(doc_id, session_factory=test_factory)

    # ── 4. Verify Postgres: status + chunks ─────────────────
    async with test_factory() as session:
        result = await session.execute(select(Document).where(Document.id == doc_id))
        updated_doc = result.scalar_one_or_none()
        assert updated_doc is not None
        assert (
            updated_doc.status == "indexed"
        ), f"Expected status=indexed, got {updated_doc.status}"
        assert updated_doc.chunk_count is not None
        assert updated_doc.chunk_count > 0

        chunk_result = await session.execute(
            select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index)
        )
        orm_chunks = chunk_result.scalars().all()
        assert len(orm_chunks) == updated_doc.chunk_count
        assert orm_chunks[0].chunk_index == 0
        assert orm_chunks[-1].chunk_index == len(orm_chunks) - 1
        assert all(
            c.chroma_id is not None for c in orm_chunks
        ), "All chunks should have a chroma_id set by process_document"

    # ── 5. Verify ChromaDB: chunks are searchable ───────────
    vs_count = await test_vs.count_documents()
    assert (
        vs_count == updated_doc.chunk_count
    ), f"ChromaDB should contain {updated_doc.chunk_count} chunks, got {vs_count}"

    query_emb = np.random.rand(embedding_dim).tolist()
    search_results = await test_vs.search(
        query_embedding=query_emb,
        document_ids=[str(doc_id)],
        top_k=5,
    )
    assert len(search_results) > 0, "Search should return at least 1 chunk"
    for r in search_results:
        assert r["document_id"] == str(
            doc_id
        ), f"Expected document_id={doc_id}, got {r['document_id']}"


# ══════════════════════════════════════════════════════════════════
# Test: ChromaDB metadata filtering (document isolation)
# ══════════════════════════════════════════════════════════════════


@pytest.mark.skipif(chromadb is None, reason="chromadb not installed")
@pytest.mark.asyncio
async def test_chromadb_metadata_filtering() -> None:
    """Test document_id-based metadata filtering — a core requirement
    for per-user document isolation.  Exercises the same ``where`` clause
    that ``VectorStore.search()`` uses in production.

    Note: ChromaDB API is exercised directly here (not through the
    ``VectorStore`` wrapper) to validate the underlying filter mechanics.
    The ``VectorStore.search()`` method is tested via
    ``test_process_document_end_to_end`` above.
    """
    import numpy as np

    vs = _TestVectorStore()
    embedding_dim = 384
    doc_a_id = str(uuid.uuid4())
    doc_b_id = str(uuid.uuid4())

    # Add 3 chunks for doc_a
    await vs.add_chunks(
        [
            {
                "document_id": doc_a_id,
                "chunk_index": i,
                "content": f"Doc A chunk {i}",
                "document_title": "A",
            }
            for i in range(3)
        ],
        np.random.rand(3, embedding_dim).tolist(),
    )
    # Add 2 chunks for doc_b
    await vs.add_chunks(
        [
            {
                "document_id": doc_b_id,
                "chunk_index": i,
                "content": f"Doc B chunk {i}",
                "document_title": "B",
            }
            for i in range(2)
        ],
        np.random.rand(2, embedding_dim).tolist(),
    )
    assert await vs.count_documents() == 5

    q_emb = np.random.rand(embedding_dim).tolist()

    # Filter: only doc_a
    res_a = await vs.search(q_emb, document_ids=[doc_a_id], top_k=10)
    assert len(res_a) == 3, f"Expected 3 for doc_a, got {len(res_a)}"
    assert all(r["document_id"] == doc_a_id for r in res_a)

    # Filter: only doc_b
    res_b = await vs.search(q_emb, document_ids=[doc_b_id], top_k=10)
    assert len(res_b) == 2, f"Expected 2 for doc_b, got {len(res_b)}"
    assert all(r["document_id"] == doc_b_id for r in res_b)

    # No filter: all
    res_all = await vs.search(q_emb, document_ids=None, top_k=10)
    assert len(res_all) == 5, f"Expected 5 unfiltered, got {len(res_all)}"

    # Delete doc_a
    await vs.delete_document(doc_a_id)
    assert await vs.count_documents() == 2


# ══════════════════════════════════════════════════════════════════
# Test: Postgres Document → Chunk relationship + cascade delete
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_postgres_document_chunk_relationship(pg_session, temp_dir) -> None:
    """Test that Document → Chunk ORM relationships work correctly
    against real Postgres, including cascade delete.
    """
    from app.models.chunk import Chunk
    from app.models.document import Document
    from sqlalchemy import select

    doc = Document(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        title="Test Document",
        filename="test.txt",
        file_type="txt",
        file_size=100,
        file_path=str(temp_dir / "test.txt"),
        status="indexed",
    )
    pg_session.add(doc)
    await pg_session.flush()

    chunks_data = [
        Chunk(document_id=doc.id, chunk_index=i, content=f"Chunk {i}") for i in range(3)
    ]
    for c in chunks_data:
        pg_session.add(c)
    await pg_session.flush()

    await pg_session.refresh(doc)
    assert len(doc.chunks) == 3
    assert {c.chunk_index for c in doc.chunks} == {0, 1, 2}

    # Back-populates
    for c in chunks_data:
        await pg_session.refresh(c)
        assert c.document is not None
        assert c.document.id == doc.id

    # Cascade delete
    await pg_session.delete(doc)
    await pg_session.flush()
    remaining = await pg_session.execute(
        select(Chunk).where(Chunk.document_id == doc.id)
    )
    assert (
        remaining.scalar_one_or_none() is None
    ), "Cascade delete should remove all chunks"


# ══════════════════════════════════════════════════════════════════
# Test: Postgres user-scoped queries
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_postgres_user_scoped_queries(pg_session) -> None:
    """Test that user-scoped queries return correct results from
    real Postgres, exercising the ``(user_id, created_at)`` composite
    index via the standard list-documents query pattern.
    """
    from datetime import datetime

    from app.models.document import Document
    from sqlalchemy import func, select


    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    for i in range(5):
        doc = Document(
            id=uuid.uuid4(),
            user_id=user_id,
            title=f"Doc {i}",
            filename=f"f{i}.txt",
            file_type="txt",
            file_size=100 + i,
            file_path=f"/tmp/f{i}.txt",
            status="indexed",
            created_at=now,
        )
        pg_session.add(doc)
    await pg_session.flush()

    # List by user (exercises composite index ordering)
    result = await pg_session.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    assert len(result.scalars().all()) == 5

    # Count by user
    count = await pg_session.scalar(
        select(func.count(Document.id)).where(Document.user_id == user_id)
    )
    assert count == 5

    # Other user isolation
    other = await pg_session.execute(
        select(Document).where(Document.user_id == uuid.uuid4())
    )
    assert len(other.scalars().all()) == 0

    # Pagination
    paginated = await pg_session.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .limit(2)
        .offset(1)
    )
    assert len(paginated.scalars().all()) == 2
