"""Rate limiting — per-endpoint and global limits using slowapi.

Usage in route handlers::

    from app.core.rate_limit import limiter

    @router.post("/login")
    @limiter.limit("5/minute", key_func=get_user_identifier)
    async def login(request: Request, ...) -> Any:
        ...

When ``slowapi`` is not installed, or ``settings.app_env == \"test\"``,
rate limits are silently bypassed (the ``.limit()`` decorator is a no-op).

The environment check is lazy and uses **dynamic module attribute access**
so that the ``patch_settings`` test fixture (which patches
``app.core.config.settings`` at the module level) correctly overrides
``app_env`` at call time.

G6 — response headers: slowapi 0.1.9's built-in header injection
(``headers_enabled=True``) crashes on endpoints that return plain dicts
(a FastAPI idiom), because it passes ``kwargs.get("response")`` (None) to
``_inject_headers``. We therefore keep slowapi headers disabled and emit
``X-RateLimit-Limit`` / ``X-RateLimit-Remaining`` / ``X-RateLimit-Reset``
/ ``Retry-After`` ourselves via :func:`build_rate_limit_headers`, driven by
``request.state.view_rate_limit`` (which slowapi sets on every limited
request). See :func:`rate_limit_headers_middleware` and
:func:`rate_limit_exceeded_handler`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

_slowapi_available: bool
_real_limiter: Any = None

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    _real_limiter = Limiter(key_func=get_remote_address, headers_enabled=False)
    _slowapi_available = True
except ImportError:
    _slowapi_available = False


def _should_rate_limit() -> bool:
    """Return ``True`` when rate limiting should be enforced.

    Accesses ``settings`` through the module attribute at call time
    (not via a module-level import) so that ``unittest.mock.patch`` —
    which replaces the module-level attribute — actually takes effect.
    """
    if not _slowapi_available:
        return False
    from app.core import config as _config

    return getattr(_config.settings, "app_env", "development") != "test"


class _RateLimiter:
    """Wrapper that delegates to slowapi or no-ops depending on runtime state."""

    def limit(self, *args: Any, **kwargs: Any) -> Callable[[Callable], Callable]:
        if _should_rate_limit():
            assert _real_limiter is not None
            return _real_limiter.limit(*args, **kwargs)

        def noop(func: Callable) -> Callable:
            return func

        return noop


limiter: _RateLimiter = _RateLimiter()


def get_user_identifier(request) -> str:
    """Per-user rate-limit key (F6).

    Extracts the authenticated user ID from the Bearer JWT in the
    ``Authorization`` header so upload/chat limits are enforced **per
    user**, not just per IP address. Falls back to the remote address
    for unauthenticated requests.

    Usage::

        @limiter.limit("10/minute", key_func=get_user_identifier)
    """
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            from app.core.security import decode_token

            payload = decode_token(token)
            if payload and payload.get("type") == "access":
                sub = payload.get("sub")
                if sub:
                    return f"user:{sub}"
    try:
        return f"ip:{request.client.host}" if request.client else "ip:unknown"
    except (AttributeError, TypeError):
        return "ip:unknown"


# ── G6: Rate-limit response headers ─────────────────────────────
# slowapi 0.1.9 sets ``request.state.view_rate_limit`` to a
# ``(RateLimitItem, args)`` tuple on every limited request (success or
# 429). We read it and compute the standard headers ourselves, so the
# behavior does not depend on slowapi's fragile response-object injection.


def _resolve_strategy(request: Request) -> None:
    """Return the slowapi RateLimiter strategy for the request's app.

    Prefers ``request.app.state.limiter`` (a real slowapi Limiter in the
    standalone test app); falls back to the module-level limiter used by
    the Veridoc app (which wraps slowapi in ``_RateLimiter``).
    """
    try:
        limiter_obj = request.app.state.limiter
        strategy = getattr(limiter_obj, "limiter", None)
        if strategy is not None:
            return strategy
    except (AttributeError, TypeError):
        pass
    return getattr(_real_limiter, "limiter", None)


def build_rate_limit_headers(request: Request) -> dict[str, str]:
    """Compute ``X-RateLimit-*`` + ``Retry-After`` headers for this request.

    Returns an empty dict when the request was not rate-limited (no
    ``view_rate_limit`` state) or when slowapi is unavailable — callers can
    safely skip header injection then.
    """
    view_rate_limit = getattr(request.state, "view_rate_limit", None)
    if not view_rate_limit:
        return {}
    strategy = _resolve_strategy(request)
    if strategy is None:
        return {}
    limit_item, args = view_rate_limit
    try:
        window_stats = strategy.get_window_stats(limit_item, *args)
        reset_in = int(1 + window_stats[0])  # integer epoch seconds
        retry_after = max(int(reset_in - time.time()), 1)
        return {
            "X-RateLimit-Limit": str(limit_item.amount),
            "X-RateLimit-Remaining": str(window_stats[1]),
            "X-RateLimit-Reset": str(reset_in),
            "Retry-After": str(retry_after),
        }
    except (AttributeError, TypeError) as exc:  # pragma: no cover - defensive
        import structlog

        structlog.get_logger(__name__).debug(
            "rate_limit_header_computation_failed", error=str(exc)
        )
        return {}


async def rate_limit_exceeded_handler(request: Request, exc) -> JSONResponse:
    """Custom 429 handler — includes Retry-After + X-RateLimit-* headers.

    slowapi's default handler only injects headers when its own
    ``headers_enabled`` flag is on (which breaks dict-returning endpoints),
    so we produce a consistent 429 JSON body plus our own headers.

    NOTE: the middleware (``rate_limit_headers_middleware``) also injects the
    same headers on the 429 response after it flows back through the chain.
    The overlap is intentional and idempotent — keeping the handler's own
    injection makes the 429 self-contained if the middleware ever changes.
    """
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please retry shortly."},
        headers=build_rate_limit_headers(request) or {"Retry-After": "1"},
    )


async def rate_limit_headers_middleware(request: Request, call_next) -> None:
    """ASGI middleware: inject rate-limit headers on every limited response.

    Registers as ``app.middleware("http")`` so success responses AND the
    custom 429 response both carry ``X-RateLimit-*`` / ``Retry-After``.
    """
    response = await call_next(request)
    if _slowapi_available:
        headers = build_rate_limit_headers(request)
        if headers:
            response.headers.update(headers)
    return response
