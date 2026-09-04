"""Tests for Veridoc prompt registry."""


import pytest

from app.services.prompt_registry import get_prompt_template, get_prompt_version

pytestmark = pytest.mark.unit

class TestGetPromptVersion:
    """Tests for prompt version lookup."""

    def test_returns_string(self) -> None:
        version = get_prompt_version("system_prompt")
        assert isinstance(version, str)

    def test_unknown_returns_fallback(self) -> None:
        version = get_prompt_version("nonexistent_prompt_xyz")
        assert version == "unknown"

    def test_existing_prompt(self) -> None:
        # The registry should have at least one prompt
        version = get_prompt_version("rag_prompt")
        assert version != ""


class TestGetPromptTemplate:
    """Tests for prompt template lookup."""

    def test_returns_string_or_none(self) -> None:
        result = get_prompt_template("system_prompt")
        assert result is None or isinstance(result, str)

    def test_unknown_returns_none(self) -> None:
        result = get_prompt_template("nonexistent_prompt_xyz")
        assert result is None
