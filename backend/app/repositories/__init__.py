"""Repository layer — encapsulates database access behind injectable, testable classes.

Usage::

    from app.repositories import DocumentRepository

    repo = DocumentRepository(session)
    doc = await repo.find_by_id_and_user(doc_id, user_id)
"""

from app.repositories.document_repo import DocumentRepository
from app.repositories.conversation_repo import ConversationRepository
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.user_repo import UserRepository
from app.repositories.usage_log_repo import UsageLogRepository

__all__ = [
    "DocumentRepository",
    "ConversationRepository",
    "ChunkRepository",
    "UserRepository",
    "UsageLogRepository",
]
