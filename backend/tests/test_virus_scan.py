"""Tests for F7 — virus-scan hook on document upload.

The upload endpoint calls ``get_virus_scanner().scan(path)`` and rejects the
file (400) when the scanner reports infected. The default ``NoopVirusScanner``
reports everything clean, so development stays unblocked while a ClamAV-backed
implementation can be swapped in via the factory.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.dependencies import get_current_user

EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def _override_get_user(app, user):
    async def override():
        return user
    app.dependency_overrides[get_current_user] = override


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestVirusScanner:
    def test_noop_scanner_reports_clean(self):
        """The default scanner always reports clean (True)."""
        from app.services.ssrf_protection import NoopVirusScanner
        assert NoopVirusScanner().scan("/tmp/any-file.txt") is True

    def test_get_virus_scanner_factory_returns_noop_by_default(self):
        """The factory returns the no-op scanner until a real one is configured."""
        from app.services.ssrf_protection import get_virus_scanner
        scanner = get_virus_scanner()
        assert scanner.scan("/tmp/file.txt") is True

    @pytest.mark.asyncio
    async def test_upload_rejects_infected_file(
        self, test_client: AsyncClient, mock_db_session, sample_user, sample_user_token, app, temp_upload_dir,
    ):
        """An EICAR file flagged by the scanner → 400, file removed, no doc created."""
        _override_get_user(app, sample_user)
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        fake_scanner = MagicMock()
        fake_scanner.scan = MagicMock(return_value=False)  # infected

        with patch("app.services.ssrf_protection.get_virus_scanner", return_value=fake_scanner):
            response = await test_client.post(
                "/api/v1/documents/upload",
                headers=_auth(sample_user_token),
                files={"file": ("eicar.txt", EICAR, "text/plain")},
                data={"title": "EICAR test"},
            )

        assert response.status_code == 400
        assert "virus scan" in response.json()["detail"]
        # No document record was created
        assert mock_db_session.add.call_count == 0
        # Upload dir is empty — the file was deleted
        assert list(temp_upload_dir.iterdir()) == []

        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_upload_accepts_clean_file_through_noop(
        self, test_client: AsyncClient, mock_db_session, sample_user, sample_user_token, app, temp_upload_dir,
    ):
        """A clean file passes the no-op scan and proceeds to doc creation."""
        _override_get_user(app, sample_user)
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        with patch("app.services.ssrf_protection.get_virus_scanner") as factory:
            factory.return_value.scan.return_value = True

            response = await test_client.post(
                "/api/v1/documents/upload",
                headers=_auth(sample_user_token),
                files={"file": ("notes.txt", b"hello world", "text/plain")},
                data={"title": "Notes"},
            )

        assert response.status_code == 201
        # Document record WAS created
        assert mock_db_session.add.call_count >= 1

        app.dependency_overrides.pop(get_current_user, None)
