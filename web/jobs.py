"""In-memory job registry for background scrape/download/transcribe tasks."""
import asyncio
import time
import uuid
from typing import Optional

_jobs: dict[str, dict] = {}
_lock = asyncio.Lock()


async def create(job_type: str, channel_id: str, label: str = "") -> str:
    job_id = uuid.uuid4().hex[:12]
    async with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "type": job_type,
            "channel_id": channel_id,
            "label": label,
            "status": "running",
            "current": 0,
            "total": 0,
            "bytes_done": 0,
            "bytes_total": 0,
            "started_at": time.time(),
            "updated_at": time.time(),
            "finished_at": None,
            "result": None,
            "error": None,
        }
    return job_id


async def update(job_id: str, **fields) -> None:
    async with _lock:
        if job_id not in _jobs:
            return
        _jobs[job_id].update(fields)
        _jobs[job_id]["updated_at"] = time.time()


async def finish(job_id: str, result=None, error: Optional[str] = None) -> None:
    async with _lock:
        if job_id not in _jobs:
            return
        _jobs[job_id]["status"] = "error" if error else "done"
        _jobs[job_id]["finished_at"] = time.time()
        _jobs[job_id]["result"] = result
        _jobs[job_id]["error"] = error


def get(job_id: str) -> Optional[dict]:
    return _jobs.get(job_id)


def list_active() -> list[dict]:
    return [j for j in _jobs.values() if j["status"] == "running"]


def compute_eta(job: dict) -> Optional[float]:
    """Seconds remaining, based on current throughput. Uses bytes if known, else count."""
    if job["status"] != "running":
        return None
    elapsed = max(time.time() - job["started_at"], 0.001)
    if job["bytes_total"] > 0 and job["bytes_done"] > 0:
        rate = job["bytes_done"] / elapsed
        remaining = job["bytes_total"] - job["bytes_done"]
        return remaining / rate if rate > 0 else None
    if job["total"] > 0 and job["current"] > 0:
        rate = job["current"] / elapsed
        remaining = job["total"] - job["current"]
        return remaining / rate if rate > 0 else None
    return None
