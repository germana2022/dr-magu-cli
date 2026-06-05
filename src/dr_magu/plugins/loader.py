from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from dr_magu.plugins.models import PluginDefinition, PluginPermissionPolicy, PluginProvides


class PluginLoader:
    """Loads local plugin manifests from project and workspace plugin folders."""

    def __init__(self, workspace_path: str | Path, plugins_path: str | Path | None = None) -> None:
        self.workspace_path = Path(workspace_path).resolve()
        self.plugins_path = Path(plugins_path).resolve() if plugins_path else None

    def plugin_roots(self) -> list[Path]:
        """Return plugin search roots ordered by override priority."""
        roots: list[Path] = []
        if self.plugins_path:
            roots.append(self.plugins_path)
        roots.extend([
            self.workspace_path / ".dr-magu" / "plugins",
            Path("plugins"),
        ])
        return roots

    def discover_plugin_dirs(self) -> list[Path]:
        """Return directories containing a plugin.yaml manifest."""
        discovered: list[Path] = []
        seen: set[str] = set()
        for root in self.plugin_roots():
            if not root.exists() or not root.is_dir():
                continue
            for child in sorted(root.iterdir()):
                if not child.is_dir():
                    continue
                manifest = child / "plugin.yaml"
                if not manifest.exists():
                    continue
                key = str(child.resolve())
                if key in seen:
                    continue
                seen.add(key)
                discovered.append(child)
        return discovered

    def load(self) -> list[PluginDefinition]:
        """Load and normalize all discovered plugin manifests."""
        plugins: list[PluginDefinition] = []
        for plugin_dir in self.discover_plugin_dirs():
            plugins.append(self.load_plugin(plugin_dir))
        return plugins

    def load_plugin(self, plugin_dir: str | Path) -> PluginDefinition:
        """Load one plugin definition from its plugin.yaml manifest."""
        directory = Path(plugin_dir).resolve()
        manifest_path = directory / "plugin.yaml"
        payload: dict[str, Any] = {}
        errors: list[str] = []

        if not manifest_path.exists():
            errors.append("Missing plugin.yaml manifest.")
        else:
            try:
                with manifest_path.open("r", encoding="utf-8") as file:
                    payload = yaml.safe_load(file) or {}
            except Exception as exc:  # pragma: no cover - defensive guard for invalid YAML
                errors.append(f"Invalid plugin.yaml: {exc}")
                payload = {}

        plugin_id = str(payload.get("id") or directory.name)
        provides_payload = payload.get("provides", {}) or {}
        permissions_payload = payload.get("permissions", {}) or {}

        return PluginDefinition(
            id=plugin_id,
            name=str(payload.get("name") or plugin_id),
            version=str(payload.get("version") or "0.1.0"),
            enabled=bool(payload.get("enabled", True)),
            description=str(payload.get("description") or ""),
            domain=str(payload.get("domain") or "general"),
            path=str(directory),
            provides=PluginProvides(
                agents=list(provides_payload.get("agents", []) or []),
                workflows=list(provides_payload.get("workflows", []) or []),
                tools=list(provides_payload.get("tools", []) or []),
                commands=list(provides_payload.get("commands", []) or []),
                schedules=list(provides_payload.get("schedules", []) or []),
            ),
            permissions=PluginPermissionPolicy(**permissions_payload),
            validation_errors=errors,
        )
