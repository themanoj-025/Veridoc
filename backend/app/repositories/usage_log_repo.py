"""UsageLog repository — encapsulates UsageLog analytics queries.

Replaces inline ``session.execute(select(UsageLog)...)`` patterns
in ``api/admin.py`` and ``api/gdpr.py``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, text, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_log import UsageLog
from app.repositories.base import BaseRepository


class UsageLogRepository(BaseRepository[UsageLog]):
    """Repository for UsageLog analytics queries."""

    model_cls = UsageLog

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_total_queries(self) -> int:
        """Total query count across all users."""
        result = await self.session.execute(select(func.count(UsageLog.id)))
        return result.scalar() or 0

    async def get_avg_latency(self) -> float:
        """Average response time across all queries."""
        result = await self.session.execute(select(func.avg(UsageLog.response_time_ms)))
        return float(result.scalar() or 0)

    async def get_percentile_latency(self, percentile: float) -> float:
        """Get a latency percentile using Postgres percentile_cont."""
        result = await self.session.execute(
            select(
                func.percentile_cont(percentile).within_group(UsageLog.response_time_ms)
            )
        )
        return float(result.scalar() or 0)

    async def get_queries_since(self, since: datetime) -> int:
        """Count queries created after a given timestamp."""
        result = await self.session.execute(
            select(func.count(UsageLog.id)).where(UsageLog.created_at >= since)
        )
        return result.scalar() or 0

    async def get_most_used_model(self) -> str | None:
        """Get the most frequently used LLM model name."""
        result = await self.session.execute(
            select(UsageLog.model_used, func.count(UsageLog.model_used).label("cnt"))
            .group_by(UsageLog.model_used)
            .order_by(text("cnt DESC"))
            .limit(1)
        )
        row = result.first()
        return str(row[0]) if row else None

    async def get_avg_cost(self) -> float:
        """Average estimated cost per query where cost is tracked."""
        result = await self.session.execute(
            select(func.avg(UsageLog.estimated_cost)).where(
                UsageLog.estimated_cost.isnot(None)
            )
        )
        return float(result.scalar() or 0)

    async def get_recent_queries(self, limit: int = 20) -> list[UsageLog]:
        """Most recent queries ordered by created_at desc."""
        result = await self.session.execute(
            select(UsageLog).order_by(UsageLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def get_daily_volume(self, since: datetime) -> list[tuple]:
        """Query volume grouped by day."""
        result = await self.session.execute(
            select(
                func.date_trunc("day", UsageLog.created_at).label("day"),
                func.count(UsageLog.id).label("count"),
            )
            .where(UsageLog.created_at >= since)
            .group_by(text("day"))
            .order_by(text("day"))
        )
        return result.all()

    async def delete_all_by_user(self, user_id: uuid.UUID) -> None:
        """Bulk delete all usage logs for a user (for GDPR account deletion)."""
        await self.session.execute(
            sa_delete(UsageLog).where(UsageLog.user_id == user_id)
        )
