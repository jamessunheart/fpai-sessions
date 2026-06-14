from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Centralized filesystem + service paths."""

    root_dir: Path
    data_dir: Path
    jobs_dir: Path
    job_logs_dir: Path
    job_registry_file: Path
    feedback_dir: Path
    apprentice_submissions_json: Path
    apprentice_submissions_log: Path


def _resolve_root() -> Path:
    env_root = os.environ.get("FPAI_ROOT")
    if env_root:
        return Path(env_root).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def _ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def load_settings() -> Settings:
    root = _resolve_root()
    data_dir = root / "data"
    jobs_dir = data_dir / "harvester-jobs"
    job_logs_dir = jobs_dir / "logs"
    job_registry_file = jobs_dir / "registry.json"
    feedback_dir = data_dir / "apprentice-feedback"
    submissions_json = root / "docs" / "coordination" / "apprentice-submissions.json"
    submissions_log = root / "docs" / "coordination" / "apprentice-submissions.log"

    _ensure_dirs(data_dir, jobs_dir, job_logs_dir, feedback_dir, submissions_json.parent, submissions_log.parent)

    return Settings(
        root_dir=root,
        data_dir=data_dir,
        jobs_dir=jobs_dir,
        job_logs_dir=job_logs_dir,
        job_registry_file=job_registry_file,
        feedback_dir=feedback_dir,
        apprentice_submissions_json=submissions_json,
        apprentice_submissions_log=submissions_log,
    )


settings = load_settings()


