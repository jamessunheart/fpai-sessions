"""
Aria Server Operations Module
Gives Aria power to manage servers from Telegram
"""

import asyncio
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("aria.ops")

class Server(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    BOTH = "both"

class ApprovalLevel(Enum):
    AUTO = "auto"           # Execute immediately
    CONFIRM = "confirm"     # Ask user to confirm
    CRITICAL = "critical"   # Always require explicit approval

@dataclass
class ServerConfig:
    name: str
    ip: str
    ssh_user: str = "root"
    description: str = ""

SERVERS = {
    Server.PRIMARY: ServerConfig(
        name="Primary",
        ip="198.54.123.234",
        description="Web, Trading, Revenue services"
    ),
    Server.SECONDARY: ServerConfig(
        name="Secondary", 
        ip="162.0.208.88",
        description="AI, Aria, Consciousness services"
    )
}

# Service categories for approval levels
CRITICAL_SERVICES = [
    "whaletrack-live", "whaletrack-magnet", "james-trader",
    "nginx", "docker", "godmode", "fpai-nerve-center",
    "fpai-credits-gateway", "aria-command"
]

NON_CRITICAL_SERVICES = [
    "fpai-consciousness-feeder", "fpai-consciousness-verifier",
    "fpai-consciousness_api", "fpai-consciousness_dashboard",
    "fpai-consciousness_decision_engine", "fpai-consciousness_gateway",
    "fpai-consciousness_network", "fpai-intelligence"
]


class ServerOps:
    """Server operations handler for Aria"""
    
    def __init__(self):
        self.pending_approvals: Dict[str, dict] = {}
    
    async def run_local(self, command: str, timeout: int = 30) -> Tuple[bool, str]:
        """Run command locally on secondary server"""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            output = stdout.decode() + stderr.decode()
            return proc.returncode == 0, output.strip()
        except asyncio.TimeoutError:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    async def run_ssh(self, server: Server, command: str, timeout: int = 30) -> Tuple[bool, str]:
        """Run command via SSH on specified server"""
        if server == Server.SECONDARY:
            # We ARE the secondary server - run locally
            return await self.run_local(command, timeout)
        
        config = SERVERS[server]
        ssh_cmd = f"ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no {config.ssh_user}@{config.ip} '{command}'"
        return await self.run_local(ssh_cmd, timeout)
    
    async def get_system_status(self) -> str:
        """Get comprehensive system status"""
        results = []
        results.append("📊 **SYSTEM STATUS**\n")
        
        for server_type in [Server.PRIMARY, Server.SECONDARY]:
            config = SERVERS[server_type]
            results.append(f"\n**{config.name} Server** ({config.ip})")
            results.append(f"_{config.description}_\n")
            
            # Check connectivity
            success, output = await self.run_ssh(server_type, "uptime", timeout=10)
            if success:
                results.append(f"✅ Online: {output.strip()}")
            else:
                results.append(f"❌ Unreachable: {output}")
                continue
            
            # Memory
            success, output = await self.run_ssh(server_type, "free -m | grep Mem | awk '{print $3\"/\"$2\"MB (\"int($3/$2*100)\"%)\"}' ")
            if success:
                results.append(f"💾 Memory: {output}")
            
            # Disk
            success, output = await self.run_ssh(server_type, "df -h / | tail -1 | awk '{print $3\"/\"$2\" (\"$5\")\"}'")
            if success:
                results.append(f"💿 Disk: {output}")
            
            # Load
            success, output = await self.run_ssh(server_type, "cat /proc/loadavg | awk '{print $1\", \"$2\", \"$3}'")
            if success:
                results.append(f"⚡ Load: {output}")
        
        # Key services check
        results.append("\n**Key Services:**")
        
        # Check trading
        success, _ = await self.run_local("curl -s -m 3 http://198.54.123.234:8601/health")
        results.append(f"{'✅' if success else '❌'} WhaleTrack Trading")
        
        # Check God Mode
        success, _ = await self.run_local("curl -s -m 3 http://198.54.123.234:3000/health")
        results.append(f"{'✅' if success else '❌'} God Mode")
        
        # Check Aria
        success, _ = await self.run_local("curl -s -m 3 http://localhost:8750/health")
        results.append(f"{'✅' if success else '❌'} Aria Command")
        
        # Check website
        success, _ = await self.run_local("curl -s -m 5 https://fullpotential.ai/ | head -1")
        results.append(f"{'✅' if success else '❌'} Website")
        
        return "\n".join(results)
    
    async def get_services(self, server: Server = Server.BOTH) -> str:
        """List running services"""
        results = ["📋 **RUNNING SERVICES**\n"]
        
        servers_to_check = [Server.PRIMARY, Server.SECONDARY] if server == Server.BOTH else [server]
        
        for srv in servers_to_check:
            config = SERVERS[srv]
            results.append(f"\n**{config.name} ({config.ip}):**")
            
            cmd = "systemctl list-units --type=service --state=running | grep -E 'fpai|whale|trade|godmode|aria|nginx' | awk '{print $1}' | head -20"
            success, output = await self.run_ssh(srv, cmd)
            
            if success and output:
                for svc in output.split('\n'):
                    if svc.strip():
                        is_critical = any(c in svc for c in CRITICAL_SERVICES)
                        emoji = "🔴" if is_critical else "🟢"
                        results.append(f"  {emoji} {svc.replace('.service', '')}")
            else:
                results.append("  ⚠️ Could not fetch services")
        
        return "\n".join(results)
    
    async def restart_service(self, service: str, force: bool = False) -> Tuple[str, Optional[str]]:
        """
        Restart a service. Returns (message, approval_id if needed)
        """
        # Determine which server
        server = Server.PRIMARY  # Default
        if any(s in service for s in ["aria", "consciousness", "ai-brain"]):
            server = Server.SECONDARY
        
        # Check approval level
        is_critical = any(c in service for c in CRITICAL_SERVICES)
        
        if is_critical and not force:
            approval_id = f"restart_{service}_{asyncio.get_event_loop().time()}"
            self.pending_approvals[approval_id] = {
                "action": "restart",
                "service": service,
                "server": server
            }
            return (
                f"⚠️ **{service}** is a critical service.\n\n"
                f"Reply `/approve {approval_id[:8]}` to confirm restart, or `/cancel` to abort.",
                approval_id
            )
        
        # Execute restart
        config = SERVERS[server]
        success, output = await self.run_ssh(server, f"systemctl restart {service}")
        
        if success:
            return f"✅ Restarted **{service}** on {config.name}", None
        else:
            return f"❌ Failed to restart {service}: {output}", None
    
    async def get_memory_status(self) -> str:
        """Get detailed memory status with recommendations"""
        results = ["💾 **MEMORY STATUS**\n"]
        
        for server_type in [Server.PRIMARY, Server.SECONDARY]:
            config = SERVERS[server_type]
            results.append(f"\n**{config.name} ({config.ip}):**")
            
            # Get memory info
            success, output = await self.run_ssh(server_type, "free -m")
            if success:
                lines = output.split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 3:
                        total = int(parts[1])
                        used = int(parts[2])
                        available = int(parts[6]) if len(parts) > 6 else total - used
                        pct = int(used / total * 100)
                        
                        emoji = "🟢" if pct < 70 else "🟡" if pct < 85 else "🔴"
                        results.append(f"  {emoji} {used}MB / {total}MB ({pct}%)")
                        results.append(f"  Available: {available}MB")
            
            # Top memory consumers
            success, output = await self.run_ssh(
                server_type, 
                "ps -eo comm,%mem --sort=-%mem | head -6 | tail -5"
            )
            if success and output:
                results.append("  Top consumers:")
                for line in output.strip().split('\n'):
                    results.append(f"    {line}")
        
        # Recommendations
        results.append("\n**Recommendations:**")
        results.append("• Use `/fix memory` to stop non-critical services")
        results.append("• Use `/restart <service>` to restart memory-heavy services")
        
        return "\n".join(results)
    
    async def get_docker_status(self) -> str:
        """Get Docker container status"""
        results = ["🐳 **DOCKER STATUS**\n"]
        
        # Check Docker on primary
        success, output = await self.run_ssh(Server.PRIMARY, "systemctl is-active docker")
        if "active" in output:
            results.append("**Primary Server:**")
            results.append("  ✅ Docker running")
            
            # Get containers
            success, output = await self.run_ssh(
                Server.PRIMARY,
                "docker ps --format '{{.Names}}: {{.Status}}' 2>/dev/null | head -10"
            )
            if success and output.strip():
                for line in output.strip().split('\n'):
                    results.append(f"  📦 {line}")
            else:
                results.append("  No containers running")
        else:
            results.append("**Primary Server:**")
            results.append("  ❌ Docker not running")
            results.append("  Use `/fix docker` to repair")
        
        return "\n".join(results)
    
    async def auto_fix(self, issue: str) -> str:
        """Auto-fix common issues"""
        issue = issue.lower().strip()
        
        if issue == "docker":
            results = ["🔧 **Fixing Docker...**\n"]
            
            # Create iptables symlink
            success, _ = await self.run_ssh(
                Server.PRIMARY,
                "ln -sf /usr/sbin/iptables-nft /usr/bin/iptables"
            )
            results.append("✅ Created iptables symlink" if success else "⚠️ Symlink may already exist")
            
            # Reset failed state
            await self.run_ssh(Server.PRIMARY, "systemctl reset-failed docker")
            results.append("✅ Reset Docker failed state")
            
            # Start Docker
            success, output = await self.run_ssh(Server.PRIMARY, "systemctl start docker")
            if success:
                results.append("✅ Docker started")
                
                # Start containers
                await self.run_ssh(Server.PRIMARY, "docker start $(docker ps -aq) 2>/dev/null")
                results.append("✅ Containers started")
            else:
                results.append(f"❌ Docker failed to start: {output}")
            
            return "\n".join(results)
        
        elif issue == "memory":
            results = ["🔧 **Freeing Memory...**\n"]
            
            # Stop Ollama on primary (should only run on secondary)
            success, _ = await self.run_ssh(Server.PRIMARY, "systemctl stop ollama 2>/dev/null; systemctl disable ollama 2>/dev/null; pkill -9 ollama 2>/dev/null")
            if success:
                results.append("✅ Stopped Ollama (should run on secondary only)")
            
            # Stop non-critical services on primary
            services_to_stop = [
                "fpai-consciousness-feeder",
                "fpai-consciousness-verifier", 
                "fpai-consciousness_api",
                "fpai-consciousness_dashboard",
                "fpai-consciousness_decision_engine",
                "fpai-consciousness_gateway",
                "fpai-consciousness_network",
                "fpai-intelligence",
                "fpai-orchestrator",
                "fpai-realtime-bridge",
                "fpai-ai-gateway",
                "fpai-team-hub",
                "fpai-trust-index",
                "fpai-zend-marketplace",
                "fpai-zend-ton",
                "fpai-zend-wallet",
                "fpai-ri-api",
                "fpai-service-bridge",
            ]
            
            stopped = 0
            for svc in services_to_stop:
                success, _ = await self.run_ssh(Server.PRIMARY, f"systemctl stop {svc} 2>/dev/null")
                if success:
                    stopped += 1
            
            results.append(f"✅ Stopped {stopped} non-critical services")
            
            # Check new memory status
            success, output = await self.run_ssh(
                Server.PRIMARY,
                "free -m | grep Mem | awk '{print $7}'"
            )
            if success:
                results.append(f"✅ Available memory now: {output}MB")
            
            return "\n".join(results)
        
        elif issue == "ssh":
            results = ["🔧 **Checking SSH connectivity...**\n"]
            
            success, output = await self.run_ssh(Server.PRIMARY, "echo 'Connected!'", timeout=15)
            if success:
                results.append("✅ SSH to Primary working")
            else:
                results.append(f"❌ Cannot reach Primary: {output}")
                results.append("\n⚠️ May need manual reboot via IPMI")
            
            return "\n".join(results)
        
        else:
            return f"❌ Unknown issue type: `{issue}`\n\nAvailable fixes:\n• `/fix docker` - Fix Docker startup\n• `/fix memory` - Free up memory\n• `/fix ssh` - Check SSH connectivity"
    
    async def get_logs(self, service: str, lines: int = 20) -> str:
        """Get recent logs for a service"""
        # Determine server
        server = Server.PRIMARY
        if any(s in service for s in ["aria", "consciousness", "ai-brain"]):
            server = Server.SECONDARY
        
        config = SERVERS[server]
        
        success, output = await self.run_ssh(
            server,
            f"journalctl -u {service} -n {lines} --no-pager 2>/dev/null | tail -{lines}"
        )
        
        if success and output.strip():
            # Truncate if too long
            if len(output) > 3500:
                output = output[:3500] + "\n...(truncated)"
            return f"📜 **Logs: {service}** ({config.name})\n\n```\n{output}\n```"
        else:
            return f"❌ Could not fetch logs for {service}"
    
    async def get_service_inventory(self) -> str:
        """Get full inventory of all available services."""
        results = ["📋 **SERVICE INVENTORY**\n"]
        
        # Primary server services
        results.append("**PRIMARY (8GB) - Web/Trading:**")
        results.append("_Active (Required):_")
        for svc in ["nginx", "godmode", "whaletrack-live", "whaletrack-magnet", "fpai-credits-gateway"]:
            results.append(f"  ✅ {svc}")
        
        results.append("\n_Disabled (available):_")
        disabled_primary = ["dashboard", "revenue-api", "email-relay", "api-portal"]
        for svc in disabled_primary:
            results.append(f"  ⏸️ {svc}")
        
        # Secondary server services
        results.append("\n**SECONDARY (32GB) - AI/Intelligence:**")
        results.append("_Active:_")
        for svc in ["aria-command", "ollama", "ai-brain", "consciousness-*"]:
            results.append(f"  ✅ {svc}")
        
        results.append("\n_Can Activate (22GB free):_")
        available = [
            ("revenue-intelligence", "Revenue optimization", "~200MB"),
            ("revenue-oracle", "Revenue predictions", "~150MB"),
            ("brick2-autopilot", "Marketing automation", "~300MB"),
            ("music-maestro", "AI music production", "~500MB"),
            ("mydreamspace", "Dream platform", "~200MB"),
            ("i-match", "Matching engine", "~200MB"),
        ]
        for svc, desc, mem in available:
            results.append(f"  ⏸️ {svc} ({mem}) - {desc}")
        
        results.append("\n**To activate:** `/activate <service>`")
        return "\n".join(results)
    
    async def activate_service(self, service: str, server: Server = Server.SECONDARY) -> str:
        """Activate a disabled service."""
        config = SERVERS[server]
        
        # Check if service exists
        success, output = await self.run_ssh(server, f"systemctl list-unit-files | grep {service}")
        if not success or not output.strip():
            return f"❌ Service `{service}` not found on {config.name}"
        
        # Enable and start
        await self.run_ssh(server, f"systemctl enable {service}")
        success, output = await self.run_ssh(server, f"systemctl start {service}")
        
        if success:
            # Get memory after starting
            _, mem = await self.run_ssh(server, "free -m | grep Mem | awk '{print $7}'")
            return f"✅ Activated **{service}** on {config.name}\nAvailable memory: {mem}MB"
        else:
            return f"❌ Failed to start {service}: {output}"
    
    async def deactivate_service(self, service: str, server: Server = Server.SECONDARY) -> str:
        """Deactivate a running service."""
        config = SERVERS[server]
        
        # Check if it's a critical service
        if service in CRITICAL_SERVICES:
            return f"⚠️ Cannot deactivate critical service: {service}"
        
        # Stop and disable
        await self.run_ssh(server, f"systemctl stop {service}")
        await self.run_ssh(server, f"systemctl disable {service}")
        
        _, mem = await self.run_ssh(server, "free -m | grep Mem | awk '{print $7}'")
        return f"✅ Deactivated **{service}** on {config.name}\nAvailable memory: {mem}MB"
    
    async def approve_action(self, approval_id_prefix: str) -> str:
        """Execute a pending approval"""
        # Find matching approval
        matching = None
        full_id = None
        for aid, action in self.pending_approvals.items():
            if aid.startswith(approval_id_prefix):
                matching = action
                full_id = aid
                break
        
        if not matching:
            return "❌ No pending approval found with that ID"
        
        # Execute the action
        if matching["action"] == "restart":
            service = matching["service"]
            server = matching["server"]
            config = SERVERS[server]
            
            success, output = await self.run_ssh(server, f"systemctl restart {service}")
            del self.pending_approvals[full_id]
            
            if success:
                return f"✅ Approved! Restarted **{service}** on {config.name}"
            else:
                return f"❌ Restart failed: {output}"
        
        return "❌ Unknown action type"


# Global instance
server_ops = ServerOps()

