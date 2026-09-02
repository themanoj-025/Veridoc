"""Tests for: F3 (RBAC), F4 (email verification), F6 (rate limiting 429),
F8 (admin audit log), G2 (prompt version recording), G4 (secret rotation warning).

All tests use the existing mocked DB session pattern from conftest.py. — Part 2."""

from __future__ import annotations

import uuid
from datetime import UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.message import Message
from app.models.user import User


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

    def _call_with(self, rotated_at, window_days=90) -> None:
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
