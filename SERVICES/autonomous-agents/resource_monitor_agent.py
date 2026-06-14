#!/usr/bin/env python3
"""
📊 Resource Monitor Agent - Server Health & Auto-Scaling
Monitors server resources and triggers expansion when needed
Part of Full Potential AI Autonomous Intelligence System
"""

import asyncio
import aiohttp
import json
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional


class ResourceMonitorAgent:
    """Monitors server resources and triggers auto-scaling"""

    def __init__(self, check_interval: int = 30):
        self.name = "ResourceMonitorAgent"
        self.check_interval = check_interval
        self.running = False

        # Thresholds for auto-scaling
        self.thresholds = {
            "cpu_percent": 80.0,      # Trigger at 80% CPU
            "memory_percent": 85.0,    # Trigger at 85% memory
            "disk_percent": 90.0,      # Trigger at 90% disk
            "agent_count": 10          # Trigger at 10 agents
        }

        # Resource history
        self.history = []
        self.alerts = []

        # Server info
        self.server_ip = "198.54.123.234"
        self.current_agents = 0

    async def log(self, message: str, level: str = "INFO"):
        """Log agent activity"""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] [{self.name}] [{level}] {message}"
        print(log_entry)

        try:
            with open(f"/tmp/resource_monitor_agent.log", "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}")

    async def check_local_resources(self) -> Dict[str, Any]:
        """Check local machine resources"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                "cpu_percent": cpu_percent,
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_percent": memory.percent,
                "disk_total_gb": round(disk.total / (1024**3), 2),
                "disk_used_gb": round(disk.used / (1024**3), 2),
                "disk_percent": disk.percent,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            await self.log(f"Error checking local resources: {e}", "ERROR")
            return {}

    async def check_server_resources(self) -> Dict[str, Any]:
        """Check remote server resources via API"""
        try:
            # Check if we have a metrics endpoint
            url = f"http://{self.server_ip}:8001/orchestrator/metrics"

            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "server": self.server_ip,
                            "metrics": data,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    else:
                        await self.log(f"Server metrics endpoint returned {response.status}", "WARNING")
                        return {"server": self.server_ip, "status": "unavailable"}

        except Exception as e:
            await self.log(f"Could not reach server metrics: {e}", "WARNING")
            return {"server": self.server_ip, "status": "unreachable"}

    async def count_active_agents(self) -> int:
        """Count how many autonomous agents are running"""
        # Check running agent processes
        agent_count = 0

        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('agent.py' in str(cmd) for cmd in cmdline):
                        agent_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            return agent_count

        except Exception as e:
            await self.log(f"Error counting agents: {e}", "ERROR")
            return 0

    def check_thresholds(self, resources: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check if any thresholds are exceeded"""
        violations = []

        if resources.get("cpu_percent", 0) > self.thresholds["cpu_percent"]:
            violations.append({
                "type": "cpu",
                "current": resources["cpu_percent"],
                "threshold": self.thresholds["cpu_percent"],
                "severity": "HIGH",
                "action": "scale_up"
            })

        if resources.get("memory_percent", 0) > self.thresholds["memory_percent"]:
            violations.append({
                "type": "memory",
                "current": resources["memory_percent"],
                "threshold": self.thresholds["memory_percent"],
                "severity": "HIGH",
                "action": "scale_up"
            })

        if resources.get("disk_percent", 0) > self.thresholds["disk_percent"]:
            violations.append({
                "type": "disk",
                "current": resources["disk_percent"],
                "threshold": self.thresholds["disk_percent"],
                "severity": "CRITICAL",
                "action": "expand_storage"
            })

        if self.current_agents > self.thresholds["agent_count"]:
            violations.append({
                "type": "agent_count",
                "current": self.current_agents,
                "threshold": self.thresholds["agent_count"],
                "severity": "MEDIUM",
                "action": "scale_horizontally"
            })

        return violations

    async def trigger_scaling_action(self, violation: Dict[str, Any]):
        """Trigger auto-scaling based on violation"""
        action = violation["action"]

        await self.log(f"🚨 THRESHOLD EXCEEDED: {violation['type']} at {violation['current']}% (threshold: {violation['threshold']}%)", "WARNING")

        if action == "scale_up":
            await self.scale_up_server()
        elif action == "expand_storage":
            await self.expand_storage()
        elif action == "scale_horizontally":
            await self.add_new_server()

    async def scale_up_server(self):
        """Increase server resources (vertical scaling)"""
        await self.log("🔼 SCALING ACTION: Vertical scale-up recommended", "INFO")

        # In production, this would call DigitalOcean/AWS API
        scaling_plan = {
            "action": "resize_droplet",
            "current_size": "basic",
            "target_size": "professional",
            "api": "digitalocean",
            "estimated_cost": "+$12/month",
            "estimated_time": "5 minutes",
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.log(f"📋 Scaling plan: {json.dumps(scaling_plan, indent=2)}", "INFO")

        # Save scaling recommendation
        self.save_scaling_recommendation(scaling_plan)

    async def expand_storage(self):
        """Add more storage to server"""
        await self.log("💾 SCALING ACTION: Storage expansion recommended", "INFO")

        scaling_plan = {
            "action": "add_volume",
            "current_storage_gb": 50,
            "additional_storage_gb": 50,
            "api": "digitalocean",
            "estimated_cost": "+$5/month",
            "estimated_time": "2 minutes",
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.log(f"📋 Scaling plan: {json.dumps(scaling_plan, indent=2)}", "INFO")
        self.save_scaling_recommendation(scaling_plan)

    async def add_new_server(self):
        """Add new server for horizontal scaling"""
        await self.log("🌐 SCALING ACTION: Horizontal scaling (new server) recommended", "INFO")

        scaling_plan = {
            "action": "create_droplet",
            "purpose": "agent_worker_node",
            "size": "basic",
            "region": "nyc3",
            "api": "digitalocean",
            "estimated_cost": "+$12/month",
            "estimated_time": "60 seconds",
            "load_balancer": "required",
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.log(f"📋 Scaling plan: {json.dumps(scaling_plan, indent=2)}", "INFO")
        self.save_scaling_recommendation(scaling_plan)

    def save_scaling_recommendation(self, plan: Dict[str, Any]):
        """Save scaling recommendation for review"""
        try:
            # Append to recommendations file
            with open("/tmp/scaling_recommendations.jsonl", "a") as f:
                f.write(json.dumps(plan) + "\n")

            # Also save latest
            with open("/tmp/scaling_latest.json", "w") as f:
                json.dump(plan, f, indent=2)

        except Exception as e:
            print(f"Failed to save scaling recommendation: {e}")

    async def run_cycle(self):
        """One monitoring cycle"""
        await self.log("📊 Starting resource monitoring cycle...")

        # Gather resource data
        local_resources = await self.check_local_resources()
        server_resources = await self.check_server_resources()
        agent_count = await self.count_active_agents()

        self.current_agents = agent_count

        # Create snapshot
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "local": local_resources,
            "server": server_resources,
            "active_agents": agent_count
        }

        self.history.append(snapshot)

        # Log current state
        if local_resources:
            await self.log(
                f"💻 Local: CPU {local_resources.get('cpu_percent', 0):.1f}%, "
                f"Memory {local_resources.get('memory_percent', 0):.1f}%, "
                f"Disk {local_resources.get('disk_percent', 0):.1f}%"
            )

        await self.log(f"🤖 Active agents: {agent_count}")

        # Check thresholds
        violations = self.check_thresholds(local_resources)

        if violations:
            for violation in violations:
                await self.trigger_scaling_action(violation)
        else:
            await self.log("✅ All resources within normal thresholds")

        # Save snapshot
        self.save_snapshot(snapshot)

    def save_snapshot(self, snapshot: Dict[str, Any]):
        """Save resource snapshot"""
        try:
            # Save latest
            with open("/tmp/resource_monitor_latest.json", "w") as f:
                json.dump(snapshot, f, indent=2)

            # Append to history
            with open("/tmp/resource_monitor_history.jsonl", "a") as f:
                f.write(json.dumps(snapshot) + "\n")

        except Exception as e:
            print(f"Failed to save snapshot: {e}")

    async def run_forever(self):
        """Main loop - runs 24/7"""
        self.running = True
        await self.log(f"🚀 {self.name} starting 24/7 autonomous operation")
        await self.log(f"⏱️ Check interval: {self.check_interval} seconds")
        await self.log(f"📊 Monitoring thresholds: CPU {self.thresholds['cpu_percent']}%, "
                      f"Memory {self.thresholds['memory_percent']}%, "
                      f"Disk {self.thresholds['disk_percent']}%")

        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                await self.log(f"💥 Error in cycle: {e}", level="ERROR")
                await asyncio.sleep(60)

    def stop(self):
        """Stop the agent"""
        self.running = False


async def main():
    """Run the resource monitor agent"""
    agent = ResourceMonitorAgent(check_interval=30)

    try:
        await agent.run_forever()
    except KeyboardInterrupt:
        agent.stop()
        await agent.log("👋 Resource monitor stopped by user")


if __name__ == "__main__":
    print("📊 Full Potential AI - Resource Monitor Agent")
    print("=" * 60)
    asyncio.run(main())
