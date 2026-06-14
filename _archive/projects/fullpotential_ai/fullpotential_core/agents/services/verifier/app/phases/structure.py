"""Phase 1: Structure Scan - Verify file and directory structure."""
import logging
from pathlib import Path
from typing import List

from app.models import PhaseResult, PhaseStatus, Check

logger = logging.getLogger(__name__)


def verify_structure(droplet_path: Path) -> PhaseResult:
    """
    Verify droplet file structure.

    Checks:
    - Required files exist (main.py, models.py, etc.)
    - Directory structure is correct
    - Basic file organization
    """
    logger.info(f"Running structure verification for {droplet_path}")

    checks: List[Check] = []

    # Required files
    required_files = [
        "app/main.py",
        "app/models.py",
        "requirements.txt",
        ".gitignore",
    ]

    for file_path in required_files:
        full_path = droplet_path / file_path
        if full_path.exists():
            checks.append(
                Check(name=f"File exists: {file_path}", status="PASS")
            )
        else:
            checks.append(
                Check(
                    name=f"File exists: {file_path}",
                    status="FAIL",
                    details=f"Missing required file: {file_path}",
                )
            )

    # Required directories
    required_dirs = [
        "app",
        "tests",
    ]

    for dir_path in required_dirs:
        full_path = droplet_path / dir_path
        if full_path.is_dir():
            checks.append(
                Check(name=f"Directory exists: {dir_path}", status="PASS")
            )
        else:
            checks.append(
                Check(
                    name=f"Directory exists: {dir_path}",
                    status="FAIL",
                    details=f"Missing required directory: {dir_path}",
                )
            )

    # Check for common files
    optional_files = [
        ".env.example",
        "Dockerfile",
        "README.md",
        "pytest.ini",
    ]

    for file_path in optional_files:
        full_path = droplet_path / file_path
        if full_path.exists():
            checks.append(
                Check(
                    name=f"Optional file: {file_path}",
                    status="PASS",
                    details="Present",
                )
            )

    # Determine overall status
    failed_checks = [c for c in checks if c.status == "FAIL"]

    if failed_checks:
        status = PhaseStatus.FAIL
    else:
        status = PhaseStatus.PASS

    return PhaseResult(
        phase="Structure Scan",
        status=status,
        duration_seconds=1,
        checks=checks,
    )
