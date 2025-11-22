"""
Autonomous Operations Manager for I PROACTIVE

Enables self-managing, self-healing, autonomous AI system that:
- Monitors all services 24/7
- Detects and fixes issues automatically
- Identifies optimization opportunities
- Makes strategic decisions without human intervention
- Continuously improves system performance
"""

import asyncio
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from .config import settings
from .model_router import ModelRouter
from .memory_manager import MemoryManager
from .decision_engine import DecisionEngine

logger = logging.getLogger(__name__)


class AutonomousOps:
    """
    Autonomous Operations Manager - The self-managing AI

    Runs continuously in background, making decisions and taking action
    without human intervention.
    """

    def __init__(
        self,
        model_router: ModelRouter,
        memory_manager: MemoryManager,
        decision_engine: DecisionEngine
    ):
        self.model_router = model_router
        self.memory_manager = memory_manager
        self.decision_engine = decision_engine

        self.enabled = False
        self.check_interval_seconds = 300  # Check every 5 minutes
        self.last_check = None
        self.actions_taken = []

        # Registry of all services to monitor
        self.services = [
            {"name": "registry", "port": 8000, "critical": True},
            {"name": "orchestrator", "port": 8001, "critical": True},
            {"name": "dashboard", "port": 8002, "critical": False},
            {"name": "i-proactive", "port": 8400, "critical": True},
            {"name": "i-match", "port": 8401, "critical": True},
        ]

    async def start(self):
        """Start autonomous operation loop"""
        self.enabled = True
        logger.info("🤖 AUTONOMOUS MODE ACTIVATED")
        logger.info(f"   Check interval: {self.check_interval_seconds}s")
        logger.info(f"   Monitoring {len(self.services)} services")

        # Run the autonomous loop
        while self.enabled:
            try:
                await self._autonomous_cycle()
            except Exception as e:
                logger.error(f"Error in autonomous cycle: {e}")

            # Wait before next cycle
            await asyncio.sleep(self.check_interval_seconds)

    async def stop(self):
        """Stop autonomous operation"""
        self.enabled = False
        logger.info("🛑 AUTONOMOUS MODE DEACTIVATED")

    async def _autonomous_cycle(self):
        """
        One complete autonomous cycle:
        1. Monitor system health
        2. Detect issues
        3. Make decisions
        4. Take actions
        5. Learn and improve
        """
        self.last_check = datetime.now()
        logger.info(f"\n{'='*60}")
        logger.info(f"🤖 AUTONOMOUS CYCLE - {self.last_check.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*60}")

        # Step 1: Monitor system health
        health_status = await self._check_system_health()

        # Step 2: Detect issues
        issues = await self._detect_issues(health_status)

        # Step 3: Auto-fix critical issues
        if issues:
            await self._auto_fix_issues(issues)

        # Step 4: Identify opportunities
        opportunities = await self._identify_opportunities(health_status)

        # Step 5: Take proactive actions
        if opportunities:
            await self._take_proactive_actions(opportunities)

        # Step 6: Learn and improve
        await self._learn_and_improve(health_status, issues, opportunities)

        logger.info(f"✅ Cycle complete. Actions taken: {len(self.actions_taken)}")

    async def _check_system_health(self) -> Dict[str, Any]:
        """Check health of all services"""
        logger.info("📊 Checking system health...")

        health_status = {
            "timestamp": datetime.now(),
            "services": {},
            "overall_status": "healthy",
            "critical_services_down": 0,
            "total_services": len(self.services)
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            for service in self.services:
                try:
                    response = await client.get(
                        f"http://localhost:{service['port']}/health"
                    )

                    if response.status_code == 200:
                        data = response.json()
                        health_status["services"][service["name"]] = {
                            "status": "healthy",
                            "data": data,
                            "critical": service["critical"]
                        }
                        logger.info(f"   ✅ {service['name']}: healthy")
                    else:
                        health_status["services"][service["name"]] = {
                            "status": "unhealthy",
                            "error": f"HTTP {response.status_code}",
                            "critical": service["critical"]
                        }
                        logger.warning(f"   ⚠️  {service['name']}: unhealthy (HTTP {response.status_code})")

                        if service["critical"]:
                            health_status["critical_services_down"] += 1

                except Exception as e:
                    health_status["services"][service["name"]] = {
                        "status": "down",
                        "error": str(e),
                        "critical": service["critical"]
                    }
                    logger.error(f"   ❌ {service['name']}: down ({e})")

                    if service["critical"]:
                        health_status["critical_services_down"] += 1

        # Determine overall status
        if health_status["critical_services_down"] > 0:
            health_status["overall_status"] = "critical"
        elif any(s["status"] != "healthy" for s in health_status["services"].values()):
            health_status["overall_status"] = "degraded"

        return health_status

    async def _detect_issues(self, health_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect issues that need attention"""
        logger.info("🔍 Detecting issues...")

        issues = []

        # Check for down services
        for service_name, service_data in health_status["services"].items():
            if service_data["status"] == "down":
                issues.append({
                    "type": "service_down",
                    "severity": "critical" if service_data["critical"] else "warning",
                    "service": service_name,
                    "description": f"{service_name} is down",
                    "action": "restart_service"
                })

        # Check for performance degradation
        for service_name, service_data in health_status["services"].items():
            if service_data["status"] == "healthy" and "data" in service_data:
                data = service_data["data"]

                # High memory usage
                if "memory_usage_mb" in data and data["memory_usage_mb"] > 500:
                    issues.append({
                        "type": "high_memory",
                        "severity": "warning",
                        "service": service_name,
                        "description": f"{service_name} using {data['memory_usage_mb']:.0f}MB memory",
                        "action": "optimize_memory"
                    })

                # High CPU usage
                if "cpu_usage_percent" in data and data["cpu_usage_percent"] > 80:
                    issues.append({
                        "type": "high_cpu",
                        "severity": "warning",
                        "service": service_name,
                        "description": f"{service_name} CPU at {data['cpu_usage_percent']:.0f}%",
                        "action": "optimize_cpu"
                    })

        if issues:
            logger.info(f"   Found {len(issues)} issues")
            for issue in issues:
                logger.info(f"   - {issue['severity'].upper()}: {issue['description']}")
        else:
            logger.info("   No issues detected ✅")

        return issues

    async def _auto_fix_issues(self, issues: List[Dict[str, Any]]):
        """Automatically fix detected issues"""
        logger.info("🔧 Auto-fixing issues...")

        for issue in issues:
            if issue["severity"] == "critical":
                logger.info(f"   Fixing: {issue['description']}")

                if issue["type"] == "service_down":
                    # Attempt to restart service
                    success = await self._restart_service(issue["service"])

                    if success:
                        logger.info(f"   ✅ Successfully restarted {issue['service']}")
                        self.actions_taken.append({
                            "timestamp": datetime.now(),
                            "action": "restart_service",
                            "service": issue["service"],
                            "result": "success"
                        })
                    else:
                        logger.error(f"   ❌ Failed to restart {issue['service']}")
                        # Log for human review
                        await self._alert_human(issue)

    async def _restart_service(self, service_name: str) -> bool:
        """Attempt to restart a service"""
        # In production, this would execute actual restart commands
        # For now, just log the intent
        logger.info(f"   Would restart {service_name} (not implemented in this version)")
        return False

    async def _identify_opportunities(self, health_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify opportunities for improvement"""
        logger.info("💡 Identifying opportunities...")

        opportunities = []

        # Check if we can optimize costs
        # Check if we can improve performance
        # Check if we can add new features

        # For now, simple heuristics
        healthy_services = sum(
            1 for s in health_status["services"].values()
            if s["status"] == "healthy"
        )

        if healthy_services == len(self.services):
            opportunities.append({
                "type": "system_optimization",
                "priority": "low",
                "description": "All services healthy - good time to optimize",
                "action": "run_optimization_analysis"
            })

        if opportunities:
            logger.info(f"   Found {len(opportunities)} opportunities")
        else:
            logger.info("   No immediate opportunities")

        return opportunities

    async def _take_proactive_actions(self, opportunities: List[Dict[str, Any]]):
        """Take proactive actions on opportunities"""
        logger.info("🚀 Taking proactive actions...")

        for opp in opportunities:
            if opp["priority"] in ["high", "critical"]:
                logger.info(f"   Acting on: {opp['description']}")
                # Take action based on opportunity type
                # (Implementation would go here)

    async def _learn_and_improve(
        self,
        health_status: Dict[str, Any],
        issues: List[Dict[str, Any]],
        opportunities: List[Dict[str, Any]]
    ):
        """Learn from this cycle and improve future performance"""
        logger.info("🧠 Learning and improving...")

        # Store learnings in memory
        learning = {
            "timestamp": datetime.now(),
            "health_status": health_status["overall_status"],
            "issues_count": len(issues),
            "opportunities_count": len(opportunities),
            "actions_taken": len(self.actions_taken)
        }

        # Use memory manager to persist learnings
        try:
            await self.memory_manager.store_session_learning(
                session_id=f"autonomous_{datetime.now().strftime('%Y%m%d')}",
                learning_data=learning
            )
            logger.info("   Stored learnings in persistent memory")
        except Exception as e:
            logger.error(f"   Failed to store learnings: {e}")

    async def _alert_human(self, issue: Dict[str, Any]):
        """Alert human when auto-fix fails"""
        logger.warning(f"⚠️  HUMAN ATTENTION NEEDED: {issue['description']}")
        # In production, would send notification (email, Slack, etc.)

    def get_status(self) -> Dict[str, Any]:
        """Get current autonomous operations status"""
        return {
            "enabled": self.enabled,
            "last_check": self.last_check,
            "check_interval_seconds": self.check_interval_seconds,
            "total_actions_taken": len(self.actions_taken),
            "recent_actions": self.actions_taken[-10:] if self.actions_taken else []
        }
