"""
Failure Analyzer - Diagnoses WHY services fail by examining logs and system state
"""
import subprocess
import re
import os
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum
from pathlib import Path

from .registry import ServiceDefinition

logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures we can diagnose."""
    MISSING_IMPORT = "missing_import"       # Python import error
    MISSING_VENV = "missing_venv"           # venv doesn't exist
    MISSING_DEPS = "missing_deps"           # Module not installed
    PORT_IN_USE = "port_in_use"             # Address already in use
    CONFIG_ERROR = "config_error"           # Missing env vars, config issues
    DATABASE_ERROR = "database_error"       # DB connection issues
    MEMORY_OOM = "memory_oom"               # Out of memory
    PERMISSION_ERROR = "permission_error"   # File/socket permission issues
    SYNTAX_ERROR = "syntax_error"           # Python syntax error
    STARTUP_TIMEOUT = "startup_timeout"     # Service took too long to start
    UNKNOWN = "unknown"                     # Needs human review


@dataclass
class FailureDiagnosis:
    """Diagnosis of a service failure."""
    service_name: str
    failure_type: FailureType
    confidence: float                       # 0.0 - 1.0
    evidence: str                           # Log snippet that matched
    suggested_fix: Optional[str] = None
    requires_human: bool = False
    missing_module: Optional[str] = None    # For MISSING_DEPS/IMPORT
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "failure_type": self.failure_type.value,
            "confidence": self.confidence,
            "evidence": self.evidence[:500] if self.evidence else None,
            "suggested_fix": self.suggested_fix,
            "requires_human": self.requires_human,
            "missing_module": self.missing_module,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# Pattern matching for log analysis
FAILURE_PATTERNS = [
    # Missing module / import errors
    (
        r"ModuleNotFoundError: No module named ['\"]?([^'\"]+)['\"]?",
        FailureType.MISSING_DEPS,
        0.95,
        "Install missing module: pip install {match}",
    ),
    (
        r"ImportError: cannot import name ['\"]?([^'\"]+)['\"]?",
        FailureType.MISSING_IMPORT,
        0.85,
        "Check if module is installed or import path is correct",
    ),
    (
        r"NameError: name ['\"]?([^'\"]+)['\"]? is not defined",
        FailureType.MISSING_IMPORT,
        0.80,
        "Missing import for: {match}",
    ),
    
    # Port/address errors
    (
        r"error while attempting to bind on address.*address already in use",
        FailureType.PORT_IN_USE,
        0.95,
        "Kill process using the port or wait for it to release",
    ),
    (
        r"OSError.*Address already in use",
        FailureType.PORT_IN_USE,
        0.95,
        "Kill process using the port or wait for it to release",
    ),
    (
        r"Errno 98.*Address already in use",
        FailureType.PORT_IN_USE,
        0.95,
        "Kill process using the port or wait for it to release",
    ),
    
    # Config errors
    (
        r"ValidationError.*field required",
        FailureType.CONFIG_ERROR,
        0.85,
        "Check .env file for missing required fields",
    ),
    (
        r"KeyError: ['\"]?([^'\"]+)['\"]?",
        FailureType.CONFIG_ERROR,
        0.70,
        "Missing config key: {match}",
    ),
    (
        r"pydantic.*validation error",
        FailureType.CONFIG_ERROR,
        0.80,
        "Check configuration values match expected types",
    ),
    
    # Database errors
    (
        r"OperationalError.*Connection refused",
        FailureType.DATABASE_ERROR,
        0.90,
        "Database server may be down, restart it first",
    ),
    (
        r"psycopg2.OperationalError",
        FailureType.DATABASE_ERROR,
        0.85,
        "PostgreSQL connection error",
    ),
    (
        r"sqlite3.OperationalError",
        FailureType.DATABASE_ERROR,
        0.85,
        "SQLite database error - check file permissions",
    ),
    
    # Permission errors
    (
        r"PermissionError: \[Errno 13\]",
        FailureType.PERMISSION_ERROR,
        0.90,
        "Check file/directory permissions",
    ),
    (
        r"Permission denied",
        FailureType.PERMISSION_ERROR,
        0.75,
        "Check file/directory permissions",
    ),
    
    # Syntax errors
    (
        r"SyntaxError: (.*)",
        FailureType.SYNTAX_ERROR,
        0.95,
        "Fix Python syntax error in code: {match}",
    ),
    (
        r"IndentationError: (.*)",
        FailureType.SYNTAX_ERROR,
        0.95,
        "Fix indentation in code: {match}",
    ),
    
    # Memory errors
    (
        r"MemoryError",
        FailureType.MEMORY_OOM,
        0.90,
        "Service ran out of memory, consider adding memory limits",
    ),
    (
        r"Killed.*OOM",
        FailureType.MEMORY_OOM,
        0.95,
        "Process killed by OOM killer",
    ),
    
    # Startup issues
    (
        r"Start request repeated too quickly",
        FailureType.STARTUP_TIMEOUT,
        0.90,
        "Service is crash-looping, check logs for root cause",
    ),
]


class FailureAnalyzer:
    """
    Analyzes service failures by examining logs and system state.
    """
    
    def __init__(self):
        self.recent_diagnoses: List[FailureDiagnosis] = []
    
    def get_journalctl_logs(self, service: ServiceDefinition, lines: int = 100) -> str:
        """Get recent logs from journalctl for a service."""
        try:
            result = subprocess.run(
                ["journalctl", "-u", service.systemd_name, "-n", str(lines), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return result.stdout + result.stderr
        except Exception as e:
            logger.error(f"Failed to get journalctl logs for {service.name}: {e}")
            return ""
    
    def check_venv_exists(self, service: ServiceDefinition) -> Tuple[bool, str]:
        """Check if the service's venv exists and has uvicorn."""
        if not service.venv_path:
            return True, "No venv required"
        
        venv_full_path = Path(service.working_dir) / service.venv_path
        uvicorn_path = venv_full_path / "bin" / "uvicorn"
        
        if not venv_full_path.exists():
            return False, f"Venv directory does not exist: {venv_full_path}"
        
        if not uvicorn_path.exists():
            return False, f"Uvicorn not found in venv: {uvicorn_path}"
        
        return True, "Venv OK"
    
    def check_requirements_exist(self, service: ServiceDefinition) -> Tuple[bool, str]:
        """Check if requirements.txt exists."""
        req_path = Path(service.working_dir) / service.requirements_file
        if not req_path.exists():
            return False, f"Requirements file not found: {req_path}"
        return True, "Requirements file found"
    
    def check_port_in_use(self, port: int) -> Tuple[bool, Optional[str]]:
        """Check if a port is in use and by what."""
        try:
            result = subprocess.run(
                ["lsof", "-i", f":{port}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout.strip():
                return True, result.stdout.strip()
            return False, None
        except Exception as e:
            logger.warning(f"Could not check port {port}: {e}")
            return False, None
    
    def analyze_logs(self, logs: str, service_name: str) -> Optional[FailureDiagnosis]:
        """
        Analyze logs to determine failure type.
        """
        for pattern, failure_type, confidence, fix_template in FAILURE_PATTERNS:
            match = re.search(pattern, logs, re.IGNORECASE | re.MULTILINE)
            if match:
                # Extract matched group if available
                matched_value = match.group(1) if match.lastindex else None
                
                # Format the fix suggestion
                suggested_fix = fix_template
                if matched_value and "{match}" in fix_template:
                    suggested_fix = fix_template.format(match=matched_value)
                
                # Find the line with the error for evidence
                evidence_lines = []
                for line in logs.split('\n'):
                    if re.search(pattern, line, re.IGNORECASE):
                        evidence_lines.append(line.strip())
                        break
                evidence = evidence_lines[0] if evidence_lines else match.group(0)
                
                diagnosis = FailureDiagnosis(
                    service_name=service_name,
                    failure_type=failure_type,
                    confidence=confidence,
                    evidence=evidence,
                    suggested_fix=suggested_fix,
                    requires_human=failure_type in [FailureType.SYNTAX_ERROR, FailureType.UNKNOWN],
                    missing_module=matched_value if failure_type in [FailureType.MISSING_DEPS, FailureType.MISSING_IMPORT] else None,
                )
                return diagnosis
        
        return None
    
    def diagnose(self, service: ServiceDefinition) -> FailureDiagnosis:
        """
        Perform comprehensive failure diagnosis for a service.
        """
        # Check venv first (common issue)
        venv_ok, venv_msg = self.check_venv_exists(service)
        if not venv_ok:
            diagnosis = FailureDiagnosis(
                service_name=service.name,
                failure_type=FailureType.MISSING_VENV,
                confidence=0.95,
                evidence=venv_msg,
                suggested_fix=f"Create venv: cd {service.working_dir} && python3 -m venv {service.venv_path}",
                requires_human=False,
            )
            self.recent_diagnoses.append(diagnosis)
            return diagnosis
        
        # Check if port is in use by something else
        port_in_use, port_info = self.check_port_in_use(service.port)
        if port_in_use:
            diagnosis = FailureDiagnosis(
                service_name=service.name,
                failure_type=FailureType.PORT_IN_USE,
                confidence=0.90,
                evidence=f"Port {service.port} in use:\n{port_info}",
                suggested_fix=f"Kill process using port {service.port} or wait",
                requires_human=False,
            )
            self.recent_diagnoses.append(diagnosis)
            return diagnosis
        
        # Get logs and analyze
        logs = self.get_journalctl_logs(service)
        if logs:
            log_diagnosis = self.analyze_logs(logs, service.name)
            if log_diagnosis:
                self.recent_diagnoses.append(log_diagnosis)
                return log_diagnosis
        
        # Unknown failure
        diagnosis = FailureDiagnosis(
            service_name=service.name,
            failure_type=FailureType.UNKNOWN,
            confidence=0.5,
            evidence=logs[-500:] if logs else "No logs available",
            suggested_fix="Review logs manually and restart",
            requires_human=True,
        )
        self.recent_diagnoses.append(diagnosis)
        return diagnosis
    
    def get_recent_diagnoses(self, limit: int = 50) -> List[FailureDiagnosis]:
        """Get recent diagnoses."""
        return self.recent_diagnoses[-limit:]
    
    def clear_diagnoses(self):
        """Clear diagnosis history."""
        self.recent_diagnoses = []


# Global analyzer instance
failure_analyzer = FailureAnalyzer()











