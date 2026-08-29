"""Tests for app.core.security — password, JWT, and file encryption utilities."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest


class TestPasswordComplexity:
    """validate_password_complexity enforces minimum requirements."""

    def test_too_short(self) -> None:
        from app.core.security import validate_password_complexity

        assert validate_password_complexity("Ab1") is not None

    def test_exactly_8_chars_valid(self) -> None:
        from app.core.security import validate_password_complexity

        # uppercase + digit = 2 categories
        assert validate_password_complexity("Abcdef1!") is None

    def test_only_lowercase_rejected(self) -> None:
        from app.core.security import validate_password_complexity

        assert validate_password_complexity("abcdefgh") is not None

    def test_only_digits_rejected(self) -> None:
        from app.core.security import validate_password_complexity

        assert validate_password_complexity("12345678") is not None

    def test_uppercase_and_digit_valid(self) -> None:
        from app.core.security import validate_password_complexity

        assert validate_password_complexity("Password1") is None

    def test_uppercase_and_symbol_valid(self) -> None:
        from app.core.security import validate_password_complexity

        assert validate_password_complexity("Password!") is None

    def test_digit_and_symbol_valid(self) -> None:
        from app.core.security import validate_password_complexity

        assert validate_password_complexity("pass1word!") is None

    def test_all_three_categories_valid(self) -> None:
        from app.core.security import validate_password_complexity

        assert validate_password_complexity("P4ssw0rd!") is None


class TestPasswordHashing:
    """hash_password and verify_password round-trip correctly."""

    def test_hash_and_verify(self) -> None:
        from app.core.security import hash_password, verify_password

        try:
            pwd = "MyStr0ng!Pass"
            hashed = hash_password(pwd)
            assert verify_password(pwd, hashed) is True
        except (ValueError, TypeError):
            pytest.skip("passlib/bcrypt version incompatibility")

    def test_wrong_password_fails(self) -> None:
        from app.core.security import hash_password, verify_password

        try:
            hashed = hash_password("correct-password")
            assert verify_password("wrong-password", hashed) is False
        except (ValueError, TypeError):
            pytest.skip("passlib/bcrypt version incompatibility")

    def test_different_hashes_for_same_password(self) -> None:
        from app.core.security import hash_password

        try:
            h1 = hash_password("same-password")
            h2 = hash_password("same-password")
            # bcrypt uses random salt, so hashes should differ
            assert h1 != h2
        except (ValueError, TypeError):
            pytest.skip("passlib/bcrypt version incompatibility")


class TestJWT:
    """create_access_token / create_refresh_token / decode_token."""

    def test_access_token_round_trip(self) -> None:
        from app.core.security import create_access_token, decode_token

        uid = uuid.uuid4()
        token = create_access_token(uid)
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == str(uid)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "jti" in payload

    def test_refresh_token_round_trip(self) -> None:
        from app.core.security import create_refresh_token, decode_token

        uid = uuid.uuid4()
        token = create_refresh_token(uid)
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_invalid_token_returns_none(self) -> None:
        from app.core.security import decode_token

        assert decode_token("not-a-real-token") is None

    def test_expired_token_returns_none(self) -> None:
        from app.core.security import _create_token

        token = _create_token(
            {"sub": "test", "type": "access"},
            timedelta(hours=-1),  # expired 1 hour ago
        )
        from app.core.security import decode_token

        assert decode_token(token) is None

    def test_get_token_jti(self) -> None:
        from app.core.security import create_access_token, get_token_jti

        token = create_access_token(uuid.uuid4())
        from app.core.security import decode_token

        payload = decode_token(token)
        jti = get_token_jti(payload)
        assert jti is not None
        assert len(jti) > 0

    def test_get_token_exp(self) -> None:
        from app.core.security import create_access_token, get_token_exp

        token = create_access_token(uuid.uuid4())
        from app.core.security import decode_token

        payload = decode_token(token)
        exp = get_token_exp(payload)
        assert exp is not None
        assert exp > datetime.now(UTC).timestamp()

    def test_get_token_jti_none_payload(self) -> None:
        from app.core.security import get_token_jti

        assert get_token_jti(None) is None

    def test_get_token_exp_none_payload(self) -> None:
        from app.core.security import get_token_exp

        assert get_token_exp(None) is None


class TestFileEncryption:
    """encrypt_file / decrypt_file round-trip correctly."""

    def test_encrypt_decrypt_round_trip(self) -> None:
        from app.core.security import decrypt_file, encrypt_file

        data = b"Hello, Veridoc! This is test content."
        encrypted, iv_hex = encrypt_file(data)
        assert encrypted != data
        assert len(iv_hex) == 32  # 16 bytes hex
        decrypted = decrypt_file(encrypted)
        assert decrypted == data

    def test_different_encryptions_produce_different_ciphertext(self) -> None:
        from app.core.security import encrypt_file

        data = b"same data"
        enc1, _ = encrypt_file(data)
        enc2, _ = encrypt_file(data)
        # Fernet uses random IV, so ciphertext differs
        assert enc1 != enc2

    def test_empty_data(self) -> None:
        from app.core.security import decrypt_file, encrypt_file

        encrypted, _ = encrypt_file(b"")
        decrypted = decrypt_file(encrypted)
        assert decrypted == b""
