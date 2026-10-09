"""Pydantic schemas for document sharing (F20)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class ShareCreate(BaseModel):
    shared_with_email: EmailStr
    permission: str = "read"


class ShareUpdate(BaseModel):
    permission: str


class ShareResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    shared_with_email: str
    permission: str
    created_at: datetime

    model_config = {"from_attributes": True}
