from __future__ import annotations

from pathlib import Path
from typing import Any
import os
import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(config_path: str | None = None) -> dict[str, Any]:
    path = Path(config_path or os.getenv("REPO_AGENT_CONFIG", "config/orchestration.yaml"))
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def default_workspace() -> str:
    return os.getenv("REPO_AGENT_WORKSPACE", ".")
