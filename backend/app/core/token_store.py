"""Refresh-token store — in-memory blacklist for token rotation + revocation.

Provides ``validate_and_consume()`` for rotation and ``revoke()`` for logout.

**Redis-backed mode** is used when Redis is available; otherwise falls back
to an **in-memory dict**.  The in-memory store is not durable across restarts,
but that is acceptable because refresh tokens have a limited lifetime (7 days
by default) and the store is primarily a defense against token-reuse attacks
within that window.

Usage::

    from app.core.token_store import validate_and_consume, revoke_token

    # On refresh: consume old token, return whether it's valid
    if not await validate_and_consume(old_jti, user_id):
        raise HTTPException(401)

    # On logout: revoke all tokens for a user
    await revoke_token(jti)
"""

from __future__ import annotations

import time
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


# ── In-memory fallback store ─────────────────────────────

_in_memory: dict[str, dict[str, Any]] = {}  # jti -> {"user_id": str, "expires_at": float}


def _cleanup_expired() -> None:
    """Remove expired entries from the in-memory store."""
    now = time.time()
    expired = [jti for jti, data in _in_memory.items() if data.get("expires_at", 0) < now]
    for jti in expired:
        _in_memory.pop(jti, None)


async def _try_redis_set(jti: str, user_id: str, ttl_seconds: int) -> bool:
    """Attempt to store in Redis. Returns True on success, False on failure."""
    try:
        from app.services.job_queue import get_job_queue
        q = get_job_queue()
        if q._arq_pool is not None:
            await q._arq_pool.set(f"token:consumed:{jti}", user_id, ex=ttl_seconds)
            return True
    except Exception as e:
        logger.warning("Redis token-store set failed", error=str(e))
    return False


async def _try_redis_get(jti: str) -> bool:
    """Check if a consumed JTI exists in Redis. Returns False on failure."""
    try:
        from app.services.job_queue import get_job_queue
        q = get_job_queue()
        if q._arq_pool is not None:
            result = await q._arq_pool.get(f"token:consumed:{jti}")
            return result is not None
    except Exception:
        pass
    return False


def _memory_set(jti: str, user_id: str, ttl_seconds: int) -> None:
    """Store in the in-memory fallback dict."""
    _cleanup_expired()
    _in_memory[jti] = {"user_id": user_id, "expires_at": time.time() + ttl_seconds}
    logger.debug("Token stored in memory (jti=%s)", jti[:8])


def _memory_exists(jti: str) -> bool:
    """Check in-memory fallback."""
    _cleanup_expired()
    return jti in _in_memory


async def validate_and_consume(jti: str, user_id: str, expires_at: float | None = None) -> bool:
    """Validate that *jti* has NOT been consumed, then mark it as consumed.

    Returns ``True`` if the token was valid (not previously consumed).
    Returns ``False`` if it was already consumed (reuse attempt).

    The token is stored with a TTL matching its remaining lifetime so the
    blacklist self-clears after the token expires naturally.
    """
    # Check if already consumed (try Redis first, then memory)
    if await _try_redis_get(jti) or _memory_exists(jti):
        logger.warning("Refresh token reuse detected", jti=jti[:8])
        return False

    # Mark as consumed
    ttl = 7 * 86400  # default 7 days
    if expires_at:
        remaining = expires_at - time.time()
        ttl = max(int(remaining), 60)

    # Try Redis, fall back to memory
    stored = await _try_redis_set(jti, user_id, ttl)
    if not stored:
        _memory_set(jti, user_id, ttl)
    return True


async def revoke_token(jti: str, user_id: str | None = None, expires_at: float | None = None) -> None:
    """Revoke a specific refresh token (for logout).

    This marks the token as consumed without checking if it was already used.
    """
    ttl = 7 * 86400
    if expires_at:
        remaining = expires_at - time.time()
        ttl = max(int(remaining), 60)

    stored = await _try_redis_set(jti, user_id or "unknown", ttl)
    if not stored:
        _memory_set(jti, user_id or "unknown", ttl)
    logger.info("Token revoked", jti=jti[:8])
