
from __future__ import annotations
import platform

def default_shell() -> str:
    system = platform.system().lower()
    if system == "windows":
        return "powershell"
    return "bash"
