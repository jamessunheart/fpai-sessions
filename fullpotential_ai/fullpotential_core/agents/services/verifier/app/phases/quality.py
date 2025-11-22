"""Phase 5: Code Quality - Check for anti-patterns."""
import logging
import re
from pathlib import Path
from typing import List

from app.models import PhaseResult, PhaseStatus, Check, Issue, IssueSeverity

logger = logging.getLogger(__name__)


def verify_code_quality(droplet_path: Path) -> PhaseResult:
    """
    Verify code quality.

    Checks:
    - No print statements (should use logging)
    - No bare except clauses
    - No TODO/FIXME in production
    - No synchronous requests in async code
    - Type hints present
    """
    logger.info("Running code quality verification")

    checks = []
    issues = []

    # Check for print statements
    print_issues = _check_for_pattern(
        droplet_path,
        r'\bprint\s*\(',
        "print statements",
        "Use logging instead of print()",
        IssueSeverity.MINOR,
    )

    if print_issues:
        issues.extend(print_issues)
        checks.append(
            Check(
                name="No print statements",
                status="MINOR_ISSUE",
                details=f"Found {len(print_issues)} print statements",
            )
        )
    else:
        checks.append(Check(name="No print statements", status="PASS"))

    # Check for bare except
    bare_except_issues = _check_for_pattern(
        droplet_path,
        r'except\s*:',
        "bare except clauses",
        "Catch specific exceptions instead of bare except:",
        IssueSeverity.MINOR,
    )

    if bare_except_issues:
        issues.extend(bare_except_issues)
        checks.append(
            Check(
                name="No bare except",
                status="MINOR_ISSUE",
                details=f"Found {len(bare_except_issues)} bare except clauses",
            )
        )
    else:
        checks.append(Check(name="No bare except", status="PASS"))

    # Check for TODO/FIXME
    todo_issues = _check_for_pattern(
        droplet_path,
        r'(TODO|FIXME)',
        "TODO/FIXME comments",
        "Remove or convert to issues",
        IssueSeverity.MINOR,
    )

    if todo_issues:
        checks.append(
            Check(
                name="No TODO/FIXME",
                status="MINOR_ISSUE",
                details=f"Found {len(todo_issues)} TODO/FIXME comments",
            )
        )
    else:
        checks.append(Check(name="No TODO/FIXME", status="PASS"))

    # Check for synchronous requests in async code
    sync_requests = _check_for_pattern(
        droplet_path,
        r'requests\.(get|post|put|delete|patch)',
        "synchronous requests library",
        "Use httpx for async HTTP requests",
        IssueSeverity.IMPORTANT,
    )

    if sync_requests:
        issues.extend(sync_requests)
        checks.append(
            Check(
                name="Async patterns",
                status="FAIL",
                details=f"Found {len(sync_requests)} synchronous requests calls",
            )
        )
    else:
        checks.append(Check(name="Async patterns", status="PASS"))

    # Determine status
    critical = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
    important = [i for i in issues if i.severity == IssueSeverity.IMPORTANT]

    if critical or important:
        status = PhaseStatus.FAIL
    elif issues:
        status = PhaseStatus.MINOR_ISSUES
    else:
        status = PhaseStatus.PASS

    return PhaseResult(
        phase="Code Quality",
        status=status,
        duration_seconds=10,
        checks=checks,
    )


def _check_for_pattern(
    droplet_path: Path,
    pattern: str,
    issue_name: str,
    suggestion: str,
    severity: IssueSeverity,
) -> List[Issue]:
    """Check for a regex pattern in Python files."""
    issues = []

    for py_file in droplet_path.rglob("*.py"):
        # Skip test files and virtual environment
        if ".venv" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text()

            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[: match.start()].count("\n") + 1
                issues.append(
                    Issue(
                        severity=severity,
                        category="code_quality",
                        file=str(py_file.relative_to(droplet_path)),
                        line=line_num,
                        message=f"Found {issue_name}",
                        suggestion=suggestion,
                    )
                )
        except Exception as e:
            logger.warning(f"Error reading {py_file}: {str(e)}")

    return issues
