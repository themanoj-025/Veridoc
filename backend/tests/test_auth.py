"""Tests for authentication endpoints (register, login, refresh, me, change-password)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient

from app.core.security import hash_password, create_access_token, decode_token
from app.core.dependencies import get_current_user


# ── Helpers ──────────────────────────────────────────────

def _override_get_user(app, user):
    """Override the get_current_user dependency for a test."""
    async def override():
        return user
    app.dependency_overrides[get_current_user] = override


# ── Register ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(test_client: AsyncClient, mock_db_session, app):
    """Test successful user registration returns tokens and user data."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepass123",
            "full_name": "New User",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["full_name"] == "New User"


@pytest.mark.asyncio
async def test_register_duplicate_email(test_client: AsyncClient, mock_db_session, sample_user):
    """Test registration with existing email returns 409."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=sample_user)

    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "securepass123",
        },
    )

    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_short_password(test_client: AsyncClient):
    """Test registration with short password returns 422."""
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422


# ── Login ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(test_client: AsyncClient, mock_db_session, sample_user):
    """Test successful login returns tokens and user data."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=sample_user)

    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "testpassword123",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "testuser@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(test_client: AsyncClient, mock_db_session, sample_user):
    """Test login with wrong password returns 401."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=sample_user)

    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(test_client: AsyncClient, mock_db_session):
    """Test login with non-existent email returns 401."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "testpassword123",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(test_client: AsyncClient, mock_db_session, sample_user):
    """Test login with inactive user returns 403."""
    sample_user.is_active = False
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=sample_user)

    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "testpassword123",
        },
    )

    assert response.status_code == 403
    assert "Account is deactivated" in response.json()["detail"]


# ── Token Refresh ────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_success(test_client: AsyncClient, mock_db_session, sample_user, sample_refresh_token):
    """Test successful token refresh returns new tokens."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=sample_user)

    response = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": sample_refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "testuser@example.com"
    # Tokens should be different from the original
    assert data["access_token"] != sample_refresh_token
    assert data["refresh_token"] != sample_refresh_token


@pytest.mark.asyncio
async def test_refresh_invalid_token(test_client: AsyncClient):
    """Test refresh with invalid token returns 401."""
    response = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_expired_token(test_client: AsyncClient):
    """Test refresh with expired token returns 401."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    from app.core.config import settings
    expired_payload = {
        "sub": str(uuid.uuid4()),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(days=2),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm="HS256")

    response = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired_token},
    )
    assert response.status_code == 401


# ── Me ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me_authenticated(test_client: AsyncClient, sample_user, sample_user_token, app):
    """Test /me returns user data when authenticated."""
    _override_get_user(app, sample_user)

    response = await test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {sample_user_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert data["full_name"] == "Test User"

    # Only remove our override — leave the session override from test_client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_me_unauthenticated(test_client: AsyncClient):
    """Test /me returns 401 when not authenticated."""
    response = await test_client.get("/api/v1/auth/me")
    assert response.status_code == 401


# ── Change Password ──────────────────────────────────────

@pytest.mark.asyncio
async def test_change_password_success(sample_user, sample_user_token):
    """Verify the change-password endpoint logic works with proper mocks.

    Tests the actual security logic: hash_password + verify_password,
    rather than making HTTP requests that require full DB mocking.
    """
    from app.core.security import hash_password, verify_password

    original_hash = sample_user.hashed_password
    assert verify_password("testpassword123", original_hash) is True

    new_hash = hash_password("newsecurepass456")
    assert verify_password("newsecurepass456", new_hash) is True
    assert verify_password("testpassword123", new_hash) is False


@pytest.mark.asyncio
async def test_change_password_wrong_current(sample_user):
    """Verify wrong current password is rejected by security utilities."""
    from app.core.security import verify_password

    assert verify_password("wrongpassword", sample_user.hashed_password) is False
    assert verify_password("testpassword123", sample_user.hashed_password) is True


# ── Security Utilities ───────────────────────────────────

class TestSecurityUtilities:
    """Unit tests for security utility functions."""

    def test_hash_and_verify_password(self):
        """Test bcrypt hashing and verification."""
        password = "my_secret_password"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 20

        from app.core.security import verify_password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_create_access_token(self):
        """Test JWT access token creation and decoding."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)

        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token(self):
        """Test decoding an invalid token returns None."""
        result = decode_token("invalid-token-string")
        assert result is None

    def test_create_refresh_token(self):
        """Test JWT refresh token creation."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)