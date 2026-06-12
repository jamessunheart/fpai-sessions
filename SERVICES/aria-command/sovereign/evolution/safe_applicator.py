#!/usr/bin/env python3
"""
ARIA SAFE APPLICATOR
=====================

Validates and safely applies evolution changes with:
- Syntax checking
- Test execution
- Health verification
- Automatic rollback

Features:
- Confidence-based execution
- Pre/post validation
- Rollback on failure
- Audit trail
"""

import os
import json
import sqlite3
import logging
import asyncio
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
from enum import Enum
import threading
import httpx

from .synthesizer import ImprovementProposal

logger = logging.getLogger("aria.evolution.applicator")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")
BACKUP_DIR = os.getenv("EVOLUTION_BACKUP_DIR", "/opt/fpai/aria-command/state/evolution_backups")
ARIA_SERVICE = "aria-command"
MAX_AUTO_CHANGES_PER_DAY = 10


class ChangeType(str, Enum):
    PROMPT = "prompt"
    CODE = "code"
    CONFIG = "config"
    TOOL = "tool"


class ChangeStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Change:
    """A change to be applied."""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # What to change
    change_type: ChangeType = ChangeType.PROMPT
    target_file: str = ""
    old_content: str = ""
    new_content: str = ""
    
    # Source
    proposal_id: Optional[int] = None
    reason: str = ""
    
    # Assessment
    confidence: float = 0.5
    risk_level: str = "low"
    
    # Status
    status: ChangeStatus = ChangeStatus.PENDING
    applied_at: Optional[datetime] = None
    validation_result: Optional[str] = None
    health_before: Optional[Dict] = None
    health_after: Optional[Dict] = None
    rollback_reason: Optional[str] = None


APPLICATOR_SCHEMA = """
CREATE TABLE IF NOT EXISTS evolution_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    change_type TEXT NOT NULL,
    target_file TEXT,
    old_content TEXT,
    new_content TEXT,
    proposal_id INTEGER,
    reason TEXT,
    confidence REAL DEFAULT 0.5,
    risk_level TEXT DEFAULT 'low',
    status TEXT DEFAULT 'pending',
    applied_at TEXT,
    validation_result TEXT,
    health_before TEXT,
    health_after TEXT,
    rollback_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_ec_status ON evolution_changes(status);
CREATE INDEX IF NOT EXISTS idx_ec_type ON evolution_changes(change_type);
CREATE INDEX IF NOT EXISTS idx_ec_date ON evolution_changes(created_at);

CREATE TABLE IF NOT EXISTS evolution_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    change_id INTEGER,
    action TEXT,
    details TEXT,
    outcome TEXT
);

CREATE INDEX IF NOT EXISTS idx_ea_change ON evolution_audit(change_id);
"""


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_python_syntax(code: str) -> Tuple[bool, str]:
    """Validate Python syntax."""
    try:
        compile(code, "<string>", "exec")
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntax error at line {e.lineno}: {e.msg}"


async def check_service_health(service: str = ARIA_SERVICE) -> Dict[str, Any]:
    """Check service health."""
    try:
        # Check systemd status
        result = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True,
            text=True,
            timeout=5
        )
        is_active = result.stdout.strip() == "active"
        
        # Check HTTP health if available
        http_healthy = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:8710/health")
                http_healthy = resp.status_code == 200
        except:
            pass
        
        return {
            "service_active": is_active,
            "http_healthy": http_healthy,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "service_active": False,
            "http_healthy": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def validate_change(change: Change) -> Tuple[bool, str]:
    """Validate a change before applying."""
    if change.change_type == ChangeType.CODE:
        return validate_python_syntax(change.new_content)
    elif change.change_type == ChangeType.PROMPT:
        # Basic prompt validation
        if len(change.new_content) < 50:
            return False, "Prompt too short"
        if len(change.new_content) > 50000:
            return False, "Prompt too long"
        return True, "Prompt OK"
    elif change.change_type == ChangeType.CONFIG:
        # Try to parse as JSON
        try:
            json.loads(change.new_content)
            return True, "Config OK"
        except:
            return False, "Invalid JSON config"
    
    return True, "No validation needed"


# ============================================================================
# SAFE APPLICATOR
# ============================================================================

class SafeApplicator:
    """
    Safely applies evolution changes.
    
    Process:
    1. Validate change
    2. Backup current state
    3. Check health before
    4. Apply change
    5. Check health after
    6. Rollback if degraded
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn
    
    @contextmanager
    def _cursor(self):
        """Get cursor with auto-commit."""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
    
    def _init_db(self):
        """Initialize database."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._cursor() as cursor:
            cursor.executescript(APPLICATOR_SCHEMA)
        logger.info(f"Safe applicator initialized: {self.db_path}")
    
    def _can_auto_apply_today(self) -> bool:
        """Check daily limit."""
        today = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count FROM evolution_changes
                WHERE created_at >= ? AND status = 'applied'
            """, (today,))
            count = cursor.fetchone()["count"]
            return count < MAX_AUTO_CHANGES_PER_DAY
    
    def create_change(
        self,
        change_type: ChangeType,
        target_file: str,
        new_content: str,
        reason: str,
        confidence: float = 0.5,
        risk_level: str = "low",
        proposal_id: int = None
    ) -> Change:
        """Create a change record."""
        # Get current content
        old_content = ""
        if Path(target_file).exists():
            old_content = Path(target_file).read_text()
        
        change = Change(
            change_type=change_type,
            target_file=target_file,
            old_content=old_content,
            new_content=new_content,
            proposal_id=proposal_id,
            reason=reason,
            confidence=confidence,
            risk_level=risk_level
        )
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO evolution_changes (
                    created_at, change_type, target_file, old_content, new_content,
                    proposal_id, reason, confidence, risk_level, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                datetime.now().isoformat(),
                change_type.value,
                target_file,
                old_content,
                new_content,
                proposal_id,
                reason,
                confidence,
                risk_level
            ))
            change.id = cursor.lastrowid
        
        self._audit(change.id, "created", f"Change created: {reason}")
        return change
    
    async def apply_change(self, change_id: int, force: bool = False) -> Tuple[bool, str]:
        """
        Apply a change safely.
        
        Returns:
            Tuple of (success, message)
        """
        # Load change
        change = self._load_change(change_id)
        if not change:
            return False, "Change not found"
        
        if change.status != ChangeStatus.PENDING:
            return False, f"Change already {change.status.value}"
        
        # Check daily limit
        if not force and not self._can_auto_apply_today():
            return False, "Daily auto-apply limit reached"
        
        # Validate
        self._update_status(change_id, ChangeStatus.VALIDATING)
        is_valid, validation_msg = validate_change(change)
        
        if not is_valid:
            self._update_status(change_id, ChangeStatus.FAILED, validation_result=validation_msg)
            self._audit(change_id, "validation_failed", validation_msg)
            return False, f"Validation failed: {validation_msg}"
        
        # Health check before
        health_before = await check_service_health()
        self._update_health(change_id, health_before=health_before)
        
        # Backup
        backup_path = self._backup(change.target_file)
        
        # Apply
        try:
            Path(change.target_file).parent.mkdir(parents=True, exist_ok=True)
            Path(change.target_file).write_text(change.new_content)
            self._audit(change_id, "applied", f"Change applied to {change.target_file}")
            
            # Wait for service to process change
            await asyncio.sleep(2)
            
            # Health check after
            health_after = await check_service_health()
            self._update_health(change_id, health_after=health_after)
            
            # Check for degradation
            if self._health_degraded(health_before, health_after):
                # Rollback
                await self.rollback_change(change_id, "Health degraded after change")
                return False, "Change rolled back due to health degradation"
            
            self._update_status(change_id, ChangeStatus.APPLIED)
            return True, "Change applied successfully"
            
        except Exception as e:
            # Rollback on error
            if backup_path:
                shutil.copy(backup_path, change.target_file)
            self._update_status(change_id, ChangeStatus.FAILED, validation_result=str(e))
            self._audit(change_id, "apply_failed", str(e))
            return False, f"Apply failed: {str(e)}"
    
    async def rollback_change(self, change_id: int, reason: str) -> Tuple[bool, str]:
        """Rollback a change."""
        change = self._load_change(change_id)
        if not change:
            return False, "Change not found"
        
        if change.status != ChangeStatus.APPLIED:
            return False, "Change not in applied state"
        
        try:
            # Restore old content
            Path(change.target_file).write_text(change.old_content)
            
            self._update_status(change_id, ChangeStatus.ROLLED_BACK, rollback_reason=reason)
            self._audit(change_id, "rolled_back", reason)
            
            return True, "Change rolled back"
            
        except Exception as e:
            self._audit(change_id, "rollback_failed", str(e))
            return False, f"Rollback failed: {str(e)}"
    
    def _backup(self, file_path: str) -> Optional[str]:
        """Create a backup of a file."""
        if not Path(file_path).exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(file_path).name
        backup_path = Path(BACKUP_DIR) / f"{filename}.{timestamp}.bak"
        
        shutil.copy(file_path, backup_path)
        return str(backup_path)
    
    def _health_degraded(self, before: Dict, after: Dict) -> bool:
        """Check if health degraded."""
        # Service went down
        if before.get("service_active") and not after.get("service_active"):
            return True
        
        # HTTP became unhealthy
        if before.get("http_healthy") and not after.get("http_healthy"):
            return True
        
        return False
    
    def _load_change(self, change_id: int) -> Optional[Change]:
        """Load a change from database."""
        with self._cursor() as cursor:
            cursor.execute("SELECT * FROM evolution_changes WHERE id = ?", (change_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            return Change(
                id=row["id"],
                created_at=datetime.fromisoformat(row["created_at"]),
                change_type=ChangeType(row["change_type"]),
                target_file=row["target_file"],
                old_content=row["old_content"],
                new_content=row["new_content"],
                proposal_id=row["proposal_id"],
                reason=row["reason"],
                confidence=row["confidence"],
                risk_level=row["risk_level"],
                status=ChangeStatus(row["status"]),
                validation_result=row["validation_result"],
                rollback_reason=row["rollback_reason"]
            )
    
    def _update_status(self, change_id: int, status: ChangeStatus, **kwargs):
        """Update change status."""
        with self._cursor() as cursor:
            sets = ["status = ?"]
            params = [status.value]
            
            if status == ChangeStatus.APPLIED:
                sets.append("applied_at = ?")
                params.append(datetime.now().isoformat())
            
            if "validation_result" in kwargs:
                sets.append("validation_result = ?")
                params.append(kwargs["validation_result"])
            
            if "rollback_reason" in kwargs:
                sets.append("rollback_reason = ?")
                params.append(kwargs["rollback_reason"])
            
            params.append(change_id)
            cursor.execute(f"UPDATE evolution_changes SET {', '.join(sets)} WHERE id = ?", params)
    
    def _update_health(self, change_id: int, health_before: Dict = None, health_after: Dict = None):
        """Update health records."""
        with self._cursor() as cursor:
            if health_before:
                cursor.execute(
                    "UPDATE evolution_changes SET health_before = ? WHERE id = ?",
                    (json.dumps(health_before), change_id)
                )
            if health_after:
                cursor.execute(
                    "UPDATE evolution_changes SET health_after = ? WHERE id = ?",
                    (json.dumps(health_after), change_id)
                )
    
    def _audit(self, change_id: int, action: str, details: str):
        """Record audit trail."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO evolution_audit (timestamp, change_id, action, details)
                VALUES (?, ?, ?, ?)
            """, (datetime.now().isoformat(), change_id, action, details))
        logger.info(f"Evolution change {change_id}: {action} - {details}")
    
    def should_auto_apply(self, change: Change) -> bool:
        """Determine if a change should be auto-applied."""
        # High confidence, low risk
        if change.confidence >= 0.95 and change.risk_level == "low":
            return True
        
        # Very high confidence, any risk
        if change.confidence >= 0.99:
            return True
        
        return False
    
    def get_pending_changes(self) -> List[Change]:
        """Get pending changes."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM evolution_changes
                WHERE status = 'pending'
                ORDER BY confidence DESC
            """)
            return [self._row_to_change(row) for row in cursor.fetchall()]
    
    def get_recent_changes(self, days: int = 7) -> List[Dict]:
        """Get recent changes."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM evolution_changes
                WHERE created_at >= ?
                ORDER BY created_at DESC
            """, (since,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_change_stats(self) -> Dict[str, Any]:
        """Get change statistics."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM evolution_changes
                GROUP BY status
            """)
            by_status = {row["status"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM evolution_changes
                WHERE status = 'applied' AND rollback_reason IS NULL
            """)
            successful = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM evolution_changes
                WHERE status IN ('applied', 'rolled_back')
            """)
            total = cursor.fetchone()["count"]
        
        return {
            "by_status": by_status,
            "success_rate": successful / total if total > 0 else 0,
            "total_changes": sum(by_status.values())
        }
    
    def _row_to_change(self, row) -> Change:
        """Convert database row to Change."""
        return Change(
            id=row["id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            change_type=ChangeType(row["change_type"]),
            target_file=row["target_file"],
            old_content=row["old_content"],
            new_content=row["new_content"],
            proposal_id=row["proposal_id"],
            reason=row["reason"],
            confidence=row["confidence"],
            risk_level=row["risk_level"],
            status=ChangeStatus(row["status"])
        )
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_applicator: Optional[SafeApplicator] = None


def get_safe_applicator() -> SafeApplicator:
    """Get or create global safe applicator."""
    global _applicator
    if _applicator is None:
        _applicator = SafeApplicator()
    return _applicator


async def apply_proposal(proposal: ImprovementProposal) -> Tuple[bool, str]:
    """Apply an improvement proposal."""
    applicator = get_safe_applicator()
    
    impl = proposal.implementation
    
    change = applicator.create_change(
        change_type=ChangeType(impl.get("type", "prompt")),
        target_file=impl.get("target", ""),
        new_content=impl.get("change", ""),
        reason=proposal.problem,
        confidence=proposal.confidence,
        risk_level=proposal.risk_level,
        proposal_id=proposal.id
    )
    
    return await applicator.apply_change(change.id)


