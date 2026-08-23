"""Admin analytics API routes — uses repositories for data access."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models.admin_audit_log import AdminAuditLog
from app.models.citation_record import CitationRecord
from app.models.user import User
from app.repositories import DocumentRepository, UsageLogRepository, UserRepository
from app.services.response_cache import get_response_cache

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ── F8: Admin audit log helper ─────────────────────────


async def _log_admin_action(
    session,
    actor_id: uuid.UUID | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict | None = None,
) -> None:
    """Record an admin action to the append-only audit log."""
    log = AdminAuditLog(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    session.add(log)
    await session.flush()


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
    """Get admin analytics from the usage_logs table."""  # F3: RBAC admin check — explicit role column
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    import structlog

    logger = structlog.get_logger(__name__)

    # F8: Log admin action to audit log
    await _log_admin_action(
        session, user.id, "analytics_accessed", "admin", None, {"method": "GET"}
    )

    user_repo = UserRepository(session)
    doc_repo = DocumentRepository(session)
    log_repo = UsageLogRepository(session)

    logger.info("admin.analytics_accessed", user_id=str(user.id)[:8])

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    # Gather analytics via repositories
    total_queries = await log_repo.get_total_queries()
    total_users = await user_repo.count_all()
    total_documents = await doc_repo.count_all()
    avg_latency_ms = await log_repo.get_avg_latency()
    p50_latency_ms = await log_repo.get_percentile_latency(0.5)
    p95_latency_ms = await log_repo.get_percentile_latency(0.95)
    queries_today = await log_repo.get_queries_since(today_start)
    queries_this_week = await log_repo.get_queries_since(week_start)
    most_used_model = await log_repo.get_most_used_model()
    avg_estimated_cost = await log_repo.get_avg_cost()

    # Top documents (most cited)
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
        top_documents.append(
            {
                "document_id": doc_id,
                "citation_count": row.citation_count,
            }
        )

    # Recent queries
    recent_logs = await log_repo.get_recent_queries(limit=20)
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
    daily_rows = await log_repo.get_daily_volume(since=week_start)
    daily_query_volume = [{"date": str(row[0]), "count": row[1]} for row in daily_rows]

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
    """Get response cache hit/miss statistics (C2)."""
    # F3: RBAC admin check
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    import structlog

    logger = structlog.get_logger(__name__)

    # F8: Log admin action
    await _log_admin_action(
        session, user.id, "cache_stats_accessed", "admin", None, None
    )

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
    """Get continuous feedback queue stats and recent entries (D1)."""
    # F3: RBAC admin check
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    import structlog

    logger = structlog.get_logger(__name__)

    # F8: Log admin action
    await _log_admin_action(
        session, user.id, "feedback_queue_accessed", "admin", None, None
    )

    # Load the feedback queue from disk
    eval_dir = Path(__file__).resolve().parent.parent.parent.parent / "eval"
    feedback_file = eval_dir / "continuous_feedback.json"

    queue: list[dict] = []
    if feedback_file.exists():
        try:
            queue = json.loads(feedback_file.read_text())
        except (json.JSONDecodeError, OSError):
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
