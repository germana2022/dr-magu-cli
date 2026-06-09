from __future__ import annotations

from pathlib import Path

from dr_magu.brain.model_config import ModelConfigLoader
from dr_magu.result import ToolResult

from .models import LLMMessage
from .openai_compatible import OpenAICompatibleProvider
from .sanitizer import debug_response_payload, user_response_payload


SYSTEM_PROMPT = """You are Dr Magu, an AI Agent Platform assistant. Be concise, helpful, and explain when an action requires a command, workflow, or approval."""


class LLMRuntime:
    """Default-model LLM runtime."""

    def __init__(self, workspace_path: str | Path, provider: OpenAICompatibleProvider | None = None):
        self.workspace_path = Path(workspace_path).resolve()
        self.provider = provider or OpenAICompatibleProvider()

    def chat(self, prompt: str, system_prompt: str = SYSTEM_PROMPT, timeout_seconds: int = 60) -> ToolResult:
        prompt = prompt.strip()
        if not prompt:
            return ToolResult(success=False, tool="llm.chat", errors=["Prompt is required."])

        model_config = ModelConfigLoader(self.workspace_path).default_model()
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=prompt),
        ]

        response = self.provider.chat(model_config, messages, timeout_seconds=timeout_seconds)

        return ToolResult(
            success=response.success,
            tool="llm.chat",
            data={
                "response": user_response_payload(response),
                "debug": {"response": debug_response_payload(response)},
                "default_model": model_config.to_dict(),
                "llm_used": response.success,
            },
            errors=[] if response.success else [response.error or "LLM request failed."],
            metadata={"response_object": response},
        )
