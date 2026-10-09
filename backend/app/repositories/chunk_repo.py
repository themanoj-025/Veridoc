"""Chunk repository — encapsulates all Chunk ORM queries.

Replaces inline ``session.execute(select(Chunk)...)`` patterns
in ``api/documents.py`` and ``services/ingestion.py``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.repositories.base import BaseRepository


class ChunkRepository(BaseRepository[Chunk]):
    """Repository for Chunk operations."""

    model_cls = Chunk

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def find_by_document(
        self,
        document_id: uuid.UUID,
        order_by_index: bool = True,
    ) -> list[Chunk]:
        """Get all chunks for a document, ordered by chunk_index."""
        stmt = select(Chunk).where(Chunk.document_id == document_id)
        if order_by_index:
            stmt = stmt.order_by(Chunk.chunk_index)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_batch(self, chunks: list[Chunk]) -> list[Chunk]:
        """Add multiple chunks in one batch."""
        for chunk in chunks:
            self.session.add(chunk)
        await self.session.flush()
        return chunks
