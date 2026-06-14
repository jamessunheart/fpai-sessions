from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from core.config import settings

_REGISTRY_TEMPLATE: Dict[str, Any] = {"version": 1, "jobs": []}


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _load_registry() -> Dict[str, Any]:
    registry_file = settings.job_registry_file
    if not registry_file.exists():
        return {"version": 1, "jobs": []}

    try:
        with open(registry_file, "r") as fh:
            data = json.load(fh)
            if "jobs" not in data:
                data["jobs"] = []
            return data
    except json.JSONDecodeError:
        # Corrupted file; keep backup and reset
        backup = registry_file.with_suffix(".bak")
        registry_file.rename(backup)
        return {"version": 1, "jobs": []}


def _save_registry(data: Dict[str, Any]) -> None:
    registry_file = settings.job_registry_file
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_file, "w") as fh:
        json.dump(data, fh, indent=2)


def job_state_path(job_id: str) -> Path:
    return settings.jobs_dir / f"{job_id}.json"


def create_job(
    *,
    apprentice: str,
    repo_url: str,
    mission_id: Optional[str] = None,
    mode: str = "gatekeeper",
    source: str = "web",
    status: str = "queued",
    metadata: Optional[Dict[str, Any]] = None,
    job_id: Optional[str] = None,
    started_at: Optional[str] = None,
) -> Dict[str, Any]:
    registry = _load_registry()
    job_id = job_id or str(uuid4())
    record = {
        "job_id": job_id,
        "apprentice": apprentice,
        "mission_id": mission_id,
        "repo_url": repo_url,
        "mode": mode,
        "source": source,
        "status": status,
        "score": None,
        "breakdown": {},
        "started_at": started_at or _now(),
        "finished_at": None,
        "logs_path": str(job_state_path(job_id)),
        "metadata": metadata or {},
        "updated_at": _now(),
    }
    registry["jobs"].append(record)
    _save_registry(registry)
    return record


def update_job(job_id: str, **updates: Any) -> Optional[Dict[str, Any]]:
    registry = _load_registry()
    for job in registry["jobs"]:
        if job["job_id"] == job_id:
            metadata_update = updates.pop("metadata", None)
            if metadata_update:
                if isinstance(metadata_update, dict):
                    job.setdefault("metadata", {}).update(metadata_update)
                else:
                    job["metadata"] = metadata_update
            job.update(updates)
            job["updated_at"] = _now()
            if updates.get("status") in {"completed", "failed"} and job.get("finished_at") is None:
                job["finished_at"] = _now()
            _save_registry(registry)
            return job
    return None


def append_log(job_id: str, line: str) -> Path:
    logs_dir = settings.job_logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"{job_id}.log"
    with open(log_file, "a") as fh:
        fh.write(f"{_now()} {line.strip()}\n")
    return log_file


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    registry = _load_registry()
    for job in registry["jobs"]:
        if job["job_id"] == job_id:
            return job
    return None


def list_jobs(
    *,
    limit: Optional[int] = None,
    apprentice: Optional[str] = None,
    mission_id: Optional[str] = None,
    source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    registry = _load_registry()
    jobs = registry["jobs"]

    def _matches(job: Dict[str, Any]) -> bool:
        if apprentice and job.get("apprentice") != apprentice:
            return False
        if mission_id and job.get("mission_id") != mission_id:
            return False
        if source and job.get("source") != source:
            return False
        return True

    filtered = [job for job in jobs if _matches(job)]
    filtered.sort(key=lambda j: j.get("started_at", ""), reverse=True)

    if limit:
        return filtered[:limit]
    return filtered

