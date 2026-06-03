from __future__ import annotations

import json
from pathlib import Path

from dr_magu.scanner.models import RepositoryScan


def write_latest_scan(workspace_path: str, scan: RepositoryScan) -> Path:
    """Persist the latest repository scan under the workspace .dr-magu directory."""
    root = Path(workspace_path).resolve()
    output_dir = root / ".dr-magu" / "scans"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "latest-scan.json"
    output_path.write_text(json.dumps(scan.model_dump(), indent=2), encoding="utf-8")
    return output_path
