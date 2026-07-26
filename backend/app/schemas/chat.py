"""Pydantic schemas for chat conversations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page_number: int | None = None
    score: float = 0.0


class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    document_ids: list[uuid.UUID] = []


class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    is_active: bool
    document_ids: list[uuid.UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: list[Citation] | None = None
    latency_ms: float | None = None
    tokens_used: int | None = None
    model_used: str | None = None
    faithfulness_score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID
    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    message: MessageResponse
    retrieval_debug: dict | None = None
