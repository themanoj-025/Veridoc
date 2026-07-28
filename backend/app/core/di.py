"""Dependency injection container — stores initialized service instances in FastAPI app.state.

Usage from lifespan::

    from app.core.di import init_container
    app.state.container = init_container(app)

Usage from getter functions::

    def get_vector_store(app: FastAPI | None = None) -> VectorStore:
        container = getattr(app, "container", None) if app else None
        if container and container.vector_store:
            return container.vector_store
        return _fallback_vector_store()  # module-level singleton

Usage from tests::

    container = DIContainer()
    container.vector_store = MagicMock()
    # Pass to service under test
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI


class DIContainer:
    """Holds initialized service instances, injectable via ``app.state.container``.

    Any attribute set to ``None`` means "use the global fallback singleton."
    """

    def __init__(self) -> None:
        self.vector_store: Any = None
        self.llm_provider: Any = None
        self.job_queue: Any = None
        self.embedding_model: Any = None
        self.reranker: Any = None

    @classmethod
    def init_default(cls, app: FastAPI | None = None) -> "DIContainer":
        """Create a container with globally-configured defaults."""
        container = cls()

        # Always initialize the job queue (it manages its own Redis connection)
        from app.services.job_queue import get_job_queue
        container.job_queue = get_job_queue()

        # LLM provider — lazy, rely on the global getter
        # Vector store — lazy, relies on global getter
        # These are left as None so the getter functions use their default singletons
        return container


def get_container(app: FastAPI | None) -> DIContainer | None:
    """Safely retrieve the DI container from ``app.state``."""
    if app is None:
        return None
    return getattr(app.state, "container", None)
