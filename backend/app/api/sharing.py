"""Document sharing API routes — manage who has access to a user's documents.

Two router prefixes:
- ``/api/v1/documents/{id}/shares`` — list and create shares
- ``/api/v1/shares/{id}`` — update and delete shares by share ID
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.document_share import DocumentShare
from app.repositories import DocumentRepository
from app.schemas.sharing import ShareCreate, ShareUpdate, ShareResponse

# ── Document-scoped routes (list + create) ──────────────────
doc_router = APIRouter(prefix="/api/v1/documents", tags=["sharing"])


@doc_router.get(
    "/{document_id}/shares",
    response_model=list[ShareResponse],
    operation_id="shares_list",
)
async def list_shares(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all users this document is shared with.

    Only the document owner can view shares.
    """
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.find_by_id_and_user(document_id, user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    result = await session.execute(
        select(DocumentShare).where(DocumentShare.document_id == document_id)
    )
    shares = result.scalars().all()

    response = []
    for share in shares:
        shared_user = await session.get(User, share.shared_with_user_id)
        response.append(
            ShareResponse(
                id=share.id,
                document_id=share.document_id,
                shared_with_email=shared_user.email if shared_user else "unknown",
                permission=share.permission,
                created_at=share.created_at,
            )
        )

    await session.close()
    return response


@doc_router.post(
    "/{document_id}/shares",
    response_model=ShareResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="shares_create",
)
async def create_share(
    document_id: uuid.UUID,
    body: ShareCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Share a document with another user by email.

    Only the document owner can share. The recipient must have an account.
    """
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.find_by_id_and_user(document_id, user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Find the target user by email
    from app.repositories.user_repo import UserRepository

    user_repo = UserRepository(session)
    target_user = await user_repo.find_by_email(body.shared_with_email)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email not found. They must have an account.",
        )

    if target_user.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share a document with yourself.",
        )

    # Check for existing share
    existing = await session.execute(
        select(DocumentShare).where(
            DocumentShare.document_id == document_id,
            DocumentShare.shared_with_user_id == target_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Document is already shared with this user.",
        )

    share = DocumentShare(
        document_id=document_id,
        shared_with_user_id=target_user.id,
        permission=body.permission,
    )
    session.add(share)
    await session.commit()
    await session.refresh(share)

    await session.close()
    return ShareResponse(
        id=share.id,
        document_id=share.document_id,
        shared_with_email=body.shared_with_email,
        permission=share.permission,
        created_at=share.created_at,
    )


# ── Share-scoped routes (update + delete by share ID) ──────
router = APIRouter(prefix="/api/v1/shares", tags=["sharing"])


@router.patch("/{share_id}", response_model=ShareResponse, operation_id="shares_update")
async def update_share(
    share_id: uuid.UUID,
    body: ShareUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update a share's permission level. Only the document owner can update."""
    share = await session.get(DocumentShare, share_id)
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        )

    doc_repo = DocumentRepository(session)
    doc = await doc_repo.find_by_id_and_user(share.document_id, user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    share.permission = body.permission
    await session.commit()
    await session.refresh(share)

    shared_user = await session.get(User, share.shared_with_user_id)

    await session.close()
    return ShareResponse(
        id=share.id,
        document_id=share.document_id,
        shared_with_email=shared_user.email if shared_user else "unknown",
        permission=share.permission,
        created_at=share.created_at,
    )


@router.delete(
    "/{share_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="shares_delete"
)
async def delete_share(
    share_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Remove a share. Only the document owner can unshare."""
    share = await session.get(DocumentShare, share_id)
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share not found"
        )

    doc_repo = DocumentRepository(session)
    doc = await doc_repo.find_by_id_and_user(share.document_id, user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    await session.delete(share)
    await session.commit()
    await session.close()
