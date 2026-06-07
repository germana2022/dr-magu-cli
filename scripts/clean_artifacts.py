
from pathlib import Path
import shutil

for pattern in ["__pycache__", ".pytest_cache"]:
    for p in Path(".").rglob(pattern):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)

for p in Path(".").rglob("*.pyc"):
    p.unlink(missing_ok=True)

print("Artifacts cleaned.")
