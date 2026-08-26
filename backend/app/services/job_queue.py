"""Job queue abstraction — durable background job processing for ingestion.

Uses ARQ (Async Redis Queue) when Redis is available, with automatic
fallback to synchronous in-process execution when Redis is not configured.
This allows the app to run without Redis during local development and testing
while still supporting the full retry/dead-letter workflow in production.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Maximum retries before a job is moved to dead-letter status
MAX_RETRIES = 3
# Base delay for exponential backoff (in seconds)
RETRY_BACKOFF_BASE = 10  # 10s, 20s, 40s


class JobQueue:
    """Abstraction over background job processing.

    Two modes:
    - **Redis-backed** (production): uses ARQ with a Redis pool for durable,
      retryable, observable job execution.
    - **Sync fallback** (dev/test): runs jobs immediately in a spawned task.
    """

    def __init__(self) -> None:
        self._arq_pool: Any = None
        self._initialized = False

    @property
    def is_redis_available(self) -> bool:
        """Check whether Redis is configured and reachable."""
        return bool(settings.redis_url)

    async def initialize(self) -> None:
        """Set up the ARQ Redis connection pool (if available)."""
        if self._initialized:
            return

        if self.is_redis_available:
            try:
                from arq.connections import create_pool

                pool = await create_pool(settings.redis_url)
                self._arq_pool = pool
                logger.info("ARQ Redis pool established at %s", settings.redis_url)
            except (OSError, ValueError, ImportError) as e:
                logger.warning(
                    "Redis unavailable at %s, falling back to sync execution: %s",
                    settings.redis_url,
                    e,
                )
                self._arq_pool = None

        self._initialized = True

    async def shutdown(self) -> None:
        """Close the ARQ Redis connection pool."""
        if self._arq_pool is not None:
            try:
                await self._arq_pool.close()
            except (OSError, ValueError) as e:
                logger.warning("Error closing ARQ pool: %s", e)
            self._arq_pool = None
        self._initialized = False

    async def enqueue_job(
        self,
        job_func: Callable[..., Any],
        *args: Any,
        job_id: str | None = None,
        max_retries: int = MAX_RETRIES,
        **kwargs: Any,
    ) -> str | None:
        """Enqueue a job for background processing.

        Returns the job ID if successfully enqueued (Redis mode),
        or ``None`` if executed synchronously (fallback mode).
        """
        if self._arq_pool is not None:
            return await self._enqueue_redis(
                job_func, *args, job_id=job_id, max_retries=max_retries, **kwargs
            )

        # Fallback: run synchronously in a spawned task
        import asyncio

        jid = job_id or str(uuid.uuid4())
        logger.info(
            "Running job %s synchronously (no Redis): %s", jid[:8], job_func.__name__
        )
        asyncio.create_task(
            self._run_with_retry(job_func, jid, max_retries, *args, **kwargs)
        )
        return None

    async def _enqueue_redis(
        self,
        job_func: Callable[..., Any],
        *args: Any,
        job_id: str | None = None,
        max_retries: int = MAX_RETRIES,
        **kwargs: Any,
    ) -> str:
        """Enqueue a job in Redis via ARQ.

        ARQ's ``enqueue_job`` accepts the function object directly
        and introspects ``__module__`` + ``__name__`` internally.
        """
        assert self._arq_pool is not None
        jid = await self._arq_pool.enqueue_job(
            job_func,  # ARQ expects the actual function object
            *args,
            _job_id=job_id,
            _max_retries=max_retries,
            _job_timeout=settings.llm_timeout + 120,
            **kwargs,
        )
        logger.info(
            "Enqueued job %s via ARQ: %s",
            str(jid)[:8] if jid else "?",
            job_func.__name__,
        )
        return str(jid) if jid else str(uuid.uuid4())

    async def _run_with_retry(
        self,
        job_func: Callable[..., Any],
        job_id: str,
        max_retries: int,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Run a job with retry + backoff in the sync fallback path."""
        import asyncio

        last_exc: Exception | None = None
        for attempt in range(1 + max_retries):
            try:
                if asyncio.iscoroutinefunction(job_func):
                    await job_func(*args, **kwargs)
                else:
                    job_func(*args, **kwargs)
                logger.info("Job %s completed on attempt %d", job_id[:8], attempt + 1)
                return
            except (RuntimeError, OSError, ValueError) as e:
                last_exc = e
                logger.warning(
                    "Job %s attempt %d failed: %s",
                    job_id[:8],
                    attempt + 1,
                    e,
                )
                if attempt < max_retries:
                    delay = RETRY_BACKOFF_BASE * (2**attempt)
                    logger.info("Retrying job %s in %ds...", job_id[:8], delay)
                    await asyncio.sleep(delay)

        # All retries exhausted — dead letter
        logger.error(
            "Job %s failed after %d attempts. Last error: %s",
            job_id[:8],
            1 + max_retries,
            last_exc,
        )

    async def get_queue_status(self) -> dict[str, Any]:
        """Get queue health and depth (for health checks)."""
        if self._arq_pool is not None:
            try:
                info = await self._arq_pool.info()
                return {
                    "mode": "redis",
                    "connected": True,
                    "redis_version": info.get("redis_version", "unknown"),
                }
            except (OSError, ValueError) as e:
                return {"mode": "redis", "connected": False, "error": str(e)}
        return {"mode": "sync_fallback", "connected": False}


def get_job_queue() -> JobQueue:
    """Get the JobQueue instance.

    Checks the DI container first (see :class:`app.core.di.DIContainer`).
    Falls back to an uncached instance when no container is active
    (standalone scripts, some test scenarios).
    """
    from app.core.di import get_di_container

    container = get_di_container()
    if container is not None:
        return container.get_or_create_job_queue()
    return JobQueue()
