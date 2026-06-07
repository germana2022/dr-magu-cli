
from __future__ import annotations
import platform
from pathlib import Path

def get_platform_info() -> dict:
    return {
        "os": platform.system(),
        "release": platform.release(),
        "python": platform.python_version(),
    }

def normalize_path(path: str) -> str:
    return str(Path(path).expanduser().resolve())
