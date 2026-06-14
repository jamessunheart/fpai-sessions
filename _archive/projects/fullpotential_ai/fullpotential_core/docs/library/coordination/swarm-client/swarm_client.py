"""
Swarm Client - Connect Claude sessions to unified orchestrator

Usage:
    from swarm_client import SwarmClient

    # Initialize and connect
    client = SwarmClient(
        session_id="session-1763233940",
        capabilities=["build", "architect"],
        orchestrator_url="http://198.54.123.234:8600"
    )

    # Start swarm worker
    client.start()

    # Worker will:
    # 1. Register with orchestrator
    # 2. Send heartbeats every 60 seconds
    # 3. Request and execute assigned tasks
    # 4. Report progress and completion
    # 5. Run indefinitely
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List, Dict, Optional, Callable
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SwarmClient:
    """Client for connecting Claude sessions to unified orchestrator"""

    def __init__(
        self,
        session_id: str,
        capabilities: List[str],
        orchestrator_url: str = "http://localhost:8600",
        heartbeat_interval: int = 60,
        work_check_interval: int = 30
    ):
        self.session_id = session_id
        self.capabilities = capabilities
        self.orchestrator_url = orchestrator_url
        self.heartbeat_interval = heartbeat_interval
        self.work_check_interval = work_check_interval

        self.client = httpx.AsyncClient(timeout=30.0)
        self.current_task = None
        self.status = "idle"

        # Task handlers
        self.task_handlers: Dict[str, Callable] = {}

    def register_handler(self, task_type: str, handler: Callable):
        """Register handler for specific task type"""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for task type: {task_type}")

    async def register(self) -> bool:
        """Register session with orchestrator"""
        try:
            response = await self.client.post(
                f"{self.orchestrator_url}/session/register",
                json={
                    "session_id": self.session_id,
                    "capabilities": self.capabilities,
                    "max_concurrent_tasks": 1,
                    "registered_at": datetime.now().isoformat()
                }
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ Registered with orchestrator: {data}")

                # Check if assigned task immediately
                if data.get("assigned_task"):
                    await self.execute_task(data["assigned_task"])

                return True
            else:
                logger.error(f"❌ Registration failed: {response.text}")
                return False

        except Exception as e:
            logger.error(f"❌ Registration error: {e}")
            return False

    async def heartbeat(self):
        """Send heartbeat to orchestrator"""
        try:
            response = await self.client.post(
                f"{self.orchestrator_url}/session/heartbeat",
                json={
                    "session_id": self.session_id,
                    "status": self.status,
                    "current_task": self.current_task["id"] if self.current_task else None,
                    "timestamp": datetime.now().isoformat()
                }
            )

            if response.status_code == 200:
                data = response.json()

                # Check if orchestrator assigned new work
                if data.get("new_assignment"):
                    logger.info(f"📋 New assignment from heartbeat: {data['new_assignment']['id']}")
                    await self.execute_task(data["new_assignment"])

                return True
            else:
                logger.warning(f"⚠️  Heartbeat failed: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"❌ Heartbeat error: {e}")
            return False

    async def request_work(self) -> Optional[Dict]:
        """Request work assignment from orchestrator"""
        try:
            response = await self.client.get(
                f"{self.orchestrator_url}/work/request",
                params={"session_id": self.session_id}
            )

            if response.status_code == 200:
                data = response.json()
                task = data.get("task")

                if task:
                    logger.info(f"📋 Received task assignment: {task['id']}")
                    return task
                else:
                    logger.debug("No work available")
                    return None
            else:
                logger.warning(f"⚠️  Work request failed: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"❌ Work request error: {e}")
            return None

    async def execute_task(self, task: Dict):
        """Execute assigned task"""
        self.current_task = task
        self.status = "busy"

        task_id = task["id"]
        task_type = task["type"]

        logger.info(f"🚀 Starting task: {task_id} (type: {task_type})")

        try:
            # Find handler for this task type
            handler = self.task_handlers.get(task_type)

            if not handler:
                raise ValueError(f"No handler registered for task type: {task_type}")

            # Execute task with handler
            result = await handler(task)

            # Mark task complete
            await self.complete_task(task_id, "completed", result)

            logger.info(f"✅ Task completed: {task_id}")

        except Exception as e:
            logger.error(f"❌ Task failed: {task_id} - {e}")
            await self.complete_task(task_id, "failed", {"error": str(e)})

        finally:
            self.current_task = None
            self.status = "idle"

    async def update_progress(self, task_id: str, progress: float, details: str = ""):
        """Report task progress to orchestrator"""
        try:
            await self.client.post(
                f"{self.orchestrator_url}/work/update",
                json={
                    "session_id": self.session_id,
                    "task_id": task_id,
                    "progress": progress,
                    "status": "in_progress",
                    "details": details,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"❌ Progress update error: {e}")

    async def complete_task(self, task_id: str, status: str, result: Dict):
        """Mark task as complete or failed"""
        try:
            response = await self.client.post(
                f"{self.orchestrator_url}/work/complete",
                json={
                    "session_id": self.session_id,
                    "task_id": task_id,
                    "status": status,
                    "result": result,
                    "completed_at": datetime.now().isoformat()
                }
            )

            if response.status_code == 200:
                logger.info(f"✅ Task completion reported: {task_id}")
            else:
                logger.warning(f"⚠️  Task completion report failed: {response.status_code}")

        except Exception as e:
            logger.error(f"❌ Task completion error: {e}")

    async def heartbeat_loop(self):
        """Send heartbeats periodically"""
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            await self.heartbeat()

    async def work_loop(self):
        """Check for work periodically when idle"""
        while True:
            if self.status == "idle":
                # Request work from orchestrator
                task = await self.request_work()

                if task:
                    await self.execute_task(task)
                else:
                    # No work available, wait before checking again
                    await asyncio.sleep(self.work_check_interval)
            else:
                # Currently busy, check again soon
                await asyncio.sleep(10)

    async def run(self):
        """Main run loop - register and start working"""
        # Register with orchestrator
        registered = await self.register()

        if not registered:
            logger.error("Failed to register with orchestrator. Retrying in 60s...")
            await asyncio.sleep(60)
            return await self.run()

        # Start background loops
        await asyncio.gather(
            self.heartbeat_loop(),
            self.work_loop()
        )

    def start(self):
        """Start swarm client (blocking)"""
        logger.info(f"🧠 Swarm Client Starting...")
        logger.info(f"   Session ID: {self.session_id}")
        logger.info(f"   Capabilities: {', '.join(self.capabilities)}")
        logger.info(f"   Orchestrator: {self.orchestrator_url}")

        try:
            asyncio.run(self.run())
        except KeyboardInterrupt:
            logger.info("🛑 Swarm client stopped")


# ============================================================================
# Example Usage
# ============================================================================

async def build_task_handler(task: Dict) -> Dict:
    """Example handler for 'build' tasks"""
    logger.info(f"Building: {task['id']}")

    # Simulate build work
    spec = task.get("spec", {})

    # TODO: Actual build logic here
    # - Read spec
    # - Generate code
    # - Run tests
    # - Deploy

    # For now, simulate with sleep
    for i in range(10):
        await asyncio.sleep(6)  # 60 seconds total
        progress = (i + 1) / 10
        # Report progress (would need reference to client)
        logger.info(f"Build progress: {progress * 100:.0f}%")

    return {
        "status": "success",
        "deployed_url": f"http://198.54.123.234:{task.get('port', 8000)}",
        "duration_minutes": 1
    }


async def architect_task_handler(task: Dict) -> Dict:
    """Example handler for 'architect' tasks"""
    logger.info(f"Architecting: {task['id']}")

    # TODO: Actual architecture work
    # - Design system
    # - Create specs
    # - Document architecture

    await asyncio.sleep(30)  # Simulate work

    return {
        "status": "success",
        "spec_created": f"/path/to/spec/{task['id']}.md",
        "duration_minutes": 0.5
    }


async def marketing_task_handler(task: Dict) -> Dict:
    """Example handler for 'marketing' tasks"""
    logger.info(f"Marketing: {task['id']}")

    # TODO: Actual marketing work
    # - Post to social media
    # - Write content
    # - Engage with community

    await asyncio.sleep(15)  # Simulate work

    return {
        "status": "success",
        "post_url": "https://twitter.com/user/status/123",
        "engagement": {"likes": 10, "retweets": 3},
        "duration_minutes": 0.25
    }


if __name__ == "__main__":
    # Example: Create swarm client for this session
    client = SwarmClient(
        session_id="session-example",
        capabilities=["build", "architect", "marketing"],
        orchestrator_url="http://198.54.123.234:8600"
    )

    # Register task handlers
    client.register_handler("build", build_task_handler)
    client.register_handler("architect", architect_task_handler)
    client.register_handler("marketing", marketing_task_handler)

    # Start working
    client.start()
