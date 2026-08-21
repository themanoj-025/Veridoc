"""Pluggable LLM provider — defaults to local Ollama, falls back to Claude/OpenAI if API key is set."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

import httpx
import structlog

from app.core.config import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def model_name(self) -> str: ...

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

    def __init__(self) -> None:
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

        async with (
            httpx.AsyncClient(timeout=120.0) as client,
            client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {"temperature": 0.1, "num_predict": 2048},
                },
            ) as response,
        ):
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

    def __init__(self) -> None:
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

    def __init__(self) -> None:
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

    When the configured primary provider errors or times out, the
    getter wraps the call in a try/except and falls back to the
    local Ollama model (if not already primary).  Every fallback
    event is logged with the provider name and error reason.
    """
    logger = structlog.get_logger(__name__)

    if settings.anthropic_api_key and settings.llm_provider == "claude":
        logger.info(
            "llm.provider_selected", provider="claude", model="claude-sonnet-4-20250514"
        )
        return _with_fallback_to_ollama(ClaudeProvider(), "claude", logger)
    elif settings.openai_api_key and settings.llm_provider == "openai":
        logger.info("llm.provider_selected", provider="openai", model="gpt-4o-mini")
        return _with_fallback_to_ollama(OpenAIProvider(), "openai", logger)
    logger.info("llm.provider_selected", provider="ollama", model=settings.ollama_model)
    return OllamaProvider()


def _with_fallback_to_ollama(primary: LLMProvider, name: str, logger) -> LLMProvider:
    """Wrap a primary LLM provider with automatic fallback to Ollama.

    When a request to the primary provider errors or times out, the
    fallback transparently redirects to the local Ollama model.
    Every fallback event is logged with the provider name, error,
    and a "FALLBACK" flag visible in structured logs.
    """
    import asyncio

    class FallbackWrapper(LLMProvider):
        def __init__(self) -> None:
            self._fallback_activated = False
            self._active_model_name = primary.model_name

        @property
        def model_name(self) -> str:
            """Return the actual model name — primary unless fallback activated."""
            return self._active_model_name

        @property
        def fallback_used(self) -> bool:
            """Whether fallback to Ollama was activated on the last call."""
            return self._fallback_activated

        async def _fallback_to_ollama(self, system_prompt, history, message) -> None:
            """Execute fallback to Ollama and update model tracking."""
            self._fallback_activated = True
            fallback = OllamaProvider()
            self._active_model_name = fallback.model_name
            logger.info(
                "llm.fallback_activated",
                primary=name,
                fallback=fallback.model_name,
            )
            return fallback

        async def chat(
            self, system_prompt: str, history: list[dict], message: str
        ) -> str:
            try:
                return await asyncio.wait_for(
                    primary.chat(system_prompt, history, message),
                    timeout=settings.llm_timeout,
                )
            except (TimeoutError, Exception) as e:
                logger.warning(
                    "llm.fallback",
                    primary=name,
                    error=str(e)[:100],
                    timeout=isinstance(e, asyncio.TimeoutError),
                )
                fallback = await self._fallback_to_ollama(
                    system_prompt, history, message
                )
                return await fallback.chat(system_prompt, history, message)

        async def stream_chat(
            self, system_prompt: str, history: list[dict], message: str
        ) -> AsyncGenerator[str, None]:
            try:
                async for token in asyncio.wait_for(
                    primary.stream_chat(system_prompt, history, message),
                    timeout=settings.llm_timeout,
                ):
                    yield token
            except (TimeoutError, Exception) as e:
                logger.warning(
                    "llm.fallback.stream",
                    primary=name,
                    error=str(e)[:100],
                    timeout=isinstance(e, asyncio.TimeoutError),
                )
                fallback = await self._fallback_to_ollama(
                    system_prompt, history, message
                )
                async for token in fallback.stream_chat(
                    system_prompt, history, message
                ):
                    yield token

    return FallbackWrapper()


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
