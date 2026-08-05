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

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
