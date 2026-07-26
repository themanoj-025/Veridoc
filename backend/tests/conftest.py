"""Pytest fixtures — mocks for DB, vector store, embedding model, and FastAPI test client."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.core.config import settings
from app.core.security import hash_password, create_access_token, create_refresh_token
from app.models.user import User


# ── Test Settings ────────────────────────────────────────

@pytest.fixture(autouse=True)
def patch_settings():
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
        yield mock_settings


# ── Mock DB Session ──────────────────────────────────────

@pytest_asyncio.fixture
async def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
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
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
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
def mock_vector_store():
    """Mock the ChromaDB vector store."""
    vs = MagicMock()
    vs.search = AsyncMock(return_value=[])
    vs.add_chunks = AsyncMock(return_value=["mock-id-1", "mock-id-2"])
    vs.delete_document = AsyncMock()
    vs.count_documents = AsyncMock(return_value=0)
    return vs


# ── Mock Embedding Model ─────────────────────────────────

@pytest.fixture
def mock_embedding_model():
    """Mock the sentence-transformers embedding model."""
    model = MagicMock()
    model.encode = MagicMock(return_value=[[0.1] * 384])  # 384-dim embedding
    return model


# ── Mock LLM Provider ────────────────────────────────────

@pytest.fixture
def mock_llm():
    """Mock the LLM provider."""
    llm = MagicMock()
    llm.model_name = "test-model"
    llm.chat = AsyncMock(return_value="This is a test response.")
    llm.stream_chat = MagicMock()

    async def async_gen():
        yield "This "
        yield "is "
        yield "a "
        yield "test."

    llm.stream_chat.return_value = async_gen()
    return llm


# ── Mock BM25 / NLTK ─────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_nltk():
    """Mock NLTK to avoid punkt download during tests."""
    with patch("nltk.word_tokenize") as mock_tokenize:
        mock_tokenize.side_effect = lambda text: text.lower().split()
        yield mock_tokenize


# ── Mock BM25 ────────────────────────────────────────────

@pytest.fixture
def mock_bm25():
    """Mock the BM25 index."""
    bm25 = MagicMock()
    bm25.get_scores = MagicMock(return_value=[0.5, 0.3, 0.1])
    return bm25


@pytest.fixture
def mock_bm25_builder(mock_bm25):
    """Patch the BM25 index builder."""
    with patch("app.services.retrieval._build_bm25_index") as mock_build:
        mock_build.return_value = mock_bm25
        yield mock_build


# ── Mock File System ─────────────────────────────────────

@pytest.fixture
def temp_upload_dir(tmp_path):
    """Create a temporary upload directory."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    with patch.object(settings, "upload_dir", upload_dir):
        yield upload_dir


# ── FastAPI Test Client ─────────────────────────────────

@pytest_asyncio.fixture
async def test_client() -> AsyncGenerator[AsyncClient, None]:
    """Create a FastAPI test client with mocked dependencies."""
    # Patch database init
    with patch("app.core.database.init_db", AsyncMock()), \
         patch("app.core.database.close_db", AsyncMock()), \
         patch("app.core.database.get_session"):

        from app.main import app

        # Override the lifespan to avoid real DB init
        app.router.lifespan = None

        transport = ASGITransport(app=app)  # type: ignore[arg-type]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
