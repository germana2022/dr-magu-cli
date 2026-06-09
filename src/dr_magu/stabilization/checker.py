from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .models import STATUS_FAIL, STATUS_PASS, STATUS_WARN, StabilizationCheck, StabilizationReport


REQUIRED_PACKAGES = [
    "agents",
    "brain",
    "commands",
    "config",
    "filesystem_tools",
    "git_tools",
    "hitl",
    "permissions",
    "plugins",
    "reports",
    "research",
    "scheduler",
    "sdlc",
    "shell_tools",
    "tools",
    "workflow_engine",
    "website_builder",
]

REQUIRED_PLUGINS = [
    "approval",
    "background-worker",
    "reporting",
    "research",
    "scheduler",
    "software-dev",
    "software-development",
    "website-builder",
    "workflow-engine",
]

REQUIRED_COMMAND_MARKERS = [
    'name="brain.context"',
    'name="research.search"',
    'name="report.create"',
    'name="approval.request"',
    'name="schedule.create"',
    'name="sdlc.agent.run"',
    'name="website.build"',
    'name="workflow.engine.run"',
    'name="workflow.runtime.inspect"',
]


def _check(name: str, passed: bool, message: str, details: dict | None = None, warn: bool = False) -> StabilizationCheck:
    if passed:
        status = STATUS_PASS
    elif warn:
        status = STATUS_WARN
    else:
        status = STATUS_FAIL
    return StabilizationCheck(name=name, status=status, message=message, details=details or {})


class PlatformStabilizationChecker:
    """Run platform readiness checks before v1.0.0."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self.src_root = self.project_root / "src" / "dr_magu"

    def run(self) -> StabilizationReport:
        checks = [
            self.check_required_packages(),
            self.check_required_plugins(),
            self.check_command_registry(),
            self.check_clean_artifacts(),
            self.check_documentation(),
            self.check_validation_file(),
        ]

        status = STATUS_PASS
        if any(check.status == STATUS_FAIL for check in checks):
            status = STATUS_FAIL
        elif any(check.status == STATUS_WARN for check in checks):
            status = STATUS_WARN

        return StabilizationReport(version="0.22.0", status=status, checks=checks)

    def check_required_packages(self) -> StabilizationCheck:
        missing = [name for name in REQUIRED_PACKAGES if not (self.src_root / name).exists()]
        return _check(
            "required_packages",
            not missing,
            "Required runtime packages are present." if not missing else "Required runtime packages are missing.",
            {"missing": missing, "required": REQUIRED_PACKAGES},
        )

    def check_required_plugins(self) -> StabilizationCheck:
        plugins_root = self.project_root / "plugins"
        missing = [name for name in REQUIRED_PLUGINS if not (plugins_root / name / "plugin.yaml").exists()]
        return _check(
            "required_plugins",
            not missing,
            "Required plugin manifests are present." if not missing else "Required plugin manifests are missing.",
            {"missing": missing, "required": REQUIRED_PLUGINS},
        )

    def check_command_registry(self) -> StabilizationCheck:
        registry_path = self.src_root / "commands" / "registry.py"
        text = registry_path.read_text(encoding="utf-8") if registry_path.exists() else ""
        missing = [marker for marker in REQUIRED_COMMAND_MARKERS if marker not in text]
        return _check(
            "command_registry",
            not missing,
            "Required command registry entries are present." if not missing else "Command registry entries are missing.",
            {"missing": missing, "required": REQUIRED_COMMAND_MARKERS},
        )

    def check_clean_artifacts(self) -> StabilizationCheck:
        pycache = [str(path.relative_to(self.project_root)) for path in self.project_root.rglob("__pycache__")]
        pyc = [str(path.relative_to(self.project_root)) for path in self.project_root.rglob("*.pyc")]
        return _check(
            "clean_artifacts",
            not pycache and not pyc,
            "No Python cache artifacts found." if not pycache and not pyc else "Python cache artifacts were found.",
            {"pycache": pycache[:20], "pyc": pyc[:20]},
        )

    def check_documentation(self) -> StabilizationCheck:
        readme = self.project_root / "README.md"
        changelog = self.project_root / "CHANGELOG.md"
        passed = readme.exists() and changelog.exists()
        return _check(
            "documentation",
            passed,
            "README and CHANGELOG are present." if passed else "README or CHANGELOG is missing.",
            {"readme": readme.exists(), "changelog": changelog.exists()},
        )

    def check_validation_file(self) -> StabilizationCheck:
        validation_files = sorted(self.project_root.glob("VALIDATION_v*.txt"))
        return _check(
            "validation_files",
            bool(validation_files),
            "Validation files are present." if validation_files else "No validation files were found.",
            {"files": [path.name for path in validation_files[-5:]]},
            warn=True,
        )
