"""Phase 6: Decision - Make final verification decision."""
import logging
from typing import List, Tuple

from app.models import (
    Decision,
    PhaseResult,
    PhaseStatus,
    Issue,
    IssueSeverity,
)

logger = logging.getLogger(__name__)


def make_decision(
    phases: List[PhaseResult],
    all_issues: List[Issue],
) -> Tuple[Decision, List[str], List[str]]:
    """
    Make final verification decision based on all phases.

    Returns:
        Tuple of (decision, strengths, recommendations)

    Decision Logic:
    - FIXES_REQUIRED if:
        - Any critical issues
        - UDC compliance fails
        - Security fails
        - More than 2 important issues
        - Tests <80% passing
    - APPROVED if:
        - All critical checks pass
        - No important issues
        - Minor issues acceptable
    - APPROVED_WITH_NOTES if:
        - Critical checks pass
        - Some minor issues to learn from
    """
    logger.info("Making verification decision")

    # Count issues by severity
    critical_issues = [i for i in all_issues if i.severity == IssueSeverity.CRITICAL]
    important_issues = [i for i in all_issues if i.severity == IssueSeverity.IMPORTANT]
    minor_issues = [i for i in all_issues if i.severity == IssueSeverity.MINOR]

    # Check phase statuses
    failed_phases = [p for p in phases if p.status == PhaseStatus.FAIL]
    minor_issue_phases = [p for p in phases if p.status == PhaseStatus.MINOR_ISSUES]

    # Identify strengths
    strengths = _identify_strengths(phases)

    # Generate recommendations
    recommendations = _generate_recommendations(phases, all_issues)

    # Decision logic
    if critical_issues:
        logger.info(
            f"FIXES_REQUIRED: {len(critical_issues)} critical issue(s) found"
        )
        return Decision.FIXES_REQUIRED, strengths, recommendations

    if failed_phases:
        failed_names = [p.phase for p in failed_phases]
        logger.info(f"FIXES_REQUIRED: Failed phases: {failed_names}")
        return Decision.FIXES_REQUIRED, strengths, recommendations

    if len(important_issues) > 2:
        logger.info(
            f"FIXES_REQUIRED: {len(important_issues)} important issues (max 2 allowed)"
        )
        return Decision.FIXES_REQUIRED, strengths, recommendations

    if minor_issues or minor_issue_phases:
        logger.info("APPROVED_WITH_NOTES: Minor issues to address")
        return Decision.APPROVED_WITH_NOTES, strengths, recommendations

    logger.info("APPROVED: All checks passed")
    return Decision.APPROVED, strengths, recommendations


def _identify_strengths(phases: List[PhaseResult]) -> List[str]:
    """Identify what was done well."""
    strengths = []

    for phase in phases:
        if phase.status == PhaseStatus.PASS:
            # Look for specific achievements
            for check in phase.checks:
                if check.details:  # Check if details is not None
                    if check.status == "PASS" and "tests passed" in check.details.lower():
                        strengths.append(check.details)
                    elif check.status == "PASS" and "coverage" in check.details.lower():
                        strengths.append(f"Good test coverage: {check.details}")

    # General strengths based on passing phases
    passing_phases = [p.phase for p in phases if p.status == PhaseStatus.PASS]

    if "UDC Compliance" in passing_phases:
        strengths.append("Clean UDC compliance")

    if "Security" in passing_phases:
        strengths.append("No security issues found")

    if "Structure Scan" in passing_phases:
        strengths.append("Well-organized file structure")

    return strengths


def _generate_recommendations(
    phases: List[PhaseResult], all_issues: List[Issue]
) -> List[str]:
    """Generate recommendations for improvement."""
    recommendations = []

    # Group issues by category
    issue_categories = {}
    for issue in all_issues:
        if issue.category not in issue_categories:
            issue_categories[issue.category] = []
        issue_categories[issue.category].append(issue)

    # Generate recommendations based on issues
    for category, issues in issue_categories.items():
        if category == "code_quality" and len(issues) > 0:
            recommendations.append(
                f"Address {len(issues)} code quality issue(s) for cleaner code"
            )
        elif category == "security" and len(issues) > 0:
            recommendations.append(
                f"Fix {len(issues)} security issue(s) before deployment"
            )

    # Check for failed phases
    for phase in phases:
        if phase.status == PhaseStatus.FAIL:
            failed_checks = [c for c in phase.checks if c.status == "FAIL"]
            if failed_checks:
                rec = f"{phase.phase}: Fix {len(failed_checks)} failed check(s)"
                recommendations.append(rec)

    # Add general recommendations
    if not recommendations:
        recommendations.append("Consider adding more edge case tests")
        recommendations.append("Keep documentation up to date")

    return recommendations
