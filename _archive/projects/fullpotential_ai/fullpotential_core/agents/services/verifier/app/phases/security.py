"""Phase 3: Security - Check for vulnerabilities."""
import logging
import re
from pathlib import Path
from typing import List

from app.models import PhaseResult, PhaseStatus, Check, Issue, IssueSeverity

logger = logging.getLogger(__name__)


def verify_security(droplet_path: Path) -> PhaseResult:
    """
    Verify security of droplet code.

    Checks:
    - No hardcoded secrets
    - Environment variables used correctly
    - Input validation present
    - No SQL injection patterns
    """
    logger.info("Running security verification")

    checks: List[Check] = []
    issues: List[Issue] = []

    # Check for hardcoded secrets
    secret_issues = _scan_for_secrets(droplet_path)
    if secret_issues:
        issues.extend(secret_issues)
        checks.append(
            Check(
                name="No hardcoded secrets",
                status="FAIL",
                details=f"Found {len(secret_issues)} potential hardcoded secrets",
            )
        )
    else:
        checks.append(Check(name="No hardcoded secrets", status="PASS"))

    # Check environment variable usage
    if _check_env_usage(droplet_path):
        checks.append(Check(name="Environment variables", status="PASS"))
    else:
        checks.append(
            Check(
                name="Environment variables",
                status="FAIL",
                details="Not using pydantic-settings for config",
            )
        )
        issues.append(
            Issue(
                severity=IssueSeverity.IMPORTANT,
                category="security",
                message="Should use pydantic-settings for configuration",
                suggestion="Use BaseSettings from pydantic-settings",
            )
        )

    # Check input validation
    if _check_input_validation(droplet_path):
        checks.append(Check(name="Input validation", status="PASS"))
    else:
        checks.append(
            Check(
                name="Input validation",
                status="FAIL",
                details="Not using Pydantic models for validation",
            )
        )

    # Check for SQL injection patterns
    sql_issues = _check_sql_injection(droplet_path)
    if sql_issues:
        issues.extend(sql_issues)
        checks.append(
            Check(
                name="SQL injection prevention",
                status="FAIL",
                details=f"Found {len(sql_issues)} potential SQL injection vulnerabilities",
            )
        )
    else:
        checks.append(Check(name="SQL injection prevention", status="PASS"))

    # Determine status
    critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
    failed_checks = [c for c in checks if c.status == "FAIL"]

    if critical_issues or failed_checks:
        status = PhaseStatus.FAIL
    else:
        status = PhaseStatus.PASS

    return PhaseResult(
        phase="Security",
        status=status,
        duration_seconds=15,
        checks=checks,
    )


def _scan_for_secrets(droplet_path: Path) -> List[Issue]:
    """Scan for hardcoded secrets."""
    issues = []

    # Patterns to search for
    secret_patterns = [
        (r'password\s*=\s*["\'](?!.*example)(.+)["\']', "password"),
        (r'secret\s*=\s*["\'](?!.*example)(.+)["\']', "secret"),
        (r'api_key\s*=\s*["\'](?!.*example)(.+)["\']', "api_key"),
        (r'sk-[a-zA-Z0-9]{20,}', "api_key"),  # OpenAI/Anthropic key pattern
        (r'-----BEGIN.*PRIVATE KEY-----', "private_key"),
    ]

    # Search Python files
    for py_file in droplet_path.rglob("*.py"):
        # Skip test files and example files
        if "test" in py_file.name or "example" in py_file.name or ".venv" in str(py_file):
            continue

        try:
            content = py_file.read_text()

            for pattern, secret_type in secret_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    issues.append(
                        Issue(
                            severity=IssueSeverity.CRITICAL,
                            category="security",
                            file=str(py_file.relative_to(droplet_path)),
                            line=line_num,
                            message=f"Potential hardcoded {secret_type} found",
                            suggestion="Move to environment variables",
                        )
                    )
        except Exception as e:
            logger.warning(f"Error reading {py_file}: {str(e)}")

    return issues


def _check_env_usage(droplet_path: Path) -> bool:
    """Check if using pydantic-settings for config."""
    config_file = droplet_path / "app" / "config.py"

    if not config_file.exists():
        return False

    content = config_file.read_text()

    # Look for pydantic-settings usage
    return (
        "pydantic_settings" in content or "pydantic.settings" in content
    ) and "BaseSettings" in content


def _check_input_validation(droplet_path: Path) -> bool:
    """Check if using Pydantic models for input validation."""
    models_file = droplet_path / "app" / "models.py"

    if not models_file.exists():
        return False

    content = models_file.read_text()

    # Look for Pydantic BaseModel usage
    return "BaseModel" in content and "from pydantic import" in content


def _check_sql_injection(droplet_path: Path) -> List[Issue]:
    """Check for SQL injection vulnerabilities."""
    issues = []

    # SQL injection patterns (string formatting in queries)
    injection_patterns = [
        (r'f"SELECT.*\{', "f-string in SQL query"),
        (r"f'SELECT.*\{", "f-string in SQL query"),
        (r'%s.*SELECT', "string formatting in SQL query"),
        (r'\.format.*SELECT', ".format() in SQL query"),
    ]

    # Search Python files
    for py_file in droplet_path.rglob("*.py"):
        if ".venv" in str(py_file):
            continue

        try:
            content = py_file.read_text()

            for pattern, issue_type in injection_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[: match.start()].count("\n") + 1
                    issues.append(
                        Issue(
                            severity=IssueSeverity.CRITICAL,
                            category="security",
                            file=str(py_file.relative_to(droplet_path)),
                            line=line_num,
                            message=f"Potential SQL injection: {issue_type}",
                            suggestion="Use parameterized queries",
                        )
                    )
        except Exception as e:
            logger.warning(f"Error reading {py_file}: {str(e)}")

    return issues
