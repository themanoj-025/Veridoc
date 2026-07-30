"""User repository — encapsulates all User ORM queries.

Replaces inline ``session.execute(select(User)...)`` patterns
in ``api/auth.py`` and ``api/admin.py``.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""

    model_cls = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def find_by_email(self, email: str) -> User | None:
        """Find a user by email address."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def find_by_id(self, id: uuid.UUID) -> User | None:
        """Find a user by primary key."""
        result = await self.session.execute(
            select(User).where(User.id == id)
        )
        return result.scalar_one_or_none()

    async def find_first_registered(self) -> User | None:
        """Find the first registered user (admin heuristic)."""
        result = await self.session.execute(
            select(User).order_by(User.created_at).limit(1)
        )
        return result.scalar_one_or_none()

    async def count_all(self) -> int:
        """Count all registered users."""
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar() or 0
