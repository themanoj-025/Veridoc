"""Tests for app.core.config — Settings model and validation."""

import os
from unittest.mock import patch

from app.core.config import Settings, _PLACEHOLDER_PATTERNS, _validate_secret


class TestSettings:
    """Test Settings model defaults and properties."""

    def test_default_values(self) -> None:
        s = Settings()
        assert s.app_env in ("development", "production", "test")
        assert s.postgres_port == 5432
        assert s.chroma_port == 8001
        assert s.jwt_algorithm == "HS256"
        assert s.access_token_expire_minutes == 30
        assert s.refresh_token_expire_days == 7

    def test_database_url_property(self) -> None:
        s = Settings(
            postgres_user="test", postgres_password="pass",
            postgres_host="localhost", postgres_port=5432,
            postgres_db="testdb",
        )
        url = s.database_url
        assert "postgresql+asyncpg://" in url
        assert "testdb" in url

    def test_database_url_sync_property(self) -> None:
        s = Settings(
            postgres_user="test", postgres_password="pass",
            postgres_host="localhost", postgres_port=5432,
            postgres_db="testdb",
        )
        url = s.database_url_sync
        assert "postgresql+psycopg2://" in url

    def test_chroma_url_property(self) -> None:
        s = Settings(chroma_host="localhost", chroma_port=8001)
        assert s.chroma_url == "http://localhost:8001"

    def test_redis_url_with_password(self) -> None:
        s = Settings(redis_host="localhost", redis_port=6379,
                     redis_password="secret", redis_db=0)
        url = s.redis_url
        assert ":secret@" in url

    def test_redis_url_without_password(self) -> None:
        s = Settings(redis_host="localhost", redis_port=6379, redis_db=0)
        url = s.redis_url
        assert "redis://localhost:6379/0" == url

    def test_redis_url_empty_host(self) -> None:
        s = Settings(redis_host="")
        assert s.redis_url == ""


class TestValidateSecret:
    """Test _validate_secret function."""

    def test_valid_secret(self) -> None:
        result = _validate_secret("my-strong-secret-key-123", "TEST_KEY")
        assert result == "my-strong-secret-key-123"

    def test_empty_secret_raises(self) -> None:
        import pytest
        with pytest.raises(ValueError, match="is not set"):
            _validate_secret("", "TEST_KEY")

    def test_placeholder_raises(self) -> None:
        import pytest
        with pytest.raises(ValueError, match="placeholder"):
            _validate_secret("change-me-please", "TEST_KEY")

    def test_all_placeholders_blocked(self) -> None:
        import pytest
        for pattern in _PLACEHOLDER_PATTERNS:
            secret = f"{pattern}-value"
            with pytest.raises(ValueError):
                _validate_secret(secret, "TEST_KEY")
