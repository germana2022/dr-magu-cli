from __future__ import annotations

import json
import tomllib
from pathlib import Path

from dr_magu.scanner.models import DetectedFile

IGNORED_DIRS = {
    ".git",
    ".dr-magu",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "bin",
    "obj",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".next",
    "coverage",
}

LANGUAGE_EXTENSIONS = {
    ".py": "Python",
    ".cs": "C#",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".rb": "Ruby",
    ".php": "PHP",
}

IMPORTANT_FILE_REASONS = {
    "README.md": "Project documentation",
    "pyproject.toml": "Python package metadata",
    "requirements.txt": "Python dependencies",
    "package.json": "Node.js package metadata",
    "pnpm-lock.yaml": "pnpm lock file",
    "package-lock.json": "npm lock file",
    "yarn.lock": "Yarn lock file",
    "Dockerfile": "Container build file",
    "docker-compose.yml": "Docker Compose configuration",
    "docker-compose.yaml": "Docker Compose configuration",
    "tsconfig.json": "TypeScript configuration",
    "next.config.js": "Next.js configuration",
    "next.config.ts": "Next.js configuration",
    "vite.config.ts": "Vite configuration",
    "vite.config.js": "Vite configuration",
    "pytest.ini": "pytest configuration",
    "setup.py": "Python legacy package metadata",
    "global.json": ".NET SDK selection",
    "pom.xml": "Maven build configuration",
    "build.gradle": "Gradle build configuration",
    "Cargo.toml": "Rust package metadata",
    "go.mod": "Go module metadata",
}


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def detect_languages(files: list[Path]) -> list[str]:
    counts: dict[str, int] = {}
    for file_path in files:
        language = LANGUAGE_EXTENSIONS.get(file_path.suffix.lower())
        if language:
            counts[language] = counts.get(language, 0) + 1
    return [name for name, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]


def detect_important_files(root: Path) -> list[DetectedFile]:
    detected: list[DetectedFile] = []
    for name, reason in IMPORTANT_FILE_REASONS.items():
        candidate = root / name
        if candidate.exists():
            detected.append(DetectedFile(path=name, reason=reason))
    for candidate in sorted(root.glob("*.sln")):
        detected.append(DetectedFile(path=candidate.name, reason=".NET solution file"))
    for candidate in sorted(root.glob("*.csproj")):
        detected.append(DetectedFile(path=candidate.name, reason=".NET project file"))
    return detected


def detect_package_managers(root: Path) -> list[str]:
    managers: list[str] = []
    markers = [
        ("pyproject.toml", "Python packaging"),
        ("requirements.txt", "pip"),
        ("poetry.lock", "Poetry"),
        ("Pipfile", "Pipenv"),
        ("package-lock.json", "npm"),
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "Yarn"),
        ("pom.xml", "Maven"),
        ("build.gradle", "Gradle"),
        ("Cargo.toml", "Cargo"),
        ("go.mod", "Go Modules"),
    ]
    for file_name, label in markers:
        if (root / file_name).exists() and label not in managers:
            managers.append(label)
    return managers


def detect_source_roots(root: Path) -> list[str]:
    candidates = ["src", "app", "pages", "lib", "components", "api", "server"]
    return [name for name in candidates if (root / name).is_dir()]


def detect_test_roots(root: Path) -> list[str]:
    candidates = ["tests", "test", "__tests__", "spec", "e2e"]
    return [name for name in candidates if (root / name).is_dir()]


def read_pyproject(root: Path) -> dict:
    path = root / "pyproject.toml"
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def read_package_json(root: Path) -> dict:
    path = root / "package.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def detect_python_stack(root: Path) -> tuple[list[str], list[str], list[str]]:
    frameworks: list[str] = []
    build_tools: list[str] = []
    test_frameworks: list[str] = []
    pyproject = read_pyproject(root)
    deps: list[str] = []
    project = pyproject.get("project", {}) if isinstance(pyproject, dict) else {}
    deps.extend(project.get("dependencies", []) or [])
    optional = project.get("optional-dependencies", {}) or {}
    for values in optional.values():
        deps.extend(values or [])
    deps_text = "\n".join(str(item).lower() for item in deps)
    if "typer" in deps_text:
        frameworks.append("Typer")
    if "textual" in deps_text:
        frameworks.append("Textual")
    if "rich" in deps_text:
        frameworks.append("Rich")
    if "fastapi" in deps_text:
        frameworks.append("FastAPI")
    if "django" in deps_text:
        frameworks.append("Django")
    if "flask" in deps_text:
        frameworks.append("Flask")
    if "pytest" in deps_text or (root / "pytest.ini").exists() or (root / "tests").is_dir():
        test_frameworks.append("pytest")
    if pyproject:
        build_system = pyproject.get("build-system", {}) or {}
        requires = "\n".join(build_system.get("requires", []) or []).lower()
        if "setuptools" in requires:
            build_tools.append("setuptools")
        if "poetry" in requires:
            build_tools.append("Poetry")
    return frameworks, build_tools, test_frameworks


def detect_node_stack(root: Path) -> tuple[list[str], list[str], list[str]]:
    frameworks: list[str] = []
    build_tools: list[str] = []
    test_frameworks: list[str] = []
    package = read_package_json(root)
    deps = {}
    deps.update(package.get("dependencies", {}) or {})
    deps.update(package.get("devDependencies", {}) or {})
    names = {str(name).lower() for name in deps}
    if "next" in names:
        frameworks.append("Next.js")
    if "react" in names:
        frameworks.append("React")
    if "vue" in names:
        frameworks.append("Vue")
    if "@angular/core" in names:
        frameworks.append("Angular")
    if "vite" in names or (root / "vite.config.ts").exists() or (root / "vite.config.js").exists():
        build_tools.append("Vite")
    if "typescript" in names or (root / "tsconfig.json").exists():
        build_tools.append("TypeScript")
    if "jest" in names:
        test_frameworks.append("Jest")
    if "vitest" in names:
        test_frameworks.append("Vitest")
    if "playwright" in names or "@playwright/test" in names:
        test_frameworks.append("Playwright")
    return frameworks, build_tools, test_frameworks


def detect_dotnet_stack(root: Path) -> tuple[list[str], list[str], list[str]]:
    frameworks: list[str] = []
    build_tools: list[str] = []
    test_frameworks: list[str] = []
    if list(root.glob("*.sln")) or list(root.rglob("*.csproj")):
        build_tools.append("dotnet CLI")
    for csproj in root.rglob("*.csproj"):
        if should_ignore(csproj):
            continue
        text = csproj.read_text(encoding="utf-8", errors="ignore").lower()
        if "microsoft.aspnetcore" in text or "web.sdk" in text:
            frameworks.append("ASP.NET Core")
        if "xunit" in text:
            test_frameworks.append("xUnit")
        if "nunit" in text:
            test_frameworks.append("NUnit")
        if "mstest" in text:
            test_frameworks.append("MSTest")
    return frameworks, build_tools, test_frameworks


def unique_sorted(values: list[str]) -> list[str]:
    return sorted(set(values), key=lambda value: value.lower())
