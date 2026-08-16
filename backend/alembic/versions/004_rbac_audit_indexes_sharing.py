"""Add RBAC role column, composite indexes, admin audit log, email verification fields, sharing & API keys tables.

This migration consolidates several schema changes:

- F3: Add ``role`` column to ``users`` (``user``/``admin``), backfill first user as admin
- F5: Remove unused ``google_id``/``github_id`` columns from ``users``
- F8: Create ``admin_audit_log`` table (append-only)
- F9: Add composite indexes ``(user_id, status)`` on documents, ``(user_id, is_active)`` on conversations
- F4: Add ``verification_token``, ``reset_token``, ``reset_token_expiry`` columns to ``users``
- F20: Create ``document_shares`` and ``api_keys`` tables
- G4: Add ``secret_rotated_at`` to ``users`` (or config — we store per-user for now)
- G2: Add ``prompt_version`` column to ``messages`` for prompt version tracking

Revision ID: 004
Revises: 003
Create Date: 2026-07-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()

    # ── F3: Add role column to users ──
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=True, server_default="user"),
    )
    # Backfill first registered user as admin
    connection.execute(
        text(
            """
            UPDATE users
            SET role = 'admin'
            WHERE id = (
                SELECT id FROM users ORDER BY created_at ASC LIMIT 1
            )
        """
        )
    )
    # Make role non-nullable
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", nullable=False, server_default=sa.text("'user'"))

    # ── F4: Add email verification & password reset columns ──
    op.add_column(
        "users",
        sa.Column("verification_token", sa.String(255), nullable=True, unique=True),
    )
    op.add_column(
        "users",
        sa.Column("reset_token", sa.String(255), nullable=True, unique=True),
    )
    op.add_column(
        "users",
        sa.Column("reset_token_expiry", sa.DateTime(timezone=True), nullable=True),
    )

    # ── F5: Remove unused OAuth columns ──
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("google_id")
        batch_op.drop_column("github_id")

    # ── G4: Add secret_rotated_at to settings / users ──
    # We store it per-user on config for now; no migration needed at schema level
    # since it's a config value, not a column. The startup warning checks a
    # config timestamp. No schema change needed.

    # ── F8: Create admin_audit_log table ──
    op.create_table(
        "admin_audit_log",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "actor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(255), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=True),
        sa.Column("target_id", sa.String(255), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_admin_audit_actor", "admin_audit_log", ["actor_id"])
    op.create_index("idx_admin_audit_action", "admin_audit_log", ["action"])
    op.create_index(
        "idx_admin_audit_created", "admin_audit_log", [sa.text("created_at DESC")]
    )

    # ── F9: Add composite indexes ──
    op.create_index("idx_documents_user_status", "documents", ["user_id", "status"])
    op.create_index(
        "idx_conversations_user_active", "conversations", ["user_id", "is_active"]
    )

    # ── F20: Create document_shares table ──
    op.create_table(
        "document_shares",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "shared_with_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("permission", sa.String(20), nullable=False, server_default="read"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("document_id", "shared_with_user_id", name="uq_doc_share"),
    )
    op.create_index("idx_doc_shares_document", "document_shares", ["document_id"])
    op.create_index("idx_doc_shares_user", "document_shares", ["shared_with_user_id"])

    # ── F20: Create api_keys table ──
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key_prefix", sa.String(8), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_limit_per_minute", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_api_keys_user", "api_keys", ["user_id"])
    op.create_index("idx_api_keys_prefix", "api_keys", ["key_prefix"], unique=True)

    # ── G2: Add prompt_version to messages ──
    op.add_column(
        "messages",
        sa.Column("prompt_version", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    # Remove prompt_version from messages
    with op.batch_alter_table("messages") as batch_op:
        batch_op.drop_column("prompt_version")

    # Drop api_keys table
    op.drop_table("api_keys")

    # Drop document_shares table
    op.drop_table("document_shares")

    # Drop composite indexes
    op.drop_index("idx_conversations_user_active", table_name="conversations")
    op.drop_index("idx_documents_user_status", table_name="documents")

    # Drop admin_audit_log table
    op.drop_table("admin_audit_log")

    # Restore OAuth columns
    op.add_column(
        "users",
        sa.Column("google_id", sa.String(255), nullable=True, unique=True),
    )
    op.add_column(
        "users",
        sa.Column("github_id", sa.String(255), nullable=True, unique=True),
    )

    # Drop reset_token_expiry
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("reset_token_expiry")
        batch_op.drop_column("reset_token")
        batch_op.drop_column("verification_token")

    # Drop role column
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("role")
