"""
Task Orchestrator
Coordinates task execution with appropriate executors
"""

import asyncio
import subprocess
from typing import Dict, Optional
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Task, TaskType, TaskStatus
from src.database import TaskDatabase
from src.credentials import CredentialVault
from src.executors import SendGridExecutor, DNSExecutor


class TaskOrchestrator:
    """
    Orchestrates task execution

    Responsibilities:
    - Match tasks to appropriate executors
    - Execute tasks
    - Handle results and errors
    - Send notifications when human action needed
    """

    def __init__(self, db_path: Optional[str] = None, vault_url: Optional[str] = None):
        self.db = TaskDatabase(db_path)
        self.vault = CredentialVault(vault_url)

        # Executor registry
        self.executors = {
            ("service_signup", "sendgrid"): SendGridExecutor,
            ("dns_configuration", "*"): DNSExecutor,
        }

    def get_executor(self, task: Task):
        """Get appropriate executor for task"""

        # Try exact match first
        key = (task.type, task.service)
        if key in self.executors:
            return self.executors[key](task, self.db, self.vault)

        # Try wildcard match
        key = (task.type, "*")
        if key in self.executors:
            return self.executors[key](task, self.db, self.vault)

        return None

    async def execute_task(self, task_id: str) -> Dict:
        """Execute a single task"""

        task = self.db.get_task(task_id)

        if not task:
            return {"error": f"Task not found: {task_id}"}

        if task.status != TaskStatus.PENDING:
            return {
                "error": f"Task is not pending (current status: {task.status})",
                "task_id": task_id
            }

        # Get executor
        executor = self.get_executor(task)

        if not executor:
            task.add_log(f"No executor found for {task.type}/{task.service}")
            task.status = TaskStatus.FAILED
            task.error_message = "No executor available"
            self.db.update_task(task)

            return {
                "error": "No executor available",
                "task_type": task.type,
                "service": task.service
            }

        # Execute task
        try:
            task.add_log(f"Starting execution with {executor.__class__.__name__}")
            self.db.update_task(task)

            result = await executor.execute()

            return {
                "success": True,
                "task_id": task_id,
                "result": result
            }

        except Exception as e:
            task.add_log(f"Execution failed: {str(e)}")
            task.mark_failed(str(e))
            self.db.update_task(task)

            return {
                "success": False,
                "task_id": task_id,
                "error": str(e)
            }

    async def process_pending_tasks(self, limit: int = 10) -> Dict:
        """Process all pending tasks"""

        pending_tasks = self.db.list_tasks(status=TaskStatus.PENDING, limit=limit)

        if not pending_tasks:
            return {"message": "No pending tasks", "processed": 0}

        results = []

        for task in pending_tasks:
            print(f"Processing task: {task.id} ({task.service})")
            result = await self.execute_task(task.id)
            results.append(result)

            # Small delay between tasks
            await asyncio.sleep(1)

        return {
            "processed": len(results),
            "results": results
        }

    def send_notification(self, task_id: str, message: str, priority: str = "normal"):
        """
        Send notification via session messaging system

        Integrates with docs/coordination/scripts/session-send-message.sh
        """

        try:
            script_path = "/Users/jamessunheart/Development/docs/coordination/scripts/session-send-message.sh"

            result = subprocess.run(
                [
                    script_path,
                    "broadcast",
                    f"Task Automation: {task_id}",
                    message,
                    priority
                ],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                print(f"✅ Notification sent for task {task_id}")
                return True
            else:
                print(f"⚠️ Notification failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"Failed to send notification: {str(e)}")
            return False

    def notify_blocked_task(self, task: Task):
        """Notify user about blocked task"""

        message = f"""
🚧 Task Blocked: {task.id}

Service: {task.service}
Type: {task.type}
Blocker: {task.blocker}

{task.blocker_details}

View task details:
http://198.54.123.234:8031/task/{task.id}

Or via CLI:
ssh root@198.54.123.234 "cd /root/agents/services/task-automation && python3 src/cli.py show {task.id}"
"""

        self.send_notification(task.id, message, priority="high")


# CLI for orchestrator
if __name__ == "__main__":
    import sys

    orchestrator = TaskOrchestrator()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "process":
            # Process all pending tasks
            result = asyncio.run(orchestrator.process_pending_tasks())
            print(f"Processed {result['processed']} tasks")

        elif command == "execute" and len(sys.argv) > 2:
            # Execute specific task
            task_id = sys.argv[2]
            result = asyncio.run(orchestrator.execute_task(task_id))
            print(f"Result: {result}")

        else:
            print("Usage:")
            print("  python3 orchestrator.py process           # Process all pending tasks")
            print("  python3 orchestrator.py execute <task_id> # Execute specific task")
    else:
        print("Task Orchestrator - Automated task execution")
        print("")
        print("Usage:")
        print("  python3 orchestrator.py process           # Process all pending tasks")
        print("  python3 orchestrator.py execute <task_id> # Execute specific task")
