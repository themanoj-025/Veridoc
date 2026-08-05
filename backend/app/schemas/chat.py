"""Pydantic schemas for chat conversations."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import PaginatedResponse


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page_number: int | None = None
    score: float = 0.0
    ocr_used: bool = False


class ConversationCreate(BaseModel):
    title: str = "New Conversation"
    document_ids: list[uuid.UUID] = []


class ConversationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    is_active: bool
    document_ids: list[uuid.UUID] = []
    document_titles: list[str] = []
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(PaginatedResponse[ConversationResponse]):
    """Paginated list of conversations."""

    pass


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    citations: list[Citation] = []
    latency_ms: float | None = None
    tokens_used: int | None = None
    model_used: str | None = None
    faithfulness_score: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_message(cls, msg) -> "MessageResponse":
        """Build response from a Message ORM object, loading citation records."""
        citations = []
        if hasattr(msg, "citation_records") and msg.citation_records:
            citations = [
                Citation(
                    chunk_id=c.chunk_id or "",
                    document_id=c.document_id or "",
                    text=c.text,
                    page_number=c.page_number,
                    score=c.score,
                )
                for c in msg.citation_records
            ]
        return cls(
            id=msg.id,
            conversation_id=msg.conversation_id,
            role=msg.role,
            content=msg.content,
            citations=citations,
            latency_ms=msg.latency_ms,
            tokens_used=msg.tokens_used,
            model_used=msg.model_used,
            faithfulness_score=msg.faithfulness_score,
            created_at=msg.created_at,
        )


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID
    message: str = Field(min_length=1, max_length=5000)


class ChatResponse(BaseModel):
    message: MessageResponse
    retrieval_debug: dict | None = None
