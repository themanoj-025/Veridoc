"""Document management API routes — uses DocumentRepository for data access."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.core.logging_config import bind_log_context
from app.core.rate_limit import get_user_identifier, limiter
from app.models.document import Document
from app.models.user import User
from app.repositories import ChunkRepository, DocumentRepository
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadResponse,
    IngestionStatus,
)
from app.services.ingestion import process_document
from app.services.job_queue import get_job_queue

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="documents_upload",
)
@limiter.limit("10/minute", key_func=get_user_identifier)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    title: str | None = Form(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Upload a document for processing.

    Rate-limited: 10 uploads per minute per user (F6).
    """
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
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Determine file type
    file_type = ext.lstrip(".")
    if file_type == "doc":
        file_type = "docx"

    # Save to disk
    file_id = uuid.uuid4()
    safe_filename = f"{file_id}_{file.filename}"
    file_path = settings.upload_dir / safe_filename
    import asyncio

    await asyncio.to_thread(file_path.write_bytes, content)

    # F7: Virus-scan hook — reject the upload if the configured scanner flags it.
    # Default NoopVirusScanner reports clean; swap in ClamAV via get_virus_scanner().
    from app.services.ssrf_protection import get_virus_scanner

    scanner = get_virus_scanner()
    if not scanner.scan(str(file_path)):
        file_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File failed virus scan and was rejected",
        )

    # Create document record via repository
    doc_repo = DocumentRepository(session)
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
    await doc_repo.create(doc)

    # Enqueue background ingestion via job queue
    await get_job_queue().enqueue_job(
        process_document,
        doc.id,
        session_factory=None,
        job_id=str(doc.id),
        max_retries=3,
    )

    await session.close()
    return DocumentUploadResponse.model_validate(doc)


@router.get("/", response_model=DocumentListResponse, operation_id="documents_list")
async def list_documents(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    limit: int = 50,
    offset: int = 0,
):
    """List documents for the current user with pagination."""
    doc_repo = DocumentRepository(session)
    docs, total = await doc_repo.list_by_user(user.id, limit=limit, offset=offset)
    await session.close()
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{document_id}", response_model=DocumentResponse, operation_id="documents_get"
)
async def get_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a specific document's details."""
    bind_log_context(document_id=str(document_id))
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.find_by_id_and_user(document_id, user.id)
    if not doc:
        await session.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    await session.close()
    return DocumentResponse.model_validate(doc)


@router.patch(
    "/{document_id}", response_model=DocumentResponse, operation_id="documents_update"
)
async def update_document(
    document_id: uuid.UUID,
    body: DocumentUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update document metadata (e.g., title)."""
    bind_log_context(document_id=str(document_id))
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.find_by_id_and_user(document_id, user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if body.title is not None:
        doc.title = body.title
    await doc_repo.update(doc)
    await session.close()
    return DocumentResponse.model_validate(doc)


@router.get("/{document_id}/content", operation_id="documents_get_content")
async def get_document_content(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get a document's text content and chunks for the frontend viewer."""
    bind_log_context(document_id=str(document_id))
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.find_by_id_and_user(document_id, user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Get chunks via repository
    chunk_repo = ChunkRepository(session)
    chunks = await chunk_repo.find_by_document(doc.id)
    await session.close()
    return {
        "id": str(doc.id),
        "title": doc.title,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "status": doc.status,
        "page_count": doc.page_count,
        "chunk_count": doc.chunk_count,
        "chunks": [
            {
                "id": str(c.id),
                "index": c.chunk_index,
                "content": c.content,
                "page_number": c.page_number,
                "ocr_used": c.ocr_used,
            }
            for c in chunks
        ],
    }


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="documents_delete",
)
async def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete a document and its chunks."""
    bind_log_context(document_id=str(document_id))
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.find_by_id_and_user(document_id, user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Delete file from disk + Chroma
    await doc_repo.delete_chroma_and_file(doc)

    # Delete from database
    await doc_repo.delete(doc)
    await session.close()


@router.post(
    "/{document_id}/reindex",
    response_model=IngestionStatus,
    operation_id="documents_reindex",
)
async def reindex_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Re-index a document (re-chunk and re-embed)."""
    bind_log_context(document_id=str(document_id))
    doc_repo = DocumentRepository(session)
    doc = await doc_repo.find_by_id_and_user(document_id, user.id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Reset status
    doc.status = "pending"
    await doc_repo.update(doc)

    # Enqueue reindex job
    await get_job_queue().enqueue_job(
        process_document,
        doc.id,
        session_factory=None,
        job_id=f"reindex-{doc.id}",
        max_retries=3,
    )

    await session.close()
    return IngestionStatus(
        document_id=doc.id,
        status="pending",
        progress=0,
        message="Re-indexing started",
    )
