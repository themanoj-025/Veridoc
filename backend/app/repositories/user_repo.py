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

    async def find_by_role(self, role: str) -> list[User]:
        """Find all users with a specific role."""
        result = await self.session.execute(
            select(User).where(User.role == role)
        )
        return list(result.scalars().all())

    async def find_by_verification_token(self, token: str) -> User | None:
        """Find a user by email verification token."""
        result = await self.session.execute(
            select(User).where(User.verification_token == token)
        )
        return result.scalar_one_or_none()

    async def find_by_reset_token(self, token: str) -> User | None:
        """Find a user by password reset token."""
        result = await self.session.execute(
            select(User).where(User.reset_token == token)
        )
        return result.scalar_one_or_none()

    async def count_all(self) -> int:
        """Count all registered users."""
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar() or 0
