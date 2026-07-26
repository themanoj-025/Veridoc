"""Document management API routes."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.document import Document
from app.models.chunk import Chunk
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentListResponse,
    IngestionStatus,
)
from app.services.ingestion import process_document

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload a document for processing."""
    # Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB",
        )

    # Determine file type
    file_type = ext.lstrip(".")
    if file_type == "doc":
        file_type = "docx"

    # Save to disk
    file_id = uuid.uuid4()
    safe_filename = f"{file_id}_{file.filename}"
    file_path = settings.upload_dir / safe_filename
    with open(file_path, "wb") as f:
        f.write(content)

    # Create document record
    doc = Document(
        id=file_id,
        user_id=user.id,
        title=title or file.filename or "Untitled",
        filename=file.filename or "untitled",
        file_type=file_type,
        file_size=len(content),
        file_path=str(file_path),
        status="pending",
    )
    session.add(doc)
    await session.flush()
    await session.refresh(doc)

    # Start async processing with its own session
    import asyncio
    from app.core.database import async_session_factory
    asyncio.create_task(process_document(doc.id, session_factory=async_session_factory))

    return DocumentUploadResponse.model_validate(doc)


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List all documents for the current user."""
    result = await session.execute(
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=len(docs),
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific document's details."""
    result = await session.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: uuid.UUID,
    body: DocumentUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update document metadata (e.g., title)."""
    result = await session.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if body.title is not None:
        doc.title = body.title
    session.add(doc)
    await session.flush()
    await session.refresh(doc)
    return DocumentResponse.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a document and its chunks."""
    result = await session.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Delete file from disk
    Path(doc.file_path).unlink(missing_ok=True)

    # Remove from Chroma
    try:
        from app.services.vector_store import get_vector_store
        vs = get_vector_store()
        await vs.delete_document(str(doc.id))
    except Exception:
        pass  # Non-critical

    # Delete from database
    await session.delete(doc)


@router.post("/{document_id}/reindex", response_model=IngestionStatus)
async def reindex_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Re-index a document (re-chunk and re-embed)."""
    result = await session.execute(
        select(Document).where(Document.id == document_id, Document.user_id == user.id)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Reset status
    doc.status = "pending"
    session.add(doc)
    await session.flush()

    import asyncio
    from app.core.database import async_session_factory
    asyncio.create_task(process_document(doc.id, session_factory=async_session_factory))

    return IngestionStatus(
        document_id=doc.id,
        status="pending",
        progress=0,
        message="Re-indexing started",
    )
