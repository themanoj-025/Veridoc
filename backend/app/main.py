"""Veridoc — Main FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings, validate_config
from app.core.database import init_db, close_db
from app.core.logging_config import (
    bind_log_context,
    clear_log_context,
    configure_logging,
    generate_request_id,
)
from app.services.job_queue import get_job_queue
from app.api import auth, documents, chat

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

    # Initialize job queue (connects to Redis if available)
    queue = get_job_queue()
    await queue.initialize()
    logger.info(
        "queue.initialized",
        mode="redis" if queue.is_redis_available else "sync_fallback",
    )

    yield

    await queue.shutdown()
    await close_db()
    logger.info("db.connections_closed")


app = FastAPI(
    title="Veridoc API",
    description="Answers you can verify, not just believe.",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiting ────────────────────────────────────────
from app.core.rate_limit import limiter, _slowapi_available

if _slowapi_available:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
    logger.info("Rate limiting enabled (%d req/min general)", settings.rate_limit_per_minute)
else:
    logger.warning("slowapi not installed, rate limiting disabled")


# ── Routers ──────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)


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
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "environment": settings.app_env,
    }


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
