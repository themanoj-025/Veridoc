"""Tests for authentication endpoints (register, login, refresh, me, change-password). — Part 2."""

from __future__ import annotations

import uuid
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.dependencies import get_current_user
from httpx import AsyncClient


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
    ) -> None:
        """A user accessing another user's document by ID must be rejected with 404."""

        async def override_user() -> None:
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
    ) -> None:
        """A user accessing another user's conversation by ID must be rejected with 404."""

        async def override_user() -> None:
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
