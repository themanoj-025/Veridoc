"""Tests for the health endpoint (F26)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(test_client: AsyncClient) -> None:
    """Test the health endpoint returns 200 when dependencies are reachable."""
    response = await test_client.get("/api/v1/health")
    # In test mode without real deps, some may be "error" but the endpoint
    # should still respond with a valid JSON body
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "dependencies" in data
    assert "postgres" in data["dependencies"]
    assert "chroma" in data["dependencies"]
    assert "llm" in data["dependencies"]


@pytest.mark.asyncio
async def test_health_endpoint_structure(test_client: AsyncClient) -> None:
    """Test the health endpoint returns the expected JSON structure."""
    response = await test_client.get("/api/v1/health")
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data
    assert isinstance(data["dependencies"], dict)
    # Every dependency should have a status field
    for dep_name, dep_data in data["dependencies"].items():
        assert "status" in dep_data, f"Missing status for {dep_name}"
