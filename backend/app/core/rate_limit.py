"""Rate limiting — per-endpoint and global limits using slowapi.

Usage in route handlers::

    from app.core.rate_limit import limiter

    @router.post("/login")
    @limiter.limit("5/minute")
    async def login(request: Request, ...):
        ...

When ``slowapi`` is not installed, or ``settings.app_env == \"test\"``,
rate limits are silently bypassed (the ``.limit()`` decorator is a no-op).

The environment check is lazy and uses **dynamic module attribute access**
so that the ``patch_settings`` test fixture (which patches
``app.core.config.settings`` at the module level) correctly overrides
``app_env`` at call time.
"""

from __future__ import annotations

from typing import Any, Callable

_slowapi_available: bool
_real_limiter: Any = None

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    _real_limiter = Limiter(key_func=get_remote_address)
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
            return _real_limiter.limit(*args, **kwargs)  # type: ignore[union-attr]

        def noop(func: Callable) -> Callable:
            return func
        return noop


limiter: _RateLimiter = _RateLimiter()
