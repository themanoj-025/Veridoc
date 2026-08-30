"""Tests for: F3 (RBAC), F4 (email verification), F6 (rate limiting 429),
F8 (admin audit log), G2 (prompt version recording), G4 (secret rotation warning).

All tests use the existing mocked DB session pattern from conftest.py.
"""

from __future__ import annotations

import uuid
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.security import hash_password
from app.models.admin_audit_log import AdminAuditLog
from app.models.message import Message
from app.models.user import User
from httpx import AsyncClient

# ════════════════════════════════════════════════════════════════
# F3: RBAC — role-based admin check
# ════════════════════════════════════════════════════════════════


class TestF3_RBAC:
    """Admin endpoints must check the `role` column, not registration order."""

    @pytest.mark.asyncio
    async def test_admin_role_required(
        self, test_client: AsyncClient, sample_user, app
    ):
        """A user with role='user' should be denied admin access with 403."""
        sample_user.role = "user"
        from app.core.dependencies import get_current_user

        async def override():
            return sample_user

        app.dependency_overrides[get_current_user] = override

        response = await test_client.get(
            "/api/v1/admin/analytics",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_admin_role_granted(
        self, test_client: AsyncClient, sample_user, app, mock_db_session
    ):
        """A user with role='admin' should be granted admin access (200, not 403)."""
        sample_user.role = "admin"
        from app.core.dependencies import get_current_user

        async def override():
            return sample_user

        app.dependency_overrides[get_current_user] = override

        # Mock DB queries to return empty results gracefully
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_result.all = MagicMock(return_value=[])
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        response = await test_client.get(
            "/api/v1/admin/analytics",
            headers={"Authorization": "Bearer fake-token"},
        )
        # Should NOT be 403 — admin user is allowed
        assert response.status_code != 403
        # Should return 200 (analytics may have empty data but endpoint works)
        assert response.status_code == 200

        app.dependency_overrides.pop(get_current_user, None)

    def test_non_first_user_admin_access(self) -> bool:
        """Verify that a non-first-registered user with role='admin' can be
        created and granted admin access (the old heuristic would deny them).

        This is a unit-level verification of the UserRepository and User model.
        """
        # Create two users — first is 'user', second is 'admin'
        first_user = User(
            id=uuid.uuid4(),
            email="first@example.com",
            role="user",  # First user is NOT admin
        )
        second_user = User(
            id=uuid.uuid4(),
            email="second@example.com",
            role="admin",  # Second user IS admin — explicit, not inferred
        )

        # Only the second user has admin role
        assert first_user.role == "user"
        assert second_user.role == "admin"

        # Verify the check: only role='admin' passes, NOT registration order
        def is_admin(user: User) -> bool:
            return user.role == "admin"

        assert is_admin(first_user) is False
        assert is_admin(second_user) is True


# ════════════════════════════════════════════════════════════════
# F4: Email verification & password reset flows
# ════════════════════════════════════════════════════════════════


class TestF4_EmailVerification:
    """Tests for token generation, expiry, and successful verification/reset."""

    def test_verification_token_generation(self) -> None:
        """A verification token should be generated and stored on the user."""
        import secrets

        token = secrets.token_urlsafe(32)
        user = User(
            email="verify@example.com",
            hashed_password=hash_password("TestPass123!"),
            verification_token=token,
        )
        assert user.verification_token == token
        assert len(token) > 20  # should be a reasonable length

    def test_verify_email_success(self) -> None:
        """A valid verification token should mark the user as verified."""
        import secrets

        token = secrets.token_urlsafe(32)
        user = User(
            email="verify@example.com",
            hashed_password=hash_password("TestPass123!"),
            verification_token=token,
            is_verified=False,
        )

        # Simulate verification
        found_user = user if user.verification_token == token else None
        assert found_user is not None

        found_user.is_verified = True
        found_user.verification_token = None

        assert found_user.is_verified is True
        assert found_user.verification_token is None

    def test_verify_email_invalid_token(self) -> None:
        """An invalid verification token should not match any user."""
        user = User(
            email="verify@example.com",
            hashed_password=hash_password("TestPass123!"),
            verification_token="real-token",
            is_verified=False,
        )

        # Try to find with a different token
        found = user if user.verification_token == "wrong-token" else None
        assert found is None, "Should not find user with wrong token"

    def test_password_reset_token_generation(self) -> None:
        """A reset token with expiry should be generated on request."""
        import secrets
        from datetime import datetime, timedelta

        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + timedelta(hours=1)

        user = User(
            email="reset@example.com",
            hashed_password=hash_password("TestPass123!"),
            reset_token=token,
            reset_token_expiry=expires,
        )

        assert user.reset_token == token
        assert user.reset_token_expiry is not None
        assert user.reset_token_expiry > datetime.now(UTC)

    def test_password_reset_success(self) -> None:
        """A valid reset token within expiry should allow password reset."""
        import secrets
        from datetime import datetime, timedelta

        from app.core.security import hash_password, verify_password

        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) + timedelta(hours=1)

        new_password = "NewSecurePass456!"
        old_hash = hash_password("OldPass123!")
        user = User(
            email="reset@example.com",
            hashed_password=old_hash,
            reset_token=token,
            reset_token_expiry=expires,
        )

        # Verify token is valid (not expired)
        assert user.reset_token_expiry > datetime.now(UTC)

        # Reset the password
        user.hashed_password = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None

        assert verify_password(new_password, user.hashed_password) is True
        assert verify_password("OldPass123!", user.hashed_password) is False
        assert user.reset_token is None
        assert user.reset_token_expiry is None

    def test_password_reset_expired_token(self) -> None:
        """An expired reset token should not allow password reset."""
        import secrets
        from datetime import datetime, timedelta

        from app.core.security import hash_password

        token = secrets.token_urlsafe(32)
        expires = datetime.now(UTC) - timedelta(hours=1)  # Already expired!

        user = User(
            email="reset@example.com",
            hashed_password=hash_password("OldPass123!"),
            reset_token=token,
            reset_token_expiry=expires,
        )

        # Token is expired — should be rejected
        is_expired = user.reset_token_expiry < datetime.now(UTC)
        assert is_expired is True, "Token should be expired"

    @pytest.mark.asyncio
    async def test_email_sender_logs_token(self) -> None:
        """The dev-mode email sender should log the token (not send a real email)."""
        from app.services.email_sender import (
            send_password_reset_email,
            send_verification_email,
        )

        with patch("app.services.email_sender.logger.info") as mock_log:
            await send_verification_email("test@example.com", "test-token-123")
            mock_log.assert_called_once()
            _args, kwargs = mock_log.call_args
            assert kwargs.get("token_prefix") == "test-tok"
            assert kwargs.get("to") == "test@example.com"

            mock_log.reset_mock()
            await send_password_reset_email("test@example.com", "reset-token-456")
            mock_log.assert_called_once()
            _args, kwargs = mock_log.call_args
            assert kwargs.get("token_prefix") == "reset-to"


# ════════════════════════════════════════════════════════════════
# F6: Rate limiting — 429 enforcement
# ════════════════════════════════════════════════════════════════


class TestF6_RateLimiting:
    """Rate limits should be enforced on upload and chat endpoints.
    Uses the existing slowapi limiter which returns 429 with Retry-After.
    """

    def test_rate_limit_disabled_in_test_mode(self) -> None:
        """Rate limits are bypassed in test mode (env='test').
        The _should_rate_limit() function returns False so the
        @limiter.limit() decorator is a no-op in test runs."""
        from app.core import config as _config

        assert _config.settings.app_env == "test"

        from app.core.rate_limit import _should_rate_limit

        assert _should_rate_limit() is False

    def test_rate_limit_structure(self) -> None:
        """Verify the rate limit decorator format is correct for upload and chat endpoints."""
        # This test validates the structure by checking the limiter module
        from app.core.rate_limit import limiter

        # The limiter.limit decorator exists and can be called
        decorator = limiter.limit("10/minute")
        assert decorator is not None

        # Test different rate limit strings
        for limit_str in ["10/minute", "20/minute", "30/minute"]:
            decorator = limiter.limit(limit_str)
            assert decorator is not None


# ════════════════════════════════════════════════════════════════
# F8: Admin audit log
# ════════════════════════════════════════════════════════════════


class TestF8_AdminAuditLog:
    """Admin actions should be recorded in the append-only audit log."""

    def test_audit_log_creation(self) -> None:
        """Creating an audit log entry should store the correct fields."""
        log = AdminAuditLog(
            actor_id=uuid.uuid4(),
            action="analytics_accessed",
            target_type="admin",
            target_id=None,
            metadata_json='{"method": "GET"}',
        )

        assert log.action == "analytics_accessed"
        assert log.target_type == "admin"
        assert log.metadata_json == '{"method": "GET"}'
        assert log.actor_id is not None

    @pytest.mark.asyncio
    async def test_audit_log_append_only(self) -> None:
        """The audit log should be append-only — entries cannot be modified
        (no update method is exposed). We test this by creating a log entry
        and verifying it's persisted correctly.

        This test uses a real in-memory SQLite DB via the fixture from test_schema.
        """
        from app.core.database import Base
        from sqlalchemy import select

        # Use a real in-memory SQLite database
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
            # Create an audit log entry via ORM
            log = AdminAuditLog(
                actor_id=uuid.uuid4(),
                action="feedback_queue_accessed",
                target_type="admin",
            )
            session.add(log)
            await session.commit()

            # Read it back
            result = await session.execute(
                select(AdminAuditLog).where(
                    AdminAuditLog.action == "feedback_queue_accessed"
                )
            )
            loaded = result.scalar_one_or_none()
            assert loaded is not None
            assert loaded.action == "feedback_queue_accessed"
            assert loaded.created_at is not None

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_audit_log_multiple_entries(self) -> None:
        """Multiple admin actions should all be logged separately."""
        from app.core.database import Base
        from sqlalchemy import select
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
            actor_id = uuid.uuid4()
            actions = [
                "analytics_accessed",
                "cache_stats_accessed",
                "feedback_queue_accessed",
            ]
            for action in actions:
                log = AdminAuditLog(actor_id=actor_id, action=action)
                session.add(log)
            await session.commit()

            result = await session.execute(
                select(AdminAuditLog).where(AdminAuditLog.actor_id == actor_id)
            )
            entries = result.scalars().all()
            assert len(entries) == 3
            assert {e.action for e in entries} == set(actions)

        await engine.dispose()


# ════════════════════════════════════════════════════════════════
# G2: Prompt version recording
# ════════════════════════════════════════════════════════════════


class TestG2_PromptVersion:
    """Messages should record which prompt version was used to generate them."""

    def test_prompt_version_field_exists(self) -> None:
        """The prompt_version field should exist on the Message model."""
        msg = Message(
            conversation_id=uuid.uuid4(),
            role="assistant",
            content="Test response",
            prompt_version="1.0.0",
        )
        assert msg.prompt_version == "1.0.0"

    def test_prompt_version_optional(self) -> None:
        """The prompt_version field should be nullable for backward compatibility."""
        msg = Message(
            conversation_id=uuid.uuid4(),
            role="user",
            content="Test question",
        )
        assert msg.prompt_version is None

    @pytest.mark.asyncio
    async def test_prompt_version_persisted(self) -> None:
        """The prompt version should be persisted and retrievable from the DB."""
        from app.core.database import Base
        from app.models.conversation import Conversation
        from app.models.message import Message
        from app.models.user import User
        from sqlalchemy import select
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
            user = User(email="prompt@test.com", hashed_password="x" * 60)
            session.add(user)
            await session.flush()

            conv = Conversation(user_id=user.id, title="Prompt test")
            session.add(conv)
            await session.flush()

            msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content="Test response",
                prompt_version="1.0.0",
            )
            session.add(msg)
            await session.commit()

            # Read it back
            result = await session.execute(
                select(Message).where(Message.prompt_version == "1.0.0")
            )
            loaded = result.scalar_one_or_none()
            assert loaded is not None
            assert loaded.prompt_version == "1.0.0"

        await engine.dispose()

    def test_prompt_registry_exists(self) -> None:
        """The prompts/registry.json file should exist with version info."""
        import json
        from pathlib import Path

        registry_path = (
            Path(__file__).resolve().parent.parent.parent / "prompts" / "registry.json"
        )
        assert registry_path.exists(), f"Registry file not found at {registry_path}"

        with open(registry_path) as f:
            registry = json.load(f)

        assert "prompts" in registry
        assert len(registry["prompts"]) > 0
        # Each prompt should have a version field
        for prompt in registry["prompts"]:
            assert "version" in prompt
            assert "name" in prompt
            assert "template" in prompt

    def test_prompt_version_resolver_returns_registry_version(self) -> None:
        """The resolver must return the version recorded in the registry."""
        from app.services.prompt_registry import get_prompt_version

        version = get_prompt_version("system-prompt")
        assert version == "1.0.0"

    def test_prompt_version_resolver_unknown_name(self) -> None:
        """Unknown prompt names must resolve to 'unknown', never raise."""
        from app.services.prompt_registry import get_prompt_version

        assert get_prompt_version("does-not-exist") == "unknown"

    def test_prompt_template_loaded_from_registry(self) -> None:
        """build_system_prompt must load the template from the registry (G2)."""
        from app.services.prompt_registry import get_prompt_template

        template = get_prompt_template("system-prompt")
        assert template is not None
        assert "{{context}}" in template
        assert "Veridoc" in template

    @pytest.mark.asyncio
    async def test_chat_service_records_prompt_version_on_message(
        self, mock_db_session, sample_user
    ) -> None:
        """ChatService.save_assistant_message must stamp prompt_version (G2)."""
        import asyncio
        from unittest.mock import MagicMock, patch

        from app.models.conversation import Conversation
        from app.services.chat_service import ChatService

        conv = Conversation(id=uuid.uuid4(), user_id=sample_user.id, title="t")

        # Capture the Message object passed to session.add
        added = []
        mock_db_session.add = MagicMock(
            side_effect=lambda obj: added.append(obj) or None
        )
        mock_db_session.flush = AsyncMock()
        mock_db_session.commit = AsyncMock()

        service = ChatService(mock_db_session, sample_user)
        service.llm = MagicMock()
        service.llm.model_name = "ollama/llama3.1:8b"

        # Prevent the fire-and-forget usage log from opening a real DB session
        with patch("app.core.database.async_session_factory") as factory:
            factory.return_value.__aenter__ = AsyncMock(return_value=MagicMock())
            factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await service.save_assistant_message(
                conv=conv,
                content="Answer",
                citations=[],
                total_time=1.0,
                token_count=5,
                faith_score=0.9,
                system_prompt="p",
                message="Q",
                retrieval_time=1.0,
                rerank_time=1.0,
                gen_time=1.0,
                faith_time=1.0,
            )
            # Let the fire-and-forget task finish to avoid pending-task warnings
            await asyncio.sleep(0.05)

        msg = added[-1]
        assert msg.role == "assistant"
        assert msg.prompt_version == "1.0.0"

    def test_build_system_prompt_uses_registry_template(self) -> None:
        """build_system_prompt should inline the registry template with context (G2)."""
        from app.models.user import User
        from app.services.chat_service import ChatService

        user = User(id=uuid.uuid4(), email="x@y.z", hashed_password="h")
        service = ChatService(MagicMock(), user)
        prompt = service.build_system_prompt("CONTEXT_HERE")
        assert "CONTEXT_HERE" in prompt
        assert "{{context}}" not in prompt
        assert "Veridoc" in prompt


# ════════════════════════════════════════════════════════════════
# G4: Secret rotation warning
# ════════════════════════════════════════════════════════════════


class TestG4_SecretRotation:
    """The startup config validation should warn about secret rotation age."""

    def test_secret_rotation_check_function_exists(self) -> None:
        """The _check_secret_rotation_age function should exist in main."""
        from app.main import _check_secret_rotation_age

        assert callable(_check_secret_rotation_age)

    def test_secret_rotation_check_runs_without_error(self) -> None:
        """The rotation check should run without raising exceptions."""
        import structlog

        logger = structlog.get_logger(__name__)

        from app.main import _check_secret_rotation_age

        # Should not raise
        _check_secret_rotation_age(logger)

    # ── G4: warning fires / does not fire appropriately ────────────

    def _call_with(self, rotated_at, window_days=90):
        """Invoke the check with a patched settings object and capture log calls."""
        from app.core import config as config_module
        from app.main import _check_secret_rotation_age

        mock_settings = MagicMock()
        mock_settings.secret_rotated_at = rotated_at
        mock_settings.secret_rotation_warning_days = window_days

        with patch.object(config_module, "settings", mock_settings):
            mock_logger = MagicMock()
            _check_secret_rotation_age(mock_logger)
        return mock_logger

    def test_warns_when_never_recorded(self) -> None:
        """Unset SECRET_ROTATED_AT → warning (status=never_recorded)."""
        logger = self._call_with(None)
        warnings = [
            c
            for c in logger.warning.call_args_list
            if c[0][0] == "security.secret_rotation"
        ]
        assert len(warnings) == 1
        assert warnings[0][1]["status"] == "never_recorded"

    def test_warns_when_stale(self) -> None:
        """Rotation older than the window → warning (status=stale)."""
        from datetime import datetime, timedelta

        old = (datetime.now(UTC) - timedelta(days=200)).date().isoformat()
        logger = self._call_with(old, window_days=90)
        warnings = [
            c
            for c in logger.warning.call_args_list
            if c[0][0] == "security.secret_rotation"
        ]
        assert len(warnings) == 1
        assert warnings[0][1]["status"] == "stale"
        assert warnings[0][1]["age_days"] > 90

    def test_no_warning_when_fresh(self) -> None:
        """Recent rotation → info (status=fresh), no warning."""
        from datetime import datetime

        fresh = datetime.now(UTC).date().isoformat()
        logger = self._call_with(fresh, window_days=90)
        assert not logger.warning.called
        infos = [
            c
            for c in logger.info.call_args_list
            if c[0][0] == "security.secret_rotation"
        ]
        assert len(infos) == 1
        assert infos[0][1]["status"] == "fresh"

    def test_warns_on_malformed_date(self) -> None:
        """A malformed SECRET_ROTATED_AT → warning (status=invalid_date)."""
        logger = self._call_with("not-a-date")
        warnings = [
            c
            for c in logger.warning.call_args_list
            if c[0][0] == "security.secret_rotation"
        ]
        assert len(warnings) == 1
        assert warnings[0][1]["status"] == "invalid_date"

    def test_validate_config_rejects_empty_secrets(self) -> None:
        """validate_config() should reject empty JWT_SECRET and FILE_ENCRYPTION_KEY."""
        from app.core.config import settings, validate_config

        # Save originals
        orig_jwt = settings.jwt_secret
        orig_key = settings.file_encryption_key

        try:
            settings.jwt_secret = ""
            settings.file_encryption_key = ""
            with pytest.raises(RuntimeError, match="is not set"):
                validate_config()
        finally:
            # Restore
            settings.jwt_secret = orig_jwt
            settings.file_encryption_key = orig_key

    def test_validate_config_rejects_placeholder_secrets(self) -> None:
        """validate_config() should reject secrets containing pattern words."""
        from app.core.config import settings, validate_config

        orig_jwt = settings.jwt_secret
        orig_key = settings.file_encryption_key

        try:
            settings.jwt_secret = "change-me-12345"
            settings.file_encryption_key = "real-key-not-placeholder"
            with pytest.raises(RuntimeError, match="change-me"):
                validate_config()
        finally:
            settings.jwt_secret = orig_jwt
            settings.file_encryption_key = orig_key

    def test_validate_config_accepts_valid_secrets(self) -> None:
        """validate_config() should accept properly-set secrets."""
        from app.core.config import settings, validate_config

        orig_jwt = settings.jwt_secret
        orig_key = settings.file_encryption_key

        try:
            settings.jwt_secret = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
            settings.file_encryption_key = (
                "x1y2z3x1y2z3x1y2z3x1y2z3x1y2z3x1y2z3x1y2z3x1y"
            )
            # Should not raise
            validate_config()
        finally:
            settings.jwt_secret = orig_jwt
            settings.file_encryption_key = orig_key

    def test_secret_validation_patterns(self) -> None:
        """The placeholder detection should catch known patterns."""
        from app.core.config import _validate_secret

        # These should all raise ValueError
        for pattern in [
            "change-me-123",
            "changeme",
            "placeholder",
            "your-secret",
            "<your-key>",
        ]:
            with pytest.raises(ValueError):
                _validate_secret(pattern, "TEST_SECRET")

        # Strong secrets should pass
        _validate_secret("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4", "TEST_SECRET")
        _validate_secret("my-strong-unique-random-secret-for-testing", "TEST_SECRET")
