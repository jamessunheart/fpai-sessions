#!/usr/bin/env python3
"""
ARIA ULTRA POWER - WORKFLOW STORE
==================================

Persistent storage for workflows using SQLite.
Manages workflow definitions, execution history, and audit logs.
"""

import sqlite3
import json
import logging
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
from contextlib import contextmanager

from .engine import Workflow, WorkflowStatus, WorkflowExecution

logger = logging.getLogger("aria.workflows.store")

# Default database path
DEFAULT_DB_PATH = "/opt/fpai/aria-command/state/workflows.db"


class WorkflowStore:
    """SQLite-backed workflow storage."""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"WorkflowStore initialized at {db_path}")
    
    @contextmanager
    def _get_conn(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            # Workflows table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    owner_id TEXT NOT NULL,
                    triggers TEXT NOT NULL,
                    actions TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    last_triggered REAL,
                    execution_count INTEGER DEFAULT 0,
                    cooldown_seconds INTEGER DEFAULT 60,
                    max_executions INTEGER
                )
            """)
            
            # Execution history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    trigger_type TEXT,
                    trigger_data TEXT,
                    actions_executed TEXT,
                    success INTEGER NOT NULL,
                    error TEXT,
                    started_at REAL NOT NULL,
                    completed_at REAL NOT NULL,
                    duration_ms REAL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
                )
            """)
            
            # Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflows_owner ON workflows(owner_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_executions_workflow ON executions(workflow_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_executions_time ON executions(completed_at)")
    
    def save_workflow(self, workflow: Workflow) -> bool:
        """Save or update a workflow."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO workflows 
                    (id, name, description, owner_id, triggers, actions, status,
                     created_at, updated_at, last_triggered, execution_count,
                     cooldown_seconds, max_executions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    workflow.id,
                    workflow.name,
                    workflow.description,
                    workflow.owner_id,
                    json.dumps(workflow.triggers),
                    json.dumps(workflow.actions),
                    workflow.status.value,
                    workflow.created_at,
                    workflow.updated_at,
                    workflow.last_triggered,
                    workflow.execution_count,
                    workflow.cooldown_seconds,
                    workflow.max_executions,
                ))
            return True
        except Exception as e:
            logger.error(f"Error saving workflow: {e}")
            return False
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        try:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT * FROM workflows WHERE id = ?",
                    (workflow_id,)
                ).fetchone()
                
                if row:
                    return self._row_to_workflow(row)
                return None
        except Exception as e:
            logger.error(f"Error getting workflow: {e}")
            return None
    
    def list_workflows(
        self,
        owner_id: str = None,
        status: WorkflowStatus = None,
        limit: int = 100
    ) -> List[Workflow]:
        """List workflows with optional filters."""
        try:
            with self._get_conn() as conn:
                query = "SELECT * FROM workflows WHERE 1=1"
                params = []
                
                if owner_id:
                    query += " AND owner_id = ?"
                    params.append(owner_id)
                
                if status:
                    query += " AND status = ?"
                    params.append(status.value)
                
                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                rows = conn.execute(query, params).fetchall()
                return [self._row_to_workflow(row) for row in rows]
        except Exception as e:
            logger.error(f"Error listing workflows: {e}")
            return []
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        try:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
                conn.execute("DELETE FROM executions WHERE workflow_id = ?", (workflow_id,))
            return True
        except Exception as e:
            logger.error(f"Error deleting workflow: {e}")
            return False
    
    def update_status(self, workflow_id: str, status: WorkflowStatus) -> bool:
        """Update workflow status."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE workflows SET status = ?, updated_at = ? WHERE id = ?",
                    (status.value, time.time(), workflow_id)
                )
            return True
        except Exception as e:
            logger.error(f"Error updating status: {e}")
            return False
    
    def record_execution(self, execution: WorkflowExecution) -> bool:
        """Record a workflow execution."""
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO executions 
                    (id, workflow_id, trigger_type, trigger_data, actions_executed,
                     success, error, started_at, completed_at, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    execution.execution_id,
                    execution.workflow_id,
                    execution.trigger_type,
                    json.dumps(execution.trigger_data),
                    json.dumps(execution.actions_executed),
                    1 if execution.success else 0,
                    execution.error,
                    execution.started_at,
                    execution.completed_at,
                    execution.duration_ms,
                ))
                
                # Update workflow execution count
                conn.execute(
                    "UPDATE workflows SET execution_count = execution_count + 1, last_triggered = ? WHERE id = ?",
                    (execution.completed_at, execution.workflow_id)
                )
            return True
        except Exception as e:
            logger.error(f"Error recording execution: {e}")
            return False
    
    def get_executions(
        self,
        workflow_id: str = None,
        limit: int = 50,
        since: float = None
    ) -> List[WorkflowExecution]:
        """Get execution history."""
        try:
            with self._get_conn() as conn:
                query = "SELECT * FROM executions WHERE 1=1"
                params = []
                
                if workflow_id:
                    query += " AND workflow_id = ?"
                    params.append(workflow_id)
                
                if since:
                    query += " AND completed_at > ?"
                    params.append(since)
                
                query += " ORDER BY completed_at DESC LIMIT ?"
                params.append(limit)
                
                rows = conn.execute(query, params).fetchall()
                return [self._row_to_execution(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting executions: {e}")
            return []
    
    def get_stats(self, owner_id: str = None) -> Dict:
        """Get workflow statistics."""
        try:
            with self._get_conn() as conn:
                # Base query
                if owner_id:
                    workflow_filter = "owner_id = ?"
                    params = [owner_id]
                else:
                    workflow_filter = "1=1"
                    params = []
                
                # Total workflows
                total = conn.execute(
                    f"SELECT COUNT(*) FROM workflows WHERE {workflow_filter}",
                    params
                ).fetchone()[0]
                
                # By status
                active = conn.execute(
                    f"SELECT COUNT(*) FROM workflows WHERE {workflow_filter} AND status = 'active'",
                    params
                ).fetchone()[0]
                
                paused = conn.execute(
                    f"SELECT COUNT(*) FROM workflows WHERE {workflow_filter} AND status = 'paused'",
                    params
                ).fetchone()[0]
                
                # Total executions
                if owner_id:
                    exec_count = conn.execute("""
                        SELECT COUNT(*) FROM executions e
                        JOIN workflows w ON e.workflow_id = w.id
                        WHERE w.owner_id = ?
                    """, [owner_id]).fetchone()[0]
                else:
                    exec_count = conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
                
                # Success rate
                if owner_id:
                    success_count = conn.execute("""
                        SELECT COUNT(*) FROM executions e
                        JOIN workflows w ON e.workflow_id = w.id
                        WHERE w.owner_id = ? AND e.success = 1
                    """, [owner_id]).fetchone()[0]
                else:
                    success_count = conn.execute(
                        "SELECT COUNT(*) FROM executions WHERE success = 1"
                    ).fetchone()[0]
                
                success_rate = (success_count / exec_count * 100) if exec_count > 0 else 0
                
                return {
                    "total_workflows": total,
                    "active_workflows": active,
                    "paused_workflows": paused,
                    "total_executions": exec_count,
                    "success_rate": round(success_rate, 1),
                }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    def _row_to_workflow(self, row: sqlite3.Row) -> Workflow:
        """Convert database row to Workflow object."""
        return Workflow(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            owner_id=row["owner_id"],
            triggers=json.loads(row["triggers"]),
            actions=json.loads(row["actions"]),
            status=WorkflowStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_triggered=row["last_triggered"],
            execution_count=row["execution_count"],
            cooldown_seconds=row["cooldown_seconds"],
            max_executions=row["max_executions"],
        )
    
    def _row_to_execution(self, row: sqlite3.Row) -> WorkflowExecution:
        """Convert database row to WorkflowExecution object."""
        return WorkflowExecution(
            execution_id=row["id"],
            workflow_id=row["workflow_id"],
            trigger_type=row["trigger_type"] or "",
            trigger_data=json.loads(row["trigger_data"]) if row["trigger_data"] else {},
            actions_executed=json.loads(row["actions_executed"]) if row["actions_executed"] else [],
            success=bool(row["success"]),
            error=row["error"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            duration_ms=row["duration_ms"],
        )
    
    def load_all_workflows(self) -> List[Workflow]:
        """Load all active workflows for the engine."""
        return self.list_workflows(status=WorkflowStatus.ACTIVE, limit=1000)
    
    def cleanup_old_executions(self, days: int = 30) -> int:
        """Clean up old execution records."""
        try:
            cutoff = time.time() - (days * 86400)
            with self._get_conn() as conn:
                cursor = conn.execute(
                    "DELETE FROM executions WHERE completed_at < ?",
                    (cutoff,)
                )
                deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} old execution records")
            return deleted
        except Exception as e:
            logger.error(f"Error cleaning up executions: {e}")
            return 0


# Singleton instance
_store: Optional[WorkflowStore] = None


def get_workflow_store() -> WorkflowStore:
    """Get the global workflow store instance."""
    global _store
    if _store is None:
        _store = WorkflowStore()
    return _store


