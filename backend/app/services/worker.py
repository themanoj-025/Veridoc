"""Worker tasks for ARQ (Async Redis Queue) — document processing.

These functions are registered with ARQ's worker pool and called
when jobs are dequeued from Redis. Each function receives a ``ctx``
dict as the first argument (containing the Redis pool and job metadata),
followed by the original job arguments.
"""

from __future__ import annotations

import uuid

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)


async def process_document_task(ctx: dict, document_id: str) -> None:
    """Process a document: parse → OCR-if-needed → chunk → embed → index.

    This is the ARQ worker entry point for document ingestion jobs.
    The ``ctx`` dict contains the Redis pool and job metadata
    (set automatically by ARQ).

    Parameters
    ----------
    ctx : dict
        ARQ job context (contains ``redis`` pool, ``job_id``, etc.).
    document_id : str
        UUID of the document to process (as a string).
    """
    from app.services.ingestion import process_document as _process
    from app.core.database import async_session_factory

    uid = uuid.UUID(document_id)
    logger.info("Worker processing document %s", document_id[:8])
    await _process(uid, session_factory=async_session_factory)
    logger.info("Worker completed document %s", document_id[:8])


# ── ARQ Worker Configuration ────────────────────────────

def _build_redis_settings() -> Any:
    """Build a RedisSettings object from the app config, or return None."""
    if not settings.redis_url:
        return None
    from arq.connections import RedisSettings
    host = settings.redis_host
    port = settings.redis_port
    password = settings.redis_password or None
    return RedisSettings(
        host=host,
        port=port,
        password=password,
        database=settings.redis_db,
    )


class WorkerSettings:
    """Settings for the ARQ worker process.

    This is the standard configuration class that ARQ discovers
    when running ``arq run`` or programmatically creating a worker.
    """

    functions = [process_document_task]
    redis_settings = _build_redis_settings()
    max_tries = 3  # Total attempts (1 initial + 2 retries)
    max_retries = 2  # Retries after the initial attempt
    job_timeout = settings.llm_timeout + 120  # Allow extra for model loading
    keep_result = 3600  # Keep job results for 1 hour
    keep_result_failure = 86400  # Keep failed job results for 24 hours
    poll_delay = 1.0  # Poll Redis every second
    burst = False  # Run continuously (not burst mode)
