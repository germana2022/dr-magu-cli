from __future__ import annotations

from pathlib import Path

from dr_magu.commands.context import CommandContext
from dr_magu.commands.processor import CommandProcessor
from dr_magu.commands.registry import registry
from dr_magu.config import load_config
from dr_magu.result import ToolResult

from .capabilities import AI_OS_CAPABILITIES, AI_OS_LAYERS
from .models import OSState


class AIOperatingSystem:
    """Unified control layer for Dr Magu platform capabilities."""

    def __init__(self, workspace_path: str | Path):
        self.workspace_path = str(Path(workspace_path).resolve())
        self.processor = CommandProcessor(registry)

    def status(self) -> ToolResult:
        state = OSState(
            version="2.0.0",
            layers=AI_OS_LAYERS,
            capabilities=AI_OS_CAPABILITIES,
            health={
                "workspace": self.workspace_path,
                "capability_count": len(AI_OS_CAPABILITIES),
                "layer_count": len(AI_OS_LAYERS),
                "ready": True,
            },
        )
        return ToolResult(success=True, tool="os.status", data=state.to_dict())

    def capabilities(self) -> ToolResult:
        return ToolResult(
            success=True,
            tool="os.capabilities",
            data={
                "count": len(AI_OS_CAPABILITIES),
                "layers": AI_OS_LAYERS,
                "capabilities": [capability.to_dict() for capability in AI_OS_CAPABILITIES],
            },
        )

    def dispatch(self, command: str) -> ToolResult:
        context = CommandContext(workspace_path=self.workspace_path, output_format="human", config=load_config())
        result = self.processor.execute_line(command, context)
        return ToolResult(
            success=result.success,
            tool="os.dispatch",
            data={
                "command": command,
                "result": {
                    "success": result.success,
                    "tool": result.tool,
                    "data": result.data,
                    "errors": result.errors,
                },
            },
            errors=result.errors,
        )

    def boot(self) -> ToolResult:
        status = self.status()
        capabilities = self.capabilities()
        return ToolResult(
            success=True,
            tool="os.boot",
            data={
                "status": status.data,
                "capabilities": capabilities.data,
                "message": "Dr Magu AI Operating System boot completed.",
            },
        )
