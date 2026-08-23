"""Feedback API routes — thumbs up/down with continuous evaluation loop."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class FeedbackRequest(BaseModel):
    message_id: str
    conversation_id: str
    feedback: str  # "up" or "down"
    question: str
    answer: str
    citations: list[dict] | None = None
    faithfulness_score: float | None = None


@router.post("/feedback", operation_id="chat_feedback")
async def submit_feedback(
    body: FeedbackRequest,
    user: User = Depends(get_current_user),
):
    """Submit thumbs up/down feedback for a chat response.

    Thumbs-down responses are automatically appended to the continuous
    feedback queue (``eval/continuous_feedback.json``) so they can be
    reviewed and promoted into the gold Q&A set.

    Thumbs-up responses increment a simple count (for analytics).
    """
    import structlog

    logger = structlog.get_logger(__name__)

    if body.feedback not in ("up", "down"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="feedback must be 'up' or 'down'",
        )

    feedback_entry = {
        "feedback": body.feedback,
        "user_id": str(user.id),
        "message_id": body.message_id,
        "conversation_id": body.conversation_id,
        "question": body.question,
        "answer": body.answer,
        "citations": body.citations or [],
        "faithfulness_score": body.faithfulness_score,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }

    if body.feedback == "down":
        # Append to continuous feedback queue for later review
        try:
            eval_dir = Path(settings.data_dir).parent / "eval"
            eval_dir.mkdir(parents=True, exist_ok=True)
            feedback_file = eval_dir / "continuous_feedback.json"

            queue = []
            if feedback_file.exists():
                try:
                    queue = json.loads(feedback_file.read_text())
                except (json.JSONDecodeError, OSError):
                    queue = []

            queue.append(feedback_entry)
            feedback_file.write_text(json.dumps(queue, indent=2, default=str))
            logger.info(
                "feedback.appended_to_queue",
                queue_size=len(queue),
                user_id=str(user.id)[:8],
            )
        except (OSError, ValueError) as e:
            logger.warning("feedback.queue_write_failed", error=str(e))

    return {
        "status": "ok",
        "feedback": body.feedback,
    }
