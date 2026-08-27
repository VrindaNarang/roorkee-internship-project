"""Sales Copilot configuration — LLM provider selection/credentials and
tunables, sourced from environment variables / `.env` (see `.env.example`).
Mirrors `app/core/config.py`'s Settings pattern so this stays consistent with
the rest of the app rather than reading `os.environ` ad hoc.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class CopilotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Explicit override: "groq" | "openrouter" | "ollama". Empty = auto-detect
    # by the preferred order below (first provider with a configured API key
    # wins; Ollama needs no key so it's always the final fallback).
    copilot_llm_provider: str = ""

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"

    max_history_turns: int = 6  # prior turns kept in the prompt, oldest dropped first
    request_timeout_seconds: float = 30.0


@lru_cache
def get_copilot_settings() -> CopilotSettings:
    return CopilotSettings()
