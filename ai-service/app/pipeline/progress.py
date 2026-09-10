"""In-memory pipeline progress for UI polling."""

from threading import Lock
from typing import Any

_lock = Lock()
_jobs: dict[str, dict[str, Any]] = {}


def init_job(job_id: str) -> None:
    with _lock:
        _jobs[job_id] = {
            "status": "running",
            "step": "starting",
            "message": "Starting pipeline...",
            "percent": 0,
            "requirementTotal": 0,
            "requirementDone": 0,
        }


def update_job(job_id: str | None, **fields: Any) -> None:
    if not job_id:
        return
    with _lock:
        job = _jobs.setdefault(
            job_id,
            {
                "status": "running",
                "step": "starting",
                "message": "",
                "percent": 0,
                "requirementTotal": 0,
                "requirementDone": 0,
            },
        )
        job.update(fields)


def complete_job(job_id: str | None) -> None:
    if not job_id:
        return
    update_job(
        job_id,
        status="completed",
        step="complete",
        message="Pipeline complete",
        percent=100,
    )


def fail_job(job_id: str | None, message: str) -> None:
    if not job_id:
        return
    update_job(job_id, status="error", step="error", message=message)


def get_job(job_id: str) -> dict[str, Any]:
    with _lock:
        return _jobs.get(job_id, {"status": "unknown", "message": "No active job"})


def clear_job(job_id: str) -> None:
    with _lock:
        _jobs.pop(job_id, None)
