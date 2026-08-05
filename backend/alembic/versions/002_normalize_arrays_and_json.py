"""Replace ARRAY(UUID) document_ids with junction table, JSON citations with normalized table.

- Creates ``conversation_documents`` junction table
- Creates ``citation_records`` normalized table
- Drops ``conversations.document_ids`` ARRAY column
- Drops ``messages.citations`` JSON column
- Adds composite indexes on ``documents(user_id, created_at)``
- Adds composite index on ``conversations(user_id, updated_at)``
- Adds ``tsvector`` GIN index on ``chunks.content``
- Migrates existing data from JSON/ARRAY columns

Revision ID: 002
Revises: 001
Create Date: 2026-07-28
"""

from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # ── 1. Create conversation_documents junction table ──
    op.create_table(
        "conversation_documents",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conversation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("conversation_id", "document_id", name="uq_conv_doc"),
    )

    # Migrate existing data from conversations.document_ids ARRAY
    conv_rows = connection.execute(
        text(
            "SELECT id, document_ids FROM conversations WHERE document_ids IS NOT NULL AND document_ids != '{}'"
        )
    ).fetchall()

    for row in conv_rows:
        conv_id, doc_ids = row
        if doc_ids:
            for doc_id in doc_ids:
                try:
                    connection.execute(
                        text("""
                            INSERT INTO conversation_documents (id, conversation_id, document_id, created_at)
                            VALUES (gen_random_uuid(), :conv_id, :doc_id, now())
                            ON CONFLICT (conversation_id, document_id) DO NOTHING
                        """),
                        {"conv_id": conv_id, "doc_id": doc_id},
                    )
                except Exception:
                    pass  # Skip invalid document IDs silently

    # ── 2. Create citation_records table ──
    op.create_table(
        "citation_records",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("chunk_id", sa.String(255), nullable=True),
        sa.Column("document_id", sa.String(255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), default=0.0, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Migrate existing data from messages.citations JSON
    msg_rows = connection.execute(
        text(
            "SELECT id, citations FROM messages WHERE citations IS NOT NULL AND citations::text != 'null'"
        )
    ).fetchall()

    for row in msg_rows:
        msg_id, citations_json = row
        if citations_json:
            if isinstance(citations_json, str):
                citations_data = json.loads(citations_json)
            elif hasattr(citations_json, "__len__"):
                # Already a Python list (SQLAlchemy deserialized it)
                citations_data = citations_json
            else:
                citations_data = []

            if citations_data:
                for cit in citations_data:
                    if isinstance(cit, dict):
                        connection.execute(
                            text("""
                                INSERT INTO citation_records (id, message_id, chunk_id, document_id, text, page_number, score, created_at)
                                VALUES (gen_random_uuid(), :msg_id, :chunk_id, :doc_id, :text, :page_num, :score, now())
                            """),
                            {
                                "msg_id": msg_id,
                                "chunk_id": cit.get("chunk_id"),
                                "doc_id": cit.get("document_id"),
                                "text": cit.get("text", ""),
                                "page_num": cit.get("page_number"),
                                "score": cit.get("score", 0.0),
                            },
                        )

    # ── 3. Drop old columns ──
    with op.batch_alter_table("conversations") as batch_op:
        batch_op.drop_column("document_ids")

    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_column("citations")

    # ── 4. Add composite indexes ──
    op.create_index(
        "idx_documents_user_created",
        "documents",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_conversations_user_updated",
        "conversations",
        ["user_id", sa.text("updated_at DESC")],
    )
    op.create_index(
        "idx_messages_conversation_created",
        "messages",
        ["conversation_id", sa.text("created_at ASC")],
    )

    # ── 5. Add tsvector GIN index for full-text search on chunks.content ──
    op.execute(
        "CREATE INDEX idx_chunks_content_tsv ON chunks "
        "USING GIN (to_tsvector('english', coalesce(content, '')))"
    )


def downgrade() -> None:
    # Remove indexes
    op.drop_index("idx_chunks_content_tsv", table_name="chunks")
    op.drop_index("idx_messages_conversation_created", table_name="messages")
    op.drop_index("idx_conversations_user_updated", table_name="conversations")
    op.drop_index("idx_documents_user_created", table_name="documents")

    # Restore JSON citations column
    op.add_column("messages", sa.Column("citations", sa.JSON(), nullable=True))

    # Restore ARRAY document_ids column
    from sqlalchemy.dialects.postgresql import ARRAY

    op.add_column(
        "conversations",
        sa.Column(
            "document_ids", ARRAY(UUID(as_uuid=True)), default=list, nullable=True
        ),
    )

    # Migrate data back (simplified: aggregate citation_records into JSON)
    connection = op.get_bind()
    cit_rows = connection.execute(
        text(
            "SELECT message_id, json_agg(json_build_object('chunk_id', chunk_id, 'document_id', document_id, 'text', text, 'page_number', page_number, 'score', score) ORDER BY created_at) AS citations FROM citation_records GROUP BY message_id"
        )
    ).fetchall()

    for row in cit_rows:
        msg_id, citations_json = row
        connection.execute(
            text("UPDATE messages SET citations = :citations WHERE id = :msg_id"),
            {"citations": citations_json, "msg_id": msg_id},
        )

    # Aggregate conversation_documents into ARRAY
    doc_rows = connection.execute(
        text(
            "SELECT conversation_id, array_agg(document_id ORDER BY created_at) AS doc_ids FROM conversation_documents GROUP BY conversation_id"
        )
    ).fetchall()

    for row in doc_rows:
        conv_id, doc_ids = row
        connection.execute(
            text(
                "UPDATE conversations SET document_ids = :doc_ids WHERE id = :conv_id"
            ),
            {"doc_ids": doc_ids, "conv_id": conv_id},
        )

    op.drop_table("citation_records")
    op.drop_table("conversation_documents")
