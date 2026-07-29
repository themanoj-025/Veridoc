"""Admin analytics API routes — surfaces usage_logs data (D12)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.usage_log import UsageLog
from app.services.response_cache import get_response_cache

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class AdminAnalyticsResponse(BaseModel):
    total_queries: int
    total_users: int
    total_documents: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    queries_today: int
    queries_this_week: int
    most_used_model: str | None
    avg_estimated_cost: float | None
    top_documents: list[dict]
    recent_queries: list[dict]
    daily_query_volume: list[dict]


@router.get("/analytics", operation_id="admin_analytics")
async def get_analytics(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get admin analytics from the usage_logs table.

    Returns query volume, latency, popular documents, and cost estimates.
    Only accessible by the admin user (first registered user or user with
    specific email). For a full multi-admin system, add a proper admin role.
    """
    # Simple admin check: only the first registered user can access
    first_user_result = await session.execute(
        select(User).order_by(User.created_at).limit(1)
    )
    first_user = first_user_result.scalar_one_or_none()

    if not first_user or first_user.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    import structlog
    logger = structlog.get_logger(__name__)
    logger.info("admin.analytics_accessed", user_id=str(user.id)[:8])

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Total query count
    total_result = await session.execute(select(func.count(UsageLog.id)))
    total_queries = total_result.scalar() or 0

    # Total users
    user_result = await session.execute(select(func.count(User.id)))
    total_users = user_result.scalar() or 0

    # Total documents (across all users)
    from app.models.document import Document
    doc_result = await session.execute(select(func.count(Document.id)))
    total_documents = doc_result.scalar() or 0

    # Average latency
    latency_result = await session.execute(
        select(func.avg(UsageLog.response_time_ms))
    )
    avg_latency_ms = float(latency_result.scalar() or 0)

    # Percentile latencies (using Postgres percentile functions)
    p50_result = await session.execute(
        select(func.percentile_cont(0.5).within_group(UsageLog.response_time_ms))
    )
    p50_latency_ms = float(p50_result.scalar() or 0)

    p95_result = await session.execute(
        select(func.percentile_cont(0.95).within_group(UsageLog.response_time_ms))
    )
    p95_latency_ms = float(p95_result.scalar() or 0)

    # Queries today
    today_result = await session.execute(
        select(func.count(UsageLog.id)).where(UsageLog.created_at >= today_start)
    )
    queries_today = today_result.scalar() or 0

    # Queries this week
    week_result = await session.execute(
        select(func.count(UsageLog.id)).where(UsageLog.created_at >= week_start)
    )
    queries_this_week = week_result.scalar() or 0

    # Most used model
    model_result = await session.execute(
        select(UsageLog.model_used, func.count(UsageLog.model_used).label("cnt"))
        .group_by(UsageLog.model_used)
        .order_by(text("cnt DESC"))
        .limit(1)
    )
    most_used_row = model_result.first()
    most_used_model = str(most_used_row[0]) if most_used_row else None

    # Average estimated cost
    cost_result = await session.execute(
        select(func.avg(UsageLog.estimated_cost)).where(UsageLog.estimated_cost.isnot(None))
    )
    avg_estimated_cost = float(cost_result.scalar() or 0)

    # Top documents (most cited)
    from app.models.citation_record import CitationRecord
    top_docs_result = await session.execute(
        select(
            CitationRecord.document_id,
            func.count(CitationRecord.id).label("citation_count"),
        )
        .group_by(CitationRecord.document_id)
        .order_by(text("citation_count DESC"))
        .limit(10)
    )
    top_documents = []
    for row in top_docs_result.all():
        doc_id = str(row.document_id) if row.document_id else "unknown"
        top_documents.append({
            "document_id": doc_id,
            "citation_count": row.citation_count,
        })

    # Recent queries
    recent_result = await session.execute(
        select(UsageLog)
        .order_by(UsageLog.created_at.desc())
        .limit(20)
    )
    recent_logs = recent_result.scalars().all()
    recent_queries = [
        {
            "query": log.query[:100],
            "latency_ms": log.response_time_ms,
            "model_used": log.model_used,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in recent_logs
    ]

    # Daily query volume (last 7 days)
    daily_result = await session.execute(
        select(
            func.date_trunc("day", UsageLog.created_at).label("day"),
            func.count(UsageLog.id).label("count"),
        )
        .where(UsageLog.created_at >= week_start)
        .group_by(text("day"))
        .order_by(text("day"))
    )
    daily_query_volume = [
        {"date": str(row[0]), "count": row[1]}
        for row in daily_result.all()
    ]

    await session.close()
    return AdminAnalyticsResponse(
        total_queries=total_queries,
        total_users=total_users,
        total_documents=total_documents,
        avg_latency_ms=round(avg_latency_ms, 2),
        p50_latency_ms=round(p50_latency_ms, 2),
        p95_latency_ms=round(p95_latency_ms, 2),
        queries_today=queries_today,
        queries_this_week=queries_this_week,
        most_used_model=most_used_model,
        avg_estimated_cost=round(avg_estimated_cost, 6) if avg_estimated_cost else None,
        top_documents=top_documents,
        recent_queries=recent_queries,
        daily_query_volume=daily_query_volume,
    )


# ── Cache Stats (C2) ─────────────────────────────────────


class CacheStatsResponse(BaseModel):
    hits: int
    misses: int
    total: int
    hit_rate: float
    memory_entries: int
    redis_available: bool
    enabled: bool
    ttl_seconds: int


@router.get("/cache-stats", operation_id="admin_cache_stats")
async def get_cache_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get response cache hit/miss statistics (C2).

    Returns hit rate, total requests, and Redis availability.
    Only accessible by the admin user (first registered user).
    """
    # Admin check: only the first registered user can access
    first_user_result = await session.execute(
        select(User).order_by(User.created_at).limit(1)
    )
    first_user = first_user_result.scalar_one_or_none()

    if not first_user or first_user.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    import structlog
    logger = structlog.get_logger(__name__)

    cache = get_response_cache()
    stats = cache.stats

    logger.info(
        "admin.cache_stats_accessed",
        user_id=str(user.id)[:8],
        hit_rate=stats["hit_rate"],
    )

    await session.close()
    return CacheStatsResponse(
        hits=stats["hits"],
        misses=stats["misses"],
        total=stats["total"],
        hit_rate=stats["hit_rate"],
        memory_entries=stats["memory_entries"],
        redis_available=stats["redis_available"],
        enabled=stats["enabled"],
        ttl_seconds=stats["ttl_seconds"],
    )


# ── Feedback Queue (D1) ──────────────────────────────────


class FeedbackQueueResponse(BaseModel):
    total: int
    thumbs_down: int
    thumbs_up: int
    avg_faithfulness: float
    recent_entries: list[dict]


@router.get("/feedback-queue", operation_id="admin_feedback_queue")
async def get_feedback_queue(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Get continuous feedback queue stats and recent entries (D1).

    Returns the count of thumbs-up/down entries, average faithfulness,
    and the most recent entries for review.
    Only accessible by the admin user.
    """
    # Admin check: only the first registered user can access
    first_user_result = await session.execute(
        select(User).order_by(User.created_at).limit(1)
    )
    first_user = first_user_result.scalar_one_or_none()

    if not first_user or first_user.id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    import structlog
    logger = structlog.get_logger(__name__)

    # Load the feedback queue from disk
    eval_dir = Path(__file__).resolve().parent.parent.parent.parent / "eval"
    feedback_file = eval_dir / "continuous_feedback.json"

    queue: list[dict] = []
    if feedback_file.exists():
        try:
            queue = json.loads(feedback_file.read_text())
        except (json.JSONDecodeError, Exception):
            queue = []

    total = len(queue)
    thumbs_down = sum(1 for e in queue if e.get("feedback") == "down")
    thumbs_up = sum(1 for e in queue if e.get("feedback") == "up")

    faith_scores = [
        e.get("faithfulness_score", 0) or 0
        for e in queue
        if e.get("faithfulness_score") is not None
    ]
    avg_faithfulness = sum(faith_scores) / max(len(faith_scores), 1)

    # Most recent 20 entries (redacted user_id)
    recent_entries = [
        {
            "feedback": e.get("feedback"),
            "question": e.get("question", "")[:100],
            "answer": e.get("answer", "")[:200],
            "faithfulness_score": e.get("faithfulness_score"),
            "timestamp": e.get("timestamp"),
        }
        for e in queue[-20:]
    ]
    recent_entries.reverse()

    logger.info(
        "admin.feedback_queue_accessed",
        user_id=str(user.id)[:8],
        queue_size=total,
    )

    await session.close()
    return FeedbackQueueResponse(
        total=total,
        thumbs_down=thumbs_down,
        thumbs_up=thumbs_up,
        avg_faithfulness=round(avg_faithfulness, 4),
        recent_entries=recent_entries,
    )
