"""Add verification_token_expiry column to users.

F4 (complete): the master requirement asks for verification_token/reset_token
fields *with expiry*. reset_token_expiry already exists; this adds the
matching expiry for verification tokens so an old verification link cannot be
replayed forever.

Revision ID: 005
Revises: 004
Create Date: 2026-07-31
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "verification_token_expiry", sa.DateTime(timezone=True), nullable=True
        ),
    )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("verification_token_expiry")
