"""Email sender abstraction — logs to console in dev mode, swaps to real SMTP in production (F4).

Currently implements a log-to-console sender that outputs the email content
as structured logs. When a real SMTP config is provided, a real sender can
be swapped in via the same interface.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


async def send_verification_email(email: str, token: str) -> None:
    """Send an email verification link.

    In dev mode, logs the token to console. In production, would send
    a real email via SMTP or a transactional email service.
    """
    verification_url = f"{_get_base_url()}/verify-email?token={token}"
    logger.info(
        "email.verification_sent",
        to=email,
        token_prefix=token[:8],
        verification_url=verification_url,
    )


async def send_password_reset_email(email: str, token: str) -> None:
    """Send a password reset link.

    In dev mode, logs the token to console. In production, would send
    a real email via SMTP or a transactional email service.
    """
    reset_url = f"{_get_base_url()}/reset-password?token={token}"
    logger.info(
        "email.password_reset_sent",
        to=email,
        token_prefix=token[:8],
        reset_url=reset_url,
    )


def _get_base_url() -> str:
    """Get the base URL for constructing email links."""
    # Default to localhost; override with FRONTEND_URL env var if set
    import os
    return os.environ.get("FRONTEND_URL", "http://localhost:3000")


def get_dev_email_sender():
    """Return the current email sender implementation.

    Currently returns the dev-mode console logger. When SMTP is configured,
    this would return a real email sender.
    """
    return {
        "send_verification": send_verification_email,
        "send_password_reset": send_password_reset_email,
    }
