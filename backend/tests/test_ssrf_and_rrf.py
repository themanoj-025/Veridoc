"""Tests for ssrf_protection and retrieval/rrf modules."""

import socket
from unittest.mock import patch

import pytest
from app.services.retrieval.rrf import reciprocal_rank_fusion
from app.services.ssrf_protection import (
    _PRIVATE_RANGES,
    NoopVirusScanner,
    validate_upload_url,
)


class TestSSRFProtection:
    """Test validate_upload_url."""

    def test_invalid_url_no_hostname(self) -> None:
        with pytest.raises(ValueError, match="Invalid URL"):
            validate_upload_url("")

    def test_malformed_url(self) -> None:
        with pytest.raises(ValueError, match="Invalid URL"):
            validate_upload_url("not-a-url")

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_private_ip_blocked(self, mock_resolve: object) -> None:
        mock_resolve.return_value = "127.0.0.1"
        assert validate_upload_url("http://evil.com/file.pdf") is False

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_private_192_168_blocked(self, mock_resolve: object) -> None:
        mock_resolve.return_value = "192.168.1.1"
        assert validate_upload_url("http://evil.com/file.pdf") is False

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_private_10_blocked(self, mock_resolve: object) -> None:
        mock_resolve.return_value = "10.0.0.1"
        assert validate_upload_url("http://evil.com/file.pdf") is False

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_link_local_blocked(self, mock_resolve: object) -> None:
        mock_resolve.return_value = "169.254.1.1"
        assert validate_upload_url("http://evil.com/file.pdf") is False

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_public_ip_allowed(self, mock_resolve: object) -> None:
        mock_resolve.return_value = "8.8.8.8"
        assert validate_upload_url("http://example.com/file.pdf") is True

    @patch("app.services.ssrf_protection.socket.gethostbyname")
    def test_dns_failure(self, mock_resolve: object) -> None:
        mock_resolve.side_effect = socket.gaierror("DNS failure")
        assert validate_upload_url("http://unknown.host/file.pdf") is False

    def test_private_ranges_defined(self) -> None:
        assert len(_PRIVATE_RANGES) >= 8


class TestNoopVirusScanner:
    """Test NoopVirusScanner."""

    def test_always_clean(self) -> None:
        scanner = NoopVirusScanner()
        assert scanner.scan("/tmp/test.pdf") is True
        assert scanner.scan("") is True


class TestReciprocalRankFusion:
    """Test reciprocal_rank_fusion function."""

    def test_empty_results(self) -> None:
        assert reciprocal_rank_fusion([], []) == []

    def test_only_bm25(self) -> None:
        bm25 = [
            {"chunk_id": "c1", "content": "hello"},
            {"chunk_id": "c2", "content": "world"},
        ]
        result = reciprocal_rank_fusion(bm25, [])
        assert len(result) == 2
        assert result[0]["chunk_id"] == "c1"

    def test_only_dense(self) -> None:
        dense = [
            {"chunk_id": "c1", "content": "hello"},
            {"chunk_id": "c3", "content": "foo"},
        ]
        result = reciprocal_rank_fusion([], dense)
        assert len(result) == 2

    def test_merging(self) -> None:
        bm25 = [
            {"chunk_id": "c1", "content": "a"},
            {"chunk_id": "c2", "content": "b"},
        ]
        dense = [
            {"chunk_id": "c2", "content": "b"},
            {"chunk_id": "c3", "content": "c"},
        ]
        result = reciprocal_rank_fusion(bm25, dense)
        ids = [r["chunk_id"] for r in result]
        assert "c1" in ids
        assert "c2" in ids
        assert "c3" in ids

    def test_top_k_limit(self) -> None:
        bm25 = [{"chunk_id": f"c{i}", "content": str(i)} for i in range(10)]
        result = reciprocal_rank_fusion(bm25, [], top_k=3)
        assert len(result) == 3

    def test_c1_appears_in_both_gets_highest_score(self) -> None:
        bm25 = [{"chunk_id": "c1", "content": "a"}]
        dense = [{"chunk_id": "c1", "content": "a"}]
        result = reciprocal_rank_fusion(bm25, dense)
        assert result[0]["chunk_id"] == "c1"
        assert result[0]["rrf_score"] > 0
