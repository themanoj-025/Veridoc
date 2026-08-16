"""Add ocr_used column to chunks table for per-chunk OCR tracking (D13).

Previously, the ``ocr_used`` flag was only stored at the document level.
This migration adds it per-chunk so the frontend can surface the source
type (OCR vs. native text extraction) for individual chunks, enabling
the OCR confidence indicator in the citation UI.

Revision ID: 003
Revises: 002
Create Date: 2026-07-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()

    # Add the column (nullable at first so we can backfill)
    op.add_column(
        "chunks",
        sa.Column("ocr_used", sa.Boolean(), nullable=True, default=False),
    )

    # Backfill: set ocr_used = True for chunks whose document used OCR
    connection.execute(
        text(
            """
            UPDATE chunks
            SET ocr_used = TRUE
            FROM documents
            WHERE chunks.document_id = documents.id
              AND documents.ocr_used = TRUE
        """
        )
    )

    # Set remaining to False
    connection.execute(
        text(
            """
            UPDATE chunks
            SET ocr_used = FALSE
            WHERE ocr_used IS NULL
        """
        )
    )

    # Now make it non-nullable
    with op.batch_alter_table("chunks") as batch_op:
        batch_op.alter_column(
            "ocr_used", nullable=False, server_default=sa.text("false")
        )


def downgrade() -> None:
    with op.batch_alter_table("chunks") as batch_op:
        batch_op.drop_column("ocr_used")
