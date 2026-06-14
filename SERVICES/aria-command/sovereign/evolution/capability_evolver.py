#!/usr/bin/env python3
"""
ARIA CAPABILITY EVOLVER
========================

Automatically expands Aria's capabilities based on:
- Repeated manual workarounds
- User requests for new features
- Integration opportunities

Features:
- Safe tool addition with sandbox testing
- Gradual rollout (test -> limited -> full)
- Automatic documentation
- Easy rollback
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
import re
import httpx

from .interaction_logger import get_interaction_logger
from .synthesizer import ImprovementProposal

logger = logging.getLogger("aria.evolution.capability")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")
TOOLS_FILE = os.getenv("ARIA_TOOLS_FILE", "/opt/fpai/aria-command/telegram/tools.py")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


@dataclass
class CapabilityProposal:
    """A proposed new capability."""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # What capability
    name: str = ""
    description: str = ""
    category: str = ""  # server, trading, build, utility
    
    # Evidence
    request_count: int = 0  # How many times was this requested
    sample_requests: List[str] = field(default_factory=list)
    
    # Implementation
    implementation_type: str = ""  # tool, command, shortcut, integration
    code_template: str = ""
    dependencies: List[str] = field(default_factory=list)
    
    # Assessment
    confidence: float = 0.5
    complexity: str = "low"  # low, medium, high
    risk: str = "low"
    
    # Status
    status: str = "proposed"  # proposed, testing, limited, active, disabled


CAPABILITY_SCHEMA = """
CREATE TABLE IF NOT EXISTS capability_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    request_count INTEGER DEFAULT 0,
    sample_requests TEXT,
    implementation_type TEXT,
    code_template TEXT,
    dependencies TEXT,
    confidence REAL DEFAULT 0.5,
    complexity TEXT DEFAULT 'low',
    risk TEXT DEFAULT 'low',
    status TEXT DEFAULT 'proposed'
);

CREATE INDEX IF NOT EXISTS idx_cap_status ON capability_proposals(status);
CREATE INDEX IF NOT EXISTS idx_cap_category ON capability_proposals(category);

CREATE TABLE IF NOT EXISTS capability_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    capability_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    user_id TEXT,
    success INTEGER DEFAULT 1,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_cu_cap ON capability_usage(capability_id);
CREATE INDEX IF NOT EXISTS idx_cu_timestamp ON capability_usage(timestamp);

CREATE TABLE IF NOT EXISTS capability_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_id TEXT,
    request_text TEXT,
    detected_capability TEXT,
    was_fulfilled INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cr_cap ON capability_requests(detected_capability);
"""


# ============================================================================
# CAPABILITY DETECTION
# ============================================================================

CAPABILITY_PATTERNS = {
    "file_operations": [
        r"can you (read|write|edit|create|delete) .*file",
        r"open .*file",
        r"show me .*file",
    ],
    "server_monitoring": [
        r"check (server|memory|cpu|disk)",
        r"(restart|stop|start) service",
        r"show (logs|status)",
    ],
    "trading": [
        r"(buy|sell|trade|position)",
        r"market (price|status|analysis)",
        r"(stop loss|take profit)",
    ],
    "automation": [
        r"schedule",
        r"remind me",
        r"every (day|hour|minute)",
        r"automate",
    ],
    "integration": [
        r"connect to",
        r"integrate with",
        r"sync with",
    ]
}


def detect_capability_request(message: str) -> Optional[str]:
    """Detect if a message is requesting a capability."""
    msg_lower = message.lower()
    
    # Check for "I wish" or "can you" patterns
    if not any(p in msg_lower for p in ["can you", "i wish", "please", "could you", "how do i"]):
        return None
    
    # Match against known patterns
    for capability, patterns in CAPABILITY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return capability
    
    return "unknown"


# ============================================================================
# CODE GENERATION TEMPLATES
# ============================================================================

TOOL_TEMPLATE = '''
async def {name}(self, params: Dict[str, Any], user_id: str) -> str:
    """
    {description}
    
    Parameters:
    {params_doc}
    
    Returns:
        {returns}
    """
    try:
        {implementation}
    except Exception as e:
        return f"Error in {name}: {{str(e)}}"
'''

COMMAND_TEMPLATE = '''
@command("{name}")
async def cmd_{name}(self, update, context, args):
    """
    {description}
    
    Usage: /{name} {usage}
    """
    try:
        {implementation}
        return "{success_message}"
    except Exception as e:
        return f"❌ Error: {{str(e)}}"
'''


# ============================================================================
# CAPABILITY EVOLVER
# ============================================================================

class CapabilityEvolver:
    """
    Automatically expands Aria's capabilities.
    
    Process:
    1. Detect capability requests
    2. Aggregate similar requests
    3. Generate implementation proposals
    4. Test in sandbox
    5. Gradually roll out
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
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
            cursor.executescript(CAPABILITY_SCHEMA)
        logger.info(f"Capability evolver initialized: {self.db_path}")
    
    def record_request(self, user_id: str, message: str):
        """Record a potential capability request."""
        detected = detect_capability_request(message)
        if not detected:
            return
        
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO capability_requests (timestamp, user_id, request_text, detected_capability)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                user_id,
                message[:500],
                detected
            ))
        
        # Check if we should propose this capability
        self._check_for_proposal(detected)
    
    def _check_for_proposal(self, capability: str, threshold: int = 5):
        """Check if a capability should be proposed."""
        with self._cursor() as cursor:
            # Count recent requests for this capability
            since = (datetime.now() - timedelta(days=7)).isoformat()
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM capability_requests
                WHERE detected_capability = ? AND timestamp >= ? AND was_fulfilled = 0
            """, (capability, since))
            
            count = cursor.fetchone()["count"]
            
            if count >= threshold:
                # Check if already proposed
                cursor.execute("""
                    SELECT id FROM capability_proposals
                    WHERE name LIKE ? AND status IN ('proposed', 'testing', 'limited')
                """, (f"%{capability}%",))
                
                if not cursor.fetchone():
                    # Create proposal
                    asyncio.create_task(self._create_proposal(capability))
    
    async def _create_proposal(self, capability: str):
        """Create a capability proposal using AI."""
        # Get sample requests
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT request_text FROM capability_requests
                WHERE detected_capability = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (capability,))
            samples = [row["request_text"] for row in cursor.fetchall()]
        
        # Use AI to design the capability (simplified for now)
        proposal = CapabilityProposal(
            name=capability.replace("_", " ").title().replace(" ", ""),
            description=f"Auto-generated capability for {capability}",
            category=capability,
            request_count=len(samples),
            sample_requests=samples,
            implementation_type="tool",
            confidence=0.6,
            complexity="medium"
        )
        
        self._store_proposal(proposal)
        logger.info(f"Created capability proposal: {proposal.name}")
    
    def _store_proposal(self, proposal: CapabilityProposal):
        """Store a proposal."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO capability_proposals (
                    created_at, name, description, category,
                    request_count, sample_requests, implementation_type,
                    code_template, dependencies, confidence, complexity, risk
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                proposal.name,
                proposal.description,
                proposal.category,
                proposal.request_count,
                json.dumps(proposal.sample_requests),
                proposal.implementation_type,
                proposal.code_template,
                json.dumps(proposal.dependencies),
                proposal.confidence,
                proposal.complexity,
                proposal.risk
            ))
            proposal.id = cursor.lastrowid
    
    async def evolve_from_proposal(self, proposal: ImprovementProposal) -> Optional[CapabilityProposal]:
        """
        Create a capability from an improvement proposal.
        """
        if proposal.category != "capability":
            return None
        
        impl = proposal.implementation
        if impl.get("type") not in ["tool", "command"]:
            return None
        
        cap = CapabilityProposal(
            name=impl.get("name", "NewCapability"),
            description=proposal.solution,
            category=impl.get("category", "utility"),
            implementation_type=impl.get("type", "tool"),
            code_template=impl.get("code", ""),
            confidence=proposal.confidence,
            complexity="medium" if len(impl.get("code", "")) > 500 else "low",
            risk=proposal.risk_level
        )
        
        self._store_proposal(cap)
        return cap
    
    def get_proposed_capabilities(self) -> List[CapabilityProposal]:
        """Get all proposed capabilities."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM capability_proposals
                WHERE status = 'proposed'
                ORDER BY confidence DESC, request_count DESC
            """)
            
            return [
                CapabilityProposal(
                    id=row["id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    name=row["name"],
                    description=row["description"],
                    category=row["category"],
                    request_count=row["request_count"],
                    sample_requests=json.loads(row["sample_requests"]) if row["sample_requests"] else [],
                    implementation_type=row["implementation_type"],
                    code_template=row["code_template"],
                    confidence=row["confidence"],
                    complexity=row["complexity"],
                    risk=row["risk"],
                    status=row["status"]
                )
                for row in cursor.fetchall()
            ]
    
    def get_active_capabilities(self) -> List[Dict]:
        """Get currently active auto-evolved capabilities."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM capability_proposals
                WHERE status IN ('active', 'limited')
                ORDER BY name
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_status(self, capability_id: int, status: str):
        """Update capability status."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE capability_proposals
                SET status = ?
                WHERE id = ?
            """, (status, capability_id))
    
    def record_usage(self, capability_id: int, user_id: str, success: bool, error: str = None):
        """Record capability usage."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO capability_usage (capability_id, timestamp, user_id, success, error)
                VALUES (?, ?, ?, ?, ?)
            """, (
                capability_id,
                datetime.now().isoformat(),
                user_id,
                1 if success else 0,
                error
            ))
    
    def get_capability_stats(self, capability_id: int) -> Dict[str, Any]:
        """Get usage statistics for a capability."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_uses,
                    SUM(success) as successes,
                    COUNT(DISTINCT user_id) as unique_users
                FROM capability_usage
                WHERE capability_id = ?
            """, (capability_id,))
            
            row = cursor.fetchone()
            total = row["total_uses"] or 0
            successes = row["successes"] or 0
            
            return {
                "total_uses": total,
                "success_rate": successes / total if total > 0 else 0,
                "unique_users": row["unique_users"] or 0
            }
    
    def should_disable(self, capability_id: int) -> bool:
        """Check if a capability should be disabled due to poor performance."""
        stats = self.get_capability_stats(capability_id)
        
        # Need at least 5 uses to judge
        if stats["total_uses"] < 5:
            return False
        
        # Disable if success rate < 50%
        return stats["success_rate"] < 0.5
    
    def get_request_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of capability requests."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT detected_capability, COUNT(*) as count
                FROM capability_requests
                WHERE timestamp >= ?
                GROUP BY detected_capability
                ORDER BY count DESC
            """, (since,))
            
            by_capability = {row["detected_capability"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("""
                SELECT COUNT(*) as total FROM capability_requests
                WHERE timestamp >= ?
            """, (since,))
            total = cursor.fetchone()["total"]
        
        return {
            "period_days": days,
            "total_requests": total,
            "by_capability": by_capability
        }
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_evolver: Optional[CapabilityEvolver] = None


def get_capability_evolver() -> CapabilityEvolver:
    """Get or create global capability evolver."""
    global _evolver
    if _evolver is None:
        _evolver = CapabilityEvolver()
    return _evolver


def record_capability_request(user_id: str, message: str):
    """Record a potential capability request."""
    get_capability_evolver().record_request(user_id, message)


def get_proposed_capabilities() -> List[CapabilityProposal]:
    """Get proposed capabilities."""
    return get_capability_evolver().get_proposed_capabilities()


