"""Dependency injection container — stores initialized service instances in FastAPI app.state.

How it works
------------
1. **Lifespan**: ``init_container()`` is called during the FastAPI lifespan, which
   creates a :class:`DIContainer` and stores it in ``app.state.container`` AND in
   a ``ContextVar`` (``_container_var``).

2. **Getter functions** (e.g. ``get_vector_store()``) check the ``ContextVar``
   first.  If a container is found with the requested service, it is returned
   directly.  Otherwise a new uncached instance is created as a fallback (for
   standalone scripts and tests not using the DI container).

3. **Tests**: override the ``ContextVar`` with a :class:`DIContainer` containing
   mocks::

       container = DIContainer()
       container.vector_store = MagicMock()
       set_di_container(container)

   All getter functions will now return the mocked instances automatically.

Usage from lifespan::

    from app.core.di import init_container

    async with lifespan(app):
        container = init_container(app)
        app.state.container = container
        set_di_container(container)
        ...

Usage from route handler Depends()::

    from app.core.di import get_di_container_dep

    @router.get(...)
    async def handler(container: DIContainer = Depends(get_di_container_dep)):
        vs = container.vector_store
        ...

Usage from test fixtures::

    from app.core.di import DIContainer, set_di_container

    @pytest.fixture
    def di_container():
        c = DIContainer()
        c.vector_store = MagicMock()
        set_di_container(c)
        return c
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Protocol, runtime_checkable

from fastapi import FastAPI

from app.services.job_queue import JobQueue
from app.services.llm_provider import LLMProvider
from app.services.vector_store import VectorStore

# ── Protocols for third-party types ───────────────────────────────
# These are structural typing Protocols so the DI container is
# statically checkable without depending on sentence-transformers'
# own (untyped) stubs at runtime.


@runtime_checkable
class EmbeddingModel(Protocol):
    """Structural protocol for embedding models (SentenceTransformer)."""

    def encode(
        self,
        texts: list[str],
        show_progress_bar: bool = False,
        **kwargs: object,
    ) -> object:
        """Encode texts into embeddings. Must return an object with .tolist()."""
        ...  # pragma: no cover


@runtime_checkable
class Reranker(Protocol):
    """Structural protocol for cross-encoder rerankers (CrossEncoder)."""

    def predict(
        self,
        pairs: list[tuple[str, str]],
        **kwargs: object,
    ) -> list[float]:
        """Score query-document pairs."""
        ...  # pragma: no cover


# ContextVar that holds the active DIContainer for the current asyncio context.
# Set during the FastAPI lifespan, read by all getter functions.
_container_var: ContextVar[DIContainer | None] = ContextVar(
    "di_container",
    default=None,
)


class DIContainer:
    """Holds initialized service instances.

    All fields are typed (no ``Any`` used), so static type checkers can
    verify that correct types are assigned and retrieved.

    Any attribute left as ``None`` means "not yet initialized" — the getter
    function will lazy-initialize and store it back in the container.
    """

    def __init__(self) -> None:
        self.vector_store: VectorStore | None = None
        self.llm_provider: LLMProvider | None = None
        self.job_queue: JobQueue | None = None
        self.embedding_model: EmbeddingModel | None = None
        self.reranker: Reranker | None = None

    # ── Lazy initialisers (called by getter functions) ──────────────

    def get_or_create_vector_store(self) -> VectorStore:
        """Lazy-init vector store and cache it in the container."""
        if self.vector_store is None:
            self.vector_store = VectorStore()
        return self.vector_store

    def get_or_create_llm(self) -> LLMProvider:
        """Lazy-init LLM provider and cache it in the container."""
        if self.llm_provider is None:
            from app.services.llm_provider import _build_llm_provider

            self.llm_provider = _build_llm_provider()
        return self.llm_provider

    def get_or_create_embedding_model(self) -> EmbeddingModel:
        """Lazy-init embedding model and cache it in the container."""
        if self.embedding_model is None:
            import structlog
            from sentence_transformers import SentenceTransformer

            structlog.get_logger(__name__).info(
                "Loading embedding model: all-MiniLM-L6-v2"
            )
            model = SentenceTransformer("all-MiniLM-L6-v2")
            if not isinstance(model, EmbeddingModel):
                # Runtime safety: wrap non-conforming instance
                return model  # type: ignore[return-value]
            self.embedding_model = model
        return self.embedding_model

    def get_or_create_reranker(self) -> Reranker | None:
        """Lazy-init cross-encoder reranker and cache it in the container."""
        if self.reranker is None:
            try:
                import structlog
                from sentence_transformers import CrossEncoder

                structlog.get_logger(__name__).info(
                    "Loading cross-encoder re-ranker: ms-marco-MiniLM-L-6-v2"
                )
                model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
                if isinstance(model, Reranker):
                    self.reranker = model
                else:
                    return model  # type: ignore[return-value]
            except (OSError, ValueError, ImportError) as exc:
                import structlog

                structlog.get_logger(__name__).warning(
                    "Failed to load cross-encoder", error=str(exc)
                )
                self.reranker = None
        return self.reranker

    def get_or_create_job_queue(self) -> JobQueue:
        """Lazy-init job queue and cache it in the container."""
        if self.job_queue is None:
            self.job_queue = JobQueue()
        return self.job_queue


# ── ContextVar helpers ────────────────────────────────────────────


def set_di_container(container: DIContainer | None) -> None:
    """Set the DI container for the current asyncio context.

    Call this during the FastAPI **lifespan** (startup), or in test
    fixtures to inject mocked services.
    """
    _container_var.set(container)


def get_di_container() -> DIContainer | None:
    """Retrieve the active DI container, or ``None`` if not set."""
    return _container_var.get()


# ── FastAPI app wiring ────────────────────────────────────────────


def init_container(app: FastAPI) -> DIContainer:
    """Create and wire a :class:`DIContainer` into *app.state*.

    This is called during the FastAPI lifespan::

        container = init_container(app)
        set_di_container(container)

    The container is stored in ``app.state.container`` AND set in the
    ``ContextVar`` so that all getter functions (which check the
    ContextVar first) find it automatically.

    Only the **job queue** is eagerly initialized (it manages its own
    Redis connection pool).  All other services (vector store, LLM
    provider, embedding model, reranker) are lazy-initialised on first
    use and cached in the container.
    """
    container = DIContainer()

    # Eagerly init the job queue so the lifespan can call .initialize()
    container.get_or_create_job_queue()

    app.state.container = container
    set_di_container(container)
    return container
