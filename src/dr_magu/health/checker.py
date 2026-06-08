from __future__ import annotations

from pathlib import Path

from .models import HealthCheckResult, HealthReport


REQUIRED_PACKAGES = [
    "agents",
    "brain",
    "commands",
    "contracts",
    "permissions",
    "plugins",
    "project_context",
    "scanner",
    "sessions",
    "tools",
    "tui",
    "workflows",
]


REQUIRED_CONFIG_FILES = [
    "config/models.yaml",
    "config/agents.yaml",
]


REQUIRED_PLUGIN_PATHS = [
    "plugins/software-dev/plugin.yaml",
]


def _ok(name: str, message: str, **details: object) -> HealthCheckResult:
    return HealthCheckResult(name=name, status="pass", message=message, details=dict(details))


def _fail(name: str, message: str, **details: object) -> HealthCheckResult:
    return HealthCheckResult(name=name, status="fail", message=message, details=dict(details))


def run_health_checks(project_root: str | Path) -> HealthReport:
    root = Path(project_root).resolve()
    checks: list[HealthCheckResult] = []

    src_root = root / "src" / "dr_magu"
    checks.append(_ok("project_root", "Project root resolved.", path=str(root)) if src_root.exists() else _fail("project_root", "src/dr_magu was not found.", path=str(root)))

    missing_packages = [name for name in REQUIRED_PACKAGES if not (src_root / name).exists()]
    if missing_packages:
        checks.append(_fail("package_structure", "Required runtime packages are missing.", missing=missing_packages))
    else:
        checks.append(_ok("package_structure", "Required runtime packages are present.", count=len(REQUIRED_PACKAGES)))

    missing_config = [path for path in REQUIRED_CONFIG_FILES if not (root / path).exists()]
    if missing_config:
        checks.append(_fail("configuration", "Required configuration files are missing.", missing=missing_config))
    else:
        checks.append(_ok("configuration", "Required configuration files are present.", count=len(REQUIRED_CONFIG_FILES)))

    missing_plugins = [path for path in REQUIRED_PLUGIN_PATHS if not (root / path).exists()]
    if missing_plugins:
        checks.append(_fail("plugins", "Required default plugin files are missing.", missing=missing_plugins))
    else:
        checks.append(_ok("plugins", "Default plugin files are present.", count=len(REQUIRED_PLUGIN_PATHS)))

    pycache_entries = [str(path.relative_to(root)) for path in root.rglob("__pycache__")]
    pyc_entries = [str(path.relative_to(root)) for path in root.rglob("*.pyc")]
    if pycache_entries or pyc_entries:
        checks.append(_fail("release_cleanliness", "Generated Python cache artifacts were found.", pycache=pycache_entries[:10], pyc=pyc_entries[:10]))
    else:
        checks.append(_ok("release_cleanliness", "No Python cache artifacts found."))

    status = "healthy" if all(check.status == "pass" for check in checks) else "unhealthy"
    return HealthReport(status=status, checks=checks)
