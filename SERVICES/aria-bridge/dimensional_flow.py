"""
ARIA DIMENSIONAL FLOW
=====================

Tracks the flow of energy/intention across dimensions.
Ensures nothing stays stuck in one place.

The goal: Vision flows to action flows to proof flows back to vision.
Nothing gets lost. Everything cycles.
"""

import logging
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
import sqlite3
from pathlib import Path

from dream_journal import get_dream_journal, VisionStatus
from feedback_loop import get_feedback_loop

logger = logging.getLogger("aria.flow")

# Database for flow tracking
FLOW_DB = Path("/opt/fpai/aria-bridge/dimensional_flow.db")


class FlowState(str, Enum):
    """States of flow."""
    FLOWING = "flowing"       # Moving smoothly
    SLOW = "slow"             # Moving but slowly
    STUCK = "stuck"           # Not moving
    BLOCKED = "blocked"       # Cannot move
    COMPLETE = "complete"     # Cycle completed


class Dimension(str, Enum):
    """The dimensions Aria bridges."""
    DREAM_ASTRAL = "dream_astral"
    INTUITIVE = "intuitive"
    MENTAL = "mental"
    DIGITAL = "digital"
    PHYSICAL = "physical"
    RELATIONAL = "relational"


@dataclass
class FlowItem:
    """An item flowing through dimensions."""
    id: str
    name: str
    description: str
    
    # Position
    current_dimension: Dimension
    previous_dimension: Optional[Dimension]
    
    # Flow state
    state: FlowState
    entered_current: str  # When it entered current dimension
    time_in_current_hours: float
    
    # Links
    vision_id: Optional[str]
    feedback_ids: List[str]
    
    # Metadata
    priority: str  # t1, t2, t3
    stuck_reason: Optional[str]
    next_action: Optional[str]


@dataclass
class DimensionalReport:
    """Report on dimensional flow health."""
    timestamp: str
    
    # Flow metrics
    total_items: int
    flowing: int
    stuck: int
    blocked: int
    
    # By dimension
    by_dimension: Dict[str, Dict]
    
    # Alerts
    stuck_items: List[str]
    blocked_items: List[str]
    
    # Health score
    flow_health: float  # 0-1


class DimensionalFlow:
    """
    Tracks and ensures flow across dimensions.
    
    Nothing stays stuck. Everything cycles.
    Vision → Action → Result → Vision
    """
    
    def __init__(self, db_path: Path = FLOW_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.journal = get_dream_journal()
        self.feedback = get_feedback_loop()
        self._init_db()
        logger.info(f"DimensionalFlow initialized: {self.db_path}")
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Flow items
        c.execute("""
            CREATE TABLE IF NOT EXISTS flow_items (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                current_dimension TEXT NOT NULL,
                previous_dimension TEXT,
                state TEXT DEFAULT 'flowing',
                entered_current TEXT NOT NULL,
                vision_id TEXT,
                feedback_ids TEXT,
                priority TEXT DEFAULT 't2',
                stuck_reason TEXT,
                next_action TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Flow transitions (history)
        c.execute("""
            CREATE TABLE IF NOT EXISTS transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                from_dimension TEXT NOT NULL,
                to_dimension TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (item_id) REFERENCES flow_items(id)
            )
        """)
        
        # Stuck alerts
        c.execute("""
            CREATE TABLE IF NOT EXISTS stuck_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                dimension TEXT NOT NULL,
                hours_stuck REAL,
                alert_sent INTEGER DEFAULT 0,
                resolved INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (item_id) REFERENCES flow_items(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ==================== TRACKING FLOW ====================
    
    def create_flow_item(
        self,
        name: str,
        description: str,
        starting_dimension: Dimension,
        vision_id: Optional[str] = None,
        priority: str = "t2"
    ) -> FlowItem:
        """Create a new item to track through dimensions."""
        item_id = f"flow_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        now = datetime.utcnow().isoformat()
        
        item = FlowItem(
            id=item_id,
            name=name,
            description=description,
            current_dimension=starting_dimension,
            previous_dimension=None,
            state=FlowState.FLOWING,
            entered_current=now,
            time_in_current_hours=0,
            vision_id=vision_id,
            feedback_ids=[],
            priority=priority,
            stuck_reason=None,
            next_action=None
        )
        
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO flow_items 
            (id, name, description, current_dimension, state, entered_current, 
             vision_id, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item.id, item.name, item.description, 
            item.current_dimension.value, item.state.value,
            item.entered_current, item.vision_id, item.priority
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📍 Flow item created: {name} in {starting_dimension.value}")
        return item
    
    def move_to_dimension(
        self,
        item_id: str,
        to_dimension: Dimension,
        notes: Optional[str] = None
    ) -> bool:
        """Move an item to a new dimension."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Get current state
        c.execute("SELECT * FROM flow_items WHERE id = ?", (item_id,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            return False
        
        from_dimension = row["current_dimension"]
        now = datetime.utcnow().isoformat()
        
        # Update item
        c.execute("""
            UPDATE flow_items 
            SET current_dimension = ?, previous_dimension = ?, 
                entered_current = ?, state = 'flowing', stuck_reason = NULL,
                updated_at = datetime('now')
            WHERE id = ?
        """, (to_dimension.value, from_dimension, now, item_id))
        
        # Record transition
        c.execute("""
            INSERT INTO transitions (item_id, from_dimension, to_dimension, timestamp, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (item_id, from_dimension, to_dimension.value, now, notes))
        
        # Resolve any stuck alerts
        c.execute("""
            UPDATE stuck_alerts SET resolved = 1 WHERE item_id = ? AND resolved = 0
        """, (item_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"➡️ Flow: {item_id} moved {from_dimension} → {to_dimension.value}")
        return True
    
    def mark_stuck(
        self,
        item_id: str,
        reason: str,
        next_action: Optional[str] = None
    ) -> bool:
        """Mark an item as stuck."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            UPDATE flow_items 
            SET state = 'stuck', stuck_reason = ?, next_action = ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (reason, next_action, item_id))
        
        # Get dimension for alert
        c.execute("SELECT current_dimension, entered_current FROM flow_items WHERE id = ?", (item_id,))
        row = c.fetchone()
        
        if row:
            entered = datetime.fromisoformat(row["entered_current"])
            hours = (datetime.utcnow() - entered).total_seconds() / 3600
            
            c.execute("""
                INSERT INTO stuck_alerts (item_id, dimension, hours_stuck)
                VALUES (?, ?, ?)
            """, (item_id, row["current_dimension"], hours))
        
        conn.commit()
        conn.close()
        
        logger.warning(f"⚠️ Flow stuck: {item_id} - {reason}")
        return True
    
    def complete_flow(self, item_id: str) -> bool:
        """Mark a flow item as complete (full cycle done)."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            UPDATE flow_items 
            SET state = 'complete', updated_at = datetime('now')
            WHERE id = ?
        """, (item_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Flow complete: {item_id}")
        return True
    
    # ==================== CHECKING FLOW ====================
    
    def check_stuck_items(self, max_hours: float = 48) -> List[FlowItem]:
        """Find items that have been in one dimension too long."""
        conn = self._get_conn()
        c = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(hours=max_hours)).isoformat()
        
        c.execute("""
            SELECT * FROM flow_items 
            WHERE state NOT IN ('complete', 'blocked')
            AND entered_current < ?
            ORDER BY entered_current ASC
        """, (cutoff,))
        
        rows = c.fetchall()
        conn.close()
        
        stuck = []
        for row in rows:
            item = self._row_to_item(row)
            item.state = FlowState.STUCK
            stuck.append(item)
        
        return stuck
    
    def get_flow_report(self) -> DimensionalReport:
        """Generate a comprehensive flow report."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Count by state
        c.execute("""
            SELECT state, COUNT(*) as count FROM flow_items GROUP BY state
        """)
        by_state = {row["state"]: row["count"] for row in c.fetchall()}
        
        # Count by dimension
        c.execute("""
            SELECT current_dimension, state, COUNT(*) as count 
            FROM flow_items 
            WHERE state != 'complete'
            GROUP BY current_dimension, state
        """)
        
        by_dimension = {}
        for row in c.fetchall():
            dim = row["current_dimension"]
            if dim not in by_dimension:
                by_dimension[dim] = {"total": 0, "stuck": 0, "flowing": 0}
            by_dimension[dim]["total"] += row["count"]
            by_dimension[dim][row["state"]] = row["count"]
        
        # Get stuck/blocked items
        stuck_items = self.check_stuck_items(24)
        c.execute("SELECT id FROM flow_items WHERE state = 'blocked'")
        blocked_ids = [row["id"] for row in c.fetchall()]
        
        conn.close()
        
        # Calculate health
        total = sum(by_state.values()) or 1
        stuck = by_state.get("stuck", 0) + by_state.get("blocked", 0)
        health = 1 - (stuck / total)
        
        return DimensionalReport(
            timestamp=datetime.utcnow().isoformat(),
            total_items=total,
            flowing=by_state.get("flowing", 0),
            stuck=by_state.get("stuck", 0),
            blocked=by_state.get("blocked", 0),
            by_dimension=by_dimension,
            stuck_items=[item.name for item in stuck_items],
            blocked_items=blocked_ids,
            flow_health=health
        )
    
    def _row_to_item(self, row) -> FlowItem:
        """Convert row to FlowItem."""
        entered = datetime.fromisoformat(row["entered_current"])
        hours = (datetime.utcnow() - entered).total_seconds() / 3600
        
        return FlowItem(
            id=row["id"],
            name=row["name"],
            description=row["description"] or "",
            current_dimension=Dimension(row["current_dimension"]),
            previous_dimension=Dimension(row["previous_dimension"]) if row["previous_dimension"] else None,
            state=FlowState(row["state"]),
            entered_current=row["entered_current"],
            time_in_current_hours=hours,
            vision_id=row["vision_id"],
            feedback_ids=json.loads(row["feedback_ids"]) if row["feedback_ids"] else [],
            priority=row["priority"],
            stuck_reason=row["stuck_reason"],
            next_action=row["next_action"]
        )
    
    # ==================== SYNCING WITH JOURNAL ====================
    
    def sync_from_journal(self) -> int:
        """Create flow items from open visions in the dream journal."""
        visions = self.journal.get_open_visions()
        created = 0
        
        for vision in visions:
            # Check if we already track this
            conn = self._get_conn()
            c = conn.cursor()
            c.execute("SELECT id FROM flow_items WHERE vision_id = ?", (vision.id,))
            existing = c.fetchone()
            conn.close()
            
            if existing:
                continue
            
            # Determine dimension based on status
            if vision.status == VisionStatus.RECEIVED:
                dim = Dimension.DREAM_ASTRAL
            elif vision.status in [VisionStatus.TRANSLATING, VisionStatus.TRANSLATED]:
                dim = Dimension.MENTAL
            elif vision.status == VisionStatus.MANIFESTING:
                dim = Dimension.DIGITAL
            else:
                dim = Dimension.DREAM_ASTRAL
            
            self.create_flow_item(
                name=vision.core_essence[:50],
                description=vision.raw_description[:200],
                starting_dimension=dim,
                vision_id=vision.id,
                priority="t2"
            )
            created += 1
        
        if created > 0:
            logger.info(f"📥 Synced {created} visions to flow tracking")
        
        return created
    
    # ==================== FORMATTING ====================
    
    def format_flow_status(self) -> str:
        """Format flow status for display."""
        report = self.get_flow_report()
        
        lines = [
            "**🌊 Dimensional Flow**\n",
            f"**Health:** {report.flow_health:.0%}",
            f"**Items:** {report.total_items} total, {report.flowing} flowing, {report.stuck} stuck",
        ]
        
        if report.by_dimension:
            lines.append("\n**By Dimension:**")
            for dim, counts in report.by_dimension.items():
                emoji = {
                    "dream_astral": "🌙",
                    "intuitive": "💫", 
                    "mental": "🧠",
                    "digital": "💻",
                    "physical": "🌍",
                    "relational": "🤝"
                }.get(dim, "•")
                lines.append(f"{emoji} {dim}: {counts['total']} ({counts.get('stuck', 0)} stuck)")
        
        if report.stuck_items:
            lines.append("\n**⚠️ Stuck Items:**")
            for item in report.stuck_items[:5]:
                lines.append(f"• {item}")
        
        if report.flow_health < 0.7:
            lines.append("\n_Flow is constricted. Review stuck items._")
        else:
            lines.append("\n_Flow is healthy. Nothing stuck._")
        
        return "\n".join(lines)


# Singleton
_flow: Optional[DimensionalFlow] = None


def get_dimensional_flow() -> DimensionalFlow:
    """Get or create dimensional flow instance."""
    global _flow
    if _flow is None:
        _flow = DimensionalFlow()
    return _flow


