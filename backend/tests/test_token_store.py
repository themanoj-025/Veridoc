"""Tests for the refresh-token store's fail-closed behavior.

The store must deny a refresh (return ``False``) when the configured Redis
backend cannot answer the consumption check — never treat the token as
unconsumed, which would let a previously used refresh token be replayed
during a Redis outage.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from app.core.token_store import (
    TokenStoreUnavailableError,
    validate_and_consume,
)


class _BrokenPool:
    """Fake ARQ pool whose get/set always raise (simulates Redis outage)."""

    async def get(self, key: str) -> None:
        raise OSError("connection refused")

    async def set(self, *args: object, **kwargs: object) -> None:
        raise OSError("connection refused")


class _WorkingPool:
    """Fake ARQ pool with an in-memory consumed set."""

    def __init__(self) -> None:
        self.consumed: set[str] = set()

    async def get(self, key: str) -> str | None:
        return key if key in self.consumed else None

    async def set(self, key: str, value: str, **kwargs: object) -> None:
        self.consumed.add(key)


def _fake_queue(pool: object) -> MagicMock:
    q = MagicMock()
    q._arq_pool = pool
    return q


@pytest.mark.asyncio
async def test_validate_and_consume_fails_closed_when_redis_errors() -> None:
    """A Redis outage must deny the refresh, not treat the token as unused."""
    q = _fake_queue(_BrokenPool())
    with patch("app.services.job_queue.get_job_queue", return_value=q):
        result = await validate_and_consume("jti-outage", "user-1")
    assert result is False


@pytest.mark.asyncio
async def test_try_redis_get_raises_on_redis_error() -> None:
    """The low-level lookup surfaces the outage instead of returning False."""
    from app.core.token_store import _try_redis_get

    q = _fake_queue(_BrokenPool())
    with (
        patch("app.services.job_queue.get_job_queue", return_value=q),
        pytest.raises(TokenStoreUnavailableError),
    ):
        await _try_redis_get("jti-outage")


@pytest.mark.asyncio
async def test_validate_and_consume_detects_reuse_when_redis_healthy() -> None:
    """With Redis healthy, a second consume of the same JTI is rejected."""
    pool = _WorkingPool()
    q = _fake_queue(pool)
    with patch("app.services.job_queue.get_job_queue", return_value=q):
        first = await validate_and_consume("jti-ok", "user-1")
        second = await validate_and_consume("jti-ok", "user-1")
    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_validate_and_consume_no_redis_falls_back_to_memory() -> None:
    """Without a Redis pool, the in-memory store still dedupes a replay."""
    q = _fake_queue(None)
    with patch("app.services.job_queue.get_job_queue", return_value=q):
        first = await validate_and_consume("jti-mem", "user-1")
        second = await validate_and_consume("jti-mem", "user-1")
    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_redis_error_is_not_swallowed_into_memory_fallback() -> None:
    """A failed Redis SET must not be silently accepted as stored."""
    from app.core.token_store import _try_redis_set

    q = _fake_queue(_BrokenPool())
    with patch("app.services.job_queue.get_job_queue", return_value=q):
        stored = await _try_redis_set("jti-set-fail", "user-1", 60)
    assert stored is False
