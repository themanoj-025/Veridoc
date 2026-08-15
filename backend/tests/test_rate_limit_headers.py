"""Tests for F6 (per-user rate limiting) and G6 (X-RateLimit-* response headers).

F6 requires per-user (not just per-IP) limits on upload & chat endpoints.
The app uses ``get_user_identifier`` as the slowapi ``key_func`` so an
authenticated request is bucketed by user ID, not client IP.

G6 requires every rate-limited endpoint to emit
``X-RateLimit-Limit`` / ``X-RateLimit-Remaining`` / ``X-RateLimit-Reset``
and a 429 with ``Retry-After``. The app implements this itself (slowapi
0.1.9's built-in header injection crashes on dict-returning endpoints),
so these tests exercise that implementation end-to-end on a real Limiter.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from app.core.rate_limit import (
    get_user_identifier,
    rate_limit_exceeded_handler,
    rate_limit_headers_middleware,
)
from app.core.security import create_access_token
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# ════════════════════════════════════════════════════════════════
# F6: Per-user rate-limit key
# ════════════════════════════════════════════════════════════════


class TestGetUserIdentifier:
    """The key function must bucket by authenticated user ID when present."""

    def test_uses_user_id_when_authenticated(self):
        """A Bearer access token yields ``user:<id>`` as the limit key."""
        uid = uuid.uuid4()
        token = create_access_token(uid)

        request = MagicMock()
        request.headers.get = MagicMock(return_value=f"Bearer {token}")

        key = get_user_identifier(request)
        assert key == f"user:{uid}"

    def test_falls_back_to_ip_when_unauthenticated(self):
        """No auth header → bucket by client IP."""
        request = MagicMock()
        request.headers.get = MagicMock(return_value="")
        request.client.host = "203.0.113.7"

        key = get_user_identifier(request)
        assert key == "ip:203.0.113.7"

    def test_rejects_refresh_tokens(self):
        """A refresh token must NOT be treated as a user identity."""
        from app.core.security import create_refresh_token

        uid = uuid.uuid4()
        refresh = create_refresh_token(uid)

        request = MagicMock()
        request.headers.get = MagicMock(return_value=f"Bearer {refresh}")
        request.client.host = "203.0.113.8"

        key = get_user_identifier(request)
        # Falls back to IP because token type is "refresh", not "access"
        assert key == "ip:203.0.113.8"


# ════════════════════════════════════════════════════════════════
# F6 + G6: Real slowapi enforcement — 429, Retry-After, headers
# ════════════════════════════════════════════════════════════════


def _build_limited_app(limit_str: str, key_func=None) -> FastAPI:
    """Build a minimal FastAPI app wired exactly like the Veridoc app.

    - slowapi headers disabled (avoids the dict-response crash in 0.1.9)
    - custom 429 exception handler (Retry-After + X-RateLimit-*)
    - middleware that injects X-RateLimit-* on every limited response
    """
    limiter = Limiter(
        key_func=key_func or get_remote_address,
        headers_enabled=False,
    )
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.middleware("http")(rate_limit_headers_middleware)

    @app.get("/limited")
    @limiter.limit(limit_str)
    async def limited(request: Request):
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_429_returned_with_retry_after():
    """Exceeding the limit returns 429 with a numeric Retry-After header."""
    app = _build_limited_app("3/minute")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for _ in range(3):
            resp = await client.get("/limited")
            assert resp.status_code == 200

        # 4th request exceeds the 3/minute limit
        resp = await client.get("/limited")
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        # Our handler emits delta-seconds (an integer), per RFC 7231
        assert int(resp.headers["Retry-After"]) >= 1


@pytest.mark.asyncio
async def test_rate_limit_headers_present_and_valued():
    """G6: every limited response carries Limit/Remaining/Reset headers."""
    app = _build_limited_app("5/minute")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/limited")
        assert resp.status_code == 200
        assert resp.headers["X-RateLimit-Limit"] == "5"
        assert resp.headers["X-RateLimit-Remaining"] == "4"
        assert "X-RateLimit-Reset" in resp.headers
        assert int(resp.headers["X-RateLimit-Reset"]) > 0


@pytest.mark.asyncio
async def test_429_response_includes_rate_limit_headers():
    """G6: the 429 response itself also carries the rate-limit headers."""
    app = _build_limited_app("2/minute")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        await client.get("/limited")
        await client.get("/limited")
        resp = await client.get("/limited")
        assert resp.status_code == 429
        assert "X-RateLimit-Limit" in resp.headers
        assert "Retry-After" in resp.headers


# ════════════════════════════════════════════════════════════════
# F6: per-user enforcement end-to-end (independent buckets)
# ════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_per_user_rate_limits_are_independent():
    """Two users with different JWTs get separate buckets (F6).

    User A burns through the limit and gets a 429; user B is unaffected
    and keeps hitting 200s — proving limits are per-user, not per-IP.
    """
    app = _build_limited_app("3/minute", key_func=get_user_identifier)

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    token_a = create_access_token(user_a)
    token_b = create_access_token(user_b)

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # User A uses their entire 3/minute budget
        for _ in range(3):
            resp = await client.get("/limited", headers=headers_a)
            assert resp.status_code == 200

        # User A is now rate limited
        resp = await client.get("/limited", headers=headers_a)
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers

        # User B has a fresh bucket — unaffected by A
        for _ in range(3):
            resp = await client.get("/limited", headers=headers_b)
            assert resp.status_code == 200, f"User B hit {resp.status_code}"

        # Same IP — if the limit were per-IP, B would be blocked too
        resp = await client.get("/limited", headers=headers_b)
        assert resp.status_code == 429


@pytest.mark.asyncio
async def test_per_user_same_user_shares_bucket():
    """Repeated requests from the SAME user consume one bucket (F6)."""
    app = _build_limited_app("2/minute", key_func=get_user_identifier)
    token = create_access_token(uuid.uuid4())
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/limited", headers=headers)).status_code == 200
        assert (await client.get("/limited", headers=headers)).status_code == 200
        assert (await client.get("/limited", headers=headers)).status_code == 429
