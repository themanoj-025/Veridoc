"""Tests for the Redis query/response cache."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core import config as _test_config
from app.services.response_cache import (
    ResponseCache,
    get_response_cache,
    reset_cache_for_testing,
)

pytestmark = pytest.mark.slow

settings = _test_config.settings


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the cache singleton and counters before each test."""
    reset_cache_for_testing()
    yield


@pytest.fixture
def cache():
    """Create a ResponseCache instance with memory fallback (no Redis)."""
    c = ResponseCache()
    assert not c._redis_available  # Memory mode by default
    yield c


# ── Cache Key Generation ─────────────────────────────────


def test_make_cache_key_is_deterministic():
    """Same conversation + query produces the same key."""
    from app.services.response_cache import _make_cache_key

    k1 = _make_cache_key("conv-1", "What is the contract value?")
    k2 = _make_cache_key("conv-1", "What is the contract value?")
    assert k1 == k2


def test_make_cache_key_differs_by_conversation():
    """Different conversations produce different keys for the same query."""
    from app.services.response_cache import _make_cache_key

    k1 = _make_cache_key("conv-1", "What is x?")
    k2 = _make_cache_key("conv-2", "What is x?")
    assert k1 != k2


def test_make_cache_key_is_case_insensitive():
    """Query case is normalized so 'Hello' and 'hello' match."""
    from app.services.response_cache import _make_cache_key


    k1 = _make_cache_key("conv-1", "Hello World")
    k2 = _make_cache_key("conv-1", "hello world")
    assert k1 == k2


# ── Memory Cache Operations ──────────────────────────────


@pytest.mark.asyncio
async def test_cache_miss_returns_none(cache):
    """A cache miss should return None."""
    result = await cache.get("conv-1", "What is the meaning of life?")
    assert result is None


@pytest.mark.asyncio
async def test_cache_set_and_get(cache):
    """A value stored in cache should be retrievable."""
    data = {
        "content": "The answer is 42.",
        "citations": [
            {"chunk_id": "c1", "document_id": "d1", "text": "Meaning is 42."}
        ],
        "faithfulness_score": 0.95,
        "model_used": "llama3.1:8b",
    }
    await cache.set("conv-1", "What is the meaning?", data)
    result = await cache.get("conv-1", "What is the meaning?")
    assert result is not None
    assert result["content"] == "The answer is 42."
    assert result["faithfulness_score"] == 0.95
    assert result["model_used"] == "llama3.1:8b"
    assert len(result["citations"]) == 1


@pytest.mark.asyncio
async def test_cache_expiry(cache):
    """Entries past their TTL should not be returned."""
    with patch.object(cache, "_ttl", 0):  # Zero TTL = immediate expiry
        await cache.set("conv-1", "Will expire", {"content": "Gone"})
        result = await cache.get("conv-1", "Will expire")
        assert result is None


@pytest.mark.asyncio
async def test_cache_isolates_conversations(cache):
    """Cache entries for different conversations should not collide."""
    await cache.set("conv-1", "Same query", {"content": "Answer A"})
    await cache.set("conv-2", "Same query", {"content": "Answer B"})

    r1 = await cache.get("conv-1", "Same query")
    r2 = await cache.get("conv-2", "Same query")
    assert r1["content"] == "Answer A"
    assert r2["content"] == "Answer B"


@pytest.mark.asyncio
async def test_cache_overwrite(cache):
    """Setting the same key twice should overwrite the old value."""
    await cache.set("conv-1", "Query", {"content": "Old answer"})
    await cache.set("conv-1", "Query", {"content": "New answer"})
    result = await cache.get("conv-1", "Query")
    assert result["content"] == "New answer"


# ── Invalidation ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_invalidate_specific_query(cache):
    """Invalidating a specific query should remove only that entry."""
    await cache.set("conv-1", "Query A", {"content": "Answer A"})
    await cache.set("conv-1", "Query B", {"content": "Answer B"})

    await cache.invalidate("conv-1", "Query A")

    assert await cache.get("conv-1", "Query A") is None
    assert await cache.get("conv-1", "Query B") is not None


@pytest.mark.asyncio
async def test_invalidate_all_conversation(cache):
    """Invalidating a full conversation should remove all its entries."""
    await cache.set("conv-1", "Q1", {"content": "A1"})
    await cache.set("conv-1", "Q2", {"content": "A2"})
    await cache.set("conv-2", "Q1", {"content": "A3"})  # Different conversation

    await cache.invalidate("conv-1")  # Invalidate all of conv-1

    assert await cache.get("conv-1", "Q1") is None
    assert await cache.get("conv-1", "Q2") is None
    assert await cache.get("conv-2", "Q1") is not None  # conv-2 is untouched


# ── Stats ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stats_hit_rate(cache):
    """Cache stats should track hit/miss correctly."""
    # Miss
    await cache.get("conv-1", "Miss")
    # Hit
    await cache.set("conv-1", "Hit", {"content": "Data"})
    await cache.get("conv-1", "Hit")

    stats = cache.stats
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["total"] == 2
    assert stats["hit_rate"] == 0.5
    assert not stats["redis_available"]
    assert stats["enabled"]


def test_stats_empty_cache(cache):
    """Stats should handle zero operations gracefully."""
    stats = cache.stats
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["total"] == 0
    assert stats["hit_rate"] == 0.0


# ── Redis Integration (mocked) ───────────────────────────


@pytest.mark.asyncio
async def test_redis_cache_hit():
    """When Redis is available, cache reads should use it."""
    reset_cache_for_testing()
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(
        return_value=json.dumps(
            {
                "content": "From Redis",
                "citations": [],
                "faithfulness_score": 0.9,
                "model_used": "redis-model",
            }
        )
    )
    mock_redis.ping = AsyncMock(return_value=True)

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        cache = ResponseCache()
        await cache.init_redis()
        assert cache._redis_available

        result = await cache.get("conv-1", "Redis query")
        assert result is not None
        assert result["content"] == "From Redis"
        mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_redis_cache_set():
    """When Redis is available, cache writes should use it."""
    reset_cache_for_testing()
    mock_redis = MagicMock()
    mock_redis.setex = AsyncMock(return_value=True)
    mock_redis.ping = AsyncMock(return_value=True)

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        cache = ResponseCache()
        await cache.init_redis()

        await cache.set(
            "conv-1",
            "Test query",
            {
                "content": "Cached response",
                "citations": [],
                "faithfulness_score": 1.0,
                "model_used": "test",
            },
        )
        mock_redis.setex.assert_called_once()


@pytest.mark.asyncio
async def test_redis_connection_failure_falls_back():
    """If Redis connection fails, cache should use memory fallback."""
    reset_cache_for_testing()
    with patch("redis.asyncio.from_url", side_effect=Exception("Connection refused")):
        cache = ResponseCache()
        await cache.init_redis()
        assert not cache._redis_available

        # Should still work via memory fallback
        await cache.set("conv-1", "Fallback query", {"content": "Memory"})
        result = await cache.get("conv-1", "Fallback query")
        assert result is not None
        assert result["content"] == "Memory"


# ── Cache Disabled ───────────────────────────────────────


@pytest.mark.asyncio
async def test_cache_disabled_does_not_connect():
    """When caching is disabled, no Redis connection is attempted."""
    with patch.object(settings, "redis_cache_enabled", False):
        cache = ResponseCache()
        await cache.init_redis()
        assert cache._redis is None
        assert not cache._redis_available
        # Set/get should still work silently
        await cache.set("conv-1", "Q", {"content": "A"})
        result = await cache.get("conv-1", "Q")
        assert result is not None


# ── Module-level Singleton ───────────────────────────────


def test_get_response_cache_singleton():
    """get_response_cache should return the same instance."""
    c1 = get_response_cache()
    c2 = get_response_cache()
    assert c1 is c2


def test_reset_cache_for_testing():
    """reset_cache_for_testing should create a new singleton."""
    c1 = get_response_cache()
    reset_cache_for_testing()
    c2 = get_response_cache()
    assert c1 is not c2
