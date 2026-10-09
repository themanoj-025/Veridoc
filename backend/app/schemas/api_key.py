"""Pydantic schemas for API key management (F20)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ApiKeyCreate(BaseModel):
    name: str
    rate_limit_per_minute: int | None = None


class ApiKeyCreatedResponse(BaseModel):
    """Includes the full plaintext key — only returned once at creation."""

    id: uuid.UUID
    name: str
    key: str  # Full plaintext key, shown only at creation
    key_prefix: str
    rate_limit_per_minute: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    """API key info returned on list/get (never includes the full key)."""

    id: uuid.UUID
    prefix: str
    name: str
    is_active: bool
    last_used_at: datetime | None = None
    rate_limit_per_minute: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
