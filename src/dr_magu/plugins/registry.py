from __future__ import annotations

from pathlib import Path

from dr_magu.plugins.loader import PluginLoader
from dr_magu.plugins.models import PluginDefinition
from dr_magu.plugins.validator import PluginValidator


class PluginRegistry:
    """Registry of local plugins discovered from configured plugin folders."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self._plugins = PluginLoader(self.workspace_path).load()
        self._validator = PluginValidator()

    def list(self, include_disabled: bool = True) -> list[PluginDefinition]:
        plugins = self._plugins if include_disabled else [plugin for plugin in self._plugins if plugin.enabled]
        return sorted(plugins, key=lambda item: item.id)

    def get(self, plugin_id: str) -> PluginDefinition:
        for plugin in self._plugins:
            if plugin.id == plugin_id:
                return plugin
        available = ", ".join(sorted(plugin.id for plugin in self._plugins)) or "none"
        raise KeyError(f"Unknown plugin '{plugin_id}'. Available plugins: {available}")

    def validate(self, plugin_id: str | None = None) -> dict[str, object]:
        plugins = [self.get(plugin_id)] if plugin_id else self.list()
        results = [self._validator.validate(plugin).model_dump() for plugin in plugins]
        return {
            "valid": all(result["valid"] for result in results),
            "results": results,
            "count": len(results),
        }

    def as_context(self) -> dict[str, object]:
        plugins = [plugin.model_dump() for plugin in self.list()]
        enabled = [plugin for plugin in plugins if plugin.get("enabled")]
        return {
            "plugins": plugins,
            "count": len(plugins),
            "enabled_count": len(enabled),
        }
