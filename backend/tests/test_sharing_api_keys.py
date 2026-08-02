"""Tests for F20 — document sharing permission enforcement and API-key auth."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.dependencies import get_current_user


def _override_get_user(app, user):
    async def override():
        return user

    app.dependency_overrides[get_current_user] = override


def _auth(user_token: str) -> dict:
    return {"Authorization": f"Bearer {user_token}"}


# ════════════════════════════════════════════════════════════════
# Document sharing — permission enforcement
# ════════════════════════════════════════════════════════════════


class TestDocumentSharing:
    @pytest.mark.asyncio
    async def test_list_shares_denied_for_non_owner(
        self,
        test_client: AsyncClient,
        mock_db_session,
        sample_user,
        sample_user_token,
        app,
    ):
        """A non-owner must get 404 when listing shares of a document."""
        _override_get_user(app, sample_user)
        # DocumentRepository.find_by_id_and_user returns None → not found
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=None
        )

        doc_id = uuid.uuid4()
        response = await test_client.get(
            f"/api/v1/documents/{doc_id}/shares",
            headers=_auth(sample_user_token),
        )
        assert response.status_code == 404

        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_create_share_denied_for_non_owner(
        self,
        test_client: AsyncClient,
        mock_db_session,
        sample_user,
        sample_user_token,
        app,
    ):
        """A non-owner must get 404 when trying to share a document."""
        _override_get_user(app, sample_user)
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=None
        )

        doc_id = uuid.uuid4()
        response = await test_client.post(
            f"/api/v1/documents/{doc_id}/shares",
            json={"shared_with_email": "other@example.com", "permission": "read"},
            headers=_auth(sample_user_token),
        )
        assert response.status_code == 404

        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_update_share_denied_for_non_owner(
        self,
        test_client: AsyncClient,
        mock_db_session,
        sample_user,
        sample_user_token,
        app,
    ):
        """Updating a share requires being the document owner."""
        _override_get_user(app, sample_user)

        # session.get(share) returns a share; find_by_id_and_user returns None
        share = MagicMock()
        share.document_id = uuid.uuid4()
        mock_db_session.get = AsyncMock(return_value=share)
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=None
        )

        response = await test_client.patch(
            f"/api/v1/shares/{uuid.uuid4()}",
            json={"permission": "write"},
            headers=_auth(sample_user_token),
        )
        assert response.status_code == 404

        app.dependency_overrides.pop(get_current_user, None)


# ════════════════════════════════════════════════════════════════
# API key management — auth and key format
# ════════════════════════════════════════════════════════════════


class TestApiKeys:
    @pytest.mark.asyncio
    async def test_create_api_key_requires_auth(self, test_client: AsyncClient):
        """Creating an API key without a token → 401."""
        response = await test_client.post(
            "/api/v1/api-keys/",
            json={"name": "ci-key", "rate_limit_per_minute": 60},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_api_key_returns_key_once(
        self,
        test_client: AsyncClient,
        mock_db_session,
        sample_user,
        sample_user_token,
        app,
    ):
        """Creating a key returns vid_<hex> once and never stores plaintext."""
        _override_get_user(app, sample_user)
        mock_db_session.execute.return_value.scalar_one_or_none = MagicMock(
            return_value=None
        )

        response = await test_client.post(
            "/api/v1/api-keys/",
            json={"name": "ci-key", "rate_limit_per_minute": 60},
            headers=_auth(sample_user_token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["key"].startswith("vid_")
        assert data["key_prefix"] == data["key"][:8]

        # The plaintext key must never be persisted — only a SHA-256 hash.
        from app.models.api_key import ApiKey

        added: ApiKey = mock_db_session.add.call_args[0][0]
        assert added.key_hash != data["key"]
        assert added.key_hash == _sha256(data["key"])

        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_revoke_api_key_denied_for_other_users_key(
        self,
        test_client: AsyncClient,
        mock_db_session,
        sample_user,
        sample_user_token,
        app,
    ):
        """Revoking a key that isn't yours → 404."""
        _override_get_user(app, sample_user)
        foreign_key = MagicMock()
        foreign_key.id = uuid.uuid4()
        foreign_key.user_id = uuid.uuid4()  # different owner
        mock_db_session.get = AsyncMock(return_value=foreign_key)

        response = await test_client.delete(
            f"/api/v1/api-keys/{foreign_key.id}",
            headers=_auth(sample_user_token),
        )
        assert response.status_code == 404

        app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_list_api_keys_requires_auth(self, test_client: AsyncClient):
        """Listing API keys without a token → 401."""
        response = await test_client.get("/api/v1/api-keys/")
        assert response.status_code == 401


def _sha256(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()
