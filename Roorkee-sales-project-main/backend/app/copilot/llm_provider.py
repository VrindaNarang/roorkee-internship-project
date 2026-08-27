"""LLM provider abstraction for the Sales Copilot (Milestone 10).

Groq, OpenRouter, and Ollama all speak the same OpenAI-compatible
chat-completions wire format, so one thin client class covers all three —
only `base_url`/`api_key`/`model` differ. `get_llm_provider()` picks the
first provider with a configured API key, in the milestone's preferred order
(Groq -> OpenRouter -> Ollama), so switching providers later is a `.env`
change, not a code change. No Claude, no OpenAI's own hosted API.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.copilot.config import get_copilot_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    base_url: str
    api_key: str | None
    model: str


class LLMProvider:
    """Thin wrapper around any OpenAI-compatible chat-completions endpoint."""

    def __init__(self, spec: ProviderSpec) -> None:
        self.spec = spec
        self._client = AsyncOpenAI(base_url=spec.base_url, api_key=spec.api_key or "not-needed")

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        """Yields response text incrementally as the provider streams it."""
        settings = get_copilot_settings()
        stream = await self._client.chat.completions.create(
            model=self.spec.model,
            messages=messages,
            temperature=0.2,
            stream=True,
            timeout=settings.request_timeout_seconds,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


def _provider_specs() -> dict[str, ProviderSpec]:
    settings = get_copilot_settings()
    return {
        "groq": ProviderSpec(
            "groq", "https://api.groq.com/openai/v1", settings.groq_api_key or None, settings.groq_model
        ),
        "openrouter": ProviderSpec(
            "openrouter", "https://openrouter.ai/api/v1", settings.openrouter_api_key or None,
            settings.openrouter_model,
        ),
        "ollama": ProviderSpec("ollama", settings.ollama_base_url, None, settings.ollama_model),
    }


def _select_provider_spec() -> ProviderSpec:
    settings = get_copilot_settings()
    specs = _provider_specs()

    if settings.copilot_llm_provider:
        if settings.copilot_llm_provider not in specs:
            raise ValueError(f"Unknown COPILOT_LLM_PROVIDER: {settings.copilot_llm_provider!r}")
        return specs[settings.copilot_llm_provider]

    if settings.groq_api_key:
        return specs["groq"]
    if settings.openrouter_api_key:
        return specs["openrouter"]
    return specs["ollama"]  # no key required — local fallback


_provider_cache: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """Returns the process-wide LLMProvider singleton, selecting (and
    logging) the active provider on first use.
    """
    global _provider_cache
    if _provider_cache is None:
        spec = _select_provider_spec()
        logger.info("Sales Copilot LLM provider: %s (model=%s)", spec.name, spec.model)
        _provider_cache = LLMProvider(spec)
    return _provider_cache


def reset_provider_cache() -> None:
    """Clears the cached provider — used by tests that change env vars."""
    global _provider_cache
    _provider_cache = None
