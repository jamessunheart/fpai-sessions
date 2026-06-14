"""
CONFIG CONTRACTS
=================

Define expected configurations and detect drift BEFORE it causes failures.

The WhaleTrack lesson: WHALETRACK_URL was 8600 when it should have been 8601.
This module would have caught that immediately.

Each config has:
- Pattern: What the value should look like
- Verify: Function to validate the value
- On Drift: What to do if invalid (alert, alert_and_fix, etc.)
- Auto Fix: How to fix it automatically (if possible)
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("aria.intelligence.config")


class DriftAction(str, Enum):
    """What to do when config drift is detected."""
    ALERT = "alert"                    # Just notify
    ALERT_AND_FIX = "alert_and_fix"    # Fix and notify
    FIX_SILENT = "fix_silent"          # Fix without alert
    BLOCK = "block"                    # Stop operations until fixed


@dataclass
class ConfigDrift:
    """A detected configuration drift."""
    key: str
    expected: str
    actual: str
    description: str
    action: DriftAction
    auto_fix_value: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    fixed: bool = False
    
    def __str__(self):
        return f"CONFIG_DRIFT: {self.key} - {self.description}"


@dataclass
class ConfigSpec:
    """Specification for a configuration value."""
    key: str
    description: str
    required: bool = True
    pattern: Optional[str] = None
    verify: Optional[Callable[[str], bool]] = None
    must_contain: Optional[str] = None
    must_not_contain: Optional[str] = None
    must_start_with: Optional[str] = None
    min_length: int = 0
    on_drift: DriftAction = DriftAction.ALERT
    auto_fix_value: Optional[str] = None
    related_to: Optional[str] = None  # Related service


# ============================================================================
# CONFIG CONTRACTS - Define all critical configurations
# ============================================================================

CONFIG_CONTRACTS: Dict[str, ConfigSpec] = {
    # WhaleTrack - THE critical one that failed
    "WHALETRACK_URL": ConfigSpec(
        key="WHALETRACK_URL",
        description="WhaleTrack API URL (MUST be port 8601, NOT 8600)",
        required=True,
        pattern=r"http://198\.54\.123\.234:8601",
        verify=lambda v: ":8601" in v and ":8600" not in v,
        must_contain=":8601",
        must_not_contain=":8600",
        on_drift=DriftAction.ALERT_AND_FIX,
        auto_fix_value="http://198.54.123.234:8601",
        related_to="whaletrack"
    ),
    
    # AI Keys
    "ANTHROPIC_API_KEY": ConfigSpec(
        key="ANTHROPIC_API_KEY",
        description="Claude API key for primary thinking",
        required=True,
        must_start_with="sk-ant-",
        min_length=50,
        on_drift=DriftAction.ALERT,
        related_to="ai-brain"
    ),
    
    "GEMINI_API_KEY": ConfigSpec(
        key="GEMINI_API_KEY",
        description="Gemini API key for fast thinking",
        required=False,  # Fallback available
        must_start_with="AIza",
        min_length=30,
        on_drift=DriftAction.ALERT,
        related_to="ai-brain"
    ),
    
    # Memory
    "MEM0_API_KEY": ConfigSpec(
        key="MEM0_API_KEY",
        description="Mem0 cloud memory API key",
        required=True,
        must_start_with="m0-",
        min_length=30,
        on_drift=DriftAction.ALERT,
        related_to="aria-command"
    ),
    
    # Telegram
    "TELEGRAM_BOT_TOKEN": ConfigSpec(
        key="TELEGRAM_BOT_TOKEN",
        description="Telegram bot token for Aria",
        required=True,
        min_length=40,
        on_drift=DriftAction.ALERT,
        related_to="aria-command"
    ),
    
    "SUNHEART_CHAT_ID": ConfigSpec(
        key="SUNHEART_CHAT_ID",
        description="James's Telegram chat ID for alerts",
        required=True,
        pattern=r"^\d+$",
        min_length=5,
        on_drift=DriftAction.ALERT,
        related_to="aria-command"
    ),
    
    # Trading
    "HYPERLIQUID_API_KEY": ConfigSpec(
        key="HYPERLIQUID_API_KEY",
        description="Hyperliquid API key for trading",
        required=False,  # Trading is optional
        min_length=20,
        on_drift=DriftAction.ALERT,
        related_to="hyperliquid"
    ),
    
    "HYPERLIQUID_API_SECRET": ConfigSpec(
        key="HYPERLIQUID_API_SECRET",
        description="Hyperliquid API secret for trading",
        required=False,
        min_length=20,
        on_drift=DriftAction.ALERT,
        related_to="hyperliquid"
    ),
    
    # Server URLs
    "AI_BRAIN_URL": ConfigSpec(
        key="AI_BRAIN_URL",
        description="AI Brain service URL (secondary server)",
        required=False,
        pattern=r"http://162\.0\.208\.88:8101",
        verify=lambda v: "162.0.208.88" in v and "8101" in v,
        on_drift=DriftAction.ALERT_AND_FIX,
        auto_fix_value="http://162.0.208.88:8101",
        related_to="ai-brain"
    ),
    
    # Ports - ensure no conflicts
    "ARIA_COMMAND_PORT": ConfigSpec(
        key="ARIA_COMMAND_PORT",
        description="Aria Command API port",
        required=False,
        pattern=r"8750",
        verify=lambda v: v == "8750",
        on_drift=DriftAction.ALERT,
        auto_fix_value="8750",
        related_to="aria-command"
    ),
}


class ConfigContract:
    """
    Validates configurations and detects drift.
    
    Proactively catches config issues BEFORE they cause failures.
    """
    
    def __init__(self):
        self.contracts = CONFIG_CONTRACTS
        self.last_validation: Dict[str, bool] = {}
        self.drift_history: List[ConfigDrift] = []
        logger.info(f"ConfigContract initialized with {len(self.contracts)} contracts")
    
    def validate_all(self) -> List[ConfigDrift]:
        """Validate all configured environment variables."""
        drifts = []
        
        for key, spec in self.contracts.items():
            drift = self.validate_config(key)
            if drift:
                drifts.append(drift)
                self.last_validation[key] = False
            else:
                self.last_validation[key] = True
        
        if drifts:
            logger.warning(f"Config validation found {len(drifts)} drift(s)")
            self.drift_history.extend(drifts)
        else:
            logger.info("All config validations passed")
        
        return drifts
    
    def validate_config(self, key: str) -> Optional[ConfigDrift]:
        """Validate a single configuration."""
        spec = self.contracts.get(key)
        if not spec:
            return None
        
        value = os.getenv(key, "")
        
        # Check if required but missing
        if spec.required and not value:
            return ConfigDrift(
                key=key,
                expected="(set)",
                actual="(not set)",
                description=f"{spec.description} - REQUIRED but not set",
                action=spec.on_drift,
                auto_fix_value=spec.auto_fix_value
            )
        
        # Skip further checks if not set and not required
        if not value:
            return None
        
        # Check minimum length
        if spec.min_length and len(value) < spec.min_length:
            return ConfigDrift(
                key=key,
                expected=f"min {spec.min_length} chars",
                actual=f"{len(value)} chars",
                description=f"{spec.description} - Too short",
                action=spec.on_drift,
                auto_fix_value=spec.auto_fix_value
            )
        
        # Check must_start_with
        if spec.must_start_with and not value.startswith(spec.must_start_with):
            return ConfigDrift(
                key=key,
                expected=f"starts with '{spec.must_start_with}'",
                actual=f"starts with '{value[:10]}...'",
                description=f"{spec.description} - Invalid prefix",
                action=spec.on_drift,
                auto_fix_value=spec.auto_fix_value
            )
        
        # Check must_contain
        if spec.must_contain and spec.must_contain not in value:
            return ConfigDrift(
                key=key,
                expected=f"contains '{spec.must_contain}'",
                actual=f"value: {value[:30]}...",
                description=f"{spec.description} - Missing required content",
                action=spec.on_drift,
                auto_fix_value=spec.auto_fix_value
            )
        
        # Check must_not_contain (THE WHALETRACK FIX)
        if spec.must_not_contain and spec.must_not_contain in value:
            return ConfigDrift(
                key=key,
                expected=f"NOT contain '{spec.must_not_contain}'",
                actual=f"contains '{spec.must_not_contain}'",
                description=f"{spec.description} - Contains forbidden content (CONFIG DRIFT!)",
                action=spec.on_drift,
                auto_fix_value=spec.auto_fix_value
            )
        
        # Check pattern
        if spec.pattern and not re.match(spec.pattern, value):
            return ConfigDrift(
                key=key,
                expected=f"matches {spec.pattern}",
                actual=f"value: {value[:30]}...",
                description=f"{spec.description} - Pattern mismatch",
                action=spec.on_drift,
                auto_fix_value=spec.auto_fix_value
            )
        
        # Check custom verify function
        if spec.verify and not spec.verify(value):
            return ConfigDrift(
                key=key,
                expected="(custom validation)",
                actual=f"value: {value[:30]}...",
                description=f"{spec.description} - Custom validation failed",
                action=spec.on_drift,
                auto_fix_value=spec.auto_fix_value
            )
        
        return None
    
    def apply_fixes(self, drifts: List[ConfigDrift]) -> List[ConfigDrift]:
        """
        Apply auto-fixes where possible.
        
        Note: This updates the runtime environment, but for persistence
        the .env file should also be updated.
        """
        fixed = []
        
        for drift in drifts:
            if drift.action in [DriftAction.ALERT_AND_FIX, DriftAction.FIX_SILENT]:
                if drift.auto_fix_value:
                    # Apply fix to runtime environment
                    os.environ[drift.key] = drift.auto_fix_value
                    drift.fixed = True
                    fixed.append(drift)
                    logger.info(f"Auto-fixed {drift.key}: {drift.auto_fix_value}")
        
        return fixed
    
    def get_related_configs(self, service: str) -> Dict[str, Any]:
        """Get all configs related to a service."""
        related = {}
        for key, spec in self.contracts.items():
            if spec.related_to == service:
                value = os.getenv(key, "")
                drift = self.validate_config(key)
                related[key] = {
                    "value_set": bool(value),
                    "valid": drift is None,
                    "drift": str(drift) if drift else None
                }
        return related
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of all validations."""
        drifts = self.validate_all()
        
        return {
            "total_configs": len(self.contracts),
            "valid": sum(1 for v in self.last_validation.values() if v),
            "invalid": sum(1 for v in self.last_validation.values() if not v),
            "drifts": [
                {
                    "key": d.key,
                    "description": d.description,
                    "action": d.action.value,
                    "can_auto_fix": d.auto_fix_value is not None
                }
                for d in drifts
            ],
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# SINGLETON
# ============================================================================

_contract: Optional[ConfigContract] = None


def get_config_contract() -> ConfigContract:
    """Get or create the config contract instance."""
    global _contract
    if _contract is None:
        _contract = ConfigContract()
    return _contract


def validate_all_configs() -> List[ConfigDrift]:
    """Convenience function to validate all configs."""
    return get_config_contract().validate_all()


def fix_config_drifts(drifts: List[ConfigDrift]) -> List[ConfigDrift]:
    """Convenience function to fix drifts."""
    return get_config_contract().apply_fixes(drifts)









