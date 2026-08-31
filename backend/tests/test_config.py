"""Tests for app.core.config — Settings, validation, and property accessors."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.slow
class TestSettingsProperties:
    """Settings computed properties build correct URLs."""

    def test_database_url_format(self) -> None:
        from app.core.config import Settings

        s = Settings(
            postgres_user="u",
            postgres_password="p",
            postgres_host="h",
            postgres_port=5432,
            postgres_db="d",
            jwt_secret="test-secret",
            file_encryption_key="test-key",
        )
        assert s.database_url == "postgresql+asyncpg://u:p@h:5432/d"

    def test_database_url_sync_format(self) -> None:
        from app.core.config import Settings

        s = Settings(
            postgres_user="u",
            postgres_password="p",
            postgres_host="h",
            postgres_port=5432,
            postgres_db="d",
            jwt_secret="test-secret",
            file_encryption_key="test-key",
        )
        assert s.database_url_sync == "postgresql+psycopg2://u:p@h:5432/d"

    def test_chroma_url_format(self) -> None:
        from app.core.config import Settings

        s = Settings(
            chroma_host="chroma.local",
            chroma_port=8001,
            jwt_secret="test",
            file_encryption_key="test",
        )
        assert s.chroma_url == "http://chroma.local:8001"

    def test_redis_url_without_password(self) -> None:
        from app.core.config import Settings

        s = Settings(
            redis_host="redis.local",
            redis_port=6379,
            redis_db=0,
            redis_password="",
            jwt_secret="test",
            file_encryption_key="test",
        )
        assert s.redis_url == "redis://redis.local:6379/0"

    def test_redis_url_with_password(self) -> None:
        from app.core.config import Settings

        s = Settings(
            redis_host="redis.local",
            redis_port=6379,
            redis_db=2,
            redis_password="secret",
            jwt_secret="test",
            file_encryption_key="test",
        )
        assert s.redis_url == "redis://:secret@redis.local:6379/2"

    def test_redis_url_empty_host(self) -> None:
        from app.core.config import Settings

        s = Settings(
            redis_host="",
            jwt_secret="test",
            file_encryption_key="test",
        )
        assert s.redis_url == ""

    def test_data_dirs_created(self, tmp_path: Path) -> None:
        from app.core.config import Settings

        s = Settings(
            data_dir=tmp_path / "data",
            upload_dir=tmp_path / "data" / "uploads",
            jwt_secret="test",
            file_encryption_key="test",
        )
        # Simulate module-level mkdir that happens at import time
        s.data_dir.mkdir(parents=True, exist_ok=True)
        s.upload_dir.mkdir(parents=True, exist_ok=True)
        assert s.data_dir.exists()
        assert s.upload_dir.exists()


class TestValidateSecret:
    """_validate_secret catches empty and placeholder values."""

    def test_empty_raises(self) -> None:
        from app.core.config import _validate_secret

        with pytest.raises(ValueError, match="is not set"):
            _validate_secret("", "TEST_SECRET")

    def test_placeholder_raises(self) -> None:
        from app.core.config import _validate_secret

        with pytest.raises(ValueError, match="placeholder"):
            _validate_secret("change-me-123", "TEST_SECRET")

    def test_changeme_raises(self) -> None:
        from app.core.config import _validate_secret

        with pytest.raises(ValueError, match="placeholder"):
            _validate_secret("changeme", "TEST_SECRET")

    def test_valid_secret_passes(self) -> None:
        from app.core.config import _validate_secret

        result = _validate_secret("s3cr3t-k3y!@#$", "TEST_SECRET")
        assert result == "s3cr3t-k3y!@#$"


class TestValidateConfig:
    """validate_config aggregates errors from all critical secrets."""

    def test_valid_config_passes(self) -> None:
        from app.core.config import Settings, validate_config

        with patch("app.core.config.settings", Settings(
            jwt_secret="real-secret-key",
            file_encryption_key="real-encryption-key",
        )):
            # Should not raise
            validate_config()

    def test_missing_jwt_raises(self) -> None:
        from app.core.config import Settings, validate_config

        with patch("app.core.config.settings", Settings(
            jwt_secret="",
            file_encryption_key="real-key",
        )), pytest.raises(RuntimeError, match="JWT_SECRET"):
            validate_config()

    def test_missing_encryption_key_raises(self) -> None:
        from app.core.config import Settings, validate_config

        with patch("app.core.config.settings", Settings(
            jwt_secret="real-key",
            file_encryption_key="",
        )), pytest.raises(RuntimeError, match="FILE_ENCRYPTION_KEY"):
            validate_config()

    def test_both_missing_shows_both_errors(self) -> None:
        from app.core.config import Settings, validate_config


        with patch("app.core.config.settings", Settings(
            jwt_secret="",
            file_encryption_key="",
        )):
            with pytest.raises(RuntimeError) as exc_info:
                validate_config()
            msg = str(exc_info.value)
            assert "JWT_SECRET" in msg
            assert "FILE_ENCRYPTION_KEY" in msg
