"""Database engine, session factory, and base model."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=(settings.app_env == "development"),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session.

    The generator yields an **open** session.  It does NOT commit, close,
    or return the session to the pool — the caller (service method or
    route handler) owns the full lifecycle:

    * Call ``await session.commit()`` to persist changes.
    * Call ``await session.rollback()`` on error.
    * Call ``await session.close()`` when done.

    This design is necessary for the SSE streaming endpoint
    (``ChatService.stream_response``), which writes to the database
    *after* the route handler has returned and the FastAPI dependency
    graph has been torn down.  If ``get_session()`` closed the session in
    its ``finally`` block, the SSE stream would crash with an
    "await on a closed session" error.
    """
    session = async_session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        # Close on error so the pool doesn't accumulate orphaned sessions
        await session.close()
        raise
    # Normal exit — intentionally NOT closing.  The caller is responsible.
    #
    # For regular request/response endpoints, the route handler calls
    # ``await session.close()`` after committing.  For the SSE stream,
    # the ``event_generator``'s ``finally`` block closes the session
    # after all tokens have been streamed and the assistant message has
    # been persisted.


async def init_db() -> None:
    """Create all tables (used in tests / first-run)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose of the engine."""
    await engine.dispose()
