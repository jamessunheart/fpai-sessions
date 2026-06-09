"""
ROOT CAUSE ANALYSIS
====================

When something fails, ask WHY, not just WHAT.

The WhaleTrack failure:
- Symptom: "WhaleTrack unreachable"
- What old system did: Retry the same thing forever
- What we should do: WHY is it unreachable?
  - Config wrong? (YES! Port 8600 vs 8601)
  - Service down?
  - Network issue?
  - Dependency failed?

This module diagnoses the actual cause, not just the symptom.
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import httpx

logger = logging.getLogger("aria.intelligence.rootcause")


class CauseCategory(str, Enum):
    """Categories of root causes."""
    CONFIG = "config"              # Configuration error
    DEPENDENCY = "dependency"      # A dependency is down
    NETWORK = "network"            # Network connectivity issue
    SERVICE = "service"            # Service itself is broken
    RESOURCE = "resource"          # Resource exhaustion (memory, disk)
    EXTERNAL = "external"          # External service issue
    CODE = "code"                  # Bug in the code
    UNKNOWN = "unknown"            # Can't determine


@dataclass
class RootCause:
    """An identified root cause."""
    service: str
    symptom: str
    category: CauseCategory
    description: str
    confidence: float  # 0.0 to 1.0
    evidence: List[str]
    suggested_fix: str
    fix_type: str  # config_change, restart, rollback, etc.
    dependencies_affected: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def __str__(self):
        return f"[{self.category.value}] {self.description} (confidence: {self.confidence:.0%})"


@dataclass
class Dependency:
    """A service dependency."""
    name: str
    type: str  # required, optional
    healthy: bool
    check_result: str


# ============================================================================
# SERVICE DEPENDENCY MAP
# ============================================================================

SERVICE_DEPENDENCIES = {
    "aria-command": {
        "required": ["telegram-api", "ai-brain"],
        "optional": ["whaletrack", "mem0", "hyperliquid"]
    },
    "whaletrack": {
        "required": ["hyperliquid"],
        "optional": []
    },
    "ai-brain": {
        "required": ["anthropic-api"],
        "optional": ["gemini-api", "ollama"]
    },
    "godmode": {
        "required": [],
        "optional": ["aria-command", "whaletrack"]
    }
}

# Config to service mapping
CONFIG_SERVICE_MAP = {
    "WHALETRACK_URL": "whaletrack",
    "ANTHROPIC_API_KEY": "ai-brain",
    "GEMINI_API_KEY": "ai-brain",
    "MEM0_API_KEY": "mem0",
    "TELEGRAM_BOT_TOKEN": "telegram-api",
    "HYPERLIQUID_API_KEY": "hyperliquid"
}


class RootCauseAnalyzer:
    """
    Analyzes failures to determine root cause.
    
    Strategy:
    1. Check configuration first (most common cause)
    2. Check dependencies (cascading failures)
    3. Check the service itself
    4. Check external factors
    5. Compare with known patterns
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=10.0)
        self.analysis_history: List[RootCause] = []
        logger.info("RootCauseAnalyzer initialized")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def analyze_failure(
        self,
        service: str,
        symptom: str,
        context: Dict[str, Any] = None
    ) -> RootCause:
        """
        Analyze a failure and determine root cause.
        
        Args:
            service: The failing service name
            symptom: Description of what's failing
            context: Additional context (error messages, etc.)
        
        Returns:
            RootCause with diagnosis and suggested fix
        """
        logger.info(f"Analyzing failure: {service} - {symptom}")
        context = context or {}
        
        causes: List[Tuple[float, RootCause]] = []
        
        # 1. Check configuration (most common and easiest to fix)
        config_cause = await self._check_config(service, symptom)
        if config_cause:
            causes.append((config_cause.confidence, config_cause))
        
        # 2. Check dependencies
        dep_cause = await self._check_dependencies(service, symptom)
        if dep_cause:
            causes.append((dep_cause.confidence, dep_cause))
        
        # 3. Check service health directly
        service_cause = await self._check_service_health(service, symptom)
        if service_cause:
            causes.append((service_cause.confidence, service_cause))
        
        # 4. Check for resource issues
        resource_cause = await self._check_resources(service, symptom)
        if resource_cause:
            causes.append((resource_cause.confidence, resource_cause))
        
        # 5. Look for patterns in similar failures
        pattern_cause = await self._check_patterns(service, symptom)
        if pattern_cause:
            causes.append((pattern_cause.confidence, pattern_cause))
        
        # Return highest confidence cause
        if causes:
            causes.sort(key=lambda x: x[0], reverse=True)
            best_cause = causes[0][1]
            
            # If multiple high-confidence causes, note them
            if len(causes) > 1 and causes[1][0] > 0.5:
                best_cause.evidence.append(
                    f"Also possible: {causes[1][1].description}"
                )
            
            self.analysis_history.append(best_cause)
            return best_cause
        
        # Unknown cause
        unknown = RootCause(
            service=service,
            symptom=symptom,
            category=CauseCategory.UNKNOWN,
            description="Could not determine root cause",
            confidence=0.1,
            evidence=["No matching patterns found", "Manual investigation needed"],
            suggested_fix="Check service logs manually",
            fix_type="manual"
        )
        self.analysis_history.append(unknown)
        return unknown
    
    async def _check_config(self, service: str, symptom: str) -> Optional[RootCause]:
        """Check for configuration issues."""
        from .config_contracts import get_config_contract, DriftAction
        
        contract = get_config_contract()
        related = contract.get_related_configs(service)
        
        drifts = []
        for key, info in related.items():
            if info.get("drift"):
                drifts.append((key, info["drift"]))
        
        if drifts:
            drift_keys = [d[0] for d in drifts]
            drift_details = [d[1] for d in drifts]
            
            # Check for the specific WhaleTrack port issue
            is_port_issue = any("8600" in d for d in drift_details)
            
            return RootCause(
                service=service,
                symptom=symptom,
                category=CauseCategory.CONFIG,
                description=f"Configuration drift detected in: {', '.join(drift_keys)}",
                confidence=0.95 if is_port_issue else 0.85,
                evidence=drift_details,
                suggested_fix=f"Fix configuration: {drift_details[0]}",
                fix_type="config_change"
            )
        
        # Check for missing configs
        missing = [k for k, v in related.items() if not v.get("value_set")]
        if missing:
            return RootCause(
                service=service,
                symptom=symptom,
                category=CauseCategory.CONFIG,
                description=f"Missing configuration: {', '.join(missing)}",
                confidence=0.80,
                evidence=[f"{k} is not set" for k in missing],
                suggested_fix=f"Set required configuration: {missing[0]}",
                fix_type="config_change"
            )
        
        return None
    
    async def _check_dependencies(self, service: str, symptom: str) -> Optional[RootCause]:
        """Check if dependencies are failing."""
        deps = SERVICE_DEPENDENCIES.get(service, {"required": [], "optional": []})
        
        failed_deps = []
        
        for dep in deps.get("required", []):
            if not await self._is_dependency_healthy(dep):
                failed_deps.append((dep, "required"))
        
        for dep in deps.get("optional", []):
            if not await self._is_dependency_healthy(dep):
                failed_deps.append((dep, "optional"))
        
        if failed_deps:
            required_failed = [d for d, t in failed_deps if t == "required"]
            
            if required_failed:
                return RootCause(
                    service=service,
                    symptom=symptom,
                    category=CauseCategory.DEPENDENCY,
                    description=f"Required dependency failing: {required_failed[0]}",
                    confidence=0.90,
                    evidence=[f"{d} is not responding" for d, _ in failed_deps],
                    suggested_fix=f"Fix dependency first: {required_failed[0]}",
                    fix_type="fix_dependency",
                    dependencies_affected=[d for d, _ in failed_deps]
                )
            else:
                # Only optional deps failing
                return RootCause(
                    service=service,
                    symptom=symptom,
                    category=CauseCategory.DEPENDENCY,
                    description=f"Optional dependencies failing: {[d for d, _ in failed_deps]}",
                    confidence=0.50,
                    evidence=[f"{d} is not responding" for d, _ in failed_deps],
                    suggested_fix="May operate in degraded mode",
                    fix_type="graceful_degradation",
                    dependencies_affected=[d for d, _ in failed_deps]
                )
        
        return None
    
    async def _is_dependency_healthy(self, dep_name: str) -> bool:
        """Check if a dependency is healthy."""
        # External API checks
        external_checks = {
            "anthropic-api": ("https://api.anthropic.com/v1/models", None),
            "gemini-api": ("https://generativelanguage.googleapis.com/v1beta/models", None),
            "telegram-api": ("https://api.telegram.org/bot{token}/getMe", "TELEGRAM_BOT_TOKEN"),
        }
        
        # Internal service checks
        internal_checks = {
            "ai-brain": "http://162.0.208.88:8101/health",
            "whaletrack": "http://198.54.123.234:8601/health",
            "aria-command": "http://162.0.208.88:8750/health",
            "mem0": "https://api.mem0.ai/v1/",
            "hyperliquid": "https://api.hyperliquid.xyz/info",
        }
        
        if dep_name in external_checks:
            url_template, token_key = external_checks[dep_name]
            if token_key:
                token = os.getenv(token_key, "")
                if not token:
                    return False
                url = url_template.format(token=token)
            else:
                url = url_template
            
            try:
                # Just check connectivity, don't validate response
                response = await self.http.head(url)
                return response.status_code < 500
            except Exception:
                return False
        
        if dep_name in internal_checks:
            url = internal_checks[dep_name]
            try:
                response = await self.http.get(url)
                return response.status_code == 200
            except Exception:
                return False
        
        # Unknown dependency, assume healthy
        return True
    
    async def _check_service_health(self, service: str, symptom: str) -> Optional[RootCause]:
        """Check if the service itself is broken."""
        from .real_verification import get_verifier
        
        try:
            verifier = get_verifier()
            result = await verifier.verify_service(service)
            
            if not result.passed:
                failed_checks = result.failed_checks
                
                return RootCause(
                    service=service,
                    symptom=symptom,
                    category=CauseCategory.SERVICE,
                    description=f"Service verification failed: {result.reason}",
                    confidence=0.75,
                    evidence=[f"{c.name}: {c.message}" for c in failed_checks],
                    suggested_fix="Restart service or check logs",
                    fix_type="restart"
                )
        except Exception as e:
            logger.debug(f"Could not verify service {service}: {e}")
        
        return None
    
    async def _check_resources(self, service: str, symptom: str) -> Optional[RootCause]:
        """Check for resource issues."""
        # Look for resource-related keywords in symptom
        resource_keywords = ["memory", "oom", "disk", "full", "exhausted", "timeout"]
        
        symptom_lower = symptom.lower()
        if any(kw in symptom_lower for kw in resource_keywords):
            return RootCause(
                service=service,
                symptom=symptom,
                category=CauseCategory.RESOURCE,
                description="Possible resource exhaustion",
                confidence=0.60,
                evidence=["Symptom suggests resource issue"],
                suggested_fix="Check server resources (memory, disk, CPU)",
                fix_type="resource_cleanup"
            )
        
        return None
    
    async def _check_patterns(self, service: str, symptom: str) -> Optional[RootCause]:
        """Check for known patterns from failure history."""
        from .intelligence_db import get_intelligence_db
        
        try:
            db = get_intelligence_db()
            similar = db.find_similar_failures(symptom, limit=3)
            
            if similar:
                # Most recent similar failure with a fix
                for failure in similar:
                    if failure.fix_worked and failure.root_cause:
                        return RootCause(
                            service=service,
                            symptom=symptom,
                            category=CauseCategory(failure.metadata.get("category", "unknown")),
                            description=f"Similar to previous failure: {failure.root_cause}",
                            confidence=0.70,
                            evidence=[
                                f"Similar failure on {failure.timestamp}",
                                f"Previous fix: {failure.fix_applied}"
                            ],
                            suggested_fix=failure.fix_applied,
                            fix_type=failure.metadata.get("fix_type", "learned_fix")
                        )
        except Exception as e:
            logger.debug(f"Could not check patterns: {e}")
        
        return None
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of recent analyses."""
        by_category = {}
        for cause in self.analysis_history[-50:]:  # Last 50
            cat = cause.category.value
            by_category[cat] = by_category.get(cat, 0) + 1
        
        return {
            "total_analyses": len(self.analysis_history),
            "by_category": by_category,
            "avg_confidence": sum(c.confidence for c in self.analysis_history[-50:]) / 
                            max(len(self.analysis_history[-50:]), 1),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# SINGLETON
# ============================================================================

_analyzer: Optional[RootCauseAnalyzer] = None


def get_root_cause_analyzer() -> RootCauseAnalyzer:
    """Get or create the root cause analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = RootCauseAnalyzer()
    return _analyzer


async def analyze_failure(
    service: str,
    symptom: str,
    context: Dict[str, Any] = None
) -> RootCause:
    """Convenience function to analyze a failure."""
    return await get_root_cause_analyzer().analyze_failure(service, symptom, context)









