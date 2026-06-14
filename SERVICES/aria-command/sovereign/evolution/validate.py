#!/usr/bin/env python3
"""
ARIA ULTRA POWER - EVOLUTION VALIDATION
=========================================

Validate and verify code changes:
- A/B testing
- Metrics comparison
- Auto-rollback on degradation
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger("aria.evolution.validate")


@dataclass
class ValidationMetrics:
    """Metrics for validating a change."""
    response_time_before: float
    response_time_after: float
    error_rate_before: float
    error_rate_after: float
    success_rate_before: float
    success_rate_after: float


@dataclass
class ValidationResult:
    """Result of change validation."""
    change_id: str
    passed: bool
    metrics: Optional[ValidationMetrics]
    reason: str
    should_rollback: bool
    confidence: float


class EvolutionValidator:
    """
    Validate code changes through testing.
    
    Features:
    - Before/after metrics comparison
    - Automatic rollback trigger
    - Confidence scoring
    """
    
    # Thresholds for validation
    MAX_RESPONSE_TIME_INCREASE = 1.5  # 50% increase
    MAX_ERROR_RATE_INCREASE = 1.2  # 20% increase
    MIN_SUCCESS_RATE_RATIO = 0.95  # Must maintain 95% of original success rate
    
    def __init__(self):
        self._baseline_metrics: Dict[str, Dict] = {}
        
        logger.info("EvolutionValidator initialized")
    
    async def capture_baseline(self, change_id: str, sample_size: int = 10):
        """Capture baseline metrics before applying a change."""
        # Would run sample interactions and measure
        # For now, capture from recent history
        
        from .self_analyze import get_self_analyzer
        
        analyzer = get_self_analyzer()
        report = analyzer.analyze(hours=1)
        
        self._baseline_metrics[change_id] = {
            "response_time": report.avg_response_time_ms,
            "success_rate": report.success_rate,
            "error_rate": 100 - report.success_rate,
            "captured_at": time.time(),
        }
    
    async def validate_change(
        self,
        change_id: str,
        wait_minutes: int = 5
    ) -> ValidationResult:
        """Validate a change by comparing before/after metrics."""
        if change_id not in self._baseline_metrics:
            return ValidationResult(
                change_id=change_id,
                passed=False,
                metrics=None,
                reason="No baseline metrics captured",
                should_rollback=False,
                confidence=0,
            )
        
        baseline = self._baseline_metrics[change_id]
        
        # Wait for change to take effect
        await asyncio.sleep(wait_minutes * 60)
        
        # Capture current metrics
        from .self_analyze import get_self_analyzer
        
        analyzer = get_self_analyzer()
        report = analyzer.analyze(hours=0.5)  # Last 30 minutes
        
        current = {
            "response_time": report.avg_response_time_ms,
            "success_rate": report.success_rate,
            "error_rate": 100 - report.success_rate,
        }
        
        # Compare metrics
        metrics = ValidationMetrics(
            response_time_before=baseline["response_time"],
            response_time_after=current["response_time"],
            error_rate_before=baseline["error_rate"],
            error_rate_after=current["error_rate"],
            success_rate_before=baseline["success_rate"],
            success_rate_after=current["success_rate"],
        )
        
        # Validate each metric
        issues = []
        
        if baseline["response_time"] > 0:
            time_ratio = current["response_time"] / baseline["response_time"]
            if time_ratio > self.MAX_RESPONSE_TIME_INCREASE:
                issues.append(f"Response time increased {time_ratio:.1f}x")
        
        if baseline["error_rate"] > 0:
            error_ratio = current["error_rate"] / baseline["error_rate"]
            if error_ratio > self.MAX_ERROR_RATE_INCREASE:
                issues.append(f"Error rate increased {error_ratio:.1f}x")
        elif current["error_rate"] > 10:
            issues.append(f"Error rate is {current['error_rate']:.1f}%")
        
        if baseline["success_rate"] > 0:
            success_ratio = current["success_rate"] / baseline["success_rate"]
            if success_ratio < self.MIN_SUCCESS_RATE_RATIO:
                issues.append(f"Success rate dropped to {success_ratio:.1%} of baseline")
        
        # Determine result
        passed = len(issues) == 0
        should_rollback = len(issues) >= 2 or any("dropped" in i for i in issues)
        confidence = 1.0 - (len(issues) * 0.3)
        
        return ValidationResult(
            change_id=change_id,
            passed=passed,
            metrics=metrics,
            reason="; ".join(issues) if issues else "All metrics within acceptable range",
            should_rollback=should_rollback,
            confidence=max(0, confidence),
        )
    
    def format_result(self, result: ValidationResult) -> str:
        """Format validation result for display."""
        emoji = "✅" if result.passed else "❌"
        
        lines = [
            f"{emoji} **Validation Result** `{result.change_id}`",
            "",
            f"Status: {'PASSED' if result.passed else 'FAILED'}",
            f"Confidence: {result.confidence:.0%}",
            f"Rollback: {'Recommended' if result.should_rollback else 'Not needed'}",
            "",
            f"**Reason:** {result.reason}",
        ]
        
        if result.metrics:
            m = result.metrics
            lines.append("")
            lines.append("**Metrics:**")
            lines.append(f"• Response Time: {m.response_time_before:.0f}ms → {m.response_time_after:.0f}ms")
            lines.append(f"• Success Rate: {m.success_rate_before:.1f}% → {m.success_rate_after:.1f}%")
            lines.append(f"• Error Rate: {m.error_rate_before:.1f}% → {m.error_rate_after:.1f}%")
        
        return "\n".join(lines)


# Singleton
_validator: Optional[EvolutionValidator] = None


def get_validator() -> EvolutionValidator:
    """Get global EvolutionValidator instance."""
    global _validator
    if _validator is None:
        _validator = EvolutionValidator()
    return _validator


