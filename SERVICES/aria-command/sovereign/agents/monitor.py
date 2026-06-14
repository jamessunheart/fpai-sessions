#!/usr/bin/env python3
"""
ARIA ASCENSION - MONITOR AGENT
==============================

Specializes in system health and monitoring:
- Server status
- Service health
- Resource usage
- Alerting
"""

import os
import re
import json
import asyncio
import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import BaseAgent, AgentCapability, AgentResponse

logger = logging.getLogger("aria.agents.monitor")

# Server configuration
PRIMARY_SERVER = os.getenv("PRIMARY_SERVER", "198.54.123.234")
SECONDARY_SERVER = os.getenv("SECONDARY_SERVER", "162.0.208.88")


class MonitorAgent(BaseAgent):
    """
    Monitor Agent - Expert in system health and monitoring.
    """
    
    name = "monitor"
    description = "Expert in system health, monitoring, alerting, and diagnostics"
    capabilities = [
        AgentCapability.MONITORING,
        AgentCapability.ALERTING,
        AgentCapability.REASONING
    ]
    priority = 25  # High priority for system queries
    
    # Monitor-related patterns
    MONITOR_PATTERNS = [
        r'\b(server|servers|service|services)\b',
        r'\b(status|health|check|monitor)\b',
        r'\b(memory|cpu|disk|resource|resources)\b',
        r'\b(alert|alarm|warning|error|down)\b',
        r'\b(restart|stop|start|logs)\b',
    ]
    
    # Known services to monitor
    SERVICES = {
        "primary": {
            "whaletrack-magnet": (8600, "/health"),
            "whaletrack-live": (8601, "/health"),
            "data-service": (8125, "/health"),
        },
        "secondary": {
            "aria-command": (8710, "/health"),
            "ai-brain": (8101, "/health"),
            "voice-api": (8750, "/health"),
        }
    }
    
    def __init__(self):
        super().__init__()
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def can_handle(self, query: str, context: Dict = None) -> float:
        """Determine if this is a monitoring-related query."""
        query_lower = query.lower()
        
        # Count pattern matches
        matches = 0
        for pattern in self.MONITOR_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                matches += 1
        
        # Direct monitor commands
        if query_lower.startswith(("/server", "/service", "/status", "/health")):
            return 0.95
        
        # Strong match
        if matches >= 2:
            return 0.85
        elif matches == 1:
            return 0.6
        
        return 0.1
    
    async def process(self, query: str, context: Dict = None) -> AgentResponse:
        """Process a monitoring-related query."""
        query_lower = query.lower()
        
        try:
            # Determine what's being asked
            if "server" in query_lower or "servers" in query_lower:
                return await self._get_server_status()
            
            elif "service" in query_lower or "services" in query_lower:
                return await self._get_service_status()
            
            elif "memory" in query_lower:
                return await self._get_memory_status()
            
            elif "logs" in query_lower:
                return await self._handle_logs_request(query)
            
            elif "restart" in query_lower:
                return await self._handle_restart_request(query)
            
            else:
                return await self._general_status()
        
        except Exception as e:
            logger.error(f"Monitor agent error: {e}")
            return self._create_response(
                success=False,
                content=f"Error checking status: {str(e)}",
                confidence=0.3
            )
    
    async def _get_server_status(self) -> AgentResponse:
        """Get status of all servers."""
        results = []
        
        # Check primary server
        try:
            response = await self.http_client.get(
                f"http://{PRIMARY_SERVER}:8600/health",
                timeout=5.0
            )
            primary_status = "🟢 Online" if response.status_code == 200 else "🟡 Degraded"
        except:
            primary_status = "🔴 Offline"
        
        results.append(f"**Primary** ({PRIMARY_SERVER}): {primary_status}")
        
        # Check secondary server
        try:
            response = await self.http_client.get(
                f"http://{SECONDARY_SERVER}:8710/health",
                timeout=5.0
            )
            secondary_status = "🟢 Online" if response.status_code == 200 else "🟡 Degraded"
        except:
            secondary_status = "🔴 Offline"
        
        results.append(f"**Secondary** ({SECONDARY_SERVER}): {secondary_status}")
        
        content = "🖥️ **Server Status**\n\n" + "\n".join(results)
        
        return self._create_response(
            success=True,
            content=content,
            confidence=0.9,
            data={"primary": primary_status, "secondary": secondary_status}
        )
    
    async def _get_service_status(self) -> AgentResponse:
        """Get status of all services."""
        lines = ["🔧 **Service Status**\n"]
        
        all_healthy = True
        
        # Check primary services
        lines.append("**Primary Server:**")
        for name, (port, endpoint) in self.SERVICES["primary"].items():
            try:
                response = await self.http_client.get(
                    f"http://{PRIMARY_SERVER}:{port}{endpoint}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    lines.append(f"  🟢 {name}")
                else:
                    lines.append(f"  🟡 {name} (degraded)")
                    all_healthy = False
            except:
                lines.append(f"  🔴 {name} (down)")
                all_healthy = False
        
        # Check secondary services
        lines.append("\n**Secondary Server:**")
        for name, (port, endpoint) in self.SERVICES["secondary"].items():
            try:
                response = await self.http_client.get(
                    f"http://{SECONDARY_SERVER}:{port}{endpoint}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    lines.append(f"  🟢 {name}")
                else:
                    lines.append(f"  🟡 {name} (degraded)")
                    all_healthy = False
            except:
                lines.append(f"  🔴 {name} (down)")
                all_healthy = False
        
        if all_healthy:
            lines.insert(1, "✅ All services healthy\n")
        else:
            lines.insert(1, "⚠️ Some services need attention\n")
        
        return self._create_response(
            success=True,
            content="\n".join(lines),
            confidence=0.9
        )
    
    async def _get_memory_status(self) -> AgentResponse:
        """Get memory status."""
        content = """
💾 **Memory Status**

To get accurate memory status, I need to run:
```
ssh root@{server} 'free -h'
```

Would you like me to check memory on:
1. Primary server
2. Secondary server
3. Both servers

Reply with the number or server name.
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.7,
            reasoning="Need approval to run memory check command"
        )
    
    async def _handle_logs_request(self, query: str) -> AgentResponse:
        """Handle a logs request."""
        # Extract service name
        service_match = re.search(r'logs?\s+(?:for\s+)?(\w+)', query.lower())
        service = service_match.group(1) if service_match else None
        
        if service:
            content = f"""
📜 **Logs for {service}**

To view logs, I can run:
```
journalctl -u {service} -n 50 --no-pager
```

Options:
- `/logs {service} 50` - Last 50 lines
- `/logs {service} errors` - Only errors
- `/logs {service} today` - Today's logs

Would you like me to fetch these logs?
"""
        else:
            content = """
📜 **Log Viewer**

Specify a service to view logs:
- `/logs aria-command`
- `/logs whaletrack-live`
- `/logs ai-brain`

Or view system logs:
- `/logs system` - System messages
- `/logs docker` - Docker logs
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.7
        )
    
    async def _handle_restart_request(self, query: str) -> AgentResponse:
        """Handle a restart request."""
        # Extract service name
        service_match = re.search(r'restart\s+(\w+[-\w]*)', query.lower())
        service = service_match.group(1) if service_match else None
        
        if service:
            content = f"""
🔄 **Restart Request: {service}**

⚠️ This will interrupt the service temporarily.

**Pre-restart checks:**
- Current status will be verified
- Connections will be gracefully closed
- Service will restart within 30 seconds

**Command to execute:**
```
systemctl restart {service}
```

Do you approve this restart?
"""
        else:
            content = """
🔄 **Restart Service**

Please specify which service to restart:
- `/restart aria-command`
- `/restart whaletrack-live`
- `/restart ai-brain`

⚠️ Restarts require explicit approval.
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.7,
            reasoning="Service restarts require human approval"
        )
    
    async def _general_status(self) -> AgentResponse:
        """Get general system status."""
        # Get quick health check
        server_response = await self._get_server_status()
        
        content = f"""
🖥️ **System Status Overview**

{server_response.content}

**Quick Commands:**
- `/servers` - Server status
- `/services` - Service health
- `/memory` - Memory usage
- `/logs <service>` - View logs
- `/restart <service>` - Restart service

What would you like to check?
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.8,
            data=server_response.data
        )


