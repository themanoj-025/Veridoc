"""Tests for app.services.ssrf_protection — URL validation and virus scanning."""

from __future__ import annotations

import socket
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

class TestValidateUploadUrl:
    """validate_upload_url blocks private/link-local IPs."""

    def test_invalid_url_raises(self) -> None:
        from app.services.ssrf_protection import validate_upload_url

        with pytest.raises(ValueError, match="Invalid URL"):
            validate_upload_url("not-a-url")

    def test_no_hostname_raises(self) -> None:
        from app.services.ssrf_protection import validate_upload_url

        with pytest.raises(ValueError, match="Invalid URL"):
            validate_upload_url("file:///etc/passwd")

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_public_ip_allowed(self, mock_resolve: object) -> None:
        from app.services.ssrf_protection import validate_upload_url

        mock_resolve.return_value = "8.8.8.8"  # Google DNS
        assert validate_upload_url("https://example.com/file.pdf") is True

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_localhost_blocked(self, mock_resolve: object) -> None:
        from app.services.ssrf_protection import validate_upload_url

        mock_resolve.return_value = "127.0.0.1"
        assert validate_upload_url("http://localhost/file.pdf") is False

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_private_10_blocked(self, mock_resolve: object) -> None:
        from app.services.ssrf_protection import validate_upload_url

        mock_resolve.return_value = "10.0.0.1"
        assert validate_upload_url("http://internal/file.pdf") is False

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_private_192_168_blocked(self, mock_resolve: object) -> None:
        from app.services.ssrf_protection import validate_upload_url

        mock_resolve.return_value = "192.168.1.1"
        assert validate_upload_url("http://router/file.pdf") is False

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_private_172_16_blocked(self, mock_resolve: object) -> None:
        from app.services.ssrf_protection import validate_upload_url

        mock_resolve.return_value = "172.16.0.1"
        assert validate_upload_url("http://docker/file.pdf") is False

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_link_local_blocked(self, mock_resolve: object) -> None:
        from app.services.ssrf_protection import validate_upload_url

        mock_resolve.return_value = "169.254.1.1"
        assert validate_upload_url("http://metadata/file.pdf") is False

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_unresolvable_returns_false(self, mock_resolve: object) -> None:
        from app.services.ssrf_protection import validate_upload_url

        mock_resolve.side_effect = socket.gaierror("DNS resolution failed")
        assert validate_upload_url("http://nonexistent.example/file.pdf") is False


class TestNoopVirusScanner:
    """NoopVirusScanner always reports clean."""

    def test_always_clean(self) -> None:
        from app.services.ssrf_protection import NoopVirusScanner

        scanner = NoopVirusScanner()
        assert scanner.scan("/any/path/file.pdf") is True

    def test_factory_returns_scanner(self) -> None:
        from app.services.ssrf_protection import get_virus_scanner

        scanner = get_virus_scanner()
        assert hasattr(scanner, "scan")
        assert scanner.scan("test") is True
