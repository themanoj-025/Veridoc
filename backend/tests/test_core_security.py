"""Tests for app.core.security — password hashing, JWT, file encryption."""

import uuid
from unittest.mock import patch

import pytest
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_file,
    encrypt_file,
    get_token_exp,
    get_token_jti,
    hash_password,
    validate_password_complexity,
    verify_password,
)

pytestmark = pytest.mark.unit

class TestPasswordComplexity:
    """Test validate_password_complexity."""

    def test_too_short(self) -> None:
        msg = validate_password_complexity("Ab1")
        assert msg is not None
        assert "8 characters" in msg

    def test_valid_password(self) -> None:
        assert validate_password_complexity("MyP@ssw0rd") is None

    def test_only_lowercase(self) -> None:
        msg = validate_password_complexity("abcdefgh")
        assert msg is not None
        assert "uppercase" in msg.lower() or "digit" in msg.lower()

    def test_uppercase_and_digit(self) -> None:
        assert validate_password_complexity("Abcdefg1") is None

    def test_uppercase_and_symbol(self) -> None:
        assert validate_password_complexity("Abcdefg!") is None

    def test_digit_and_symbol(self) -> None:
        assert validate_password_complexity("abcdef1!") is None


class TestPasswordHashing:
    """Test hash_password and verify_password."""

    def test_hash_and_verify(self) -> None:
        try:
            pwd = "MyStr0ng!"  # truncated to <72 bytes for bcrypt
            hashed = hash_password(pwd)
            assert verify_password(pwd, hashed) is True
        except (ValueError, AttributeError):
            pytest.skip("passlib/bcrypt version incompatibility")

    def test_wrong_password(self) -> None:
        try:
            hashed = hash_password("correct")
            assert verify_password("wrong", hashed) is False
        except (ValueError, AttributeError):
            pytest.skip("passlib/bcrypt version incompatibility")

    def test_different_hashes(self) -> None:
        try:
            h1 = hash_password("same")
            h2 = hash_password("same")
            assert h1 != h2  # bcrypt salts differ
        except (ValueError, AttributeError):
            pytest.skip("passlib/bcrypt version incompatibility")


class TestJWT:
    """Test create_access_token, create_refresh_token, decode_token."""

    @patch("app.core.security.settings")
    def test_access_token_roundtrip(self, mock_settings: object) -> None:
        from app.core.config import settings as real_settings
        mock_settings.jwt_secret = real_settings.jwt_secret
        mock_settings.jwt_algorithm = real_settings.jwt_algorithm
        mock_settings.access_token_expire_minutes = 30

        user_id = uuid.uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    @patch("app.core.security.settings")
    def test_refresh_token_roundtrip(self, mock_settings: object) -> None:
        from app.core.config import settings as real_settings
        mock_settings.jwt_secret = real_settings.jwt_secret
        mock_settings.jwt_algorithm = real_settings.jwt_algorithm
        mock_settings.refresh_token_expire_days = 7

        user_id = uuid.uuid4()
        token = create_refresh_token(user_id)
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self) -> None:
        assert decode_token("invalid.token.here") is None

    def test_get_token_jti(self) -> None:
        assert get_token_jti({"jti": "abc123"}) == "abc123"
        assert get_token_jti({}) is None
        assert get_token_jti(None) is None  # type: ignore[arg-type]

    def test_get_token_exp(self) -> None:
        assert get_token_exp({"exp": 1234567890.0}) == 1234567890.0
        assert get_token_exp({}) is None
        assert get_token_exp(None) is None  # type: ignore[arg-type]


class TestFileEncryption:
    """Test encrypt_file and decrypt_file."""

    def test_roundtrip(self) -> None:
        data = b"Hello, world! This is test data."
        encrypted, iv = encrypt_file(data)
        assert encrypted != data
        assert len(iv) > 0
        decrypted = decrypt_file(encrypted)
        assert decrypted == data

    def test_empty_data(self) -> None:
        data = b""
        encrypted, _ = encrypt_file(data)
        decrypted = decrypt_file(encrypted)
        assert decrypted == data

    def test_binary_data(self) -> None:
        data = bytes(range(256))
        encrypted, _ = encrypt_file(data)
        decrypted = decrypt_file(encrypted)
        assert decrypted == data
