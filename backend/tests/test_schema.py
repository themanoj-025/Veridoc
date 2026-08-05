"""Tests for database schema — junction tables, relationships, and integrity.

These tests use a **real in-memory SQLite database** (not mocks) so they
actually exercise SQLAlchemy ORM relationship loading, foreign-key
constraints, unique constraints, and cascade delete behavior.

This is a regression suite for the A3 schema changes:
  - ``conversation_documents`` junction table replaces ``conversations.document_ids`` ARRAY
  - ``citation_records`` normalized table replaces ``messages.citations`` JSON column
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import pytest
import pytest_asyncio

from app.core.database import Base
from app.models import (
    User,
    Document,
    Conversation,
    Message,
    ConversationDocument,
    CitationRecord,
)
from app.schemas.chat import MessageResponse, Citation


# ── Fixture: real in-memory SQLite DB ────────────────────


@pytest_asyncio.fixture
async def real_db_session():
    """Create a real in-memory SQLite database, create all tables,
    and yield a session.  Each test gets a fresh database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with factory() as session:
        yield session

    await engine.dispose()


# ── Seed tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_conversation_document_relationship(real_db_session: AsyncSession):
    """Seed test: create user → documents → conversation → junction links →
    message → citation records, then verify every relationship loads correctly.

    This exercises:
      - ``Conversation.document_links`` → ``ConversationDocument``
      - ``ConversationDocument.conversation`` → ``Conversation``
      - ``Message.citation_records`` → ``CitationRecord``
      - ``Conversation.messages`` → ``Message``
      - ``CitationRecord.message`` → ``Message``
      - Cascade delete: deleting a Conversation removes its junction records
    """
    session = real_db_session

    # ── Create user ──────────────────────────────────────
    user = User(
        email="alice@example.com",
        hashed_password="a" * 60,  # placeholder hash (not used for auth here)
        full_name="Alice",
    )
    session.add(user)
    await session.flush()

    # ── Create documents ─────────────────────────────────
    doc1 = Document(
        user_id=user.id,
        title="RAG Paper",
        filename="rag.pdf",
        file_type="pdf",
        file_size=500_000,
        file_path="/tmp/rag.pdf",
    )
    doc2 = Document(
        user_id=user.id,
        title="Legal Contract",
        filename="contract.pdf",
        file_type="pdf",
        file_size=300_000,
        file_path="/tmp/contract.pdf",
    )
    session.add_all([doc1, doc2])
    await session.flush()

    # ── Create conversation ──────────────────────────────
    conv = Conversation(
        user_id=user.id,
        title="Ask about docs",
    )
    session.add(conv)
    await session.flush()

    # ── Link documents via junction table ────────────────
    link1 = ConversationDocument(
        conversation_id=conv.id,
        document_id=doc1.id,
    )
    link2 = ConversationDocument(
        conversation_id=conv.id,
        document_id=doc2.id,
    )
    session.add_all([link1, link2])
    await session.flush()

    # ── Verify junction: conversation → document_links ───
    await session.refresh(conv)
    assert len(conv.document_links) == 2, (
        f"Expected 2 document_links, got {len(conv.document_links)}"
    )
    linked_doc_ids = {link.document_id for link in conv.document_links}
    assert linked_doc_ids == {doc1.id, doc2.id}

    # ── Verify junction: link → conversation (back-populates) ──
    assert link1.conversation is not None
    assert link1.conversation.id == conv.id

    # ── Create assistant message ─────────────────────────
    msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content="Based on the documents, the answer is...",
    )
    session.add(msg)
    await session.flush()

    # ── Add citation records ─────────────────────────────
    cit1 = CitationRecord(
        message_id=msg.id,
        chunk_id="chunk-a1",
        document_id=str(doc1.id),
        text="RAG systems use retrieval-augmented generation.",
        page_number=3,
        score=0.95,
    )
    cit2 = CitationRecord(
        message_id=msg.id,
        chunk_id="chunk-b2",
        document_id=str(doc2.id),
        text="The NDA clause begins on page 5.",
        page_number=5,
        score=0.88,
    )
    session.add_all([cit1, cit2])
    await session.flush()

    # ── Verify citation: message → citation_records ──────
    await session.refresh(msg)
    assert len(msg.citation_records) == 2, (
        f"Expected 2 citation_records, got {len(msg.citation_records)}"
    )
    assert {c.chunk_id for c in msg.citation_records} == {"chunk-a1", "chunk-b2"}
    assert {c.text for c in msg.citation_records} == {
        "RAG systems use retrieval-augmented generation.",
        "The NDA clause begins on page 5.",
    }
    assert {c.score for c in msg.citation_records} == {0.95, 0.88}

    # ── Verify citation: record → message (back-populates) ──
    assert cit1.message is not None
    assert cit1.message.id == msg.id
    assert cit2.message is not None
    assert cit2.message.id == msg.id

    # ── Verify message → conversation (back-populates) ───
    assert msg.conversation is not None
    assert msg.conversation.id == conv.id

    # ── Verify conversation → messages (back-populates) ──
    await session.refresh(conv)
    assert len(conv.messages) == 1, f"Expected 1 message, got {len(conv.messages)}"
    assert conv.messages[0].id == msg.id
    assert conv.messages[0].role == "assistant"

    # ── Verify from_message() factory converts citation records ──
    resp = MessageResponse.from_message(msg)
    assert len(resp.citations) == 2
    assert isinstance(resp.citations[0], Citation)
    assert {c.text for c in resp.citations} == {
        "RAG systems use retrieval-augmented generation.",
        "The NDA clause begins on page 5.",
    }
    assert {c.score for c in resp.citations} == {0.88, 0.95}

    # ── Verify cascade: delete conversation removes junction ──
    count_before = await session.scalar(
        text("SELECT COUNT(*) FROM conversation_documents")
    )
    assert count_before == 2

    await session.delete(conv)
    await session.flush()

    count_after = await session.scalar(
        text("SELECT COUNT(*) FROM conversation_documents")
    )
    assert count_after == 0, "Cascade delete did not remove junction records"

    # Recreate conversation and message for citation cascade check
    conv2 = Conversation(user_id=user.id, title="Restored")
    session.add(conv2)
    await session.flush()

    msg2 = Message(conversation_id=conv2.id, role="assistant", content="Content")
    session.add(msg2)
    await session.flush()

    cit = CitationRecord(
        message_id=msg2.id,
        chunk_id="chunk-x",
        document_id="doc-x",
        text="Text",
    )
    session.add(cit)
    await session.flush()

    # Delete conversation → cascade deletes message → cascade deletes citation
    await session.delete(conv2)
    await session.flush()

    count_citations = await session.scalar(
        text("SELECT COUNT(*) FROM citation_records")
    )
    assert count_citations == 0, "Cascade delete did not remove citation records"


@pytest.mark.asyncio
async def test_conversation_document_unique_constraint(real_db_session: AsyncSession):
    """Verify the unique constraint on ``(conversation_id, document_id)``
    rejects duplicate links."""
    session = real_db_session

    user = User(email="bob@example.com", hashed_password="b" * 60)
    session.add(user)
    await session.flush()

    doc = Document(
        user_id=user.id,
        title="Doc",
        filename="d.txt",
        file_type="txt",
        file_size=100,
        file_path="/tmp/d.txt",
    )
    session.add(doc)
    await session.flush()

    conv = Conversation(user_id=user.id, title="Test Conv")
    session.add(conv)
    await session.flush()

    # First link — should succeed
    session.add(ConversationDocument(conversation_id=conv.id, document_id=doc.id))
    await session.flush()

    # Second link with same pair — should fail unique constraint
    dup = ConversationDocument(conversation_id=conv.id, document_id=doc.id)
    session.add(dup)
    with pytest.raises(IntegrityError):
        await session.flush()

    # Roll back the failed insert so session stays clean
    await session.rollback()


@pytest.mark.asyncio
async def test_message_citation_cascade(real_db_session: AsyncSession):
    """Verify that deleting a Message cascades to its CitationRecords."""
    session = real_db_session

    user = User(email="carol@example.com", hashed_password="c" * 60)
    session.add(user)
    await session.flush()

    conv = Conversation(user_id=user.id, title="Cascade Test")
    session.add(conv)
    await session.flush()

    msg = Message(conversation_id=conv.id, role="assistant", content="Test")
    session.add(msg)
    await session.flush()

    cit = CitationRecord(message_id=msg.id, chunk_id="c1", document_id="d1", text="T")
    session.add(cit)
    await session.flush()

    assert await session.scalar(text("SELECT COUNT(*) FROM citation_records")) == 1

    await session.delete(msg)
    await session.flush()

    assert await session.scalar(text("SELECT COUNT(*) FROM citation_records")) == 0, (
        "Deleting message did not cascade to citation_records"
    )
