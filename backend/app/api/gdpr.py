"""GDPR-style data export and deletion endpoints (D10) — uses repositories."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.message import Message
from app.models.usage_log import UsageLog
from app.models.user import User
from app.repositories import (
    ConversationRepository,
    DocumentRepository,
    UsageLogRepository,
)

router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.get("/export", operation_id="user_export_data")
async def export_user_data(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Export all user data in JSON format (GDPR Article 20)."""
    doc_repo = DocumentRepository(session)
    conv_repo = ConversationRepository(session)

    # User profile
    user_data = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }

    # Documents
    documents = await doc_repo.list_all_by_user(user.id)
    documents_data = [
        {
            "id": str(d.id),
            "title": d.title,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "status": d.status,
            "page_count": d.page_count,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in documents
    ]

    # Conversations with messages
    conversations = await conv_repo.list_all_by_user(user.id)
    conversations_data = []
    for conv in conversations:
        msg_result = await session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()
        conversations_data.append(
            {
                "id": str(conv.id),
                "title": conv.title,
                "is_active": conv.is_active,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "messages": [
                    {
                        "id": str(m.id),
                        "role": m.role,
                        "content": m.content,
                        "latency_ms": m.latency_ms,
                        "faithfulness_score": m.faithfulness_score,
                        "created_at": (
                            m.created_at.isoformat() if m.created_at else None
                        ),
                    }
                    for m in messages
                ],
            }
        )

    # Usage logs (last 1000)
    log_result = await session.execute(
        select(UsageLog)
        .where(UsageLog.user_id == user.id)
        .order_by(UsageLog.created_at.desc())
        .limit(1000)
    )
    logs = log_result.scalars().all()
    usage_data = [
        {
            "id": str(log.id),
            "query": log.query[:200],
            "response_time_ms": log.response_time_ms,
            "model_used": log.model_used,
            "estimated_cost": log.estimated_cost,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

    await session.close()

    export = {
        "exported_at": datetime.now(UTC).isoformat(),
        "user": user_data,
        "documents": documents_data,
        "conversations": conversations_data,
        "usage_logs": usage_data,
    }

    return JSONResponse(
        content=export,
        headers={
            "Content-Disposition": f"attachment; filename=veridoc-export-{user.id}.json",
        },
    )


@router.delete("/delete-account", operation_id="user_delete_account")
async def delete_account(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Any:
    """Delete the user account and all associated data (GDPR Article 17)."""
    import structlog

    logger = structlog.get_logger(__name__)

    # Delete all documents (chunks cascade) via repository
    doc_repo = DocumentRepository(session)
    await doc_repo.delete_all_by_user(user.id)

    # Delete all conversations (messages cascade) via repository
    conv_repo = ConversationRepository(session)
    await conv_repo.delete_all_by_user(user.id)

    # Delete usage logs via repository
    log_repo = UsageLogRepository(session)
    await log_repo.delete_all_by_user(user.id)

    # Delete the user
    await session.delete(user)
    await session.commit()

    logger.info("user.account_deleted", user_id=str(user.id)[:8])

    return {"message": "Account and all associated data have been permanently deleted"}
