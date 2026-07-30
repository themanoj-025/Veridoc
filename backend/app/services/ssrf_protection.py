"""SSRF protection and virus-scanning hooks for document uploads (F7).

Currently provides:
- SSRF guard: blocks private/link-local IP ranges for URL-based uploads
- VirusScanner protocol with a no-op default stub

In production, swap the VirusScanner implementation for ClamAV integration.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import Protocol
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger(__name__)

# Private and link-local IP ranges that should never be accessed
_PRIVATE_RANGES = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
]


def validate_upload_url(url: str) -> bool:
    """Validate that a URL does not resolve to a private/internal IP address.

    Returns True if the URL is safe, False if it resolves to a private IP.
    Raises ValueError if the URL is malformed.
    """
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(f"Invalid URL: {url}")

    try:
        # Resolve the hostname to an IP address
        ip_str = socket.gethostbyname(parsed.hostname)
        ip = ipaddress.ip_address(ip_str)

        for cidr in _PRIVATE_RANGES:
            if ip in ipaddress.ip_network(cidr):
                logger.warning(
                    "SSRF blocked: URL resolves to private IP",
                    url=url,
                    resolved_ip=ip_str,
                    network=cidr,
                )
                return False

        return True
    except socket.gaierror as e:
        logger.warning("SSRF check failed: unable to resolve hostname", url=url, error=str(e))
        return False


class VirusScanner(Protocol):
    """Protocol for virus scanning uploaded files.

    Implementations must provide a ``scan(file_path: str) -> bool`` method
    that returns True if the file is clean, False if infected.
    """

    def scan(self, file_path: str) -> bool:
        """Scan a file for viruses. Returns True if clean, False if infected."""
        ...


class NoopVirusScanner:
    """No-op virus scanner — always reports clean.

    Replace with a real ClamAV integration in production.
    """

    def scan(self, file_path: str) -> bool:
        """No-op scan: always returns True (clean)."""
        logger.debug("No-op virus scan (always clean): %s", file_path)
        return True
