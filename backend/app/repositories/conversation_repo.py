"""Conversation repository — encapsulates all Conversation ORM queries.

Replaces inline ``session.execute(select(Conversation)...)`` patterns
in ``api/chat.py``, ``api/gdpr.py``, and ``services/chat_service.py``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.conversation_document import ConversationDocument
from app.models.document import Document
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository for Conversation operations."""

    model_cls = Conversation

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ── User-scoped lookups ──────────────────────────────────

    async def find_by_id_and_user(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> Conversation | None:
        """Find a conversation by ID, scoped to the owning user."""
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        active_only: bool = True,
    ) -> tuple[list[Conversation], int]:
        """Paginated list of conversations for a user with linked document info.

        Uses a single JOIN + array_agg query to avoid N+1 loading.
        Returns (conversations, total_count).
        """
        # Total count
        count_stmt = select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
        if active_only:
            count_stmt = count_stmt.where(Conversation.is_active.is_(True))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Items with joined document data
        result = await self.session.execute(
            select(
                Conversation,
                func.array_agg(
                    ConversationDocument.document_id,
                    order_by=ConversationDocument.document_id,
                ).label("doc_ids"),
                func.array_agg(
                    Document.title,
                    order_by=ConversationDocument.document_id,
                ).label("doc_titles"),
            )
            .outerjoin(
                ConversationDocument,
                ConversationDocument.conversation_id == Conversation.id,
            )
            .outerjoin(Document, Document.id == ConversationDocument.document_id)
            .where(Conversation.user_id == user_id)
            .group_by(Conversation.id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )
        rows = result.all()
        # The rows are raw tuples because of the array_agg columns
        return list(rows), total

    async def list_all_by_user(self, user_id: uuid.UUID) -> list[Conversation]:
        """Get ALL conversations for a user (no pagination). Used by GDPR export."""
        result = await self.session.execute(
            select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.created_at)
        )
        return list(result.scalars().all())

    # ── Document linking ─────────────────────────────────────

    async def get_document_links(self, conversation_id: uuid.UUID) -> list[ConversationDocument]:
        """Get all document links for a conversation."""
        result = await self.session.execute(
            select(ConversationDocument).where(
                ConversationDocument.conversation_id == conversation_id,
            )
        )
        return list(result.scalars().all())

    async def get_document_ids_and_titles(
        self, conversation_id: uuid.UUID
    ) -> tuple[list[uuid.UUID], list[str]]:
        """Get document IDs and titles linked to a conversation."""
        links = await self.get_document_links(conversation_id)
        doc_ids = [link.document_id for link in links]

        doc_titles: list[str] = []
        if doc_ids:
            doc_result = await self.session.execute(
                select(Document.title).where(Document.id.in_(doc_ids))
            )
            doc_titles = [row[0] for row in doc_result.all()]

        return doc_ids, doc_titles

    async def add_document_link(self, conversation_id: uuid.UUID, document_id: uuid.UUID) -> None:
        """Create a junction record linking a conversation to a document."""
        link = ConversationDocument(
            conversation_id=conversation_id,
            document_id=document_id,
        )
        self.session.add(link)

    async def get_document_ids_for_conv(self, conversation_id: uuid.UUID) -> list[str]:
        """Get document IDs for a conversation (as strings, for retrieval)."""
        result = await self.session.execute(
            select(ConversationDocument.document_id).where(
                ConversationDocument.conversation_id == conversation_id,
            )
        )
        return [str(row[0]) for row in result.all()]

    async def delete_all_by_user(self, user_id: uuid.UUID) -> None:
        """Bulk delete all conversations owned by a user (for GDPR account deletion)."""
        from sqlalchemy import delete as sa_delete
        await self.session.execute(
            sa_delete(Conversation).where(Conversation.user_id == user_id)
        )
