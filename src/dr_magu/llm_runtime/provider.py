from __future__ import annotations

from typing import Protocol

from dr_magu.brain.models import ResolvedModelConfig

from .models import LLMMessage, LLMResponse


class LLMProvider(Protocol):
    """LLM provider contract."""

    def chat(self, model_config: ResolvedModelConfig, messages: list[LLMMessage], timeout_seconds: int = 60) -> LLMResponse:
        """Execute a chat completion request."""
        ...
