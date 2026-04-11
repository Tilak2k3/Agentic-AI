"""OpenAI-compatible client for Hugging Face Inference Router (chat completions)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from agentic_ai.config import get_llm_router_config


@runtime_checkable
class ChatCompletionsPort(Protocol):
    def create(self, *args: Any, **kwargs: Any) -> Any: ...


@runtime_checkable
class ChatPort(Protocol):
    completions: ChatCompletionsPort


@runtime_checkable
class OpenAIClientPort(Protocol):
    chat: ChatPort


def get_openai_router_client() -> OpenAIClientPort | None:
    """Return a real OpenAI SDK client pointed at the HF router, or None if not configured."""
    cfg = get_llm_router_config()
    if cfg is None:
        return None
    from openai import OpenAI

    return OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
