"""Base repository — abstract common SQLAlchemy async query patterns.

All entity repositories inherit from this class to reduce boilerplate
and provide a consistent, testable interface for database access.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelT = TypeVar("ModelT", bound=DeclarativeBase)


class BaseRepository(Generic[ModelT]):
    """Generic repository with common query patterns.

    Usage::

        class DocumentRepository(BaseRepository[Document]):
            model_cls = Document
    """

    model_cls: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Read ─────────────────────────────────────────────────

    async def find_by_id(self, id: uuid.UUID) -> ModelT | None:
        """Find a single entity by primary key."""
        result = await self.session.execute(
            select(self.model_cls).where(getattr(self.model_cls, "id") == id)
        )
        return result.scalar_one_or_none()

    async def find_all(
        self,
        limit: int = 50,
        offset: int = 0,
        order_field: str | None = "created_at",
        order_desc: bool = True,
        **filters: Any,
    ) -> list[ModelT]:
        """Find entities with optional filters, pagination, and ordering."""
        stmt = select(self.model_cls)
        for field_name, value in filters.items():
            column = getattr(self.model_cls, field_name, None)
            if column is not None:
                stmt = stmt.where(column == value)
        if order_field and hasattr(self.model_cls, order_field):
            column = getattr(self.model_cls, order_field)
            stmt = stmt.order_by(column.desc() if order_desc else column.asc())
        stmt = stmt.limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count(self, **filters: Any) -> int:
        """Count entities matching optional filters."""
        stmt = select(func.count(getattr(self.model_cls, "id")))
        for field_name, value in filters.items():
            column = getattr(self.model_cls, field_name, None)
            if column is not None:
                stmt = stmt.where(column == value)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # ── Write ────────────────────────────────────────────────

    async def create(self, entity: ModelT) -> ModelT:
        """Add a new entity to the session and flush."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        """Mark an existing entity as dirty and flush."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Delete an entity from the session."""
        await self.session.delete(entity)
