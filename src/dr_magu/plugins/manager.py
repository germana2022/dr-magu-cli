from __future__ import annotations

from pathlib import Path

from dr_magu.plugins.registry import PluginRegistry
from dr_magu.result import ToolResult


class PluginManager:
    """User-facing plugin operations for CLI, TUI, and Brain context."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.registry = PluginRegistry(self.workspace_path)

    def list_plugins(self) -> ToolResult:
        data = self.registry.as_context()
        return ToolResult(success=True, tool="plugin.list", data=data)

    def show_plugin(self, plugin_id: str) -> ToolResult:
        try:
            plugin = self.registry.get(plugin_id)
        except KeyError as exc:
            return ToolResult(success=False, tool="plugin.show", errors=[str(exc)])
        return ToolResult(success=True, tool="plugin.show", data=plugin.model_dump())

    def validate_plugin(self, plugin_id: str | None = None) -> ToolResult:
        try:
            data = self.registry.validate(plugin_id)
        except KeyError as exc:
            return ToolResult(success=False, tool="plugin.validate", errors=[str(exc)])
        return ToolResult(success=bool(data["valid"]), tool="plugin.validate", data=data)
