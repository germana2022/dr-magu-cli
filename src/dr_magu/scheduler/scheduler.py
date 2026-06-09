
from pathlib import Path
import json

class SchedulerStore:
    def __init__(self, workspace):
        self.base = Path(workspace) / ".dr-magu" / "schedules"
        self.base.mkdir(parents=True, exist_ok=True)

    def create(self, name:str, cron:str, command:str):
        payload = {"name": name, "cron": cron, "command": command, "enabled": True}
        path = self.base / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def list(self):
        items=[]
        for f in self.base.glob("*.json"):
            items.append(json.loads(f.read_text(encoding="utf-8")))
        return items
