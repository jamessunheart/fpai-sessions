#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - TERMINAL EXECUTION
=========================================

Execute commands on any server with safety levels.

Safety Levels:
- GREEN (auto): Read-only commands - status, logs, df, ps, cat, grep
- YELLOW (approve): Modify commands - restart, pip install, git pull
- RED (confirm twice): Dangerous - rm, deploy, database changes
"""

import os
import re
import asyncio
import logging
from typing import Optional, Dict, List, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncssh
import socket

logger = logging.getLogger("aria.terminal")


def _detect_current_server():
    """Detect which server we are currently running on."""
    try:
        hostname = socket.gethostname()
        # Check by hostname pattern
        if "3016" in hostname:
            return "secondary"
        if "0934" in hostname:
            return "primary"
        
        # Check by IP
        local_ips = socket.gethostbyname_ex(hostname)[2]
        if "162.0.208.88" in local_ips:
            return "secondary"
        if "198.54.123.234" in local_ips:
            return "primary"
    except Exception:
        pass
    return None

# Detect on module load
CURRENT_SERVER = _detect_current_server()
logger.info(f"Terminal executor running on: {CURRENT_SERVER or 'unknown'}")

# ============================================================================
# CONFIGURATION
# ============================================================================

class SafetyLevel(str, Enum):
    GREEN = "green"      # Auto-execute
    YELLOW = "yellow"    # Requires approval
    RED = "red"          # Requires double confirmation

class Server(str, Enum):
    LOCAL = "local"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    ALL = "all"

SERVERS = {
    Server.PRIMARY: {
        "host": "198.54.123.234",
        "user": "root",
        "name": "Primary (Web/Trading)"
    },
    Server.SECONDARY: {
        "host": "162.0.208.88",
        "user": "root",
        "name": "Secondary (AI/Consciousness)"
    }
}

# Command safety classification
GREEN_COMMANDS = [
    # Status and info
    r"^systemctl\s+(status|is-active|is-enabled)",
    r"^journalctl",
    r"^cat\s+",
    r"^head\s+",
    r"^tail\s+",
    r"^less\s+",
    r"^grep\s+",
    r"^find\s+",
    r"^ls\s+",
    r"^ll\s*",
    r"^pwd$",
    r"^whoami$",
    r"^hostname$",
    r"^date$",
    r"^uptime$",
    r"^df\s+",
    r"^du\s+",
    r"^free\s+",
    r"^top\s+-bn1",
    r"^ps\s+",
    r"^netstat\s+",
    r"^ss\s+",
    # Curl to localhost
    r"^curl\s+.+localhost",
    r"^curl\s+-s\s+http://localhost",
    # Curl to our known servers (read-only API queries)
    r"^curl\s+.*198\.54\.123\.234",   # Primary server
    r"^curl\s+.*162\.0\.208\.88",     # Secondary server
    r"^curl\s+.*:8600",                # WhaleTrack Magnet
    r"^curl\s+.*:8601",                # WhaleTrack Live
    r"^curl\s+.*/api/",                # Any API endpoint (GET)
    r"^curl\s+.*/health",              # Health checks
    r"^curl\s+-s\s+http://",           # Silent GET requests
    # Docker
    r"^docker\s+(ps|images|logs)",
    r"^pip\s+(list|show|freeze)",
    r"^python3?\s+-c\s+['\"]import",
    r"^python3?\s+--version",
    r"^git\s+(status|log|diff|branch|show)",
    r"^wc\s+",
    r"^sort\s+",
    r"^uniq\s+",
    r"^echo\s+",
]

YELLOW_COMMANDS = [
    # Service management
    r"^systemctl\s+(restart|reload|start|stop)",
    r"^service\s+",
    # Package management
    r"^pip\s+install",
    r"^pip3\s+install",
    r"^apt\s+(update|upgrade|install)",
    # Git writes
    r"^git\s+(pull|push|commit|checkout|merge)",
    # File writes
    r"^cp\s+",
    r"^mv\s+",
    r"^mkdir\s+",
    r"^touch\s+",
    # Docker management
    r"^docker\s+(start|stop|restart|pull)",
    r"^docker-compose\s+",
    # Process management
    r"^kill\s+",
    r"^pkill\s+",
]

RED_COMMANDS = [
    # Destructive
    r"^rm\s+",
    r"^rmdir\s+",
    r"^dd\s+",
    # System level
    r"^shutdown",
    r"^reboot",
    r"^init\s+",
    r"^systemctl\s+(disable|mask)",
    # Database
    r"^mysql\s+",
    r"^psql\s+",
    r"^redis-cli\s+",
    r"^mongo\s+",
    # Deploy
    r"deploy",
    # Dangerous curl
    r"^curl\s+.*\|\s*(bash|sh)",
    # User management
    r"^useradd",
    r"^userdel",
    r"^passwd",
    r"^chown",
    r"^chmod\s+777",
]

BLOCKED_COMMANDS = [
    r"^rm\s+-rf\s+/",       # Never rm -rf /
    r"mkfs",                 # No formatting
    r">\s*/dev/sd",          # No writing to devices
    r":\(\)\{",              # Fork bomb
    r"mv\s+/",               # No moving root
]


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    server: str = ""
    command: str = ""
    safety_level: str = ""
    execution_time_ms: int = 0
    error: Optional[str] = None
    requires_approval: bool = False
    approval_id: Optional[str] = None


@dataclass
class PendingCommand:
    """A command waiting for approval."""
    id: str
    command: str
    server: str
    safety_level: SafetyLevel
    created_at: datetime = field(default_factory=datetime.now)
    approved: bool = False
    denied: bool = False
    executed: bool = False


class TerminalExecutor:
    """
    Execute commands with safety controls.
    
    Features:
    - Safety level classification
    - Approval flow for dangerous commands
    - Multi-server support
    - Output streaming
    """
    
    def __init__(self):
        self.ssh_connections: Dict[Server, asyncssh.SSHClientConnection] = {}
        self.pending_commands: Dict[str, PendingCommand] = {}
        self.approval_callback: Optional[Callable] = None
    
    async def close(self):
        """Close all connections."""
        for conn in self.ssh_connections.values():
            conn.close()
    
    def set_approval_callback(self, callback: Callable):
        """Set callback for approval requests."""
        self.approval_callback = callback
    
    def classify_command(self, command: str) -> SafetyLevel:
        """Classify command safety level."""
        command = command.strip()
        
        # Check blocked first
        for pattern in BLOCKED_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return SafetyLevel.RED  # Will be blocked
        
        # Check red
        for pattern in RED_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return SafetyLevel.RED
        
        # Check yellow
        for pattern in YELLOW_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return SafetyLevel.YELLOW
        
        # Check green
        for pattern in GREEN_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return SafetyLevel.GREEN
        
        # Default to yellow for unknown
        return SafetyLevel.YELLOW
    
    def is_blocked(self, command: str) -> Tuple[bool, str]:
        """Check if command is completely blocked."""
        for pattern in BLOCKED_COMMANDS:
            if re.search(pattern, command, re.IGNORECASE):
                return True, f"Command blocked for safety: matches {pattern}"
        return False, ""
    
    async def _get_ssh_connection(self, server: Server) -> asyncssh.SSHClientConnection:
        """Get or create SSH connection."""
        if server not in self.ssh_connections:
            config = SERVERS[server]
            self.ssh_connections[server] = await asyncssh.connect(
                config["host"],
                username=config["user"],
                known_hosts=None
            )
        return self.ssh_connections[server]
    
    async def execute(
        self,
        command: str,
        server: Server = Server.SECONDARY,
        force: bool = False,
        timeout: int = 60
    ) -> CommandResult:
        """
        Execute a command.
        
        Args:
            command: Command to execute
            server: Target server
            force: Skip safety checks (use with caution)
            timeout: Command timeout in seconds
        
        Returns:
            CommandResult with output or approval request
        """
        import time
        start = time.time()
        
        # Check if blocked
        blocked, reason = self.is_blocked(command)
        if blocked:
            return CommandResult(
                success=False,
                command=command,
                server=server.value,
                error=reason
            )
        
        # Classify safety
        safety = self.classify_command(command)
        
        # Handle based on safety level
        if safety == SafetyLevel.RED and not force:
            return await self._request_approval(command, server, safety, double_confirm=True)
        
        elif safety == SafetyLevel.YELLOW and not force:
            return await self._request_approval(command, server, safety, double_confirm=False)
        
        # Execute (GREEN or forced)
        try:
            if server == Server.LOCAL:
                result = await self._execute_local(command, timeout)
            elif server == Server.ALL:
                result = await self._execute_all(command, timeout)
            else:
                result = await self._execute_ssh(server, command, timeout)
            
            result.execution_time_ms = int((time.time() - start) * 1000)
            result.safety_level = safety.value
            return result
            
        except Exception as e:
            return CommandResult(
                success=False,
                command=command,
                server=server.value,
                error=str(e),
                safety_level=safety.value
            )
    
    async def _execute_local(self, command: str, timeout: int) -> CommandResult:
        """Execute locally."""
        import subprocess
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                server="local",
                command=command
            )
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                command=command,
                server="local",
                error=f"Command timed out after {timeout}s"
            )
    
    async def _execute_ssh(self, server: Server, command: str, timeout: int) -> CommandResult:
        """Execute on remote server via SSH, or locally if already on that server."""
        # If we're already on the target server, run locally
        if CURRENT_SERVER == server.value:
            logger.info(f"Running locally (already on {server.value})")
            result = await self._execute_local(command, timeout)
            result.server = server.value  # Mark as the intended server
            return result
        
        # Otherwise use SSH
        try:
            conn = await self._get_ssh_connection(server)
            
            result = await asyncio.wait_for(
                conn.run(command),
                timeout=timeout
            )
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                server=server.value,
                command=command
            )
        except asyncio.TimeoutError:
            return CommandResult(
                success=False,
                command=command,
                server=server.value,
                error=f"Command timed out after {timeout}s"
            )
        except Exception as e:
            return CommandResult(
                success=False,
                command=command,
                server=server.value,
                error=f"SSH connection failed: {str(e)}"
            )
    
    async def _execute_all(self, command: str, timeout: int) -> CommandResult:
        """Execute on all servers."""
        results = []
        
        for server in [Server.PRIMARY, Server.SECONDARY]:
            result = await self._execute_ssh(server, command, timeout)
            results.append(f"=== {SERVERS[server]['name']} ===\n{result.stdout}")
            if result.stderr:
                results.append(f"STDERR: {result.stderr}")
        
        return CommandResult(
            success=all(r.success for r in results) if results else False,
            stdout="\n\n".join(results),
            server="all",
            command=command
        )
    
    async def _request_approval(
        self,
        command: str,
        server: Server,
        safety: SafetyLevel,
        double_confirm: bool
    ) -> CommandResult:
        """Request approval for dangerous command."""
        import hashlib
        
        # Generate approval ID
        approval_id = hashlib.md5(
            f"{command}{server}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        # Store pending
        self.pending_commands[approval_id] = PendingCommand(
            id=approval_id,
            command=command,
            server=server.value,
            safety_level=safety
        )
        
        confirm_msg = " (requires double confirmation)" if double_confirm else ""
        
        return CommandResult(
            success=False,
            command=command,
            server=server.value,
            safety_level=safety.value,
            requires_approval=True,
            approval_id=approval_id,
            error=f"Command requires approval{confirm_msg}. ID: {approval_id}"
        )
    
    async def approve_and_execute(self, approval_id: str, confirm_count: int = 1) -> CommandResult:
        """Approve and execute a pending command."""
        pending = self.pending_commands.get(approval_id)
        
        if not pending:
            return CommandResult(
                success=False,
                error=f"Approval ID {approval_id} not found or expired"
            )
        
        if pending.executed:
            return CommandResult(
                success=False,
                error=f"Command already executed"
            )
        
        if pending.denied:
            return CommandResult(
                success=False,
                error=f"Command was denied"
            )
        
        # Check double confirm for RED
        if pending.safety_level == SafetyLevel.RED and confirm_count < 2:
            return CommandResult(
                success=False,
                error="RED level commands require double confirmation. Confirm again.",
                requires_approval=True,
                approval_id=approval_id
            )
        
        # Execute
        pending.approved = True
        pending.executed = True
        
        server = Server(pending.server)
        return await self.execute(pending.command, server, force=True)
    
    def deny_command(self, approval_id: str) -> bool:
        """Deny a pending command."""
        if approval_id in self.pending_commands:
            self.pending_commands[approval_id].denied = True
            return True
        return False
    
    def get_pending(self) -> List[PendingCommand]:
        """Get all pending commands."""
        return [p for p in self.pending_commands.values() if not p.executed and not p.denied]


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_executor: Optional[TerminalExecutor] = None


def get_executor() -> TerminalExecutor:
    """Get or create global executor."""
    global _executor
    if _executor is None:
        _executor = TerminalExecutor()
    return _executor


async def run_command(command: str, server: str = "secondary") -> CommandResult:
    """Run a command on specified server."""
    executor = get_executor()
    server_enum = Server(server.lower())
    return await executor.execute(command, server_enum)


async def run_on_all(command: str) -> CommandResult:
    """Run a command on all servers."""
    executor = get_executor()
    return await executor.execute(command, Server.ALL)


def classify_command(command: str) -> str:
    """Get safety level of a command."""
    executor = get_executor()
    return executor.classify_command(command).value

