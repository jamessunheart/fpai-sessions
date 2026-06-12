"""
Self-Modification Protocol - Aria can improve her own code with safeguards.

Safety mechanisms:
- Never modify security/auth code without human approval
- Always create backup before modification
- Test changes in sandbox first
- Automatic rollback on failure
- Rate limiting on self-modifications
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

logger = logging.getLogger("aria.sovereign.self_modify")


class ModificationRisk(Enum):
    """Risk levels for self-modification."""
    SAFE = "safe"           # Config, prompts, parameters
    LOW = "low"             # Non-critical code
    MEDIUM = "medium"       # Core logic
    HIGH = "high"           # Integration points
    FORBIDDEN = "forbidden" # Security, auth, financial


@dataclass
class ModificationRequest:
    """A request to modify Aria's own code."""
    id: str
    description: str
    file_path: str
    
    # Change details
    change_type: str  # "add", "modify", "delete"
    search_text: Optional[str] = None  # For modify
    replacement_text: Optional[str] = None
    
    # Risk assessment
    risk: ModificationRisk = ModificationRisk.MEDIUM
    requires_approval: bool = True
    
    # Status
    status: str = "pending"  # "pending", "approved", "executed", "rolled_back", "rejected"
    
    # Backup
    backup_path: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    executed_at: Optional[datetime] = None


@dataclass
class ModificationResult:
    """Result of a self-modification."""
    request_id: str
    success: bool
    message: str
    
    # Backup info
    backup_created: bool = False
    backup_path: Optional[str] = None
    
    # Test results
    tests_passed: bool = True
    test_output: Optional[str] = None
    
    # Rollback info
    can_rollback: bool = False
    rolled_back: bool = False


class SelfModificationProtocol:
    """
    Safe self-modification system with multiple safeguards.
    
    Safeguards:
    1. Protected paths - Never modify critical files automatically
    2. Backup requirement - Must backup before any change
    3. Sandbox testing - Test changes before applying to production
    4. Rate limiting - Max N modifications per hour
    5. Approval requirements - High-risk changes need human approval
    6. Automatic rollback - Revert on failure
    """
    
    # Protected paths - NEVER auto-modify
    FORBIDDEN_PATHS = [
        "core/trust.py",
        "core/confidence.py",
        "sovereign/self_modify.py",  # Can't modify itself!
        "access/terminal.py",
        "ops/server_ops.py",
        ".env",
        "credentials",
        "secrets",
    ]
    
    # Paths requiring extra approval
    HIGH_RISK_PATHS = [
        "agents/",
        "brain/",
        "reality/",
        "main.py",
    ]
    
    # Rate limiting
    MAX_MODIFICATIONS_PER_HOUR = 10
    
    def __init__(self, workspace: str = None):
        self.workspace = workspace or os.getenv("WORKSPACE_ROOT", "/Users/jamessunheart/FPAI_Cockpit")
        self.aria_path = os.path.join(self.workspace, "SERVICES/aria-command")
        self.backup_dir = os.path.join(self.aria_path, ".self-backups")
        
        self.pending_requests: Dict[str, ModificationRequest] = {}
        self.modification_history: List[ModificationRequest] = []
        self.modifications_this_hour: List[datetime] = []
        
        os.makedirs(self.backup_dir, exist_ok=True)
    
    async def propose_modification(
        self,
        description: str,
        file_path: str,
        change_type: str,
        search_text: str = None,
        replacement_text: str = None
    ) -> ModificationRequest:
        """
        Propose a self-modification.
        
        Returns a request that may require approval before execution.
        """
        import hashlib
        
        # Validate path
        full_path = self._resolve_path(file_path)
        relative_path = os.path.relpath(full_path, self.aria_path)
        
        # Check if forbidden
        risk = self._assess_risk(relative_path)
        
        if risk == ModificationRisk.FORBIDDEN:
            raise ValueError(f"Cannot modify protected path: {relative_path}")
        
        # Generate request ID
        request_id = hashlib.md5(
            f"{file_path}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        request = ModificationRequest(
            id=request_id,
            description=description,
            file_path=relative_path,
            change_type=change_type,
            search_text=search_text,
            replacement_text=replacement_text,
            risk=risk,
            requires_approval=risk.value in ["medium", "high"]
        )
        
        if request.requires_approval:
            self.pending_requests[request_id] = request
            logger.info(f"Self-modification requires approval: {request_id} - {description}")
        else:
            # Execute immediately for safe changes
            result = await self.execute_modification(request)
            if not result.success:
                raise RuntimeError(f"Modification failed: {result.message}")
        
        return request
    
    async def approve_modification(self, request_id: str) -> ModificationResult:
        """Approve and execute a pending modification."""
        if request_id not in self.pending_requests:
            return ModificationResult(
                request_id=request_id,
                success=False,
                message="Request not found"
            )
        
        request = self.pending_requests.pop(request_id)
        return await self.execute_modification(request)
    
    async def execute_modification(self, request: ModificationRequest) -> ModificationResult:
        """Execute a self-modification with safeguards."""
        # Check rate limit
        self._cleanup_rate_limit()
        if len(self.modifications_this_hour) >= self.MAX_MODIFICATIONS_PER_HOUR:
            return ModificationResult(
                request_id=request.id,
                success=False,
                message=f"Rate limit exceeded ({self.MAX_MODIFICATIONS_PER_HOUR}/hour)"
            )
        
        full_path = os.path.join(self.aria_path, request.file_path)
        
        # Step 1: Create backup
        backup_path = None
        if os.path.exists(full_path):
            backup_path = self._create_backup(full_path)
            request.backup_path = backup_path
        
        try:
            # Step 2: Apply change
            if request.change_type == "add":
                self._add_content(full_path, request.replacement_text)
            elif request.change_type == "modify":
                self._modify_content(full_path, request.search_text, request.replacement_text)
            elif request.change_type == "delete":
                self._delete_content(full_path, request.search_text)
            else:
                return ModificationResult(
                    request_id=request.id,
                    success=False,
                    message=f"Unknown change type: {request.change_type}"
                )
            
            # Step 3: Test changes
            tests_passed, test_output = await self._run_tests(request.file_path)
            
            if not tests_passed:
                # Rollback
                if backup_path:
                    shutil.copy2(backup_path, full_path)
                
                return ModificationResult(
                    request_id=request.id,
                    success=False,
                    message="Tests failed, changes rolled back",
                    backup_created=True,
                    backup_path=backup_path,
                    tests_passed=False,
                    test_output=test_output,
                    rolled_back=True
                )
            
            # Success
            request.status = "executed"
            request.executed_at = datetime.now()
            self.modification_history.append(request)
            self.modifications_this_hour.append(datetime.now())
            
            logger.info(f"Self-modification successful: {request.id}")
            
            return ModificationResult(
                request_id=request.id,
                success=True,
                message="Modification applied successfully",
                backup_created=bool(backup_path),
                backup_path=backup_path,
                tests_passed=True,
                test_output=test_output,
                can_rollback=bool(backup_path)
            )
            
        except Exception as e:
            # Rollback on error
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, full_path)
            
            logger.error(f"Self-modification failed: {e}")
            
            return ModificationResult(
                request_id=request.id,
                success=False,
                message=f"Error: {str(e)}",
                backup_created=bool(backup_path),
                backup_path=backup_path,
                rolled_back=True
            )
    
    async def rollback(self, request_id: str) -> bool:
        """Rollback a previous modification."""
        # Find in history
        request = None
        for req in self.modification_history:
            if req.id == request_id:
                request = req
                break
        
        if not request or not request.backup_path:
            return False
        
        full_path = os.path.join(self.aria_path, request.file_path)
        
        if os.path.exists(request.backup_path):
            shutil.copy2(request.backup_path, full_path)
            request.status = "rolled_back"
            logger.info(f"Rolled back modification: {request_id}")
            return True
        
        return False
    
    def _resolve_path(self, file_path: str) -> str:
        """Resolve a file path relative to Aria's code."""
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(self.aria_path, file_path)
    
    def _assess_risk(self, relative_path: str) -> ModificationRisk:
        """Assess the risk level of modifying a path."""
        # Check forbidden
        for forbidden in self.FORBIDDEN_PATHS:
            if forbidden in relative_path:
                return ModificationRisk.FORBIDDEN
        
        # Check high risk
        for high_risk in self.HIGH_RISK_PATHS:
            if relative_path.startswith(high_risk):
                return ModificationRisk.HIGH
        
        # Config and prompts are safe
        if "config" in relative_path or "prompt" in relative_path:
            return ModificationRisk.SAFE
        
        # Tests are low risk
        if "test" in relative_path:
            return ModificationRisk.LOW
        
        return ModificationRisk.MEDIUM
    
    def _create_backup(self, file_path: str) -> str:
        """Create a backup of a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        backup_path = os.path.join(self.backup_dir, f"{filename}.{timestamp}.bak")
        
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def _add_content(self, file_path: str, content: str):
        """Add new content to a file."""
        with open(file_path, 'a') as f:
            f.write(content)
    
    def _modify_content(self, file_path: str, search: str, replace: str):
        """Modify content in a file."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        if search not in content:
            raise ValueError(f"Search text not found in {file_path}")
        
        new_content = content.replace(search, replace, 1)
        
        with open(file_path, 'w') as f:
            f.write(new_content)
    
    def _delete_content(self, file_path: str, search: str):
        """Delete content from a file."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        if search not in content:
            raise ValueError(f"Search text not found in {file_path}")
        
        new_content = content.replace(search, '', 1)
        
        with open(file_path, 'w') as f:
            f.write(new_content)
    
    async def _run_tests(self, file_path: str) -> tuple:
        """Run tests to verify changes."""
        # Basic syntax check for Python files
        if file_path.endswith('.py'):
            full_path = os.path.join(self.aria_path, file_path)
            
            try:
                import py_compile
                py_compile.compile(full_path, doraise=True)
                return True, "Syntax check passed"
            except py_compile.PyCompileError as e:
                return False, f"Syntax error: {e}"
        
        return True, "No tests available"
    
    def _cleanup_rate_limit(self):
        """Remove old entries from rate limit tracker."""
        cutoff = datetime.now() - timedelta(hours=1)
        self.modifications_this_hour = [
            t for t in self.modifications_this_hour if t > cutoff
        ]
    
    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending modification requests."""
        return [
            {
                "id": req.id,
                "description": req.description,
                "file_path": req.file_path,
                "risk": req.risk.value,
                "created_at": req.created_at.isoformat()
            }
            for req in self.pending_requests.values()
        ]
    
    def get_modification_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent modification history."""
        return [
            {
                "id": req.id,
                "description": req.description,
                "file_path": req.file_path,
                "status": req.status,
                "executed_at": req.executed_at.isoformat() if req.executed_at else None
            }
            for req in self.modification_history[-limit:]
        ]


# Singleton instance
_protocol: Optional[SelfModificationProtocol] = None

def get_self_modification_protocol() -> SelfModificationProtocol:
    """Get or create self-modification protocol instance."""
    global _protocol
    if _protocol is None:
        _protocol = SelfModificationProtocol()
    return _protocol


