"""Query/response cache — Redis-backed with in-memory fallback.

Stores complete LLM responses keyed by a hash of (conversation_id, query)
so repeated questions skip the full retrieve → rerank → generate pipeline.

Design
------
- Primary storage: Redis via ``redis.asyncio`` (TTL-based expiry).
- Fallback: in-memory ``dict`` when Redis is unavailable (testing/dev).
- Cache key format: ``veridoc:cache:{sha256}``
- Hit/miss counters are logged and exposed for monitoring.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from app.core import config as _config
import contextlib

logger = logging.getLogger("veridoc.cache")
settings = _config.settings

# ── In-memory fallback (used when Redis is unavailable) ──
_memory_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_hits = 0
_misses = 0


def _reset_stats() -> None:
    """Reset hit/miss counters and memory cache — used in testing."""
    global _hits, _misses
    _hits = 0
    _misses = 0
    _memory_cache.clear()


def _make_cache_key(conversation_id: str, query: str) -> str:
    """Build a deterministic cache key from conversation + query.

    Key format: ``veridoc:cache:{conversation_id}:{sha256(query)}``
    This allows prefix-scanning by conversation_id for invalidation.
    """
    raw = f"{conversation_id}::{query.strip().lower()}"
    h = hashlib.sha256(raw.encode()).hexdigest()
    return f"veridoc:cache:{conversation_id}:{h}"


class ResponseCache:
    """Cache for LLM responses with Redis primary and memory fallback.

    Usage::

        cache = ResponseCache()
        await cache.init_redis()

        # On user query:
        cached = await cache.get(conversation_id, query)
        if cached:
            # Return cached response immediately
            ...

        # After LLM generates response:
        await cache.set(conversation_id, query, response_data)
    """

    def __init__(self) -> None:
        self._redis = None
        self._enabled = settings.redis_cache_enabled
        self._ttl = settings.redis_cache_ttl_seconds
        self._redis_available = False

    async def init_redis(self) -> None:
        """Try to connect to Redis. Silently falls back to memory cache."""
        if not self._enabled:
            logger.info(
                "Response cache is disabled via config (redis_cache_enabled=False)"
            )
            return
        if not settings.redis_url:
            logger.info(
                "No Redis URL configured — response cache uses in-memory fallback"
            )
            return
        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped] — no stubs available

            self._redis = aioredis.from_url(
                settings.redis_url,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            await self._redis.ping()
            self._redis_available = True
            logger.info(
                "Response cache connected to Redis at %s:%d (TTL=%ds)",
                settings.redis_host,
                settings.redis_port,
                self._ttl,
            )
        except (OSError, ValueError) as e:
            logger.warning(
                "Redis unavailable for response cache, using memory fallback: %s", e
            )
            self._redis = None
            self._redis_available = False

    async def close(self) -> None:
        """Close the Redis connection if open."""
        if self._redis is not None:
            with contextlib.suppress(OSError, ValueError):
                await self._redis.close()
            self._redis = None
            self._redis_available = False

    async def get(self, conversation_id: str, query: str) -> dict[str, Any] | None:
        """Retrieve a cached response. Returns ``None`` on miss."""
        global _hits, _misses
        key = _make_cache_key(conversation_id, query)

        if self._redis_available and self._redis is not None:
            try:
                raw = await self._redis.get(key)
                if raw is not None:
                    _hits += 1
                    data = json.loads(raw)
                    logger.debug(
                        "Cache HIT for key=%s (conversation=%s)",
                        key[:40],
                        conversation_id,
                    )
                    return data
            except (OSError, ValueError) as e:
                logger.debug("Cache read error (falling through): %s", e)
                # Fall through to memory cache

        # Memory fallback
        entry = _memory_cache.get(key)
        if entry is not None:
            expiry, data = entry
            if time.time() < expiry:
                _hits += 1
                logger.debug("Memory-cache HIT for key=%s", key[:40])
                return data
            else:
                del _memory_cache[key]

        _misses += 1
        logger.debug("Cache MISS for key=%s", key[:40])
        return None

    async def set(
        self,
        conversation_id: str,
        query: str,
        data: dict[str, Any],
    ) -> None:
        """Store a response in the cache."""
        key = _make_cache_key(conversation_id, query)
        serialized = json.dumps(data, default=str)

        if self._redis_available and self._redis is not None:
            try:
                await self._redis.setex(key, self._ttl, serialized)
                logger.debug("Cache SET (Redis) key=%s TTL=%ds", key[:40], self._ttl)
                return
            except (OSError, ValueError) as e:
                logger.debug("Cache set error (falling through): %s", e)

        # Memory fallback
        _memory_cache[key] = (time.time() + self._ttl, data)
        logger.debug("Cache SET (memory) key=%s TTL=%ds", key[:40], self._ttl)

    async def invalidate(self, conversation_id: str, query: str | None = None) -> None:
        """Remove a specific cached entry, or all entries for a conversation."""
        if query is not None:
            key = _make_cache_key(conversation_id, query)
            if self._redis_available and self._redis is not None:
                with contextlib.suppress(OSError, ValueError):
                    await self._redis.delete(key)
            _memory_cache.pop(key, None)
        else:
            # Invalidate all entries for this conversation using key prefix
            prefix = f"veridoc:cache:{conversation_id}:"
            if self._redis_available and self._redis is not None:
                try:
                    cursor = 0
                    while True:
                        cursor, keys = await self._redis.scan(
                            cursor=cursor, match=f"{prefix}*", count=100
                        )
                        for k in keys:
                            await self._redis.delete(k)
                        if cursor == 0:
                            break
                except (OSError, ValueError):
                    pass
            # Clear all memory entries for this conversation
            to_delete = [k for k in _memory_cache if k.startswith(prefix)]
            for k in to_delete:
                _memory_cache.pop(k, None)

    @property
    def stats(self) -> dict[str, Any]:
        """Return cache hit/miss statistics."""
        total = _hits + _misses
        return {
            "hits": _hits,
            "misses": _misses,
            "total": total,
            "hit_rate": round(_hits / total, 4) if total > 0 else 0.0,
            "memory_entries": len(_memory_cache),
            "redis_available": self._redis_available,
            "enabled": self._enabled,
            "ttl_seconds": self._ttl,
        }


# ── Module-level singleton ───────────────────────────────
_cache_instance: ResponseCache | None = None


def get_response_cache() -> ResponseCache:
    """Get or create the global ResponseCache singleton."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResponseCache()
    return _cache_instance


def reset_cache_for_testing() -> None:
    """Reset the cache singleton and counters — used in tests only."""
    global _cache_instance, _hits, _misses, _memory_cache
    _cache_instance = None
    _hits = 0
    _misses = 0
    _memory_cache = {}
