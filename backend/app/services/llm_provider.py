"""Pluggable LLM provider — defaults to local Ollama, falls back to Claude/OpenAI if API key is set."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import AsyncGenerator

import httpx

from app.core.config import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @abstractmethod
    async def chat(self, system_prompt: str, history: list[dict], message: str) -> str:
        """Non-streaming chat."""
        ...

    @abstractmethod
    async def stream_chat(
        self, system_prompt: str, history: list[dict], message: str
    ) -> AsyncGenerator[str, None]:
        """Streaming chat — yields tokens."""
        ...  # pragma: no cover


class OllamaProvider(LLMProvider):
    """Default provider — local Ollama, no API key needed."""

    def __init__(self):
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model

    @property
    def model_name(self) -> str:
        return f"ollama/{self.model}"

    async def chat(self, system_prompt: str, history: list[dict], message: str) -> str:
        full_content = ""
        async for token in self.stream_chat(system_prompt, history, message):
            full_content += token
        return full_content

    async def stream_chat(
        self, system_prompt: str, history: list[dict], message: str
    ) -> AsyncGenerator[str, None]:
        messages = [{"role": "system", "content": system_prompt}]
        for h in history:
            messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.1, "num_predict": 2048},
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue


class ClaudeProvider(LLMProvider):
    """Optional Claude API provider — only works if ANTHROPIC_API_KEY is set."""

    def __init__(self):
        import anthropic
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"

    @property
    def model_name(self) -> str:
        return f"claude/{self.model}"

    async def chat(self, system_prompt: str, history: list[dict], message: str) -> str:
        msg = await self.client.messages.create(
            model=self.model,
            system=system_prompt,
            messages=[
                *[{"role": h["role"], "content": h["content"]} for h in history],
                {"role": "user", "content": message},
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        return msg.content[0].text if msg.content else ""

    async def stream_chat(
        self, system_prompt: str, history: list[dict], message: str
    ) -> AsyncGenerator[str, None]:
        async with self.client.messages.stream(
            model=self.model,
            system=system_prompt,
            messages=[
                *[{"role": h["role"], "content": h["content"]} for h in history],
                {"role": "user", "content": message},
            ],
            max_tokens=2048,
            temperature=0.1,
        ) as stream:
            async for text in stream.text_stream:
                yield text


class OpenAIProvider(LLMProvider):
    """Optional OpenAI API provider — only works if OPENAI_API_KEY is set."""

    def __init__(self):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"

    @property
    def model_name(self) -> str:
        return f"openai/{self.model}"

    async def chat(self, system_prompt: str, history: list[dict], message: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                *[{"role": h["role"], "content": h["content"]} for h in history],
                {"role": "user", "content": message},
            ],
            max_tokens=2048,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    async def stream_chat(
        self, system_prompt: str, history: list[dict], message: str
    ) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                *[{"role": h["role"], "content": h["content"]} for h in history],
                {"role": "user", "content": message},
            ],
            max_tokens=2048,
            temperature=0.1,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ── Factory ──────────────────────────────────────────────


def _build_llm_provider() -> LLMProvider:
    """Build the appropriate LLM provider from settings (no caching).

    This function exists separately so it can be called from
    ``DIContainer.get_or_create_llm()`` without circular imports.
    """
    if settings.anthropic_api_key and settings.llm_provider == "claude":
        return ClaudeProvider()
    elif settings.openai_api_key and settings.llm_provider == "openai":
        return OpenAIProvider()
    return OllamaProvider()


def get_llm() -> LLMProvider:
    """Get the LLM provider based on environment configuration.

    Checks the DI container first.  Falls back to a direct (uncached)
    provider instance when no container is active (standalone scripts
    and tests).
    """
    from app.core.di import get_di_container

    container = get_di_container()
    if container is not None:
        return container.get_or_create_llm()
    return _build_llm_provider()
