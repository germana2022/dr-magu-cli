
from dataclasses import dataclass

@dataclass
class WorkerJob:
    job_id: str
    status: str = "queued"
