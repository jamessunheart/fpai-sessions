#!/usr/bin/env python3
"""
ARIA ULTRA POWER - SELF ANALYZER
==================================

Analyze own performance and identify improvements:
- Response time analysis
- Error detection
- Capability gap identification
- Performance benchmarking
"""

import sqlite3
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("aria.evolution.self_analyze")

STATE_DIR = Path("/opt/fpai/aria-command/state")
LOGS_DB = STATE_DIR / "interactions.db"


@dataclass
class PerformanceMetric:
    """A performance metric."""
    name: str
    value: float
    target: float
    unit: str
    status: str  # "good", "warning", "bad"
    trend: str  # "improving", "stable", "declining"


@dataclass
class IssueDetection:
    """A detected issue."""
    issue_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    frequency: int
    first_seen: float
    last_seen: float
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class CapabilityGap:
    """A detected capability gap."""
    capability: str
    user_requests: int
    failed_attempts: int
    description: str
    implementation_effort: str  # "trivial", "small", "medium", "large"
    priority: int  # 1-10


@dataclass
class PerformanceReport:
    """Complete performance analysis report."""
    period_hours: int
    total_interactions: int
    success_rate: float
    avg_response_time_ms: float
    metrics: List[PerformanceMetric]
    issues: List[IssueDetection]
    capability_gaps: List[CapabilityGap]
    improvement_suggestions: List[str]
    overall_score: float  # 0-100
    generated_at: float = field(default_factory=time.time)


class SelfAnalyzer:
    """
    Analyze Aria's own performance.
    
    Features:
    - Response time tracking
    - Error pattern detection
    - Capability gap identification
    - Trend analysis
    """
    
    def __init__(self):
        self._target_metrics = {
            "avg_response_time": 5000,  # ms
            "success_rate": 95,  # %
            "tool_accuracy": 90,  # %
            "user_satisfaction": 80,  # % (inferred)
        }
        
        logger.info("SelfAnalyzer initialized")
    
    def analyze(self, hours: int = 24) -> PerformanceReport:
        """Run full performance analysis."""
        cutoff = time.time() - (hours * 3600)
        
        # Get interaction data
        interactions = self._get_interactions(cutoff)
        
        # Calculate metrics
        metrics = self._calculate_metrics(interactions)
        
        # Detect issues
        issues = self._detect_issues(interactions)
        
        # Find capability gaps
        gaps = self._find_capability_gaps(interactions)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(metrics, issues, gaps)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(metrics, issues)
        
        return PerformanceReport(
            period_hours=hours,
            total_interactions=len(interactions),
            success_rate=self._get_metric_value(metrics, "success_rate"),
            avg_response_time_ms=self._get_metric_value(metrics, "avg_response_time"),
            metrics=metrics,
            issues=issues,
            capability_gaps=gaps,
            improvement_suggestions=suggestions,
            overall_score=overall_score,
        )
    
    def _get_interactions(self, since: float) -> List[Dict]:
        """Get interaction records from database."""
        interactions = []
        
        try:
            if LOGS_DB.exists():
                conn = sqlite3.connect(LOGS_DB)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM interactions 
                    WHERE timestamp > ?
                    ORDER BY timestamp DESC
                """, (since,))
                
                for row in cursor.fetchall():
                    interactions.append(dict(row))
                
                conn.close()
        except Exception as e:
            logger.error(f"Failed to get interactions: {e}")
        
        return interactions
    
    def _calculate_metrics(self, interactions: List[Dict]) -> List[PerformanceMetric]:
        """Calculate performance metrics."""
        metrics = []
        
        if not interactions:
            return metrics
        
        # Response time
        response_times = [i.get("response_time_ms", 0) for i in interactions if i.get("response_time_ms")]
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            target = self._target_metrics["avg_response_time"]
            status = "good" if avg_time < target else "warning" if avg_time < target * 1.5 else "bad"
            
            metrics.append(PerformanceMetric(
                name="avg_response_time",
                value=avg_time,
                target=target,
                unit="ms",
                status=status,
                trend=self._calculate_trend(response_times),
            ))
        
        # Success rate
        successful = sum(1 for i in interactions if i.get("success", True))
        success_rate = (successful / len(interactions) * 100) if interactions else 0
        target = self._target_metrics["success_rate"]
        status = "good" if success_rate >= target else "warning" if success_rate >= target * 0.9 else "bad"
        
        metrics.append(PerformanceMetric(
            name="success_rate",
            value=success_rate,
            target=target,
            unit="%",
            status=status,
            trend="stable",
        ))
        
        # Tool usage
        tool_uses = sum(1 for i in interactions if i.get("tools_used"))
        tool_rate = (tool_uses / len(interactions) * 100) if interactions else 0
        
        metrics.append(PerformanceMetric(
            name="tool_usage_rate",
            value=tool_rate,
            target=50,
            unit="%",
            status="good" if tool_rate >= 30 else "warning",
            trend="stable",
        ))
        
        return metrics
    
    def _detect_issues(self, interactions: List[Dict]) -> List[IssueDetection]:
        """Detect issues in interactions."""
        issues = []
        
        # Track error patterns
        error_counts = {}
        for i in interactions:
            if i.get("error"):
                error = i["error"]
                if error not in error_counts:
                    error_counts[error] = {
                        "count": 0,
                        "first": i["timestamp"],
                        "last": i["timestamp"],
                    }
                error_counts[error]["count"] += 1
                error_counts[error]["last"] = max(error_counts[error]["last"], i["timestamp"])
        
        for error, data in error_counts.items():
            if data["count"] >= 3:
                # Recurring error
                severity = "high" if data["count"] >= 10 else "medium" if data["count"] >= 5 else "low"
                
                issues.append(IssueDetection(
                    issue_type="recurring_error",
                    severity=severity,
                    description=f"Error occurring {data['count']} times: {error[:100]}",
                    frequency=data["count"],
                    first_seen=data["first"],
                    last_seen=data["last"],
                    suggested_fix=self._suggest_fix_for_error(error),
                    auto_fixable=self._is_auto_fixable(error),
                ))
        
        # Detect slow responses
        slow_responses = [i for i in interactions if i.get("response_time_ms", 0) > 10000]
        if len(slow_responses) >= 5:
            issues.append(IssueDetection(
                issue_type="slow_response",
                severity="medium",
                description=f"{len(slow_responses)} responses took over 10 seconds",
                frequency=len(slow_responses),
                first_seen=slow_responses[-1]["timestamp"] if slow_responses else time.time(),
                last_seen=slow_responses[0]["timestamp"] if slow_responses else time.time(),
                suggested_fix="Consider caching frequent queries or optimizing tool calls",
                auto_fixable=False,
            ))
        
        # Detect approval overhead
        approval_requests = [i for i in interactions if "approval" in str(i.get("response", "")).lower()]
        if len(approval_requests) >= 10:
            issues.append(IssueDetection(
                issue_type="approval_overhead",
                severity="low",
                description=f"Asking for approval {len(approval_requests)} times - may be over-cautious",
                frequency=len(approval_requests),
                first_seen=approval_requests[-1]["timestamp"] if approval_requests else time.time(),
                last_seen=approval_requests[0]["timestamp"] if approval_requests else time.time(),
                suggested_fix="Review and expand green-list commands for trusted operations",
                auto_fixable=True,
            ))
        
        return issues
    
    def _find_capability_gaps(self, interactions: List[Dict]) -> List[CapabilityGap]:
        """Find capability gaps from user requests."""
        gaps = []
        
        # Track failed or unsupported requests
        failed_intents = {}
        for i in interactions:
            if not i.get("success") or "cannot" in str(i.get("response", "")).lower():
                intent = i.get("intent", "unknown")
                topic = i.get("topic", "")
                key = f"{intent}:{topic}"
                
                if key not in failed_intents:
                    failed_intents[key] = {"requests": 0, "failed": 0}
                failed_intents[key]["requests"] += 1
                failed_intents[key]["failed"] += 1
        
        for key, data in failed_intents.items():
            if data["failed"] >= 3:
                intent, topic = key.split(":", 1) if ":" in key else (key, "")
                
                gaps.append(CapabilityGap(
                    capability=f"{intent} - {topic}" if topic else intent,
                    user_requests=data["requests"],
                    failed_attempts=data["failed"],
                    description=f"User requested {intent} {topic} but failed {data['failed']} times",
                    implementation_effort="medium",
                    priority=min(10, data["failed"]),
                ))
        
        return sorted(gaps, key=lambda g: g.priority, reverse=True)[:5]
    
    def _generate_suggestions(
        self,
        metrics: List[PerformanceMetric],
        issues: List[IssueDetection],
        gaps: List[CapabilityGap]
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        # Based on metrics
        for m in metrics:
            if m.status == "bad":
                suggestions.append(f"Critical: Improve {m.name} (currently {m.value:.1f} vs target {m.target})")
            elif m.status == "warning":
                suggestions.append(f"Improve {m.name} (currently {m.value:.1f} vs target {m.target})")
        
        # Based on issues
        for issue in issues:
            if issue.severity in ["high", "critical"]:
                if issue.suggested_fix:
                    suggestions.append(f"Fix {issue.issue_type}: {issue.suggested_fix}")
        
        # Based on gaps
        for gap in gaps[:3]:
            suggestions.append(f"Add capability: {gap.capability} ({gap.user_requests} requests)")
        
        return suggestions[:10]
    
    def _calculate_overall_score(
        self,
        metrics: List[PerformanceMetric],
        issues: List[IssueDetection]
    ) -> float:
        """Calculate overall performance score."""
        score = 100
        
        # Deduct for bad metrics
        for m in metrics:
            if m.status == "bad":
                score -= 15
            elif m.status == "warning":
                score -= 5
        
        # Deduct for issues
        for issue in issues:
            if issue.severity == "critical":
                score -= 20
            elif issue.severity == "high":
                score -= 10
            elif issue.severity == "medium":
                score -= 5
            elif issue.severity == "low":
                score -= 2
        
        return max(0, min(100, score))
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend from values."""
        if len(values) < 10:
            return "stable"
        
        first_half = sum(values[len(values)//2:]) / (len(values)//2)
        second_half = sum(values[:len(values)//2]) / (len(values)//2)
        
        diff_pct = (second_half - first_half) / first_half * 100 if first_half > 0 else 0
        
        if diff_pct < -10:
            return "improving"
        elif diff_pct > 10:
            return "declining"
        else:
            return "stable"
    
    def _get_metric_value(self, metrics: List[PerformanceMetric], name: str) -> float:
        """Get metric value by name."""
        for m in metrics:
            if m.name == name:
                return m.value
        return 0
    
    def _suggest_fix_for_error(self, error: str) -> Optional[str]:
        """Suggest fix for common errors."""
        if "timeout" in error.lower():
            return "Increase timeout or optimize slow operations"
        if "api" in error.lower():
            return "Check API keys and rate limits"
        if "import" in error.lower():
            return "Check for missing dependencies"
        if "permission" in error.lower():
            return "Verify access permissions"
        return None
    
    def _is_auto_fixable(self, error: str) -> bool:
        """Check if error might be auto-fixable."""
        auto_fixable_patterns = ["timeout", "cache", "retry"]
        return any(p in error.lower() for p in auto_fixable_patterns)
    
    def format_report(self, report: PerformanceReport) -> str:
        """Format report for display."""
        lines = [
            f"📊 **Performance Report** ({report.period_hours}h)",
            "",
            f"Overall Score: {report.overall_score:.0f}/100",
            f"Interactions: {report.total_interactions}",
            f"Success Rate: {report.success_rate:.1f}%",
            f"Avg Response: {report.avg_response_time_ms:.0f}ms",
            "",
        ]
        
        if report.issues:
            lines.append("**Issues Detected:**")
            for issue in report.issues[:5]:
                emoji = "🔴" if issue.severity in ["high", "critical"] else "🟡"
                lines.append(f"{emoji} {issue.description[:60]}...")
            lines.append("")
        
        if report.improvement_suggestions:
            lines.append("**Suggestions:**")
            for sug in report.improvement_suggestions[:5]:
                lines.append(f"• {sug}")
        
        return "\n".join(lines)


# Singleton
_analyzer: Optional[SelfAnalyzer] = None


def get_self_analyzer() -> SelfAnalyzer:
    """Get global SelfAnalyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SelfAnalyzer()
    return _analyzer


