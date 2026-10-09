"""Pytest fixtures — mocks for DB, vector store, embedding model, and FastAPI test client."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from app.core.config import settings
from app.core.database import get_session as db_get_session
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models.user import User
from httpx import ASGITransport, AsyncClient

# ── Test Settings ────────────────────────────────────────


@pytest.fixture(autouse=True)
def patch_settings() -> Any:
    """Override settings for testing."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.app_env = "test"
        mock_settings.jwt_secret = "test-secret-key-for-testing-only"
        mock_settings.jwt_algorithm = "HS256"
        mock_settings.access_token_expire_minutes = 30
        mock_settings.refresh_token_expire_days = 7
        mock_settings.database_url = "sqlite+aiosqlite:///:memory:"
        mock_settings.log_level = "ERROR"
        mock_settings.cors_origins = "*"
        mock_settings.rate_limit_per_minute = 1000
        mock_settings.redis_cache_enabled = True
        mock_settings.redis_cache_ttl_seconds = 3600
        # External service URLs (avoid real connections in tests)
        mock_settings.chroma_url = "http://localhost:8000"
        mock_settings.ollama_base_url = "http://localhost:11434"
        mock_settings.ollama_model = "test-model"
        mock_settings.minio_endpoint = "localhost:9000"
        mock_settings.minio_access_key = "test"
        mock_settings.minio_secret_key = "test"
        mock_settings.minio_use_ssl = False
        mock_settings.minio_bucket = "test-bucket"
        mock_settings.llm_provider = "ollama"
        yield mock_settings


# ── Mock DB Session ──────────────────────────────────────


@pytest_asyncio.fixture
async def mock_db_session() -> Any:
    """Create a mock async database session."""
    from datetime import datetime

    session = AsyncMock()
    session.execute = AsyncMock()

    async def _refresh_side_effect(obj) -> Any:
        """Simulate DB refresh by setting server-default fields."""
        import uuid as _uuid

        if hasattr(obj, "id") and obj.id is None:
            obj.id = _uuid.uuid4()
        if hasattr(obj, "is_active") and obj.is_active is None:
            obj.is_active = True
        if hasattr(obj, "is_verified") and obj.is_verified is None:
            obj.is_verified = False
        if hasattr(obj, "created_at") and obj.created_at is None:
            obj.created_at = datetime.now(UTC)

    session.flush = AsyncMock()
    session.refresh = AsyncMock(side_effect=_refresh_side_effect)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


# ── Mock User ────────────────────────────────────────────


@pytest.fixture
def sample_user() -> User:
    """Create a sample user for testing."""
    return User(
        id=uuid.uuid4(),
        email="testuser@example.com",
        hashed_password=hash_password("testpassword123"),
        full_name="Test User",
        is_active=True,
        is_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def sample_user_token(sample_user: User) -> str:
    """Generate a valid JWT access token for the sample user."""
    return create_access_token(sample_user.id)


@pytest.fixture
def sample_refresh_token(sample_user: User) -> str:
    """Generate a valid JWT refresh token for the sample user."""
    return create_refresh_token(sample_user.id)


# ── Mock Chroma/Vector Store ─────────────────────────────


@pytest.fixture
def mock_vector_store() -> Any:
    """Mock the ChromaDB vector store."""
    vs = MagicMock()
    vs.search = AsyncMock(return_value=[])
    vs.add_chunks = AsyncMock(return_value=["mock-id-1", "mock-id-2"])
    vs.delete_document = AsyncMock()
    vs.count_documents = AsyncMock(return_value=0)
    return vs


# ── Mock Embedding Model ─────────────────────────────────


@pytest.fixture
def mock_embedding_model() -> Any:
    """Mock the sentence-transformers embedding model."""
    model = MagicMock()
    model.encode = MagicMock(return_value=[[0.1] * 384])  # 384-dim embedding
    return model


# ── Mock LLM Provider ────────────────────────────────────


@pytest.fixture
def mock_llm() -> Any:
    """Mock the LLM provider."""
    llm = MagicMock()
    llm.model_name = "test-model"
    llm.chat = AsyncMock(return_value="This is a test response.")
    llm.stream_chat = MagicMock()

    async def async_gen() -> Any:
        yield "This "
        yield "is "
        yield "a "
        yield "test."

    llm.stream_chat.return_value = async_gen()
    return llm


# ── Mock BM25 / NLTK ─────────────────────────────────────


@pytest.fixture(autouse=True)
def mock_nltk() -> Any:
    """Mock NLTK to avoid punkt download during tests."""
    with patch("nltk.word_tokenize") as mock_tokenize:
        mock_tokenize.side_effect = lambda text: text.lower().split()
        yield mock_tokenize


# ── Mock BM25 ────────────────────────────────────────────


@pytest.fixture
def mock_bm25() -> Any:
    """Mock the BM25 index."""
    bm25 = MagicMock()
    bm25.get_scores = MagicMock(return_value=[0.5, 0.3, 0.1])
    return bm25


@pytest.fixture
def mock_bm25_builder(mock_bm25) -> Any:
    """Patch the BM25 index builder in the retrieval package."""
    with patch("app.services.retrieval.bm25.get_bm25_index") as mock_build:
        mock_build.return_value = (mock_bm25, [])  # Returns (index, chunks) tuple
        yield mock_build


# ── Mock File System ─────────────────────────────────────


@pytest.fixture
def temp_upload_dir(tmp_path) -> Any:
    """Create a temporary upload directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    with patch.object(settings, "upload_dir", upload_dir):
        yield upload_dir


# ── FastAPI Test Client ─────────────────────────────────


@pytest_asyncio.fixture
async def test_client(mock_db_session, mock_httpx) -> AsyncGenerator[AsyncClient, None]:
    """Create a FastAPI test client with mocked dependencies."""
    from app.main import app

    # Override the lifespan to avoid real DB init
    app.router.lifespan = None

    # Override DB session dependency
    async def override_get_session() -> Any:
        yield mock_db_session

    app.dependency_overrides[db_get_session] = override_get_session

    transport = cast(ASGITransport, ASGITransport(app=app))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_httpx() -> Any:
    """Mock httpx.AsyncClient and health check internals for tests."""
    mock_response = MagicMock()
    mock_response.status_code = 503  # Simulate unavailable

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    # Patch httpx and JobQueue to prevent real connections
    patches = [
        patch("httpx.AsyncClient", return_value=mock_client),
    ]
    for p in patches:
        p.start()
    yield mock_client
    for p in patches:
        p.stop()


# ════════════════════════════════════════════════════════════════
# Integration-test fixtures (shared by test_integration*.py — fixtures
# defined in a test module are NOT visible to sibling modules)
# ════════════════════════════════════════════════════════════════

try:
    from testcontainers.postgres import PostgresContainer as _PostgresContainer
except ImportError:
    _PostgresContainer = None


def _docker_available() -> bool:
    """Check if Docker is running and accessible."""
    if _PostgresContainer is None:
        return False
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except (OSError, ImportError):
        return False


@pytest.fixture(scope="session")
def postgres_container() -> None:
    """Start a Postgres container for the test session.

    Gracefully skips if Docker is not available or testcontainers
    is not installed.
    """
    if _PostgresContainer is None:
        pytest.skip("testcontainers not installed")
    if not _docker_available():
        pytest.skip("Docker not available or testcontainers not installed")
    try:
        with _PostgresContainer("postgres:16-alpine") as pg:
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
    # testcontainers 4.x returns postgresql+psycopg2:// (sync driver); the
    # asyncio extension requires an async driver. Handle both URL shapes.
    async_url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
        "postgresql://", "postgresql+asyncpg://"
    )
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
    f = temp_dir / "sample_document.txt"
    f.write_text(content, encoding="utf-8")
    return f


@pytest.fixture
def app() -> Any:
    """Provide the FastAPI app instance for dependency overrides."""
    from app.main import app as _app

    return _app
