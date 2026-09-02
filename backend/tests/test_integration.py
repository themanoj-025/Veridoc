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
    cd backend && python -m pytest tests/test_integration.py -v --timeout=120
"""

from __future__ import annotations

import uuid
from datetime import UTC
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

pytestmark = pytest.mark.slow
pytestmark = pytest.mark.integration

pytestmark = pytest.mark.slow
# ── Module-level skips ────────────────────────────────────────────
# Skip if testcontainers not installed
try:
    from testcontainers.postgres import PostgresContainer
except ImportError:
    PostgresContainer = None

# Skip if chromadb not installed
try:
    import chromadb
except ImportError:
    chromadb = None

pytestmark = [
    pytest.mark.timeout(120),  # containers need time to pull/boot
]


def _docker_available() -> bool:
    """Check if Docker is running and accessible."""
    if PostgresContainer is None:
        return False
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except (OSError, ImportError):
        return False


# ══════════════════════════════════════════════════════════════════
# Test helper — a VectorStore-compatible wrapper for EphemeralClient
# ══════════════════════════════════════════════════════════════════


class _TestVectorStore:
    """A drop-in replacement for ``VectorStore`` that uses ChromaDB's
    ``EphemeralClient`` instead of ``HttpClient``.

    Exposes the same ``add_chunks``, ``search``, ``get_all_chunks``,
    ``delete_document``, and ``count_documents`` interface so that
    ``process_document()`` can be tested against a real (but in-memory)
    ChromaDB instance.
    """

    def __init__(self) -> None:
        import chromadb

        self._client = chromadb.EphemeralClient()
        self._collection_name = "veridoc_documents"
        try:
            self._collection = self._client.get_collection(self._collection_name)
        except (ValueError, chromadb.errors.NotFoundError):
            self._collection = self._client.create_collection(
                self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )

    async def add_chunks(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
    ) -> list[str]:
        ids = [str(uuid.uuid4()) for _ in chunks]
        documents = [c["content"] for c in chunks]
        metadatas = [
            {
                "document_id": c["document_id"],
                "chunk_index": c.get("chunk_index", 0),
                "page_number": c.get("page_number"),
                "document_title": c.get("document_title", ""),
            }
            for c in chunks
        ]
        # Compatibility shim for newer chromadb (>=1.5) which rejects
        # ``None`` metadata values.  The production ``VectorStore`` also
        # passes ``page_number=None`` via this same code path when a chunk
        # has no page number.  If the pinned chromadb version is upgraded
        # in ``requirements.txt``, apply the same ``None``-filter in
        # ``VectorStore.add_chunks()`` too.
        clean_metadatas = [
            {k: v for k, v in m.items() if v is not None} for m in metadatas
        ]
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=clean_metadatas,
        )
        return ids

    async def search(
        self,
        query_embedding: list[float],
        document_ids: list[str] | None = None,
        top_k: int = 20,
    ) -> list[dict]:
        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}}
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        chunks: list[dict] = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                chunks.append(
                    {
                        "chunk_id": results["ids"][0][i],
                        "content": results["documents"][0][i],
                        "document_id": meta.get("document_id", ""),
                        "document_title": meta.get("document_title", ""),
                        "page_number": meta.get("page_number"),
                        "score": (
                            1.0 - results["distances"][0][i]
                            if results.get("distances")
                            else 0.0
                        ),
                        "source": "vector",
                    }
                )
        return chunks

    async def get_all_chunks(self, document_ids: list[str] | None = None) -> list[dict]:
        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}}
        results = self._collection.get(where=where, include=["documents", "metadatas"])
        chunks: list[dict] = []
        if results["ids"]:
            for i in range(len(results["ids"])):
                meta = results["metadatas"][i] if results["metadatas"] else {}
                chunks.append(
                    {
                        "chunk_id": results["ids"][i],
                        "content": (
                            results["documents"][i] if results["documents"] else ""
                        ),
                        "document_id": meta.get("document_id", ""),
                        "document_title": meta.get("document_title", ""),
                        "page_number": meta.get("page_number"),
                    }
                )
        return chunks

    async def delete_document(self, document_id: str) -> None:
        self._collection.delete(where={"document_id": document_id})

    async def count_documents(self) -> int:
        return self._collection.count()


# ══════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def postgres_container() -> None:
    """Start a Postgres container for the test session.

    Yields a ``testcontainers.postgres.PostgresContainer`` instance
    whose connection URL can be used with SQLAlchemy async engines.

    Gracefully skips if Docker is not available or testcontainers
    is not installed.
    """
    if not _docker_available():
        pytest.skip("Docker not available or testcontainers not installed")
    try:
        with PostgresContainer("postgres:16-alpine") as pg:
            yield pg
    except (OSError, RuntimeError) as exc:
        pytest.skip(f"Docker container failed to start: {exc}")


@pytest_asyncio.fixture
async def pg_engine_and_factory(postgres_container) -> None:
    """Create a SQLAlchemy async engine + session factory pointing to
    the testcontainer Postgres.  All tables are created at setup and
    dropped at teardown (or on engine dispose).
    """
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    url = postgres_container.get_connection_url()
    async_url = url.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(async_url, echo=False, pool_pre_ping=True)

    from app.core.database import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    yield engine, factory
    await engine.dispose()


@pytest_asyncio.fixture
async def pg_session(pg_engine_and_factory) -> None:
    """A single Postgres session for the test."""
    _engine, factory = pg_engine_and_factory
    async with factory() as session:
        yield session


@pytest.fixture
def temp_dir(tmp_path) -> Path:
    """Create a temporary upload directory for test files."""
    d = tmp_path / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def sample_text_file(temp_dir) -> Path:
    """Create a sample .txt document with realistic multi-paragraph content."""
    content = (
        "Machine Learning Fundamentals\n\n"
        "Machine learning is a subset of artificial intelligence that enables "
        "systems to learn and improve from experience without being explicitly "
        "programmed. It focuses on the development of computer programs that "
        "can access data and use it to learn for themselves.\n\n"
        "Types of Machine Learning\n\n"
        "There are three main types of machine learning: supervised learning, "
        "unsupervised learning, and reinforcement learning. Supervised learning "
        "uses labeled data to train models. Unsupervised learning finds patterns "
        "in unlabeled data. Reinforcement learning uses rewards and punishments "
        "to train agents.\n\n"
        "Supervised Learning Details\n\n"
        "Supervised learning is the most common form of machine learning. In "
        "this paradigm, the algorithm is trained on a labeled dataset, where "
        "each training example is paired with an output label. The algorithm "
        "learns to map inputs to outputs by finding patterns in the training data. "
        "Common algorithms include linear regression, decision trees, random "
        "forests, and neural networks.\n\n"
        "Applications\n\n"
        "Machine learning has numerous applications including image recognition, "
        "natural language processing, recommendation systems, fraud detection, "
        "and autonomous vehicles. Each application leverages different types of "
        "machine learning algorithms depending on the specific requirements and "
        "the nature of the available data.\n\n"
        "Conclusion\n\n"
        "Machine learning continues to evolve rapidly, with new techniques and "
        "applications emerging regularly. Understanding the fundamentals is "
        "essential for anyone working in modern technology."
    )
    file_path = temp_dir / "ml_fundamentals.txt"
    file_path.write_text(content, encoding="utf-8")
    return file_path


# ══════════════════════════════════════════════════════════════════
# Test: process_document() end-to-end via mocked dependencies
# ══════════════════════════════════════════════════════════════════


@pytest.mark.skipif(chromadb is None, reason="chromadb not installed")
@pytest.mark.asyncio