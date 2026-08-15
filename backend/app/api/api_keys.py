"""API key management routes — create, list, and revoke API keys."""

from __future__ import annotations

import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.api_key import ApiKey
from app.models.user import User
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


def _hash_key(plaintext: str) -> str:
    """Hash an API key with SHA-256 for storage."""
    return hashlib.sha256(plaintext.encode()).hexdigest()


def _generate_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        Tuple of (full_key, prefix, hash).
        Full key format: ``vid_`` + 40 hex chars = 44 chars.
    """
    raw = secrets.token_hex(20)
    full = f"vid_{raw}"
    prefix = full[:8]  # e.g. "vid_a1b2"
    return full, prefix, _hash_key(full)


@router.get("/", response_model=list[ApiKeyResponse], operation_id="api_keys_list")
async def list_api_keys(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all active API keys for the current user.

    Never returns the full key — only the prefix and metadata.
    """
    result = await session.execute(
        select(ApiKey)
        .where(ApiKey.user_id == user.id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()
    await session.close()
    return [
        ApiKeyResponse(
            id=k.id,
            prefix=k.key_prefix,
            name=k.name,
            is_active=k.is_active,
            last_used_at=k.last_used_at,
            rate_limit_per_minute=k.rate_limit_per_minute,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.post(
    "/",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="api_keys_create",
)
async def create_api_key(
    body: ApiKeyCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new API key.

    The full plaintext key is returned **only once** in the response.
    Store it securely — it cannot be retrieved again.
    """
    full_key, prefix, key_hash = _generate_key()

    key = ApiKey(
        user_id=user.id,
        key_prefix=prefix,
        key_hash=key_hash,
        name=body.name,
        rate_limit_per_minute=body.rate_limit_per_minute,
    )
    session.add(key)
    await session.commit()
    await session.refresh(key)

    await session.close()
    return ApiKeyCreatedResponse(
        id=key.id,
        name=key.name,
        key=full_key,
        key_prefix=prefix,
        rate_limit_per_minute=key.rate_limit_per_minute,
        created_at=key.created_at,
    )


@router.delete(
    "/{key_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="api_keys_delete"
)
async def revoke_api_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Revoke (delete) an API key. Irreversible."""
    key = await session.get(ApiKey, key_id)
    if not key or key.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found"
        )

    await session.delete(key)
    await session.commit()
    await session.close()
