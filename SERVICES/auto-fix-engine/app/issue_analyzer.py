"""Analyzes Verifier reports to identify fixable issues"""

from typing import List, Dict, Any
from .models import Issue, IssueType


class IssueAnalyzer:
    """Analyzes Verifier reports and extracts fixable issues"""

    def analyze_verification_report(self, report: Dict[str, Any]) -> List[Issue]:
        """
        Analyze a Verifier report and extract issues.

        Returns list of Issue objects prioritized by severity.
        """
        issues = []

        phases = report.get("phases", [])

        for phase in phases:
            phase_name = phase.get("phase", "Unknown")
            phase_status = phase.get("status", "")
            checks = phase.get("checks", [])

            # Analyze UDC Compliance failures
            if phase_name == "UDC Compliance" and phase_status == "FAIL":
                for check in checks:
                    if check.get("status") == "FAIL":
                        details = check.get("details", "")

                        if "failed to start" in details.lower():
                            issues.append(Issue(
                                type=IssueType.STARTUP_FAILURE,
                                severity="critical",
                                description=f"Service failed to start: {details}",
                                phase=phase_name,
                                details=check
                            ))

            # Analyze Functionality failures
            if phase_name == "Functionality" and phase_status == "FAIL":
                for check in checks:
                    if check.get("status") == "FAIL":
                        name = check.get("name", "")
                        details = check.get("details", "")

                        if "test" in name.lower():
                            issues.append(Issue(
                                type=IssueType.TEST_FAILURE,
                                severity="important",
                                description=f"Tests failing: {details}",
                                phase=phase_name,
                                details=check
                            ))

            # Analyze Code Quality issues
            if phase_name == "Code Quality":
                for check in checks:
                    status = check.get("status", "")
                    if status in ["FAIL", "MINOR_ISSUE"]:
                        name = check.get("name", "")
                        details = check.get("details", "")

                        issues.append(Issue(
                            type=IssueType.CODE_QUALITY,
                            severity="minor",
                            description=f"{name}: {details}",
                            phase=phase_name,
                            details=check
                        ))

            # Analyze Security issues
            if phase_name == "Security" and phase_status == "FAIL":
                for check in checks:
                    if check.get("status") == "FAIL":
                        issues.append(Issue(
                            type=IssueType.SECURITY,
                            severity="critical",
                            description=check.get("details", "Security issue"),
                            phase=phase_name,
                            details=check
                        ))

        # Sort by severity: critical > important > minor
        severity_order = {"critical": 0, "important": 1, "minor": 2}
        issues.sort(key=lambda x: severity_order.get(x.severity, 3))

        return issues

    def prioritize_issues(self, issues: List[Issue]) -> List[Issue]:
        """
        Prioritize issues for fixing.

        Critical issues (startup, security) first, then important, then minor.
        """
        critical = [i for i in issues if i.severity == "critical"]
        important = [i for i in issues if i.severity == "important"]
        minor = [i for i in issues if i.severity == "minor"]

        return critical + important + minor

    def can_auto_fix(self, issue: Issue) -> bool:
        """Determine if an issue can be automatically fixed"""

        # Can auto-fix most code quality issues
        if issue.type == IssueType.CODE_QUALITY:
            return True

        # Can try to fix startup failures (often import/dependency issues)
        if issue.type == IssueType.STARTUP_FAILURE:
            return True

        # Can try to fix test failures
        if issue.type == IssueType.TEST_FAILURE:
            return True

        # Can add missing dependencies
        if issue.type == IssueType.DEPENDENCY_MISSING:
            return True

        # Can fix some import errors
        if issue.type == IssueType.IMPORT_ERROR:
            return True

        # Security issues need manual review
        if issue.type == IssueType.SECURITY:
            return False

        return True
