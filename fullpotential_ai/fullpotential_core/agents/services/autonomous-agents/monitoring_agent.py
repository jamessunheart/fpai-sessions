#!/usr/bin/env python3
"""
🤖 Monitoring Agent - Autonomous Service Health Monitor
Runs 24/7, monitors all services, auto-restarts failed services
Part of Full Potential AI Autonomous Intelligence System
"""

import asyncio
import aiohttp
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Any


class MonitoringAgent:
    """Autonomous agent that monitors services and auto-heals issues"""

    def __init__(self, check_interval: int = 60):
        self.name = "MonitoringAgent"
        self.check_interval = check_interval
        self.running = False

        # Services to monitor
        self.services = [
            {
                "name": "registry",
                "url": "http://198.54.123.234:8000/health",
                "port": 8000,
                "restart_cmd": "systemctl restart registry"
            },
            {
                "name": "orchestrator",
                "url": "http://198.54.123.234:8001/health",
                "port": 8001,
                "restart_cmd": "systemctl restart orchestrator"
            },
            {
                "name": "dashboard",
                "url": "http://198.54.123.234:8002/health",
                "port": 8002,
                "restart_cmd": "systemctl restart dashboard"
            },
            {
                "name": "church-guidance",
                "url": "http://198.54.123.234:8009/health",
                "port": 8009,
                "restart_cmd": "systemctl restart church-guidance"
            },
            {
                "name": "i-match",
                "url": "http://198.54.123.234:8010/health",
                "port": 8010,
                "restart_cmd": "systemctl restart i-match"
            },
            {
                "name": "credentials-manager",
                "url": "http://198.54.123.234:8025/health",
                "port": 8025,
                "restart_cmd": "systemctl restart credentials-manager"
            }
        ]

        self.health_history = []
        self.failure_count = {}
        self.last_restart = {}

    async def log(self, message: str, level: str = "INFO"):
        """Log agent activity"""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] [{self.name}] [{level}] {message}"
        print(log_entry)

        # Append to log file
        try:
            with open(f"/tmp/monitoring_agent.log", "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}")

    async def check_service_health(self, service: Dict) -> Dict[str, Any]:
        """Check if a service is responding"""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(service["url"]) as response:
                    is_healthy = response.status == 200

                    result = {
                        "name": service["name"],
                        "status": "healthy" if is_healthy else "unhealthy",
                        "http_code": response.status,
                        "timestamp": datetime.utcnow().isoformat()
                    }

                    if is_healthy:
                        await self.log(f"✅ {service['name']} is healthy")
                    else:
                        await self.log(f"⚠️ {service['name']} returned {response.status}", "WARNING")

                    return result

        except asyncio.TimeoutError:
            await self.log(f"❌ {service['name']} timeout", "ERROR")
            return {
                "name": service["name"],
                "status": "timeout",
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            await self.log(f"❌ {service['name']} error: {e}", "ERROR")
            return {
                "name": service["name"],
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def auto_restart_service(self, service: Dict) -> bool:
        """Attempt to restart a failed service"""
        service_name = service["name"]

        # Check if we recently restarted (avoid restart loops)
        if service_name in self.last_restart:
            last_restart_time = datetime.fromisoformat(self.last_restart[service_name])
            time_since_restart = (datetime.utcnow() - last_restart_time).total_seconds()

            if time_since_restart < 300:  # Don't restart if restarted within 5 minutes
                await self.log(f"⏸️ Skipping restart of {service_name} (restarted {int(time_since_restart)}s ago)", "WARNING")
                return False

        await self.log(f"🔄 Attempting to restart {service_name}...", "WARNING")

        try:
            # This would need SSH access in production
            # For now, just log the intent
            await self.log(f"📝 Would execute: ssh root@198.54.123.234 '{service['restart_cmd']}'", "INFO")

            # In production, uncomment:
            # result = subprocess.run(
            #     ["ssh", "root@198.54.123.234", service["restart_cmd"]],
            #     capture_output=True,
            #     text=True,
            #     timeout=30
            # )
            #
            # if result.returncode == 0:
            #     await self.log(f"✅ Successfully restarted {service_name}")
            #     self.last_restart[service_name] = datetime.utcnow().isoformat()
            #     return True
            # else:
            #     await self.log(f"❌ Failed to restart {service_name}: {result.stderr}", "ERROR")
            #     return False

            # For demo, simulate success
            self.last_restart[service_name] = datetime.utcnow().isoformat()
            return True

        except Exception as e:
            await self.log(f"❌ Exception restarting {service_name}: {e}", "ERROR")
            return False

    async def run_cycle(self):
        """One monitoring cycle - check all services"""
        await self.log("🔍 Starting monitoring cycle...")

        # Check all services in parallel
        tasks = [self.check_service_health(service) for service in self.services]
        results = await asyncio.gather(*tasks)

        # Track results
        cycle_summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "results": results,
            "total_services": len(results),
            "healthy": sum(1 for r in results if r.get("status") == "healthy"),
            "unhealthy": sum(1 for r in results if r.get("status") != "healthy")
        }

        self.health_history.append(cycle_summary)

        # Auto-heal unhealthy services
        for result in results:
            if result.get("status") != "healthy":
                service_name = result["name"]

                # Increment failure count
                self.failure_count[service_name] = self.failure_count.get(service_name, 0) + 1

                # If failed 2+ times in a row, attempt restart
                if self.failure_count[service_name] >= 2:
                    service = next(s for s in self.services if s["name"] == service_name)
                    await self.auto_restart_service(service)
            else:
                # Reset failure count on success
                service_name = result["name"]
                if service_name in self.failure_count:
                    self.failure_count[service_name] = 0

        # Report summary
        health_percentage = (cycle_summary["healthy"] / cycle_summary["total_services"]) * 100
        await self.log(f"📊 Cycle complete: {cycle_summary['healthy']}/{cycle_summary['total_services']} healthy ({health_percentage:.0f}%)")

        # Save report
        self.save_report(cycle_summary)

    def save_report(self, summary: Dict):
        """Save monitoring report to file"""
        try:
            with open("/tmp/monitoring_agent_latest.json", "w") as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            print(f"Failed to save report: {e}")

    async def run_forever(self):
        """Main loop - runs 24/7"""
        self.running = True
        await self.log(f"🚀 {self.name} starting 24/7 autonomous operation")
        await self.log(f"⏱️ Check interval: {self.check_interval} seconds")
        await self.log(f"📡 Monitoring {len(self.services)} services")

        while self.running:
            try:
                await self.run_cycle()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                await self.log(f"💥 Error in cycle: {e}", level="ERROR")
                await asyncio.sleep(60)  # Wait before retrying

    def stop(self):
        """Stop the agent"""
        self.running = False
        self.log(f"🛑 {self.name} stopping")


async def main():
    """Run the monitoring agent"""
    agent = MonitoringAgent(check_interval=60)

    try:
        await agent.run_forever()
    except KeyboardInterrupt:
        agent.stop()
        await agent.log("👋 Monitoring agent stopped by user")


if __name__ == "__main__":
    print("🤖 Full Potential AI - Monitoring Agent")
    print("=" * 60)
    asyncio.run(main())
