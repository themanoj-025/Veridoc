"""Tests for email_sender service."""

import os

import pytest

from app.services.email_sender import (
    _get_base_url,
    get_dev_email_sender,
    send_password_reset_email,
    send_verification_email,
)


class TestGetBaseUrl:
    """Tests for _get_base_url helper."""

    def test_default_url(self) -> None:
        old = os.environ.pop("FRONTEND_URL", None)
        try:
            assert _get_base_url() == "http://localhost:3000"
        finally:
            if old is not None:
                os.environ["FRONTEND_URL"] = old

    def test_custom_url(self) -> None:
        os.environ["FRONTEND_URL"] = "https://example.com"
        try:
            assert _get_base_url() == "https://example.com"
        finally:
            os.environ.pop("FRONTEND_URL", None)


class TestDevEmailSender:
    """Tests for get_dev_email_sender factory."""

    def test_returns_dict_with_expected_keys(self) -> None:
        sender = get_dev_email_sender()
        assert isinstance(sender, dict)
        assert "send_verification" in sender
        assert "send_password_reset" in sender
        assert callable(sender["send_verification"])
        assert callable(sender["send_password_reset"])


class TestSendVerificationEmail:
    """Tests for send_verification_email (async, log-based)."""

    @pytest.mark.asyncio
    async def test_does_not_raise(self) -> None:
        # Dev mode just logs — should never raise
        await send_verification_email("test@example.com", "tok_abcdef1234567890")


class TestSendPasswordResetEmail:
    """Tests for send_password_reset_email (async, log-based)."""

    @pytest.mark.asyncio
    async def test_does_not_raise(self) -> None:
        await send_password_reset_email("test@example.com", "rst_abcdef1234567890")
