"""Structured logging configuration with ``structlog``.

Correlation IDs (``request_id``, ``user_id``, ``conversation_id``,
``document_id``) are bound to the current async context via
``structlog.contextvars.bind_contextvars()`` and appear in every log
line emitted during the request.

Usage in service modules — replace::

    import logging
    logger = logging.getLogger(__name__)

with::

    import structlog
    logger = structlog.get_logger(__name__)

Then any log call (``logger.info(...)``, ``logger.warning(...)``, etc.)
automatically includes the correlation IDs bound to the current context.
"""

from __future__ import annotations

import logging
import uuid

import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer, TimeStamper


def bind_log_context(**kwargs: object) -> None:
    """Bind key-value pairs to the current async log context.

    Every log call made after this will include these keys.  Typical
    usage from middleware or service code::

        bind_log_context(conversation_id=str(conv.id))
        bind_log_context(user_id=str(user.id))
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_log_context() -> None:
    """Clear all bound context variables for the current async context."""
    structlog.contextvars.clear_contextvars()


def _add_correlation_ids(
    logger: logging.Logger,
    method_name: str,
    event_dict: dict,
) -> dict:
    """Processor that ensures correlation ID keys exist in every log event.

    This processor runs AFTER ``merge_contextvars``, so the context vars
    are already in *event_dict*.  We only need to ``setdefault`` the keys
    so every log line has a consistent shape.
    """
    event_dict.setdefault("request_id", None)
    event_dict.setdefault("user_id", None)
    event_dict.setdefault("conversation_id", None)
    event_dict.setdefault("document_id", None)
    return event_dict


def configure_logging(env: str = "development", log_level: str = "INFO") -> None:
    """Configure structlog and the stdlib logging bridge.

    Call once at application startup:

    * **development** → colored console output (human-readable).
    * **production** or other → JSON lines (machine-parseable, ideal for
      log aggregators like Loki, Datadog, CloudWatch).
    """
    is_dev = env == "development"

    shared_processors: list[object] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.contextvars.merge_contextvars,
        _add_correlation_ids,
    ]

    if is_dev:
        renderer: object = ConsoleRenderer()
    else:
        renderer = JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            renderer,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Ensure standard-library loggers also respect our level
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
        force=True,
    )


def generate_request_id() -> str:
    """Generate a short, unique request identifier."""
    return uuid.uuid4().hex[:12]
