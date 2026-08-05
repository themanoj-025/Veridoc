"""Pydantic schemas for document management."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import PaginatedResponse


class DocumentUploadResponse(BaseModel):
    id: uuid.UUID
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    filename: str
    file_type: str
    file_size: int
    status: str
    ocr_used: bool
    page_count: int | None
    chunk_count: int | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    title: str | None = None


class DocumentListResponse(PaginatedResponse[DocumentResponse]):
    """Paginated list of documents.

    Inherits ``items`` (the documents), ``total``, ``limit``, ``offset``
    from ``PaginatedResponse``.
    """

    pass


class IngestionStatus(BaseModel):
    document_id: uuid.UUID
    status: str
    progress: int  # 0-100
    message: str | None = None
