"""Chat API routes — conversations, messages, SSE streaming."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.conversation import Conversation
from app.models.conversation_document import ConversationDocument
from app.schemas.chat import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
    MessageResponse,
    ChatRequest,
)
from app.services.chat_service import ChatService
from app.core.logging_config import bind_log_context

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


# ── Helpers ──────────────────────────────────────────────

async def _build_conversation_response(session: AsyncSession, conv: Conversation) -> ConversationResponse:
    """Build a ConversationResponse from a Conversation ORM object,
    loading document IDs and titles from the junction table."""
    # Load linked documents via junction table
    result = await session.execute(
        select(ConversationDocument).where(
            ConversationDocument.conversation_id == conv.id,
        )
    )
    links = result.scalars().all()
    doc_ids = [link.document_id for link in links]

    # Fetch document titles for convenience
    doc_titles = []
    if doc_ids:
        doc_result = await session.execute(
            select(Document.title).where(Document.id.in_(doc_ids))
        )
        doc_titles = [row[0] for row in doc_result.all()]

    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        is_active=conv.is_active,
        document_ids=doc_ids,
        document_titles=doc_titles,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )




# ── Conversations ────────────────────────────────────────

@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED, operation_id="chat_create_conversation")
async def create_conversation(
    body: ConversationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new conversation."""
    # Validate document IDs belong to user
    if body.document_ids:
        result = await session.execute(
            select(Document).where(
                Document.id.in_(body.document_ids),
                Document.user_id == user.id,
            )
        )
        valid_docs = result.scalars().all()
        if len(valid_docs) != len(body.document_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more document IDs are invalid",
            )

    conv = Conversation(
        user_id=user.id,
        title=body.title,
    )
    session.add(conv)
    await session.flush()

    # Create junction records for each document
    for doc_id in body.document_ids:
        link = ConversationDocument(
            conversation_id=conv.id,
            document_id=doc_id,
        )
        session.add(link)

    await session.flush()
    await session.refresh(conv)
    result = await _build_conversation_response(session, conv)
    await session.close()
    return result


@router.get("/conversations", response_model=ConversationListResponse, operation_id="chat_list_conversations")
async def list_conversations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
    offset: int = 0,
):
    """List conversations for the current user with pagination.

    Uses a single JOIN + array_agg query (not N+1) to load conversations
    with their linked document IDs and titles in one round trip.
    """
    from sqlalchemy import func

    # Get total count
    count_result = await session.execute(
        select(func.count(Conversation.id))
        .where(Conversation.user_id == user.id, Conversation.is_active == True)
    )
    total = count_result.scalar() or 0

    result = await session.execute(
        select(
            Conversation,
            func.array_agg(ConversationDocument.document_id, order_by=ConversationDocument.document_id).label("doc_ids"),
            func.array_agg(Document.title, order_by=ConversationDocument.document_id).label("doc_titles"),
        )
        .outerjoin(ConversationDocument, ConversationDocument.conversation_id == Conversation.id)
        .outerjoin(Document, Document.id == ConversationDocument.document_id)
        .where(Conversation.user_id == user.id, Conversation.is_active == True)
        .group_by(Conversation.id)
        .order_by(desc(Conversation.updated_at))
        .limit(limit)
        .offset(offset)
    )
    rows = result.all()
    responses = []
    for conv_raw, doc_ids_raw, doc_titles_raw in rows:
        doc_ids = [d for d in (doc_ids_raw or []) if d is not None]
        doc_titles = [t for t in (doc_titles_raw or []) if t is not None]
        responses.append(ConversationResponse(
            id=conv_raw.id,
            user_id=conv_raw.user_id,
            title=conv_raw.title,
            is_active=conv_raw.is_active,
            document_ids=doc_ids,
            document_titles=doc_titles,
            created_at=conv_raw.created_at,
            updated_at=conv_raw.updated_at,
        ))
    await session.close()
    return ConversationListResponse(
        items=responses,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse, operation_id="chat_get_conversation")
async def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific conversation."""
    bind_log_context(conversation_id=str(conversation_id))
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        await session.close()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    result = await _build_conversation_response(session, conv)
    await session.close()
    return result


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="chat_delete_conversation")
async def delete_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a conversation."""
    bind_log_context(conversation_id=str(conversation_id))
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    await session.delete(conv)
    await session.close()


# ── Messages ─────────────────────────────────────────────

@router.get("/conversations/{conversation_id}/messages", operation_id="chat_get_messages")
async def get_messages(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get all messages in a conversation."""
    bind_log_context(conversation_id=str(conversation_id))
    result = await session.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    await session.close()
    return [
        MessageResponse.from_message(m) for m in conv.messages
    ]


@router.post("/stream", operation_id="chat_stream")
async def stream_chat(
    body: ChatRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Stream a chat response via SSE with citations.

    Delegates to ChatService for the full pipeline.
    """
    bind_log_context(conversation_id=str(body.conversation_id))
    service = ChatService(session, user)
    conv = await service.validate_conversation(body.conversation_id)
    return await service.stream_response(body, conv, session)
