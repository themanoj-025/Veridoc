"""Document repository — encapsulates all Document ORM queries.

Replaces inline ``session.execute(select(Document)...)`` patterns
in ``api/documents.py``, ``api/chat.py``, ``api/gdpr.py``, and
``services/ingestion.py``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document operations with user-ownership scoping."""

    model_cls = Document

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ── User-scoped lookups ──────────────────────────────────

    async def find_by_id_and_user(
        self, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Document | None:
        """Find a document by ID, scoped to the owning user."""
        result = await self.session.execute(
            select(Document).where(
                Document.id == document_id, Document.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        """Paginated list of documents for a user, ordered by created_at desc.

        Returns (documents, total_count).
        """
        # Total count
        count_result = await self.session.execute(
            select(func.count(Document.id)).where(Document.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Items
        result = await self.session.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        docs = list(result.scalars().all())
        return docs, total

    async def list_all_by_user(self, user_id: uuid.UUID) -> list[Document]:
        """Get ALL documents for a user (no pagination). Used by GDPR export."""
        result = await self.session.execute(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """Count total documents owned by a user."""
        return await self.count(user_id=user_id)

    async def count_all(self) -> int:
        """Count ALL documents across all users (admin)."""
        result = await self.session.execute(select(func.count(Document.id)))
        return result.scalar() or 0

    # ── Ownership validation (batch) ─────────────────────────

    async def validate_ownership(
        self,
        document_ids: list[uuid.UUID],
        user_id: uuid.UUID,
    ) -> list[Document]:
        """Return only the documents from *document_ids* that belong to *user_id*.

        Returns the list of valid documents. If lengths differ from input,
        some IDs were invalid or didn't belong to the user.
        """
        result = await self.session.execute(
            select(Document).where(
                Document.id.in_(document_ids),
                Document.user_id == user_id,
            )
        )
        return list(result.scalars().all())

    async def list_ids_by_user(self, user_id: uuid.UUID) -> list[uuid.UUID]:
        """Get all document IDs for a user."""
        result = await self.session.execute(
            select(Document.id).where(Document.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def delete_all_by_user(self, user_id: uuid.UUID) -> None:
        """Bulk delete all documents owned by a user (for GDPR account deletion).

        Also deletes associated files from disk and vectors from Chroma.
        """
        docs = await self.list_by_user(user_id, limit=10000, offset=0)
        for doc in docs[0]:
            await self.delete_chroma_and_file(doc)
        from sqlalchemy import delete as sa_delete

        await self.session.execute(
            sa_delete(Document).where(Document.user_id == user_id)
        )

    async def delete_chroma_and_file(self, doc: Document) -> None:
        """Delete associated vector-store entries and the on-disk file."""
        from pathlib import Path

        import structlog

        # Delete file from disk
        Path(doc.file_path).unlink(missing_ok=True)

        # Remove from Chroma
        try:
            from app.services.vector_store import get_vector_store

            vs = get_vector_store()
            await vs.delete_document(str(doc.id))
        except Exception:
            structlog.get_logger(__name__).warning(
                "Chroma deletion failed (non-critical)", document_id=str(doc.id)
            )
