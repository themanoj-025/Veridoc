"""Veridoc — Main FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings, validate_config
from app.core.database import init_db, close_db
from app.core.logging_config import (
    bind_log_context,
    clear_log_context,
    configure_logging,
    generate_request_id,
)
from sqlalchemy import text

from app.core.di import init_container
from app.api import auth, documents, chat, feedback, search, gdpr, admin, sharing, api_keys
from app.core.rate_limit import (
    limiter,
    _slowapi_available,
    rate_limit_exceeded_handler,
    rate_limit_headers_middleware,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    # Configure structured logging before anything else
    configure_logging(env=settings.app_env, log_level=settings.log_level)
    logger = structlog.get_logger(__name__)

    logger.info("app.startup", app_env=settings.app_env)

    # Fail-fast: validate security-critical config before anything else
    validate_config()
    logger.info("config.validated")

    # Initialize database
    await init_db()
    logger.info("db.initialized")

    # Pre-download NLTK data so it's NOT done at query time
    try:
        import nltk
        nltk.download("punkt", quiet=True)
        nltk.download("punkt_tab", quiet=True)
        logger.info("nltk.downloaded")
    except Exception as e:
        logger.warning("nltk.download_failed", error=str(e))

    # Initialize DI container (stores all services in app.state + ContextVar)
    # G4: Log secret rotation reminder
    _check_secret_rotation_age(logger)

    container = init_container(app)
    logger.info("di.container_initialized")

    # Initialize job queue (connects to Redis if available). init_container
    # eagerly initializes the queue, so the type is never None here — but we
    # assert to satisfy static type checkers (F2: zero type errors).
    queue = container.job_queue
    assert queue is not None, "DI container failed to initialize job queue"
    await queue.initialize()
    logger.info(
        "queue.initialized",
        mode="redis" if queue.is_redis_available else "sync_fallback",
    )

    # Initialize response cache (Redis-backed query cache)
    from app.services.response_cache import get_response_cache
    cache = get_response_cache()
    await cache.init_redis()

    yield

    await cache.close()
    await queue.shutdown()
    await close_db()
    logger.info("db.connections_closed")


def _check_secret_rotation_age(logger) -> None:
    """G4: Warn at startup if secrets haven't been rotated within the config window.

    Never a hard failure. Uses ``SECRET_ROTATED_AT`` (ISO date) and
    ``SECRET_ROTATION_WARNING_DAYS`` from settings:
    - unset → warning (can't verify)
    - older than the window → warning
    - recent → info
    - malformed date → warning
    """
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings

    window = getattr(settings, "secret_rotation_warning_days", 90)
    rotated_at = getattr(settings, "secret_rotated_at", None)

    if not rotated_at:
        logger.warning(
            "security.secret_rotation",
            status="never_recorded",
            window_days=window,
            hint=(
                "SECRET_ROTATED_AT is not set. Set it to the ISO date of the last "
                "JWT_SECRET/FILE_ENCRYPTION_KEY rotation to track secret age."
            ),
        )
        return

    try:
        rotated = datetime.fromisoformat(str(rotated_at))
        if rotated.tzinfo is None:
            rotated = rotated.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - rotated).days
    except ValueError:
        logger.warning(
            "security.secret_rotation",
            status="invalid_date",
            value=str(rotated_at),
            hint="SECRET_ROTATED_AT must be an ISO-8601 date, e.g. 2026-07-31.",
        )
        return

    if age_days > window:
        logger.warning(
            "security.secret_rotation",
            status="stale",
            age_days=age_days,
            window_days=window,
            hint=f"JWT_SECRET/FILE_ENCRYPTION_KEY were rotated {age_days} days ago (window: {window}). Please rotate them.",
        )
    else:
        logger.info(
            "security.secret_rotation",
            status="fresh",
            age_days=age_days,
            window_days=window,
        )


app = FastAPI(
    title="Veridoc API",
    description="Answers you can verify, not just believe.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── F12: Response Compression (gzip) ─────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiting ────────────────────────────────────────
if _slowapi_available:
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = limiter
    # G6: custom 429 handler emits Retry-After + X-RateLimit-* headers
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    # G6: middleware injects X-RateLimit-* headers on every limited response
    app.middleware("http")(rate_limit_headers_middleware)
    logger.info("Rate limiting enabled (%d req/min general)", settings.rate_limit_per_minute)
else:
    logger.warning("slowapi not installed, rate limiting disabled")


# ── Prometheus Metrics ──────────────────────────────────
try:
    from prometheus_fastapi_instrumentator import Instrumentator

    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        env_var_name="ENABLE_METRICS",
    )
    instrumentator.instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
    logger.info("Prometheus metrics enabled at /metrics")
except ImportError:
    logger.warning("prometheus-fastapi-instrumentator not installed, metrics disabled")


# ── Routers ──────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(feedback.router)
app.include_router(search.router)
app.include_router(gdpr.router)
app.include_router(admin.router)
app.include_router(sharing.doc_router)
app.include_router(sharing.router)
app.include_router(api_keys.router)


# ── Correlation ID Middleware ───────────────────────────
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Bind ``request_id`` and basic request metadata before each request."""
    request_id = generate_request_id()
    bind_log_context(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        clear_log_context()


# ── Health ───────────────────────────────────────────────
@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint — pings Postgres, ChromaDB, MinIO, and the LLM provider.

    Returns ``200`` only when all dependencies are reachable.
    Returns ``503`` when one or more dependencies are down, with per-dependency status.
    """
    import asyncio
    from datetime import datetime

    deps = {
        "postgres": {"status": "unknown"},
        "chroma": {"status": "unknown"},
        "minio": {"status": "unknown"},
        "llm": {"status": "unknown"},
        "redis": {"status": "unknown"},
    }

    async def _check_postgres():
        try:
            from app.core.database import async_session_factory
            async with async_session_factory() as session:
                await asyncio.wait_for(
                    session.execute(text("SELECT 1")),
                    timeout=5.0,
                )
            deps["postgres"] = {"status": "ok"}
        except Exception as e:
            deps["postgres"] = {"status": "error", "error": str(e)}

    async def _check_chroma():
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{settings.chroma_url}/api/v1/heartbeat")
                if resp.status_code == 200:
                    deps["chroma"] = {"status": "ok"}
                else:
                    deps["chroma"] = {"status": "error", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            deps["chroma"] = {"status": "error", "error": str(e)}

    async def _check_minio():
        try:
            from minio import Minio
            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_use_ssl,
            )
            client.bucket_exists(settings.minio_bucket)
            deps["minio"] = {"status": "ok"}
        except Exception as e:
            deps["minio"] = {"status": "error", "error": str(e)}

    async def _check_llm():
        try:
            from app.services.llm_provider import get_llm
            llm = get_llm()
            # Provider-specific ping
            if llm.model_name.startswith("ollama/"):
                import httpx
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"{settings.ollama_base_url}/api/generate",
                        json={"model": settings.ollama_model, "prompt": "hi", "stream": False},
                    )
                    if resp.status_code == 200:
                        deps["llm"] = {"status": "ok"}
                    else:
                        deps["llm"] = {"status": "error", "error": f"HTTP {resp.status_code}"}
            else:
                deps["llm"] = {"status": "ok", "note": f"Provider health not checked: {llm.model_name}"}
        except Exception as e:
            deps["llm"] = {"status": "error", "error": str(e)}

    async def _check_redis():
        try:
            from app.services.job_queue import JobQueue
            q = JobQueue()
            status = await q.get_queue_status()
            deps["redis"] = {
                "status": "ok" if status.get("connected", False) else "unavailable",
                "mode": status.get("mode", "unknown"),
            }
        except Exception as e:
            deps["redis"] = {"status": "error", "error": str(e)}

    await asyncio.gather(
        _check_postgres(),
        _check_chroma(),
        _check_minio(),
        _check_llm(),
        _check_redis(),
    )

    all_ok = all(d["status"] == "ok" for d in deps.values())
    overall_status = "ok" if all_ok else "degraded"
    status_code = 200 if all_ok else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "version": "0.1.0",
            "environment": settings.app_env,
            "timestamp": datetime.utcnow().isoformat(),
            "dependencies": deps,
        },
    )


# ── Global Exception Handler (non-HTTP exceptions only) ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Structured error response for unhandled exceptions.

    Only handles non-HTTPException errors — FastAPI already catches
    HTTPException and generates the appropriate response.
    """
    if isinstance(exc, HTTPException):
        # Let FastAPI handle HTTPExceptions natively
        return await request.app.exception_handlers[HTTPException](request, exc)  # type: ignore
    log = structlog.get_logger(__name__)
    log.error("unhandled_exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal error occurred",
            "error_type": type(exc).__name__,
        },
    )
