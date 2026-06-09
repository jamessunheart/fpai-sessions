"""
Healing Executor - Executes healing actions to fix service failures
"""
import subprocess
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable, Dict
from enum import Enum
from pathlib import Path

from .config import HEALING_TIMEOUT, MAX_AUTO_RESTARTS, RESTART_COOLDOWN
from .registry import ServiceDefinition
from .failure_analyzer import FailureType, FailureDiagnosis

logger = logging.getLogger(__name__)


class HealingResult(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    REQUIRES_HUMAN = "requires_human"


@dataclass
class HealingOutcome:
    """Outcome of a healing attempt."""
    service_name: str
    failure_type: FailureType
    action_name: str
    result: HealingResult
    execution_time_ms: int
    error: Optional[str] = None
    notes: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> dict:
        return {
            "service_name": self.service_name,
            "failure_type": self.failure_type.value,
            "action_name": self.action_name,
            "result": self.result.value,
            "execution_time_ms": self.execution_time_ms,
            "error": self.error,
            "notes": self.notes,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class HealingAction:
    """Base class for healing actions."""
    
    name: str = "base_action"
    risk_level: str = "low"  # low, medium, high
    reversible: bool = True
    timeout_seconds: int = 60
    
    def can_handle(self, failure_type: FailureType) -> bool:
        """Check if this action can handle the given failure type."""
        raise NotImplementedError
    
    def execute(self, service: ServiceDefinition, diagnosis: FailureDiagnosis) -> HealingOutcome:
        """Execute the healing action."""
        raise NotImplementedError
    
    def rollback(self, service: ServiceDefinition) -> bool:
        """Rollback the action if possible."""
        return False


class RestartServiceAction(HealingAction):
    """Simply restart the service via systemd."""
    
    name = "restart_service"
    risk_level = "low"
    reversible = True
    timeout_seconds = 30
    
    def can_handle(self, failure_type: FailureType) -> bool:
        # Can handle most failure types as a last resort
        return failure_type in [
            FailureType.UNKNOWN,
            FailureType.STARTUP_TIMEOUT,
            FailureType.MEMORY_OOM,
        ]
    
    def execute(self, service: ServiceDefinition, diagnosis: FailureDiagnosis) -> HealingOutcome:
        start_time = datetime.now()
        try:
            result = subprocess.run(
                ["systemctl", "restart", service.systemd_name],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if result.returncode == 0:
                return HealingOutcome(
                    service_name=service.name,
                    failure_type=diagnosis.failure_type,
                    action_name=self.name,
                    result=HealingResult.SUCCESS,
                    execution_time_ms=execution_time,
                    notes=f"Service {service.systemd_name} restarted successfully",
                )
            else:
                return HealingOutcome(
                    service_name=service.name,
                    failure_type=diagnosis.failure_type,
                    action_name=self.name,
                    result=HealingResult.FAILED,
                    execution_time_ms=execution_time,
                    error=result.stderr or result.stdout,
                )
        except subprocess.TimeoutExpired:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.TIMEOUT,
                execution_time_ms=self.timeout_seconds * 1000,
                error="Restart command timed out",
            )
        except Exception as e:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.FAILED,
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e),
            )


class CreateVenvAction(HealingAction):
    """Create a virtual environment for the service."""
    
    name = "create_venv"
    risk_level = "low"
    reversible = True
    timeout_seconds = 120
    
    def can_handle(self, failure_type: FailureType) -> bool:
        return failure_type == FailureType.MISSING_VENV
    
    def execute(self, service: ServiceDefinition, diagnosis: FailureDiagnosis) -> HealingOutcome:
        start_time = datetime.now()
        
        if not service.venv_path:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.SKIPPED,
                execution_time_ms=0,
                notes="Service doesn't use venv",
            )
        
        venv_full_path = Path(service.working_dir) / service.venv_path
        
        try:
            # Create venv
            logger.info(f"Creating venv at {venv_full_path}")
            result = subprocess.run(
                ["python3", "-m", "venv", str(venv_full_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=service.working_dir,
            )
            
            if result.returncode != 0:
                return HealingOutcome(
                    service_name=service.name,
                    failure_type=diagnosis.failure_type,
                    action_name=self.name,
                    result=HealingResult.FAILED,
                    execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    error=result.stderr or result.stdout,
                )
            
            # Install requirements
            req_path = Path(service.working_dir) / service.requirements_file
            if req_path.exists():
                pip_path = venv_full_path / "bin" / "pip"
                logger.info(f"Installing requirements from {req_path}")
                result = subprocess.run(
                    [str(pip_path), "install", "-q", "-r", str(req_path)],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    cwd=service.working_dir,
                )
                
                if result.returncode != 0:
                    return HealingOutcome(
                        service_name=service.name,
                        failure_type=diagnosis.failure_type,
                        action_name=self.name,
                        result=HealingResult.FAILED,
                        execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                        error=f"pip install failed: {result.stderr}",
                    )
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.SUCCESS,
                execution_time_ms=execution_time,
                notes=f"Created venv and installed deps at {venv_full_path}",
            )
            
        except subprocess.TimeoutExpired:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.TIMEOUT,
                execution_time_ms=self.timeout_seconds * 1000,
                error="Venv creation timed out",
            )
        except Exception as e:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.FAILED,
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e),
            )


class InstallDepsAction(HealingAction):
    """Install missing Python dependencies."""
    
    name = "install_deps"
    risk_level = "low"
    reversible = False  # Can't easily uninstall
    timeout_seconds = 90
    
    def can_handle(self, failure_type: FailureType) -> bool:
        return failure_type == FailureType.MISSING_DEPS
    
    def execute(self, service: ServiceDefinition, diagnosis: FailureDiagnosis) -> HealingOutcome:
        start_time = datetime.now()
        
        missing_module = diagnosis.missing_module
        if not missing_module:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.FAILED,
                execution_time_ms=0,
                error="No missing module specified in diagnosis",
            )
        
        # Determine pip path
        if service.venv_path:
            pip_path = Path(service.working_dir) / service.venv_path / "bin" / "pip"
        else:
            pip_path = "pip3"
        
        try:
            logger.info(f"Installing {missing_module} for {service.name}")
            result = subprocess.run(
                [str(pip_path), "install", "-q", missing_module],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                cwd=service.working_dir,
            )
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if result.returncode == 0:
                return HealingOutcome(
                    service_name=service.name,
                    failure_type=diagnosis.failure_type,
                    action_name=self.name,
                    result=HealingResult.SUCCESS,
                    execution_time_ms=execution_time,
                    notes=f"Installed {missing_module}",
                )
            else:
                return HealingOutcome(
                    service_name=service.name,
                    failure_type=diagnosis.failure_type,
                    action_name=self.name,
                    result=HealingResult.FAILED,
                    execution_time_ms=execution_time,
                    error=result.stderr or result.stdout,
                )
                
        except subprocess.TimeoutExpired:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.TIMEOUT,
                execution_time_ms=self.timeout_seconds * 1000,
                error="pip install timed out",
            )
        except Exception as e:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.FAILED,
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e),
            )


class KillPortAction(HealingAction):
    """Kill process using a specific port."""
    
    name = "kill_port"
    risk_level = "medium"
    reversible = False
    timeout_seconds = 30
    
    def can_handle(self, failure_type: FailureType) -> bool:
        return failure_type == FailureType.PORT_IN_USE
    
    def execute(self, service: ServiceDefinition, diagnosis: FailureDiagnosis) -> HealingOutcome:
        start_time = datetime.now()
        
        try:
            # Find PID using port
            result = subprocess.run(
                ["lsof", "-t", f"-i:{service.port}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            pids = result.stdout.strip().split('\n')
            pids = [p for p in pids if p.isdigit()]
            
            if not pids:
                return HealingOutcome(
                    service_name=service.name,
                    failure_type=diagnosis.failure_type,
                    action_name=self.name,
                    result=HealingResult.SKIPPED,
                    execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                    notes=f"No process found on port {service.port}",
                )
            
            # Kill the processes
            killed = []
            for pid in pids:
                logger.info(f"Killing PID {pid} on port {service.port}")
                kill_result = subprocess.run(
                    ["kill", "-9", pid],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if kill_result.returncode == 0:
                    killed.append(pid)
            
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            if killed:
                return HealingOutcome(
                    service_name=service.name,
                    failure_type=diagnosis.failure_type,
                    action_name=self.name,
                    result=HealingResult.SUCCESS,
                    execution_time_ms=execution_time,
                    notes=f"Killed PIDs: {', '.join(killed)}",
                )
            else:
                return HealingOutcome(
                    service_name=service.name,
                    failure_type=diagnosis.failure_type,
                    action_name=self.name,
                    result=HealingResult.FAILED,
                    execution_time_ms=execution_time,
                    error="Could not kill processes",
                )
                
        except Exception as e:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name=self.name,
                result=HealingResult.FAILED,
                execution_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                error=str(e),
            )


class HealingExecutor:
    """
    Orchestrates healing actions based on failure diagnosis.
    """
    
    def __init__(self):
        # Register all available actions
        self.actions: Dict[str, HealingAction] = {
            "restart_service": RestartServiceAction(),
            "create_venv": CreateVenvAction(),
            "install_deps": InstallDepsAction(),
            "kill_port": KillPortAction(),
        }
        
        # Track healing attempts per service
        self.attempt_counts: Dict[str, int] = {}
        self.last_attempt_time: Dict[str, datetime] = {}
        self.outcomes: list = []
    
    def get_action_for_failure(self, failure_type: FailureType) -> Optional[HealingAction]:
        """Find the best action to handle a failure type."""
        for action in self.actions.values():
            if action.can_handle(failure_type):
                return action
        return None
    
    def can_attempt_healing(self, service_name: str) -> tuple[bool, str]:
        """Check if we can attempt healing (respecting cooldown and max attempts)."""
        attempts = self.attempt_counts.get(service_name, 0)
        
        if attempts >= MAX_AUTO_RESTARTS:
            return False, f"Max attempts ({MAX_AUTO_RESTARTS}) reached"
        
        last_attempt = self.last_attempt_time.get(service_name)
        if last_attempt:
            elapsed = (datetime.now() - last_attempt).total_seconds()
            if elapsed < RESTART_COOLDOWN:
                return False, f"Cooldown active ({int(RESTART_COOLDOWN - elapsed)}s remaining)"
        
        return True, "OK"
    
    def heal(self, service: ServiceDefinition, diagnosis: FailureDiagnosis) -> HealingOutcome:
        """
        Attempt to heal a service based on the diagnosis.
        """
        # Check if healing requires human intervention
        if diagnosis.requires_human:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name="none",
                result=HealingResult.REQUIRES_HUMAN,
                execution_time_ms=0,
                notes=f"Requires human: {diagnosis.suggested_fix}",
            )
        
        # Check if we can attempt healing
        can_heal, reason = self.can_attempt_healing(service.name)
        if not can_heal:
            return HealingOutcome(
                service_name=service.name,
                failure_type=diagnosis.failure_type,
                action_name="none",
                result=HealingResult.SKIPPED,
                execution_time_ms=0,
                notes=reason,
            )
        
        # Find appropriate action
        action = self.get_action_for_failure(diagnosis.failure_type)
        
        if not action:
            # Fall back to restart
            action = self.actions["restart_service"]
            logger.warning(f"No specific action for {diagnosis.failure_type}, falling back to restart")
        
        # Execute the action
        logger.info(f"Executing {action.name} for {service.name} (failure: {diagnosis.failure_type.value})")
        
        self.attempt_counts[service.name] = self.attempt_counts.get(service.name, 0) + 1
        self.last_attempt_time[service.name] = datetime.now()
        
        outcome = action.execute(service, diagnosis)
        self.outcomes.append(outcome)
        
        # If action succeeded but wasn't restart, also restart the service
        if outcome.result == HealingResult.SUCCESS and action.name != "restart_service":
            logger.info(f"Action succeeded, restarting {service.name}")
            restart_outcome = self.actions["restart_service"].execute(service, diagnosis)
            
            if restart_outcome.result != HealingResult.SUCCESS:
                outcome.notes = f"{outcome.notes or ''} (restart failed: {restart_outcome.error})"
                outcome.result = HealingResult.FAILED
        
        return outcome
    
    def reset_attempts(self, service_name: str):
        """Reset attempt counter for a service (call when service is healthy)."""
        if service_name in self.attempt_counts:
            self.attempt_counts[service_name] = 0
    
    def get_outcomes(self, limit: int = 100) -> list:
        """Get recent healing outcomes."""
        return self.outcomes[-limit:]
    
    def get_stats(self) -> dict:
        """Get healing statistics."""
        if not self.outcomes:
            return {"total": 0, "success_rate": 0}
        
        total = len(self.outcomes)
        successes = sum(1 for o in self.outcomes if o.result == HealingResult.SUCCESS)
        
        return {
            "total_attempts": total,
            "successes": successes,
            "failures": total - successes,
            "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
            "by_action": self._stats_by_action(),
            "by_failure_type": self._stats_by_failure_type(),
        }
    
    def _stats_by_action(self) -> dict:
        stats = {}
        for outcome in self.outcomes:
            action = outcome.action_name
            if action not in stats:
                stats[action] = {"total": 0, "success": 0}
            stats[action]["total"] += 1
            if outcome.result == HealingResult.SUCCESS:
                stats[action]["success"] += 1
        return stats
    
    def _stats_by_failure_type(self) -> dict:
        stats = {}
        for outcome in self.outcomes:
            ft = outcome.failure_type.value
            if ft not in stats:
                stats[ft] = {"total": 0, "success": 0}
            stats[ft]["total"] += 1
            if outcome.result == HealingResult.SUCCESS:
                stats[ft]["success"] += 1
        return stats


# Global executor instance
healing_executor = HealingExecutor()











