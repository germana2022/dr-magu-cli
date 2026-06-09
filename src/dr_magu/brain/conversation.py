from __future__ import annotations

from pathlib import Path

from dr_magu.brain.intent_models import (
    INTENT_DOCUMENT_ACTION,
    INTENT_GENERAL_CHAT,
    INTENT_RESEARCH_ACTION,
    INTENT_SCHEDULE_ACTION,
    INTENT_SOFTWARE_ACTION,
    INTENT_WORKSPACE_ACTION,
)
from dr_magu.brain.intent_router import classify_prompt
from dr_magu.brain.model_config import ModelConfigLoader
from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.llm_runtime.runtime import LLMRuntime
from dr_magu.result import ToolResult


class ConversationalBrain:
    """Natural-language entry point for Dr Magu.

    v1.1.1 is deterministic and model-aware. It resolves the configured default
    model and exposes it in responses, but it does not call the LLM yet.
    """

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = Path(workspace_path).resolve()

    def ask(self, prompt: str) -> ToolResult:
        prompt = prompt.strip()
        if not prompt:
            return ToolResult(success=False, tool="brain.ask", errors=["Prompt is required."])

        classification = classify_prompt(prompt)
        model = ModelConfigLoader(self.workspace_path).default_model().to_dict()
        routed_command = self._command_for_intent(classification.intent, prompt)

        if routed_command:
            command_context = CommandContext(
                workspace_path=str(self.workspace_path),
                output_format="human",
                config=load_config(),
            )
            route_result = CommandProcessor(registry).execute_line(routed_command, command_context)
            return ToolResult(
                success=route_result.success,
                tool="brain.ask",
                data={
                    "prompt": prompt,
                    "classification": classification.to_dict(),
                    "default_model": model,
                    "llm_used": False,
                    "llm_ready": bool(model.get("model")),
                    "routed_command": routed_command,
                    "route_result": {
                        "success": route_result.success,
                        "tool": route_result.tool,
                        "data": route_result.data,
                        "errors": route_result.errors,
                    },
                },
                errors=route_result.errors,
            )

        llm_result = LLMRuntime(self.workspace_path).chat(prompt)
        if llm_result.success:
            return ToolResult(
                success=True,
                tool="brain.ask",
                data={
                    "prompt": prompt,
                    "classification": classification.to_dict(),
                    "default_model": model,
                    "llm_used": True,
                    "llm_ready": bool(model.get("model")),
                    "response": llm_result.data["response"]["content"],
                    "llm_response": llm_result.data["response"],
                },
            )

        return ToolResult(
            success=False,
            tool="brain.ask",
            data={
                "prompt": prompt,
                "classification": classification.to_dict(),
                "default_model": model,
                "llm_used": False,
                "llm_ready": bool(model.get("model")),
                "message": "General chat mode was detected, but the LLM runtime request failed.",
            },
            errors=llm_result.errors,
        )

    def _command_for_intent(self, intent: str, prompt: str) -> str | None:
        escaped_prompt = prompt.replace('"', '\\"')
        lowered = prompt.lower()

        if intent == INTENT_RESEARCH_ACTION:
            return f'research.search "{escaped_prompt}"'

        if intent == INTENT_DOCUMENT_ACTION:
            return f'report.create "{escaped_prompt}" --summary "Generated from conversational prompt."'

        if intent == INTENT_WORKSPACE_ACTION:
            if "context" in lowered or "documentation" in lowered:
                return "context.generate"
            return "repo.scan"

        if intent == INTENT_SOFTWARE_ACTION:
            if "website" in lowered or "site" in lowered or "sitio" in lowered:
                return f'website.build "{escaped_prompt}"'
            if "ticket" in lowered:
                return "sdlc.agent.run ticket-generator"
            if "test" in lowered:
                return "sdlc.agent.run test-generator"
            if "review" in lowered:
                return "sdlc.agent.run code-reviewer"
            if "doc" in lowered:
                return "sdlc.agent.run documentation-writer"
            return "sdlc.agent.run repository-analyzer"

        if intent == INTENT_SCHEDULE_ACTION:
            return None

        if intent == INTENT_GENERAL_CHAT:
            if any(keyword in lowered for keyword in ["best", "top", "compare", "crm", "systems", "platforms", "tools", "solutions"]):
                return f'research.search "{escaped_prompt}"'

        return None


def ask(prompt: str, workspace_path: str | Path = ".") -> ToolResult:
    """Route a natural-language prompt through the Conversational Brain."""
    return ConversationalBrain(workspace_path).ask(prompt)
