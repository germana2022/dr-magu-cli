from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

from dr_magu.project_context.models import GeneratedContextFile, ProjectContext
from dr_magu.result import ToolResult
from dr_magu.scanner.models import RepositoryScan
from dr_magu.scanner.repository_scanner import scan_repository
from dr_magu.scanner.writers import write_latest_scan


CONTEXT_FILE_NAMES = {
    "project": "PROJECT_CONTEXT.md",
    "tech_stack": "TECH_STACK.md",
    "repository_map": "REPOSITORY_MAP.md",
    "architecture": "ARCHITECTURE_NOTES.md",
    "json": "dr-magu-context.json",
}


def generate_project_context(workspace_path: str, refresh: bool = False) -> ToolResult:
    """Generate deterministic context files from the latest repository scan.

    This function intentionally does not use an LLM. It turns scanner metadata into
    stable Markdown and JSON files that future agents can consume safely.
    """
    start = perf_counter()
    try:
        root = Path(workspace_path).resolve()
        scan = _load_or_create_scan(root, refresh)
        output_dir = root / ".dr-magu" / "context"
        output_dir.mkdir(parents=True, exist_ok=True)

        context = _build_project_context(scan)

        generated: list[GeneratedContextFile] = []
        files_to_write = {
            CONTEXT_FILE_NAMES["project"]: render_project_context(scan),
            CONTEXT_FILE_NAMES["tech_stack"]: render_tech_stack(scan),
            CONTEXT_FILE_NAMES["repository_map"]: render_repository_map(scan),
            CONTEXT_FILE_NAMES["architecture"]: render_architecture_notes(scan),
        }

        for file_name, content in files_to_write.items():
            path = output_dir / file_name
            path.write_text(content, encoding="utf-8")
            generated.append(GeneratedContextFile(
                name=file_name,
                path=str(path),
                description=_describe_context_file(file_name),
            ))

        json_path = output_dir / CONTEXT_FILE_NAMES["json"]
        context.generated_files = generated + [GeneratedContextFile(
            name=CONTEXT_FILE_NAMES["json"],
            path=str(json_path),
            description="Structured machine-readable project context.",
        )]
        json_path.write_text(json.dumps(context.model_dump(), indent=2), encoding="utf-8")

        data = context.model_dump()
        data["context_dir"] = str(output_dir)
        return ToolResult(
            success=True,
            tool="context.generate",
            data=data,
            metadata={"duration_ms": int((perf_counter() - start) * 1000)},
        )
    except Exception as exc:
        return ToolResult(success=False, tool="context.generate", errors=[str(exc)])


def show_project_context(workspace_path: str) -> ToolResult:
    """Load the structured project context from disk."""
    try:
        root = Path(workspace_path).resolve()
        context_path = root / ".dr-magu" / "context" / CONTEXT_FILE_NAMES["json"]
        if not context_path.exists():
            return ToolResult(
                success=False,
                tool="context.show",
                errors=["Project context was not found. Run 'dr-magu context generate' first."],
            )
        data = json.loads(context_path.read_text(encoding="utf-8"))
        return ToolResult(success=True, tool="context.show", data=data)
    except Exception as exc:
        return ToolResult(success=False, tool="context.show", errors=[str(exc)])


def get_context_path(workspace_path: str) -> ToolResult:
    """Return the expected project context directory path."""
    root = Path(workspace_path).resolve()
    context_dir = root / ".dr-magu" / "context"
    return ToolResult(
        success=True,
        tool="context.path",
        data={
            "workspace_path": str(root),
            "context_dir": str(context_dir),
            "exists": context_dir.exists(),
        },
    )


def _load_or_create_scan(root: Path, refresh: bool) -> RepositoryScan:
    scan_path = root / ".dr-magu" / "scans" / "latest-scan.json"
    if refresh or not scan_path.exists():
        result = scan_repository(str(root))
        if not result.success or not result.data:
            raise RuntimeError("; ".join(result.errors) or "Repository scan failed.")
        scan = RepositoryScan.model_validate(result.data)
        write_latest_scan(str(root), scan)
        return scan

    data = json.loads(scan_path.read_text(encoding="utf-8"))
    return RepositoryScan.model_validate(data)


def _build_project_context(scan: RepositoryScan) -> ProjectContext:
    return ProjectContext(
        workspace_path=scan.workspace_path,
        project_name=scan.project_name,
        project_type=scan.project_type,
        primary_language=scan.primary_language,
        languages=scan.languages,
        frameworks=scan.frameworks,
        package_managers=scan.package_managers,
        build_tools=scan.build_tools,
        test_frameworks=scan.test_frameworks,
        capabilities=scan.capabilities,
        source_roots=scan.source_roots,
        test_roots=scan.test_roots,
        important_files=[item.model_dump() for item in scan.important_files],
    )


def render_project_context(scan: RepositoryScan) -> str:
    """Render a human-readable project context document."""
    return "\n".join([
        "# Project Context",
        "",
        f"## Project",
        f"- Name: {scan.project_name}",
        f"- Workspace: {scan.workspace_path}",
        f"- Type: {scan.project_type}",
        f"- Primary language: {scan.primary_language or 'unknown'}",
        "",
        "## Capabilities",
        *_render_bullets(scan.capabilities),
        "",
        "## Entry Points",
        *_render_bullets(_entry_points(scan)),
        "",
        "## Important Files",
        *_render_file_bullets(scan),
        "",
        "## Notes",
        "- This context was generated deterministically from repository metadata.",
        "- No LLM, agent, or external service was used to create this file.",
        "",
    ])


def render_tech_stack(scan: RepositoryScan) -> str:
    return "\n".join([
        "# Tech Stack",
        "",
        "## Languages",
        *_render_bullets(scan.languages),
        "",
        "## Frameworks and Libraries",
        *_render_bullets(scan.frameworks),
        "",
        "## Package Managers",
        *_render_bullets(scan.package_managers),
        "",
        "## Build Tools",
        *_render_bullets(scan.build_tools),
        "",
        "## Test Frameworks",
        *_render_bullets(scan.test_frameworks),
        "",
    ])


def render_repository_map(scan: RepositoryScan) -> str:
    return "\n".join([
        "# Repository Map",
        "",
        "## Source Roots",
        *_render_bullets(scan.source_roots),
        "",
        "## Test Roots",
        *_render_bullets(scan.test_roots),
        "",
        "## Important Files",
        *_render_file_bullets(scan),
        "",
        f"## Repository Size",
        f"- Files scanned: {scan.file_count}",
        f"- Directories scanned: {scan.directory_count}",
        "",
    ])


def render_architecture_notes(scan: RepositoryScan) -> str:
    layers = _architecture_layers(scan)
    return "\n".join([
        "# Architecture Notes",
        "",
        f"Dr Magu detected this workspace as a **{scan.project_type}**.",
        "",
        "## Detected Architecture Layers",
        *_render_bullets(layers),
        "",
        "## Deterministic Context Flow",
        "```text",
        "Repository Scanner",
        "  ↓",
        "Latest Scan JSON",
        "  ↓",
        "Context Generator",
        "  ↓",
        "Markdown + JSON Context Files",
        "```",
        "",
        "## Future Use",
        "- These files are intended to become safe base context for future LangGraph agents.",
        "- Agent execution, model selection, and LLM prompting are intentionally out of scope for this version.",
        "",
    ])


def _render_bullets(items: list[str]) -> list[str]:
    if not items:
        return ["- none detected"]
    return [f"- {item}" for item in items]


def _render_file_bullets(scan: RepositoryScan) -> list[str]:
    if not scan.important_files:
        return ["- none detected"]
    return [f"- `{item.path}` — {item.reason}" for item in scan.important_files]


def _entry_points(scan: RepositoryScan) -> list[str]:
    paths = {item.path for item in scan.important_files}
    entries: list[str] = []
    if "pyproject.toml" in paths:
        entries.append("Python package entry points from pyproject.toml")
    if "package.json" in paths:
        entries.append("Node.js scripts from package.json")
    if any(path.endswith(".sln") for path in paths):
        entries.append(".NET solution entry point")
    if "README.md" in paths:
        entries.append("README.md documentation entry point")
    return entries


def _architecture_layers(scan: RepositoryScan) -> list[str]:
    layers: list[str] = []
    capabilities = set(scan.capabilities)
    frameworks = set(scan.frameworks)
    if "CLI tooling" in capabilities or "Typer" in frameworks:
        layers.append("CLI layer")
    if "Terminal UI" in capabilities or "Textual" in frameworks:
        layers.append("Terminal UI layer")
    if "Persistent Dr Magu workspace metadata" in capabilities:
        layers.append("Workspace metadata layer")
    if scan.source_roots:
        layers.append("Source code layer")
    if scan.test_roots:
        layers.append("Test layer")
    if not layers:
        layers.append("General project structure")
    return layers


def _describe_context_file(file_name: str) -> str:
    descriptions = {
        CONTEXT_FILE_NAMES["project"]: "Human-readable project summary.",
        CONTEXT_FILE_NAMES["tech_stack"]: "Detected languages, frameworks, package managers, build tools, and test tools.",
        CONTEXT_FILE_NAMES["repository_map"]: "Important files, source roots, test roots, and repository size.",
        CONTEXT_FILE_NAMES["architecture"]: "Deterministic architecture notes based on scan metadata.",
    }
    return descriptions.get(file_name, "Generated context file.")
