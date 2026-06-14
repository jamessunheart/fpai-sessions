#!/usr/bin/env python3
"""
ARIA EVOLUTION DASHBOARD API
=============================

REST API endpoints for viewing and managing Aria's self-improvement system.

Endpoints:
- GET /evolution/changes - List all applied changes
- GET /evolution/proposals - List pending proposals
- GET /evolution/patterns - Current detected patterns
- POST /evolution/rollback/{change_id} - Rollback a specific change
- POST /evolution/approve/{proposal_id} - Approve a proposal
- POST /evolution/reject/{proposal_id} - Reject a proposal
- GET /evolution/summary - Overall statistics
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
import threading

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger("aria.api.evolution")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")

router = APIRouter(prefix="/evolution", tags=["evolution"])


# ============================================================================
# MODELS
# ============================================================================

class ChangeResponse(BaseModel):
    id: int
    created_at: str
    change_type: str
    target_file: Optional[str]
    reason: str
    status: str
    applied_at: Optional[str]
    confidence: float
    risk_level: str
    rollback_reason: Optional[str]
    category: Optional[str]
    problem: Optional[str]
    solution: Optional[str]


class ProposalResponse(BaseModel):
    id: int
    created_at: str
    category: str
    problem: str
    solution: str
    confidence: float
    expected_impact: str
    risk_level: str
    status: str


class PatternResponse(BaseModel):
    id: int
    detector: str
    severity: str
    problem_description: str
    suggested_fix: str
    detected_at: str
    addressed: bool


class SummaryResponse(BaseModel):
    total_changes: int
    applied_changes: int
    rolled_back_changes: int
    pending_proposals: int
    approved_proposals: int
    rejected_proposals: int
    high_severity_patterns: int
    total_patterns: int
    improvement_rate: float  # % of proposals that improved things


class RollbackRequest(BaseModel):
    reason: Optional[str] = "Manual rollback via dashboard"


# ============================================================================
# DATABASE HELPERS
# ============================================================================

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    if not hasattr(_local, 'conn') or _local.conn is None:
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


@contextmanager
def _cursor():
    conn = _get_conn()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _ensure_tables():
    """Ensure all required tables exist."""
    with _cursor() as cursor:
        # Evolution changes table
        cursor.execute("""
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
            )
        """)
        
        # Improvement proposals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS improvement_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                category TEXT NOT NULL,
                problem TEXT,
                evidence TEXT,
                solution TEXT,
                implementation TEXT,
                confidence REAL DEFAULT 0.5,
                expected_impact TEXT DEFAULT 'medium',
                risk_level TEXT DEFAULT 'low',
                status TEXT DEFAULT 'pending',
                applied_at TEXT,
                outcome TEXT
            )
        """)
        
        # Detected patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS detected_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detector TEXT NOT NULL,
                severity TEXT NOT NULL,
                interaction_ids TEXT,
                problem_description TEXT,
                suggested_fix TEXT,
                evidence TEXT,
                detected_at TEXT NOT NULL,
                addressed INTEGER DEFAULT 0
            )
        """)
        
        # Evolution audit table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evolution_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                change_id INTEGER,
                action TEXT,
                details TEXT,
                outcome TEXT
            )
        """)


# Initialize tables on import
try:
    _ensure_tables()
except Exception as e:
    logger.error(f"Failed to initialize evolution tables: {e}")


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/changes", response_model=List[ChangeResponse])
async def get_changes(
    status: Optional[str] = Query(None, description="Filter by status: pending, applied, failed, rolled_back"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """Get list of all evolution changes with optional filtering."""
    with _cursor() as cursor:
        query = """
            SELECT 
                c.id, c.created_at, c.change_type, c.target_file, c.reason,
                c.status, c.applied_at, c.confidence, c.risk_level, c.rollback_reason,
                p.category, p.problem, p.solution
            FROM evolution_changes c
            LEFT JOIN improvement_proposals p ON c.proposal_id = p.id
        """
        params = []
        
        if status:
            query += " WHERE c.status = ?"
            params.append(status)
        
        query += " ORDER BY c.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        
        return [
            ChangeResponse(
                id=row['id'],
                created_at=row['created_at'],
                change_type=row['change_type'],
                target_file=row['target_file'],
                reason=row['reason'] or "",
                status=row['status'],
                applied_at=row['applied_at'],
                confidence=row['confidence'] or 0.5,
                risk_level=row['risk_level'] or "low",
                rollback_reason=row['rollback_reason'],
                category=row['category'],
                problem=row['problem'],
                solution=row['solution']
            )
            for row in cursor.fetchall()
        ]


@router.get("/changes/{change_id}")
async def get_change_detail(change_id: int):
    """Get detailed information about a specific change."""
    with _cursor() as cursor:
        cursor.execute("""
            SELECT 
                c.*,
                p.category, p.problem, p.evidence, p.solution, p.implementation
            FROM evolution_changes c
            LEFT JOIN improvement_proposals p ON c.proposal_id = p.id
            WHERE c.id = ?
        """, (change_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Change not found")
        
        return dict(row)


@router.get("/proposals", response_model=List[ProposalResponse])
async def get_proposals(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, applied, rejected"),
    limit: int = Query(50, ge=1, le=200)
):
    """Get list of improvement proposals."""
    with _cursor() as cursor:
        query = """
            SELECT id, created_at, category, problem, solution, 
                   confidence, expected_impact, risk_level, status
            FROM improvement_proposals
        """
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        
        return [
            ProposalResponse(
                id=row['id'],
                created_at=row['created_at'],
                category=row['category'] or "unknown",
                problem=row['problem'] or "",
                solution=row['solution'] or "",
                confidence=row['confidence'] or 0.5,
                expected_impact=row['expected_impact'] or "medium",
                risk_level=row['risk_level'] or "low",
                status=row['status'] or "pending"
            )
            for row in cursor.fetchall()
        ]


@router.get("/patterns", response_model=List[PatternResponse])
async def get_patterns(
    severity: Optional[str] = Query(None, description="Filter by severity: low, medium, high"),
    hours: int = Query(24, ge=1, le=168, description="Look back hours"),
    addressed: Optional[bool] = Query(None, description="Filter by addressed status")
):
    """Get detected patterns from recent interactions."""
    with _cursor() as cursor:
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        query = """
            SELECT id, detector, severity, problem_description, 
                   suggested_fix, detected_at, addressed
            FROM detected_patterns
            WHERE detected_at > ?
        """
        params = [since]
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
        
        if addressed is not None:
            query += " AND addressed = ?"
            params.append(1 if addressed else 0)
        
        query += " ORDER BY detected_at DESC"
        
        cursor.execute(query, params)
        
        return [
            PatternResponse(
                id=row['id'],
                detector=row['detector'],
                severity=row['severity'],
                problem_description=row['problem_description'] or "",
                suggested_fix=row['suggested_fix'] or "",
                detected_at=row['detected_at'],
                addressed=bool(row['addressed'])
            )
            for row in cursor.fetchall()
        ]


@router.post("/rollback/{change_id}")
async def rollback_change(change_id: int, request: RollbackRequest):
    """Rollback a specific applied change."""
    with _cursor() as cursor:
        # Get the change
        cursor.execute("""
            SELECT id, status, target_file, old_content, new_content
            FROM evolution_changes
            WHERE id = ?
        """, (change_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Change not found")
        
        if row['status'] != 'applied':
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot rollback change with status: {row['status']}"
            )
        
        target_file = row['target_file']
        old_content = row['old_content']
        
        if not target_file or not old_content:
            raise HTTPException(
                status_code=400,
                detail="Change does not have rollback data"
            )
        
        # Perform rollback
        try:
            with open(target_file, 'w') as f:
                f.write(old_content)
            
            # Update status
            cursor.execute("""
                UPDATE evolution_changes
                SET status = 'rolled_back', rollback_reason = ?
                WHERE id = ?
            """, (request.reason, change_id))
            
            # Audit log
            cursor.execute("""
                INSERT INTO evolution_audit (timestamp, change_id, action, details, outcome)
                VALUES (?, ?, 'rollback', ?, 'success')
            """, (datetime.now().isoformat(), change_id, request.reason))
            
            return {
                "success": True,
                "message": f"Successfully rolled back change {change_id}",
                "target_file": target_file
            }
            
        except Exception as e:
            cursor.execute("""
                INSERT INTO evolution_audit (timestamp, change_id, action, details, outcome)
                VALUES (?, ?, 'rollback', ?, ?)
            """, (datetime.now().isoformat(), change_id, request.reason, f"failed: {e}"))
            
            raise HTTPException(status_code=500, detail=f"Rollback failed: {e}")


@router.post("/approve/{proposal_id}")
async def approve_proposal(proposal_id: int):
    """Approve a pending proposal for application."""
    with _cursor() as cursor:
        cursor.execute("""
            SELECT id, status FROM improvement_proposals WHERE id = ?
        """, (proposal_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        if row['status'] != 'pending':
            raise HTTPException(
                status_code=400,
                detail=f"Proposal is not pending (status: {row['status']})"
            )
        
        cursor.execute("""
            UPDATE improvement_proposals
            SET status = 'approved'
            WHERE id = ?
        """, (proposal_id,))
        
        cursor.execute("""
            INSERT INTO evolution_audit (timestamp, change_id, action, details, outcome)
            VALUES (?, ?, 'approve', 'Manual approval via dashboard', 'success')
        """, (datetime.now().isoformat(), proposal_id))
        
        return {"success": True, "message": f"Proposal {proposal_id} approved"}


@router.post("/reject/{proposal_id}")
async def reject_proposal(proposal_id: int, reason: str = "Rejected via dashboard"):
    """Reject a pending proposal."""
    with _cursor() as cursor:
        cursor.execute("""
            SELECT id, status FROM improvement_proposals WHERE id = ?
        """, (proposal_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Proposal not found")
        
        cursor.execute("""
            UPDATE improvement_proposals
            SET status = 'rejected', outcome = ?
            WHERE id = ?
        """, (reason, proposal_id))
        
        cursor.execute("""
            INSERT INTO evolution_audit (timestamp, change_id, action, details, outcome)
            VALUES (?, ?, 'reject', ?, 'success')
        """, (datetime.now().isoformat(), proposal_id, reason))
        
        return {"success": True, "message": f"Proposal {proposal_id} rejected"}


@router.get("/summary", response_model=SummaryResponse)
async def get_summary():
    """Get overall evolution statistics."""
    with _cursor() as cursor:
        # Changes stats
        cursor.execute("SELECT COUNT(*) FROM evolution_changes")
        total_changes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM evolution_changes WHERE status = 'applied'")
        applied_changes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM evolution_changes WHERE status = 'rolled_back'")
        rolled_back = cursor.fetchone()[0]
        
        # Proposals stats
        cursor.execute("SELECT COUNT(*) FROM improvement_proposals WHERE status = 'pending'")
        pending_proposals = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM improvement_proposals WHERE status IN ('approved', 'applied')")
        approved_proposals = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM improvement_proposals WHERE status = 'rejected'")
        rejected_proposals = cursor.fetchone()[0]
        
        # Patterns stats
        since_24h = (datetime.now() - timedelta(hours=24)).isoformat()
        cursor.execute("""
            SELECT COUNT(*) FROM detected_patterns 
            WHERE detected_at > ? AND severity = 'high'
        """, (since_24h,))
        high_severity = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM detected_patterns WHERE detected_at > ?", (since_24h,))
        total_patterns = cursor.fetchone()[0]
        
        # Calculate improvement rate
        total_completed = applied_changes + rolled_back
        improvement_rate = (applied_changes / total_completed * 100) if total_completed > 0 else 0.0
        
        return SummaryResponse(
            total_changes=total_changes,
            applied_changes=applied_changes,
            rolled_back_changes=rolled_back,
            pending_proposals=pending_proposals,
            approved_proposals=approved_proposals,
            rejected_proposals=rejected_proposals,
            high_severity_patterns=high_severity,
            total_patterns=total_patterns,
            improvement_rate=round(improvement_rate, 1)
        )


@router.get("/audit")
async def get_audit_log(limit: int = Query(100, ge=1, le=500)):
    """Get evolution audit log."""
    with _cursor() as cursor:
        cursor.execute("""
            SELECT id, timestamp, change_id, action, details, outcome
            FROM evolution_audit
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        return [dict(row) for row in cursor.fetchall()]


@router.post("/analyze")
async def trigger_analysis(hours: int = Query(24, ge=1, le=168)):
    """Manually trigger pattern detection and analysis."""
    try:
        from sovereign.evolution.pattern_detectors import detect_patterns, save_patterns
        from sovereign.evolution.synthesizer import analyze_and_propose
        
        # Detect patterns
        patterns = detect_patterns(hours)
        save_patterns(patterns)
        
        # Run synthesis if high severity patterns found
        proposals = []
        high_severity = [p for p in patterns if p.severity == "high"]
        
        if high_severity:
            try:
                proposals = await analyze_and_propose(hours)
            except Exception as e:
                logger.error(f"Synthesis failed: {e}")
        
        return {
            "success": True,
            "patterns_detected": len(patterns),
            "high_severity_patterns": len(high_severity),
            "proposals_generated": len(proposals),
            "patterns": [p.to_dict() for p in patterns]
        }
        
    except Exception as e:
        logger.error(f"Analysis trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


