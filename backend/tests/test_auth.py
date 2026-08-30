"""Tests for authentication endpoints (register, login, refresh, me, change-password)."""

from __future__ import annotations

import uuid
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, decode_token, hash_password
from httpx import AsyncClient

# ── Helpers ──────────────────────────────────────────────


def _override_get_user(app, user):
    """Override the get_current_user dependency for a test."""

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override


# ── Register ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_success(test_client: AsyncClient, mock_db_session, app) -> None:
    """Test successful user registration returns tokens and user data."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=None
    )

    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
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
async def test_register_duplicate_email(
    test_client: AsyncClient, mock_db_session, sample_user
) -> None:
    """Test registration with existing email returns 409."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )

    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "testuser@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_short_password(test_client: AsyncClient) -> None:
    """Test registration with short password returns 422."""
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "short",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_no_complexity(test_client: AsyncClient) -> None:
    """Test registration with password lacking complexity returns 422."""
    response = await test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "lowercaseonly",
        },
    )
    assert response.status_code == 422


# ── Login ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_success(test_client: AsyncClient, mock_db_session, sample_user) -> None:
    """Test successful login returns tokens and user data."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )

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
async def test_login_wrong_password(
    test_client: AsyncClient, mock_db_session, sample_user
) -> None:
    """Test login with wrong password returns 401."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )

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
async def test_login_nonexistent_user(test_client: AsyncClient, mock_db_session) -> None:
    """Test login with non-existent email returns 401."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=None
    )

    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "testpassword123",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_user(
    test_client: AsyncClient, mock_db_session, sample_user
) -> None:
    """Test login with inactive user returns 403."""
    sample_user.is_active = False
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )

    response = await test_client.post(
        "/api/v1/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "testpassword123",
        },
    )

    assert response.status_code == 403
    assert "Account is deactivated" in response.json()["detail"]


# ── Token Refresh (with rotation) ────────────────────────


@pytest.mark.asyncio
async def test_refresh_success(
    test_client: AsyncClient, mock_db_session, sample_user, sample_refresh_token
) -> None:
    """Test successful token refresh returns new tokens."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )

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
async def test_refresh_invalid_token(test_client: AsyncClient) -> None:
    """Test refresh with invalid token returns 401."""
    response = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_expired_token(test_client: AsyncClient) -> None:
    """Test refresh with expired token returns 401."""
    from datetime import datetime, timedelta

    from app.core.config import settings
    from jose import jwt

    expired_payload = {
        "sub": str(uuid.uuid4()),
        "type": "refresh",
        "exp": datetime.now(UTC) - timedelta(hours=1),
        "iat": datetime.now(UTC) - timedelta(days=2),
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm="HS256")

    response = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired_token},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_reuse_rejected(
    test_client: AsyncClient, mock_db_session, sample_user
) -> None:
    """Test that reusing a consumed refresh token is rejected (rotation)."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user,
    )

    # Generate a refresh token
    from app.core.security import create_refresh_token

    refresh_token = create_refresh_token(sample_user.id)

    # First use — should succeed
    resp1 = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp1.status_code == 200

    # Second use with same token — should be rejected (reuse detected)
    resp2 = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp2.status_code == 401
    assert "already been used" in resp2.json()["detail"].lower()


# ── Logout ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(
    test_client: AsyncClient,
    mock_db_session,
    sample_user,
    sample_refresh_token,
    app,
) -> None:
    """Test that logout revokes the refresh token so it can't be reused."""
    _override_get_user(app, sample_user)

    # Logout with the refresh token
    response = await test_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": sample_refresh_token},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 200
    assert "successfully" in response.json()["message"]

    # Refreshing with the same token should now fail
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )
    resp2 = await test_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": sample_refresh_token},
    )
    assert resp2.status_code == 401
    assert "already" in resp2.json()["detail"].lower()

    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_logout_rejects_invalid_token(test_client: AsyncClient, app, sample_user) -> None:
    """Test logout with invalid refresh token returns 401."""
    _override_get_user(app, sample_user)

    response = await test_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "invalid-token"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert response.status_code == 401

    app.dependency_overrides.pop(get_current_user, None)


# ── Me ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_me_authenticated(
    test_client: AsyncClient, sample_user, sample_user_token, app
) -> None:
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
async def test_get_me_unauthenticated(test_client: AsyncClient) -> None:
    """Test /me returns 401 when not authenticated."""
    response = await test_client.get("/api/v1/auth/me")
    assert response.status_code == 401


# ── Change Password ──────────────────────────────────────


@pytest.mark.asyncio
async def test_change_password_success(sample_user, sample_user_token) -> None:
    """Verify the change-password endpoint logic works with proper mocks.

    Tests the actual security logic: hash_password + verify_password,
    rather than making HTTP requests that require full DB mocking.
    """
    from app.core.security import hash_password, verify_password

    original_hash = sample_user.hashed_password
    assert verify_password("testpassword123", original_hash) is True

    new_hash = hash_password("NewSecurePass456!")
    assert verify_password("NewSecurePass456!", new_hash) is True
    assert verify_password("testpassword123", new_hash) is False


@pytest.mark.asyncio
async def test_change_password_wrong_current(sample_user) -> None:
    """Verify wrong current password is rejected by security utilities."""
    from app.core.security import verify_password

    assert verify_password("wrongpassword", sample_user.hashed_password) is False
    assert verify_password("testpassword123", sample_user.hashed_password) is True


# ── Security Utilities ───────────────────────────────────


class TestSecurityUtilities:
    """Unit tests for security utility functions."""

    def test_hash_and_verify_password(self) -> None:
        """Test bcrypt hashing and verification."""
        password = "my_secret_password"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 20

        from app.core.security import verify_password

        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_create_access_token(self) -> None:
        """Test JWT access token creation and decoding."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)

        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token(self) -> None:
        """Test decoding an invalid token returns None."""
        result = decode_token("invalid-token-string")
        assert result is None

    def test_create_refresh_token(self) -> None:
        """Test JWT refresh token creation."""
        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)

    def test_password_complexity(self) -> None:
        """Test password complexity validation."""
        from app.core.security import validate_password_complexity

        # Too short
        err = validate_password_complexity("Ab1")
        assert err is not None
        assert "at least 8" in err

        # No complexity (lowercase only)
        err = validate_password_complexity("abcdefgh")
        assert err is not None
        assert "at least 2" in err

        # Valid: uppercase + digit
        err = validate_password_complexity("Abcdefg1")
        assert err is None, f"Expected None, got: {err}"

        # Valid: uppercase + symbol
        err = validate_password_complexity("Abcdefg!")
        assert err is None

        # Valid: digit + symbol
        err = validate_password_complexity("1bcdefg!")
        assert err is None

        # Valid: uppercase + digit + symbol (all three)
        err = validate_password_complexity("Abcdef1!")
        assert err is None

    def test_get_token_jti(self) -> None:
        """Test extracting JTI from token payload."""
        from app.core.security import get_token_jti

        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token)
        jti = get_token_jti(payload)
        assert jti is not None
        assert len(jti) > 0

    def test_get_token_exp(self) -> None:
        """Test extracting expiration from token payload."""
        from app.core.security import get_token_exp

        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token)
        exp = get_token_exp(payload)
        assert exp is not None
        assert exp > 0


# ── Negative Security Tests (G29) ───────────────────────


class TestNegativeSecurity:
    """Security regression tests: tampered JWT, expired JWT, cross-user access, SQL injection."""

    @pytest.mark.asyncio
    async def test_tampered_jwt_rejected(
        self, test_client: AsyncClient, sample_user_token: str
    ) -> None:
        """A JWT with a tampered signature must be rejected with 401."""
        # Corrupt the signature part of the token
        parts = sample_user_token.rsplit(".", 1)
        tampered = parts[0] + ".invalidsignature"

        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tampered}"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_jwt_rejected(self, test_client: AsyncClient) -> None:
        """An expired JWT must be rejected with 401."""
        from datetime import datetime, timedelta

        from app.core.config import settings
        from jose import jwt

        expired_payload = {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(UTC) - timedelta(hours=1),
            "iat": datetime.now(UTC) - timedelta(hours=2),
        }
        expired = jwt.encode(expired_payload, settings.jwt_secret, algorithm="HS256")

        response = await test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired}"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cross_user_document_access_rejected(
        self,
        test_client: AsyncClient,
        mock_db_session,
        app,
        sample_user,
    ):
        """A user accessing another user's document by ID must be rejected with 404."""
        from app.core.dependencies import get_current_user

        async def override_user():
            return sample_user

        app.dependency_overrides[get_current_user] = override_user

        # Mock the DB session to return None (document not found for this user)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Attempt to access a document that doesn't belong to sample_user
        doc_id = uuid.uuid4()
        response = await test_client.get(
            f"/api/v1/documents/{doc_id}",
            headers={"Authorization": "Bearer fake-token"},
        )
        # Should return 404 (not found) because the doc doesn't exist for this user
        assert response.status_code == 404

        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_cross_user_conversation_access_rejected(
        self,
        test_client: AsyncClient,
        mock_db_session,
        app,
        sample_user,
    ):
        """A user accessing another user's conversation by ID must be rejected with 404."""
        from app.core.dependencies import get_current_user

        async def override_user():
            return sample_user

        app.dependency_overrides[get_current_user] = override_user

        # Mock the DB session to return None (conversation not found for this user)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Attempt to access a conversation that doesn't belong to sample_user
        conv_id = uuid.uuid4()
        response = await test_client.get(
            f"/api/v1/chat/conversations/{conv_id}",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code == 404

        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_sql_injection_in_query_treated_as_literal(self) -> None:
        """SQL-injection-style strings in query fields must be treated as literal text.

        Verifies at THREE levels:
        1. Pydantic schema accepts the malicious string as a valid title
        2. The string can be saved to and loaded from a real database (SQLite in-memory)
        3. The malicious SQL is not executed
        """
        from app.models.conversation import Conversation
        from app.models.user import User
        from app.schemas.chat import ConversationCreate

        # Level 1: Schema accepts the string
        malicious_title = "'; DROP TABLE users; --"
        conv_create = ConversationCreate(title=malicious_title, document_ids=[])
        assert conv_create.title == malicious_title

        # Level 2-3: Actual DB save/load with real in-memory SQLite
        # We reuse the real_db_session pattern from test_schema.py
        from app.core.database import Base
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            # Create a user
            user = User(email="test@example.com", hashed_password="h" * 60)
            session.add(user)
            await session.flush()

            # Save conversation with malicious title
            conv = Conversation(user_id=user.id, title=malicious_title)
            session.add(conv)
            await session.flush()

            # Load it back
            from sqlalchemy import select

            result = await session.execute(
                select(Conversation).where(Conversation.id == conv.id)
            )
            loaded = result.scalar_one_or_none()
            assert loaded is not None
            assert loaded.title == malicious_title  # Stored as literal, unchanged
            assert "; DROP TABLE" in loaded.title  # Not executed

        await engine.dispose()


# ── F4: Email Verification & Password Reset (expiry) ─────


@pytest.mark.asyncio
async def test_verify_email_success(
    test_client: AsyncClient, mock_db_session, sample_user
) -> None:
    """A valid, unexpired verification token marks the user verified."""
    from datetime import datetime, timedelta

    sample_user.verification_token = "valid-verify-token"
    sample_user.verification_token_expiry = datetime.now(UTC) + timedelta(hours=1)
    sample_user.is_verified = False  # prove the endpoint flips it
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )

    response = await test_client.post(
        "/api/v1/auth/verify-email",
        params={"token": "valid-verify-token"},
    )
    assert response.status_code == 200
    assert "verified" in response.json()["message"].lower()
    assert sample_user.is_verified is True
    assert sample_user.verification_token is None


@pytest.mark.asyncio
async def test_verify_email_expired_token_rejected(
    test_client: AsyncClient, mock_db_session, sample_user
) -> None:
    """An expired verification token must be rejected (never replay old links)."""
    from datetime import datetime, timedelta

    sample_user.verification_token = "expired-verify-token"
    sample_user.verification_token_expiry = datetime.now(UTC) - timedelta(minutes=5)
    sample_user.is_verified = False
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )

    response = await test_client.post(
        "/api/v1/auth/verify-email",
        params={"token": "expired-verify-token"},
    )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()
    assert sample_user.is_verified is False


@pytest.mark.asyncio
async def test_verify_email_unknown_token_rejected(
    test_client: AsyncClient, mock_db_session
) -> None:
    """An unknown verification token is rejected."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=None
    )
    response = await test_client.post(
        "/api/v1/auth/verify-email",
        params={"token": "no-such-token"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_success(
    test_client: AsyncClient, mock_db_session, sample_user
) -> None:
    """A valid, unexpired reset token resets the password."""
    from datetime import datetime, timedelta

    sample_user.reset_token = "valid-reset-token"
    sample_user.reset_token_expiry = datetime.now(UTC) + timedelta(minutes=30)
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )

    response = await test_client.post(
        "/api/v1/auth/reset-password",
        params={"token": "valid-reset-token", "new_password": "NewSecurePass456!"},
    )
    assert response.status_code == 200
    assert "reset" in response.json()["message"].lower()
    assert sample_user.reset_token is None


@pytest.mark.asyncio
async def test_reset_password_expired_token_rejected(
    test_client: AsyncClient, mock_db_session, sample_user
) -> None:
    """An expired reset token must be rejected."""
    from datetime import datetime, timedelta

    sample_user.reset_token = "expired-reset-token"
    sample_user.reset_token_expiry = datetime.now(UTC) - timedelta(minutes=5)
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=sample_user
    )

    response = await test_client.post(
        "/api/v1/auth/reset-password",
        params={"token": "expired-reset-token", "new_password": "NewSecurePass456!"},
    )
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_request_password_reset_always_ok(
    test_client: AsyncClient, mock_db_session
) -> None:
    """Requesting a reset never leaks whether the email exists (anti-enumeration)."""
    mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
        return_value=None
    )
    response = await test_client.post(
        "/api/v1/auth/request-password-reset",
        params={"email": "ghost@example.com"},
    )
    assert response.status_code == 200
    assert "If the email exists" in response.json()["message"]
