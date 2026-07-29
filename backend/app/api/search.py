"""Full-text search API routes — exposes the tsvector GIN index (D7)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from app.models.chunk import Chunk

router = APIRouter(prefix="/api/v1/search", tags=["search"])


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    content: str
    page_number: int | None = None
    rank: float = 0.0


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


@router.get("/fulltext", operation_id="search_fulltext")
async def fulltext_search(
    q: str,
    document_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Full-text search across document chunks using the Postgres tsvector GIN index.

    Queries the ``chunks.content_tsv`` GIN index for fast full-text search
    inside document content. Supports:

    - Plain text search (auto-stemming via English dictionary)
    - Optional ``document_id`` filter to scope search to a specific document
    - Pagination via ``limit`` and ``offset``

    The tsvector index was created in Alembic migration ``002`` but was
    previously unused — this endpoint closes that gap.
    """
    if not q or len(q.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must be at least 2 characters",
        )

    # Sanitize query for tsquery (remove special characters)
    import re
    safe_query = re.sub(r"[^\w\s]", " ", q.strip())
    # Convert to tsquery format: "word1 word2" → "word1 & word2"
    tsquery = " & ".join(safe_query.split())

    # Get user's document IDs for ownership check
    doc_result = await session.execute(
        select(Document.id).where(Document.user_id == user.id)
    )
    user_doc_ids = [str(row[0]) for row in doc_result.all()]

    if not user_doc_ids:
        await session.close()
        return SearchResponse(query=q, results=[], total=0)

    # Scope to specific document if requested
    if document_id:
        if document_id not in user_doc_ids:
            await session.close()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )
        user_doc_ids = [document_id]

    # Count total matches
    count_sql = text(
        """
        SELECT COUNT(*) FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.content_tsv @@ to_tsquery('english', :query)
        AND d.id = ANY(:doc_ids)
        """
    )
    count_result = await session.execute(
        count_sql,
        {"query": tsquery, "doc_ids": [uuid.UUID(did) for did in user_doc_ids]},
    )
    total = count_result.scalar() or 0

    # Search using tsvector index with rank
    search_sql = text(
        """
        SELECT
            c.id as chunk_id,
            c.document_id,
            d.title as document_title,
            c.content,
            c.page_number,
            ts_rank(c.content_tsv, to_tsquery('english', :query)) as rank
        FROM chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE c.content_tsv @@ to_tsquery('english', :query)
        AND d.id = ANY(:doc_ids)
        ORDER BY rank DESC
        LIMIT :limit
        OFFSET :offset
        """
    )
    result = await session.execute(
        search_sql,
        {
            "query": tsquery,
            "doc_ids": [uuid.UUID(did) for did in user_doc_ids],
            "limit": limit,
            "offset": offset,
        },
    )
    rows = result.all()

    await session.close()
    return SearchResponse(
        query=q,
        results=[
            SearchResult(
                chunk_id=str(row.chunk_id),
                document_id=str(row.document_id),
                document_title=row.document_title,
                content=row.content[:500],  # Truncate for preview
                page_number=row.page_number,
                rank=float(row.rank) if row.rank else 0.0,
            )
            for row in rows
        ],
        total=total,
    )
