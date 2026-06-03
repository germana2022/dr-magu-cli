from __future__ import annotations

from pathlib import Path
from time import perf_counter

from dr_magu.result import ToolResult
from dr_magu.scanner.detectors import (
    IGNORED_DIRS,
    detect_dotnet_stack,
    detect_important_files,
    detect_languages,
    detect_node_stack,
    detect_package_managers,
    detect_python_stack,
    detect_source_roots,
    detect_test_roots,
    should_ignore,
    unique_sorted,
)
from dr_magu.scanner.models import RepositoryScan
from dr_magu.workspace import Workspace


def scan_repository(workspace_path: str, max_files: int = 5000) -> ToolResult:
    """Run a deterministic repository scan without using an LLM."""
    start = perf_counter()
    try:
        workspace = Workspace(workspace_path)
        root = workspace.root
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(str(root))

        files: list[Path] = []
        directory_count = 0
        for path in root.rglob("*"):
            if should_ignore(path.relative_to(root)):
                continue
            if path.is_dir():
                directory_count += 1
                continue
            files.append(path)
            if len(files) >= max_files:
                break

        languages = detect_languages(files)
        frameworks: list[str] = []
        build_tools: list[str] = []
        test_frameworks: list[str] = []

        py_frameworks, py_build_tools, py_tests = detect_python_stack(root)
        node_frameworks, node_build_tools, node_tests = detect_node_stack(root)
        dotnet_frameworks, dotnet_build_tools, dotnet_tests = detect_dotnet_stack(root)

        frameworks.extend(py_frameworks + node_frameworks + dotnet_frameworks)
        build_tools.extend(py_build_tools + node_build_tools + dotnet_build_tools)
        test_frameworks.extend(py_tests + node_tests + dotnet_tests)

        package_managers = detect_package_managers(root)
        important_files = detect_important_files(root)
        source_roots = detect_source_roots(root)
        test_roots = detect_test_roots(root)
        capabilities = _detect_capabilities(root, frameworks, source_roots, test_roots)

        scan = RepositoryScan(
            workspace_path=str(root),
            project_name=root.name,
            project_type=_detect_project_type(languages, frameworks, important_files),
            primary_language=languages[0] if languages else None,
            languages=languages,
            frameworks=unique_sorted(frameworks),
            package_managers=unique_sorted(package_managers),
            build_tools=unique_sorted(build_tools),
            test_frameworks=unique_sorted(test_frameworks),
            important_files=important_files,
            source_roots=source_roots,
            test_roots=test_roots,
            capabilities=unique_sorted(capabilities),
            file_count=len(files),
            directory_count=directory_count,
            ignored_directories=sorted(IGNORED_DIRS),
        )
        return ToolResult(
            success=True,
            tool="repo.scan",
            data=scan.model_dump(),
            metadata={"duration_ms": int((perf_counter() - start) * 1000)},
        )
    except Exception as exc:
        return ToolResult(success=False, tool="repo.scan", errors=[str(exc)])


def _detect_project_type(languages: list[str], frameworks: list[str], important_files: list) -> str:
    framework_set = set(frameworks)
    important_paths = {item.path for item in important_files}
    if "Textual" in framework_set and "Typer" in framework_set:
        return "Python CLI/TUI application"
    if "Next.js" in framework_set:
        return "Next.js application"
    if "React" in framework_set:
        return "React application"
    if "ASP.NET Core" in framework_set:
        return ".NET web application"
    if "pyproject.toml" in important_paths:
        return "Python package"
    if "package.json" in important_paths:
        return "Node.js package"
    if languages:
        return f"{languages[0]} project"
    return "Unknown project type"


def _detect_capabilities(root: Path, frameworks: list[str], source_roots: list[str], test_roots: list[str]) -> list[str]:
    capabilities: list[str] = []
    framework_set = set(frameworks)
    if "Typer" in framework_set:
        capabilities.append("CLI tooling")
    if "Textual" in framework_set:
        capabilities.append("Terminal UI")
    if (root / ".dr-magu").exists():
        capabilities.append("Persistent Dr Magu workspace metadata")
    if source_roots:
        capabilities.append("Source code organization")
    if test_roots:
        capabilities.append("Automated tests")
    if (root / ".git").exists():
        capabilities.append("Git repository")
    return capabilities
