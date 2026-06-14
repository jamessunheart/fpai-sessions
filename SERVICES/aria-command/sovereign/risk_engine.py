#!/usr/bin/env python3
"""
ARIA RISK ASSESSMENT ENGINE
============================

Classifies proposed changes by risk level to determine whether they
can be auto-executed or need human approval.

Risk Levels:
1 (Safe)     - Auto-execute: Prompt improvements, log changes
2 (Low)      - Auto-execute: Config tweaks, thresholds
3 (Medium)   - Daily Digest: New helpers, error handling
4 (High)     - Approval Required: API changes, new endpoints
5 (Critical) - Approval Required: Trading, security, core systems

Features:
- File-based risk classification
- Pattern-based change detection
- Protected file enforcement
- Historical risk tracking
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import IntEnum

logger = logging.getLogger("aria.sovereign.risk_engine")


class RiskLevel(IntEnum):
    """Risk levels for changes."""
    SAFE = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


@dataclass
class RiskAssessment:
    """Assessment of a proposed change."""
    level: RiskLevel
    auto_execute: bool
    factors: List[str] = field(default_factory=list)
    requires_approval: bool = False
    requires_notification: bool = False
    protected_file: bool = False


# ============================================================================
# PROTECTED FILES - Always require approval
# ============================================================================

PROTECTED_FILES: Set[str] = {
    # Core brain files
    "brain/opus_brain.py",
    "brain/tools.py",
    
    # Bot core
    "telegram/bot.py",
    
    # Trading (ALWAYS protected)
    "trading/executor.py",
    "trading/awareness.py",
    
    # Security sensitive
    "access/terminal.py",
    "ops/server_ops.py",
    
    # Self-modification
    "sovereign/self_modify.py",
    "sovereign/auto_executor.py",
    "sovereign/risk_engine.py",
    
    # Main entry point
    "main.py",
    "__init__.py",
}


# ============================================================================
# FILE RISK CLASSIFICATION
# ============================================================================

FILE_RISK_PATTERNS: List[tuple[str, RiskLevel]] = [
    # Critical - Trading, Security, Core
    (r"trading/", RiskLevel.CRITICAL),
    (r"security/", RiskLevel.CRITICAL),
    (r"auth/", RiskLevel.CRITICAL),
    (r"payments?/", RiskLevel.CRITICAL),
    (r"crypto/", RiskLevel.CRITICAL),
    
    # High - API, Database, Infrastructure
    (r"api/", RiskLevel.HIGH),
    (r"database/", RiskLevel.HIGH),
    (r"db/", RiskLevel.HIGH),
    (r"infra/", RiskLevel.HIGH),
    (r"ops/", RiskLevel.HIGH),
    (r"access/", RiskLevel.HIGH),
    
    # Medium - Business Logic
    (r"brain/", RiskLevel.MEDIUM),
    (r"telegram/", RiskLevel.MEDIUM),
    (r"agents/", RiskLevel.MEDIUM),
    (r"reality/", RiskLevel.MEDIUM),
    (r"proactive/", RiskLevel.MEDIUM),
    
    # Low - Utilities, Helpers
    (r"utils?/", RiskLevel.LOW),
    (r"helpers?/", RiskLevel.LOW),
    (r"tests?/", RiskLevel.LOW),
    (r"logging/", RiskLevel.LOW),
    
    # Safe - Config, Docs, Prompts
    (r"prompts?/", RiskLevel.SAFE),
    (r"config/", RiskLevel.SAFE),
    (r"templates?/", RiskLevel.SAFE),
    (r"\.md$", RiskLevel.SAFE),
    (r"\.txt$", RiskLevel.SAFE),
    (r"\.json$", RiskLevel.LOW),
    (r"\.yaml$", RiskLevel.LOW),
]


# ============================================================================
# CHANGE PATTERN RISK CLASSIFICATION
# ============================================================================

CHANGE_RISK_PATTERNS: List[tuple[str, RiskLevel, str]] = [
    # Critical patterns
    (r"subprocess|os\.system|exec\(|eval\(", RiskLevel.CRITICAL, "Shell execution"),
    (r"ssh|remote.*exec", RiskLevel.CRITICAL, "Remote execution"),
    (r"api_key|secret|password|token", RiskLevel.CRITICAL, "Credential handling"),
    (r"transfer|withdraw|deposit|trade|order", RiskLevel.CRITICAL, "Financial operation"),
    (r"delete.*table|drop.*table|truncate", RiskLevel.CRITICAL, "Database destruction"),
    
    # High patterns
    (r"@app\.(get|post|put|delete|patch)", RiskLevel.HIGH, "API endpoint change"),
    (r"async def.*\(.*request", RiskLevel.HIGH, "Request handler"),
    (r"cursor\.execute", RiskLevel.HIGH, "Direct SQL execution"),
    (r"requests?\.(get|post|put)", RiskLevel.HIGH, "External HTTP call"),
    (r"httpx\.(get|post|put)", RiskLevel.HIGH, "External HTTP call"),
    
    # Medium patterns
    (r"class.*\(.*\):", RiskLevel.MEDIUM, "Class definition"),
    (r"async def|def.*\(", RiskLevel.MEDIUM, "Function definition"),
    (r"import|from.*import", RiskLevel.MEDIUM, "Import change"),
    (r"try:|except:|finally:", RiskLevel.MEDIUM, "Error handling"),
    
    # Low patterns
    (r"logger\.|logging\.", RiskLevel.LOW, "Logging change"),
    (r"print\(|f\".*\"", RiskLevel.LOW, "Output change"),
    (r"#.*TODO|#.*FIXME|#.*NOTE", RiskLevel.LOW, "Comment change"),
    
    # Safe patterns
    (r"^\s*#", RiskLevel.SAFE, "Comment only"),
    (r"^\s*\"\"\"", RiskLevel.SAFE, "Docstring only"),
    (r"^\s*$", RiskLevel.SAFE, "Whitespace only"),
]


class RiskEngine:
    """
    Assesses the risk level of proposed changes.
    
    Uses file paths, change patterns, and protected file lists
    to determine appropriate action.
    """
    
    def __init__(self, protected_files: Set[str] = None):
        self.protected_files = protected_files or PROTECTED_FILES
        self._assessment_history: List[Dict[str, Any]] = []
    
    def assess(
        self,
        file_path: str,
        diff: str,
        change_description: str = ""
    ) -> RiskAssessment:
        """
        Assess the risk of a proposed change.
        
        Args:
            file_path: Path to the file being changed
            diff: The unified diff of the change
            change_description: Human-readable description
            
        Returns:
            RiskAssessment with level and factors
        """
        factors = []
        max_level = RiskLevel.SAFE
        
        # Check protected files
        protected = self._is_protected(file_path)
        if protected:
            factors.append(f"Protected file: {file_path}")
            max_level = RiskLevel.CRITICAL
        
        # Assess file path risk
        file_level = self._assess_file_path(file_path)
        if file_level > max_level:
            max_level = file_level
            factors.append(f"File category: {file_path}")
        
        # Assess change patterns
        pattern_level, pattern_factors = self._assess_diff_patterns(diff)
        if pattern_level > max_level:
            max_level = pattern_level
        factors.extend(pattern_factors)
        
        # Assess change size
        size_level = self._assess_change_size(diff)
        if size_level > max_level:
            max_level = size_level
            factors.append(f"Large change: {self._count_lines(diff)} lines")
        
        # Determine action
        auto_execute = max_level <= RiskLevel.LOW
        requires_approval = max_level >= RiskLevel.HIGH
        requires_notification = max_level >= RiskLevel.MEDIUM
        
        assessment = RiskAssessment(
            level=max_level,
            auto_execute=auto_execute and not protected,
            factors=factors,
            requires_approval=requires_approval or protected,
            requires_notification=requires_notification,
            protected_file=protected
        )
        
        # Log assessment
        self._assessment_history.append({
            "file_path": file_path,
            "level": max_level,
            "factors": factors,
            "auto_execute": assessment.auto_execute
        })
        
        logger.info(
            f"Risk assessment: {file_path} -> Level {max_level.value} "
            f"(auto={assessment.auto_execute}, approval={requires_approval})"
        )
        
        return assessment
    
    def _is_protected(self, file_path: str) -> bool:
        """Check if file is protected."""
        normalized = file_path.lstrip("/").lstrip("./")
        
        for protected in self.protected_files:
            if normalized.endswith(protected) or protected in normalized:
                return True
        
        return False
    
    def _assess_file_path(self, file_path: str) -> RiskLevel:
        """Assess risk based on file path."""
        for pattern, level in FILE_RISK_PATTERNS:
            if re.search(pattern, file_path, re.IGNORECASE):
                return level
        return RiskLevel.MEDIUM  # Default
    
    def _assess_diff_patterns(self, diff: str) -> tuple[RiskLevel, List[str]]:
        """Assess risk based on change patterns in diff."""
        max_level = RiskLevel.SAFE
        factors = []
        
        # Only look at added lines (+ prefix)
        added_lines = [
            line[1:] for line in diff.split("\n")
            if line.startswith("+") and not line.startswith("+++")
        ]
        
        all_added = "\n".join(added_lines)
        
        for pattern, level, description in CHANGE_RISK_PATTERNS:
            if re.search(pattern, all_added, re.IGNORECASE | re.MULTILINE):
                if level > max_level:
                    max_level = level
                factors.append(f"{description} (risk {level.value})")
        
        return max_level, factors
    
    def _assess_change_size(self, diff: str) -> RiskLevel:
        """Assess risk based on change size."""
        lines = self._count_lines(diff)
        
        if lines > 200:
            return RiskLevel.HIGH
        elif lines > 100:
            return RiskLevel.MEDIUM
        elif lines > 50:
            return RiskLevel.LOW
        else:
            return RiskLevel.SAFE
    
    def _count_lines(self, diff: str) -> int:
        """Count lines changed in diff."""
        changed = 0
        for line in diff.split("\n"):
            if line.startswith("+") or line.startswith("-"):
                if not line.startswith("+++") and not line.startswith("---"):
                    changed += 1
        return changed
    
    def get_auto_execute_threshold(self) -> RiskLevel:
        """Get the current auto-execute threshold."""
        return RiskLevel.LOW
    
    def can_auto_execute(self, assessment: RiskAssessment) -> bool:
        """Check if a change can be auto-executed."""
        return (
            assessment.auto_execute and
            not assessment.protected_file and
            assessment.level <= self.get_auto_execute_threshold()
        )
    
    def format_assessment(self, assessment: RiskAssessment) -> str:
        """Format assessment for display."""
        risk_icons = {
            RiskLevel.SAFE: "🟢",
            RiskLevel.LOW: "🟡",
            RiskLevel.MEDIUM: "🟠",
            RiskLevel.HIGH: "🔴",
            RiskLevel.CRITICAL: "⛔"
        }
        
        icon = risk_icons.get(assessment.level, "❓")
        
        lines = [
            f"{icon} **Risk Level {assessment.level.value}**",
            "",
        ]
        
        if assessment.protected_file:
            lines.append("⚠️ **Protected File** - Requires manual approval")
        elif assessment.auto_execute:
            lines.append("✅ Can be auto-executed")
        elif assessment.requires_approval:
            lines.append("🔒 Requires approval")
        else:
            lines.append("📋 Will appear in daily digest")
        
        if assessment.factors:
            lines.append("")
            lines.append("**Risk Factors:**")
            for factor in assessment.factors[:5]:  # Limit to 5
                lines.append(f"• {factor}")
        
        return "\n".join(lines)


# ============================================================================
# SINGLETON
# ============================================================================

_engine: Optional[RiskEngine] = None


def get_risk_engine() -> RiskEngine:
    """Get or create global risk engine."""
    global _engine
    if _engine is None:
        _engine = RiskEngine()
    return _engine


def assess_change(file_path: str, diff: str, description: str = "") -> RiskAssessment:
    """Assess a change."""
    return get_risk_engine().assess(file_path, diff, description)


def can_auto_execute(file_path: str, diff: str) -> bool:
    """Check if a change can be auto-executed."""
    assessment = assess_change(file_path, diff)
    return get_risk_engine().can_auto_execute(assessment)


