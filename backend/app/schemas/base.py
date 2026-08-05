"""Shared base schemas — paginated response envelope.

All list endpoints return ``PaginatedResponse[T]`` with the shape:

.. code-block:: json

    {
        "items": [...],
        "total": 42,
        "limit": 50,
        "offset": 0
    }

This is the only list envelope used by the API.  Single-item endpoints
and mutation endpoints return their specific response types directly.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Unified envelope for paginated list responses.

    Every list endpoint returns this type.  The ``items`` field type
    varies per endpoint; ``total``, ``limit``, and ``offset`` provide
    enough information for the client to implement infinite-scroll,
    page-numbered navigation, or "load more" buttons.
    """

    items: list[T]
    total: int
    limit: int = 50
    offset: int = 0
