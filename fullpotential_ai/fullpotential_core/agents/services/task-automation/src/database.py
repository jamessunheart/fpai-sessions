"""
Task Automation Framework - Database Layer
SQLite-based persistence for task queue
"""

import sqlite3
import json
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from .models import Task, TaskStatus, TaskType, AutomationLevel


class TaskDatabase:
    """SQLite database for task management"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "database" / "tasks.db"

        self.db_path = db_path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                service TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL,
                automation_level TEXT,
                blocker TEXT,
                blocker_details TEXT,
                assigned_to TEXT,
                priority INTEGER DEFAULT 5,
                params TEXT,
                result TEXT,
                credentials TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                logs TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS service_configs (
                name TEXT PRIMARY KEY,
                signup_automation TEXT NOT NULL,
                api_available BOOLEAN,
                cli_tool BOOLEAN,
                difficulty TEXT,
                blockers TEXT,
                signup_url TEXT,
                api_docs_url TEXT,
                notes TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS human_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                description TEXT NOT NULL,
                instructions TEXT NOT NULL,
                url TEXT,
                screenshot_path TEXT,
                completed BOOLEAN DEFAULT 0,
                completed_at TEXT,
                result TEXT,
                FOREIGN KEY (task_id) REFERENCES tasks (id)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_service ON tasks(service)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON tasks(created_at)")

        conn.commit()
        conn.close()

    def _task_to_dict(self, task: Task) -> dict:
        """Convert Task model to database dict"""
        return {
            "id": task.id,
            "type": task.type.value if isinstance(task.type, TaskType) else task.type,
            "service": task.service,
            "description": task.description,
            "status": task.status.value if isinstance(task.status, TaskStatus) else task.status,
            "automation_level": task.automation_level.value if task.automation_level else None,
            "blocker": task.blocker.value if task.blocker else None,
            "blocker_details": task.blocker_details,
            "assigned_to": task.assigned_to,
            "priority": task.priority,
            "params": json.dumps(task.params),
            "result": json.dumps(task.result) if task.result else None,
            "credentials": json.dumps(task.credentials) if task.credentials else None,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
            "logs": json.dumps(task.logs)
        }

    def _dict_to_task(self, row: dict) -> Task:
        """Convert database dict to Task model"""
        return Task(
            id=row["id"],
            type=row["type"],
            service=row["service"],
            description=row["description"],
            status=row["status"],
            automation_level=row["automation_level"],
            blocker=row["blocker"],
            blocker_details=row["blocker_details"],
            assigned_to=row["assigned_to"],
            priority=row["priority"],
            params=json.loads(row["params"]) if row["params"] else {},
            result=json.loads(row["result"]) if row["result"] else None,
            credentials=json.loads(row["credentials"]) if row["credentials"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error_message=row["error_message"],
            retry_count=row["retry_count"],
            max_retries=row["max_retries"],
            logs=json.loads(row["logs"]) if row["logs"] else []
        )

    def create_task(self, task: Task) -> Task:
        """Create a new task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        task_dict = self._task_to_dict(task)

        columns = ", ".join(task_dict.keys())
        placeholders = ", ".join(["?" for _ in task_dict])

        cursor.execute(
            f"INSERT INTO tasks ({columns}) VALUES ({placeholders})",
            list(task_dict.values())
        )

        conn.commit()
        conn.close()

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._dict_to_task(dict(row))
        return None

    def update_task(self, task: Task) -> Task:
        """Update existing task"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        task_dict = self._task_to_dict(task)

        set_clause = ", ".join([f"{k} = ?" for k in task_dict.keys() if k != "id"])
        values = [v for k, v in task_dict.items() if k != "id"]
        values.append(task.id)

        cursor.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?",
            values
        )

        conn.commit()
        conn.close()

        return task

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        service: Optional[str] = None,
        limit: int = 100
    ) -> List[Task]:
        """List tasks with optional filtering"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status.value if isinstance(status, TaskStatus) else status)

        if service:
            query += " AND service = ?"
            params.append(service)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [self._dict_to_task(dict(row)) for row in rows]

    def get_stats(self) -> dict:
        """Get task statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT status, COUNT(*) as count FROM tasks GROUP BY status")
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}

        cursor.execute("SELECT COUNT(*) FROM tasks")
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        completed = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'blocked'")
        blocked = cursor.fetchone()[0]

        conn.close()

        success_rate = (completed / total * 100) if total > 0 else 0

        return {
            "total": total,
            "completed": completed,
            "blocked": blocked,
            "success_rate": round(success_rate, 1),
            "status_breakdown": status_counts
        }
