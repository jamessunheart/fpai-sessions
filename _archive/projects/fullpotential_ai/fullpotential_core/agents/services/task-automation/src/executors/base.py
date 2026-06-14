"""
Base Executor Class
All task executors inherit from this
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.models import Task, TaskStatus, BlockerType
from src.database import TaskDatabase
from src.credentials import CredentialVault


class BaseExecutor(ABC):
    """Base class for all task executors"""

    def __init__(self, task: Task, db: TaskDatabase, vault: CredentialVault):
        self.task = task
        self.db = db
        self.vault = vault

    @abstractmethod
    async def execute(self) -> Dict:
        """
        Execute the task

        Returns:
            Dict with result information

        Raises:
            Exception on failure
        """
        pass

    def log(self, message: str):
        """Add log entry to task"""
        self.task.add_log(message)
        self.db.update_task(self.task)

    def mark_in_progress(self):
        """Mark task as in progress"""
        self.task.mark_in_progress()
        self.db.update_task(self.task)
        self.log("Task execution started")

    def mark_blocked(self, blocker: BlockerType, details: str):
        """Mark task as blocked"""
        self.task.mark_blocked(blocker, details)
        self.db.update_task(self.task)

    def mark_completed(self, result: Dict):
        """Mark task as completed"""
        self.task.mark_completed(result)
        self.db.update_task(self.task)

    def mark_failed(self, error: str):
        """Mark task as failed"""
        self.task.mark_failed(error)
        self.db.update_task(self.task)

    def get_credential(self, credential_type: str) -> Optional[str]:
        """Get credential from vault"""
        return self.vault.get_credential(self.task.service, credential_type)

    def store_credential(self, credential_type: str, value: str, metadata: Optional[Dict] = None):
        """Store credential in vault"""
        success = self.vault.store_credential(
            service=self.task.service,
            credential_type=credential_type,
            value=value,
            metadata=metadata or {}
        )
        if success:
            self.log(f"Stored {credential_type} in credential vault")
        else:
            self.log(f"Failed to store {credential_type} in vault")
        return success

    def notify_human(self, action_type: str, message: str, instructions: str):
        """
        Notify human that action is needed

        This will integrate with the session messaging system
        """
        self.log(f"HUMAN ACTION REQUIRED: {action_type}")
        self.log(f"Message: {message}")
        self.log(f"Instructions: {instructions}")

        # TODO: Integrate with session-send-message.sh
        # For now, just log it

    def check_prerequisites(self) -> bool:
        """
        Check if all prerequisites for task execution are met
        Override in subclasses if needed
        """
        return True
