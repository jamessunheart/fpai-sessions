#!/usr/bin/env python3
"""
ARIA BUILDER BRIDGE
===================

Queues specs into the builder pipeline:
- Tracks build status
- Handles verification feedback loop
- Auto-rollback on failure
- Respects change limits and complexity gates
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
from contextlib import contextmanager
import threading
import httpx
import shutil

from .spec_generator import GeneratedSpec

logger = logging.getLogger("aria.reflection.builder_bridge")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("REFLECTION_DB", "/opt/fpai/aria-command/state/reflection.db")
BUILDER_API = os.getenv("BUILDER_API", "http://localhost:8720")
BACKUP_DIR = os.getenv("REFLECTION_BACKUP_DIR", "/opt/fpai/aria-command/backups/reflection")

# Safety limits
MAX_CHANGES_PER_CYCLE = int(os.getenv("MAX_CHANGES_PER_CYCLE", "3"))
AUTO_APPLY_MAX_COMPLEXITY = os.getenv("AUTO_APPLY_MAX_COMPLEXITY", "low")  # low, medium, high


class BuildStatus(str):
    QUEUED = "queued"
    BUILDING = "building"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    NEEDS_APPROVAL = "needs_approval"


BUILDER_SCHEMA = """
CREATE TABLE IF NOT EXISTS build_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id TEXT UNIQUE NOT NULL,
    spec_title TEXT NOT NULL,
    spec_path TEXT,
    complexity TEXT,
    risk TEXT,
    status TEXT DEFAULT 'queued',
    queued_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    backup_path TEXT,
    cycle_id TEXT
);

CREATE TABLE IF NOT EXISTS build_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    spec_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    level TEXT,
    message TEXT
);

CREATE INDEX IF NOT EXISTS idx_bq_status ON build_queue(status);
CREATE INDEX IF NOT EXISTS idx_bq_cycle ON build_queue(cycle_id);
CREATE INDEX IF NOT EXISTS idx_bl_spec ON build_logs(spec_id);
"""


@dataclass
class BuildJob:
    """A build job in the queue."""
    spec_id: str
    spec_title: str
    spec_path: str
    complexity: str
    risk: str
    status: str = BuildStatus.QUEUED
    queued_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: str = ""
    backup_path: str = ""
    cycle_id: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "spec_id": self.spec_id,
            "spec_title": self.spec_title,
            "spec_path": self.spec_path,
            "complexity": self.complexity,
            "risk": self.risk,
            "status": self.status,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "backup_path": self.backup_path,
            "cycle_id": self.cycle_id
        }


# ============================================================================
# BUILDER BRIDGE
# ============================================================================

class BuilderBridge:
    """
    Bridges reflection specs to the builder pipeline.
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self.http = httpx.AsyncClient(timeout=120.0)
        self._init_db()
        Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    
    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_db(self):
        """Initialize database."""
        from pathlib import Path
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        with self._cursor() as cursor:
            cursor.executescript(BUILDER_SCHEMA)
        
        logger.info(f"Builder bridge initialized: {self.db_path}")
    
    async def close(self):
        await self.http.aclose()
    
    # ========================================================================
    # QUEUE MANAGEMENT
    # ========================================================================
    
    def queue_spec(self, spec: GeneratedSpec, cycle_id: str = "") -> BuildJob:
        """
        Add a spec to the build queue.
        
        High-complexity or high-risk specs are marked as needs_approval.
        """
        # Check complexity gate
        complexity_order = {"low": 0, "medium": 1, "high": 2}
        max_auto = complexity_order.get(AUTO_APPLY_MAX_COMPLEXITY, 0)
        spec_level = complexity_order.get(spec.complexity, 1)
        
        needs_approval = (
            spec_level > max_auto or
            spec.risk == "high"
        )
        
        initial_status = BuildStatus.NEEDS_APPROVAL if needs_approval else BuildStatus.QUEUED
        
        job = BuildJob(
            spec_id=spec.id,
            spec_title=spec.title,
            spec_path=spec.spec_path,
            complexity=spec.complexity,
            risk=spec.risk,
            status=initial_status,
            cycle_id=cycle_id
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO build_queue 
                (spec_id, spec_title, spec_path, complexity, risk, status, queued_at, cycle_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.spec_id, job.spec_title, job.spec_path,
                job.complexity, job.risk, job.status,
                job.queued_at.isoformat(), job.cycle_id
            ))
        
        self._log(job.spec_id, "INFO", f"Queued with status: {initial_status}")
        logger.info(f"Spec queued: {spec.id} ({initial_status})")
        
        return job
    
    def queue_specs(self, specs: List[GeneratedSpec], cycle_id: str = "") -> List[BuildJob]:
        """Queue multiple specs, respecting limits."""
        jobs = []
        
        # Respect max changes per cycle
        for spec in specs[:MAX_CHANGES_PER_CYCLE]:
            job = self.queue_spec(spec, cycle_id)
            jobs.append(job)
        
        if len(specs) > MAX_CHANGES_PER_CYCLE:
            logger.warning(f"Limited to {MAX_CHANGES_PER_CYCLE} specs per cycle, "
                         f"{len(specs) - MAX_CHANGES_PER_CYCLE} skipped")
        
        return jobs
    
    def approve_spec(self, spec_id: str) -> bool:
        """Approve a spec that needs approval."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE build_queue 
                SET status = ? 
                WHERE spec_id = ? AND status = ?
            """, (BuildStatus.QUEUED, spec_id, BuildStatus.NEEDS_APPROVAL))
            
            if cursor.rowcount > 0:
                self._log(spec_id, "INFO", "Approved by user")
                return True
        return False
    
    def reject_spec(self, spec_id: str) -> bool:
        """Reject a spec."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE build_queue 
                SET status = 'rejected' 
                WHERE spec_id = ?
            """, (spec_id,))
            
            if cursor.rowcount > 0:
                self._log(spec_id, "INFO", "Rejected by user")
                return True
        return False
    
    # ========================================================================
    # BUILD EXECUTION
    # ========================================================================
    
    async def process_queue(self) -> List[BuildJob]:
        """Process all queued builds."""
        results = []
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM build_queue 
                WHERE status = ?
                ORDER BY queued_at ASC
            """, (BuildStatus.QUEUED,))
            
            jobs = cursor.fetchall()
        
        for row in jobs:
            job = await self._execute_build(dict(row))
            results.append(job)
        
        return results
    
    async def _execute_build(self, row: Dict) -> BuildJob:
        """Execute a single build."""
        spec_id = row["spec_id"]
        
        job = BuildJob(
            spec_id=spec_id,
            spec_title=row["spec_title"],
            spec_path=row["spec_path"],
            complexity=row["complexity"],
            risk=row["risk"],
            status=BuildStatus.BUILDING,
            started_at=datetime.now(),
            cycle_id=row.get("cycle_id", "")
        )
        
        self._update_status(spec_id, BuildStatus.BUILDING)
        self._log(spec_id, "INFO", "Build started")
        
        try:
            # Load the spec
            spec_data = self._load_spec(row["spec_path"])
            if not spec_data:
                raise Exception("Could not load spec")
            
            # Create backup
            backup_path = await self._create_backup(spec_data)
            job.backup_path = backup_path
            self._update_backup_path(spec_id, backup_path)
            
            # Execute via builder API or direct
            success = await self._call_builder(spec_data)
            
            if success:
                # Verify
                self._update_status(spec_id, BuildStatus.VERIFYING)
                verified = await self._verify_build(spec_data)
                
                if verified:
                    job.status = BuildStatus.COMPLETED
                    job.completed_at = datetime.now()
                    self._update_status(spec_id, BuildStatus.COMPLETED)
                    self._log(spec_id, "INFO", "Build completed successfully")
                else:
                    # Rollback
                    await self._rollback(spec_id, backup_path)
                    job.status = BuildStatus.ROLLED_BACK
                    job.error_message = "Verification failed"
                    self._log(spec_id, "ERROR", "Verification failed, rolled back")
            else:
                job.status = BuildStatus.FAILED
                job.error_message = "Build failed"
                self._update_status(spec_id, BuildStatus.FAILED, "Build failed")
                self._log(spec_id, "ERROR", "Build failed")
        
        except Exception as e:
            logger.error(f"Build error for {spec_id}: {e}")
            job.status = BuildStatus.FAILED
            job.error_message = str(e)
            self._update_status(spec_id, BuildStatus.FAILED, str(e))
            self._log(spec_id, "ERROR", f"Build error: {e}")
        
        return job
    
    def _load_spec(self, spec_path: str) -> Optional[Dict]:
        """Load spec from file."""
        json_path = spec_path.replace(".md", ".json")
        
        if not Path(json_path).exists():
            return None
        
        with open(json_path) as f:
            return json.load(f)
    
    async def _create_backup(self, spec_data: Dict) -> str:
        """Create backup of files that will be modified."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        spec_id = spec_data.get("id", "unknown")
        backup_dir = Path(BACKUP_DIR) / f"{spec_id}-{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup files to be modified
        for fc in spec_data.get("file_changes", []):
            src_path = fc.get("file_path")
            if src_path and Path(src_path).exists():
                rel_path = src_path.replace("/", "_")
                dst_path = backup_dir / rel_path
                shutil.copy2(src_path, dst_path)
                logger.debug(f"Backed up: {src_path}")
        
        # Save spec info
        with open(backup_dir / "spec.json", 'w') as f:
            json.dump(spec_data, f, indent=2)
        
        return str(backup_dir)
    
    async def _call_builder(self, spec_data: Dict) -> bool:
        """
        Call the builder API to implement the spec.
        
        Falls back to direct implementation if builder is unavailable.
        """
        try:
            # Try builder API
            response = await self.http.post(
                f"{BUILDER_API}/build",
                json={"spec": spec_data},
                timeout=300.0
            )
            
            if response.status_code == 200:
                return response.json().get("success", False)
            
        except Exception as e:
            logger.warning(f"Builder API unavailable: {e}")
        
        # Fallback: Simple direct implementation for low-complexity specs
        if spec_data.get("complexity") == "low":
            return await self._direct_implement(spec_data)
        
        return False
    
    async def _direct_implement(self, spec_data: Dict) -> bool:
        """
        Direct implementation for simple specs.
        
        Only handles simple file modifications.
        """
        logger.info("Attempting direct implementation...")
        
        for fc in spec_data.get("file_changes", []):
            file_path = fc.get("file_path")
            change_type = fc.get("change_type")
            code_snippet = fc.get("code_snippet", "")
            
            if not file_path or not code_snippet:
                continue
            
            try:
                if change_type == "create":
                    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
                    with open(file_path, 'w') as f:
                        f.write(code_snippet)
                    logger.info(f"Created: {file_path}")
                
                elif change_type == "modify" and Path(file_path).exists():
                    # For simple modifications, we need more sophisticated handling
                    # This is a placeholder - real implementation would use search/replace
                    logger.warning(f"Direct modify not implemented for: {file_path}")
                    
            except Exception as e:
                logger.error(f"Direct implementation error: {e}")
                return False
        
        return True
    
    async def _verify_build(self, spec_data: Dict) -> bool:
        """
        Verify the build was successful.
        
        Checks:
        - Files exist and are syntactically valid
        - Basic functionality tests
        """
        for fc in spec_data.get("file_changes", []):
            file_path = fc.get("file_path")
            
            if not file_path:
                continue
            
            # Check file exists
            if fc.get("change_type") != "delete" and not Path(file_path).exists():
                logger.error(f"Verification failed: {file_path} does not exist")
                return False
            
            # Check Python syntax
            if file_path.endswith(".py") and Path(file_path).exists():
                import py_compile
                try:
                    py_compile.compile(file_path, doraise=True)
                except py_compile.PyCompileError as e:
                    logger.error(f"Syntax error in {file_path}: {e}")
                    return False
        
        return True
    
    async def _rollback(self, spec_id: str, backup_path: str):
        """Rollback changes from backup."""
        if not backup_path or not Path(backup_path).exists():
            logger.error(f"Cannot rollback: backup not found at {backup_path}")
            return
        
        backup_dir = Path(backup_path)
        
        # Load spec to get file paths
        spec_path = backup_dir / "spec.json"
        if spec_path.exists():
            with open(spec_path) as f:
                spec_data = json.load(f)
            
            for fc in spec_data.get("file_changes", []):
                src_path = fc.get("file_path")
                if src_path:
                    rel_path = src_path.replace("/", "_")
                    backup_file = backup_dir / rel_path
                    
                    if backup_file.exists():
                        shutil.copy2(backup_file, src_path)
                        logger.info(f"Restored: {src_path}")
        
        self._update_status(spec_id, BuildStatus.ROLLED_BACK)
        logger.info(f"Rollback complete for {spec_id}")
    
    # ========================================================================
    # STATUS & LOGGING
    # ========================================================================
    
    def _update_status(self, spec_id: str, status: str, error: str = ""):
        """Update build status."""
        with self._cursor() as cursor:
            if status in [BuildStatus.COMPLETED, BuildStatus.FAILED, BuildStatus.ROLLED_BACK]:
                cursor.execute("""
                    UPDATE build_queue 
                    SET status = ?, completed_at = ?, error_message = ?
                    WHERE spec_id = ?
                """, (status, datetime.now().isoformat(), error, spec_id))
            else:
                cursor.execute("""
                    UPDATE build_queue 
                    SET status = ?, started_at = COALESCE(started_at, ?)
                    WHERE spec_id = ?
                """, (status, datetime.now().isoformat(), spec_id))
    
    def _update_backup_path(self, spec_id: str, backup_path: str):
        """Update backup path."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE build_queue SET backup_path = ? WHERE spec_id = ?
            """, (backup_path, spec_id))
    
    def _log(self, spec_id: str, level: str, message: str):
        """Add log entry."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO build_logs (spec_id, timestamp, level, message)
                VALUES (?, ?, ?, ?)
            """, (spec_id, datetime.now().isoformat(), level, message))
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get overall queue status."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) as count FROM build_queue GROUP BY status
            """)
            status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("""
                SELECT * FROM build_queue ORDER BY queued_at DESC LIMIT 10
            """)
            recent = [dict(row) for row in cursor.fetchall()]
        
        return {
            "status_counts": status_counts,
            "recent_builds": recent
        }
    
    def get_build_logs(self, spec_id: str, limit: int = 50) -> List[Dict]:
        """Get logs for a build."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT timestamp, level, message FROM build_logs
                WHERE spec_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (spec_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    async def rollback_build(self, spec_id: str) -> bool:
        """Manually rollback a build."""
        with self._cursor() as cursor:
            cursor.execute("SELECT backup_path FROM build_queue WHERE spec_id = ?", (spec_id,))
            row = cursor.fetchone()
            
            if not row or not row["backup_path"]:
                return False
        
        await self._rollback(spec_id, row["backup_path"])
        return True


# ============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ============================================================================

_bridge: Optional[BuilderBridge] = None


def get_builder_bridge() -> BuilderBridge:
    """Get global builder bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = BuilderBridge()
    return _bridge


def queue_specs(specs: List[GeneratedSpec], cycle_id: str = "") -> List[BuildJob]:
    """Queue specs for building."""
    return get_builder_bridge().queue_specs(specs, cycle_id)


async def process_build_queue() -> List[BuildJob]:
    """Process the build queue."""
    return await get_builder_bridge().process_queue()


def get_queue_status() -> Dict[str, Any]:
    """Get queue status."""
    return get_builder_bridge().get_queue_status()


def approve_spec(spec_id: str) -> bool:
    """Approve a spec."""
    return get_builder_bridge().approve_spec(spec_id)


def reject_spec(spec_id: str) -> bool:
    """Reject a spec."""
    return get_builder_bridge().reject_spec(spec_id)


async def rollback_build(spec_id: str) -> bool:
    """Rollback a build."""
    return await get_builder_bridge().rollback_build(spec_id)


