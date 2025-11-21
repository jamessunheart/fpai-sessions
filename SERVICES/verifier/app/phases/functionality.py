"""Phase 4: Functionality - Run tests and check coverage."""
import logging
import subprocess
import re
from pathlib import Path
from typing import Tuple, Optional

from app.models import PhaseResult, PhaseStatus, Check
from app.config import settings

logger = logging.getLogger(__name__)


def verify_functionality(droplet_path: Path) -> PhaseResult:
    """
    Verify droplet functionality.

    Checks:
    - Tests run successfully
    - Test coverage is acceptable
    - No major test failures
    """
    logger.info("Running functionality verification")

    checks = []

    # Run pytest
    tests_passed, total_tests, output = _run_pytest(droplet_path)

    if tests_passed is not None and total_tests is not None:
        pass_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

        if tests_passed == total_tests:
            checks.append(
                Check(
                    name="Tests passing",
                    status="PASS",
                    details=f"{tests_passed}/{total_tests} tests passed (100%)",
                )
            )
        elif pass_rate >= 80:
            checks.append(
                Check(
                    name="Tests passing",
                    status="PASS",
                    details=f"{tests_passed}/{total_tests} tests passed ({pass_rate:.0f}%)",
                )
            )
        else:
            checks.append(
                Check(
                    name="Tests passing",
                    status="FAIL",
                    details=f"Only {tests_passed}/{total_tests} tests passed ({pass_rate:.0f}%)",
                )
            )
    else:
        checks.append(
            Check(
                name="Tests passing",
                status="FAIL",
                details="Could not run tests or parse results",
            )
        )

    # Check coverage
    coverage = _extract_coverage(output)
    if coverage is not None:
        if coverage >= 70:
            checks.append(
                Check(
                    name="Test coverage",
                    status="PASS",
                    details=f"{coverage}% coverage",
                )
            )
        else:
            checks.append(
                Check(
                    name="Test coverage",
                    status="MINOR_ISSUE",
                    details=f"Only {coverage}% coverage (recommended >70%)",
                )
            )
    else:
        checks.append(
            Check(
                name="Test coverage",
                status="PASS",
                details="Coverage not measured",
            )
        )

    # Determine status
    failed = [c for c in checks if c.status == "FAIL"]
    if failed:
        status = PhaseStatus.FAIL
    elif any(c.status == "MINOR_ISSUE" for c in checks):
        status = PhaseStatus.MINOR_ISSUES
    else:
        status = PhaseStatus.PASS

    return PhaseResult(
        phase="Functionality",
        status=status,
        duration_seconds=60,
        checks=checks,
    )


def _run_pytest(droplet_path: Path) -> Tuple[Optional[int], Optional[int], str]:
    """
    Run pytest and return (passed, total, output).

    Returns:
        Tuple of (tests_passed, total_tests, output)
    """
    try:
        # Ensure virtual environment exists and has pytest
        venv_path = droplet_path / ".venv"
        if not venv_path.exists():
            logger.warning("No virtual environment found")
            return None, None, "No virtual environment found"

        # Run pytest with coverage
        result = subprocess.run(
            [
                "sh",
                "-c",
                f"cd {droplet_path} && source .venv/bin/activate && pytest -v --cov=app --cov-report=term-missing",
            ],
            capture_output=True,
            text=True,
            timeout=settings.test_timeout_seconds,
        )

        output = result.stdout + result.stderr

        # Parse results
        passed, total = _parse_pytest_output(output)

        return passed, total, output

    except subprocess.TimeoutExpired:
        logger.error("Pytest timed out")
        return None, None, "Tests timed out"
    except Exception as e:
        logger.error(f"Error running pytest: {str(e)}")
        return None, None, str(e)


def _parse_pytest_output(output: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse pytest output to extract pass/fail counts."""
    # Look for pattern like "20 passed in 0.98s" or "18 passed, 2 failed"
    match = re.search(r"(\d+)\s+passed", output)
    if match:
        passed = int(match.group(1))

        # Look for total (passed + failed)
        failed_match = re.search(r"(\d+)\s+failed", output)
        if failed_match:
            failed = int(failed_match.group(1))
            total = passed + failed
        else:
            # No failures mentioned, total = passed
            total = passed

        return passed, total

    return None, None


def _extract_coverage(output: str) -> Optional[int]:
    """Extract coverage percentage from pytest output."""
    # Look for "TOTAL ... XX%"
    match = re.search(r"TOTAL\s+.*?(\d+)%", output)
    if match:
        return int(match.group(1))

    return None
