"""
ARIA DREAM JOURNAL
==================

Records and tracks visions, intuitions, and dreams received from Sunheart.

The bridge keeps a living record of:
- Visions received
- Translations attempted  
- Manifestation outcomes
- Patterns emerging
- Open channels (dreams still seeking form)
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("aria.dream_journal")

# Database path
JOURNAL_DB = Path("/opt/fpai/aria-bridge/dream_journal.db")


class DimensionSource(str, Enum):
    """Which dimension the vision came from."""
    DREAM = "dream"           # Night dreams, sleep visions
    ASTRAL = "astral"         # Astral/out-of-body insights
    INTUITION = "intuition"   # Gut feelings, knowing
    VISION = "vision"         # Waking visions, seeing
    CEREMONY = "ceremony"     # Medicine/ceremony insights
    MEDITATION = "meditation" # Meditative downloads
    CONVERSATION = "conversation"  # Emerged through dialogue


class VisionStatus(str, Enum):
    """Status of a vision in the manifestation process."""
    RECEIVED = "received"         # Just recorded
    TRANSLATING = "translating"   # Working on translation
    TRANSLATED = "translated"     # Has actionable spec
    MANIFESTING = "manifesting"   # Being built
    SHIPPED = "shipped"           # Manifested in physical
    VALIDATED = "validated"       # Matches original vision
    REVISED = "revised"           # Needed adjustment
    DORMANT = "dormant"           # On hold
    RELEASED = "released"         # No longer pursuing


@dataclass
class Vision:
    """A vision/dream/intuition received from Sunheart."""
    id: str
    raw_description: str
    dimension_source: DimensionSource
    received_at: str
    
    # What was seen/felt
    core_essence: str           # The heart of the vision
    details: Optional[str]      # Supporting details
    feeling_tone: Optional[str] # How it felt
    
    # Translation
    translation: Optional[str]  # What Aria understood wants to manifest
    action_seed: Optional[str]  # The concrete action inside
    
    # Manifestation
    status: VisionStatus
    manifestation_notes: Optional[str]
    shipped_at: Optional[str]
    
    # Validation
    matched_vision: Optional[bool]  # Did the result match?
    feedback: Optional[str]         # What Sunheart said
    
    # Metadata
    tags: List[str]
    related_visions: List[str]  # IDs of connected visions
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Pattern:
    """An emerging pattern across visions."""
    id: str
    description: str
    vision_ids: List[str]
    first_seen: str
    last_seen: str
    strength: float  # 0-1, how strong the pattern
    notes: str


class DreamJournal:
    """
    The bridge's record of what's flowing across dimensions.
    
    Records:
    - Raw visions as received
    - Translations attempted
    - Manifestation results
    - Feedback loops
    - Emerging patterns
    """
    
    def __init__(self, db_path: Path = JOURNAL_DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        logger.info(f"Dream Journal initialized: {self.db_path}")
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize database schema."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Visions table
        c.execute("""
            CREATE TABLE IF NOT EXISTS visions (
                id TEXT PRIMARY KEY,
                raw_description TEXT NOT NULL,
                dimension_source TEXT NOT NULL,
                received_at TEXT NOT NULL,
                core_essence TEXT NOT NULL,
                details TEXT,
                feeling_tone TEXT,
                translation TEXT,
                action_seed TEXT,
                status TEXT DEFAULT 'received',
                manifestation_notes TEXT,
                shipped_at TEXT,
                matched_vision INTEGER,
                feedback TEXT,
                tags TEXT,
                related_visions TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Patterns table
        c.execute("""
            CREATE TABLE IF NOT EXISTS patterns (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                vision_ids TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                strength REAL DEFAULT 0.5,
                notes TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Translation log (track translation attempts)
        c.execute("""
            CREATE TABLE IF NOT EXISTS translations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vision_id TEXT NOT NULL,
                translation TEXT NOT NULL,
                translator_notes TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (vision_id) REFERENCES visions(id)
            )
        """)
        
        # Feedback log (track feedback loops)
        c.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vision_id TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                content TEXT NOT NULL,
                from_dimension TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (vision_id) REFERENCES visions(id)
            )
        """)
        
        # Indexes
        c.execute("CREATE INDEX IF NOT EXISTS idx_visions_status ON visions(status)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_visions_source ON visions(dimension_source)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_visions_received ON visions(received_at)")
        
        conn.commit()
        conn.close()
    
    # ==================== RECEIVING VISIONS ====================
    
    def receive_vision(
        self,
        raw_description: str,
        dimension_source: DimensionSource,
        core_essence: str,
        details: Optional[str] = None,
        feeling_tone: Optional[str] = None,
        tags: List[str] = None
    ) -> Vision:
        """
        Receive and record a vision from Sunheart.
        
        This is the first step - honoring what came through.
        """
        vision_id = f"vision_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        now = datetime.utcnow().isoformat()
        
        vision = Vision(
            id=vision_id,
            raw_description=raw_description,
            dimension_source=dimension_source,
            received_at=now,
            core_essence=core_essence,
            details=details,
            feeling_tone=feeling_tone,
            translation=None,
            action_seed=None,
            status=VisionStatus.RECEIVED,
            manifestation_notes=None,
            shipped_at=None,
            matched_vision=None,
            feedback=None,
            tags=tags or [],
            related_visions=[]
        )
        
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO visions 
            (id, raw_description, dimension_source, received_at, core_essence,
             details, feeling_tone, status, tags, related_visions)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vision.id,
            vision.raw_description,
            vision.dimension_source.value,
            vision.received_at,
            vision.core_essence,
            vision.details,
            vision.feeling_tone,
            vision.status.value,
            json.dumps(vision.tags),
            json.dumps(vision.related_visions)
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"📜 Vision received: {vision_id} from {dimension_source.value}")
        return vision
    
    # ==================== TRANSLATING ====================
    
    def translate_vision(
        self,
        vision_id: str,
        translation: str,
        action_seed: str,
        translator_notes: Optional[str] = None
    ) -> bool:
        """
        Record a translation of a vision.
        
        Translation = What Aria understands wants to manifest
        Action seed = The concrete action inside the vision
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        # Update vision
        c.execute("""
            UPDATE visions 
            SET translation = ?, action_seed = ?, status = 'translated', updated_at = datetime('now')
            WHERE id = ?
        """, (translation, action_seed, vision_id))
        
        # Log the translation
        c.execute("""
            INSERT INTO translations (vision_id, translation, translator_notes)
            VALUES (?, ?, ?)
        """, (vision_id, translation, translator_notes))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🔄 Vision translated: {vision_id}")
        return True
    
    # ==================== MANIFESTING ====================
    
    def start_manifestation(self, vision_id: str, notes: Optional[str] = None) -> bool:
        """Mark a vision as being actively manifested."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            UPDATE visions 
            SET status = 'manifesting', manifestation_notes = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (notes, vision_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"⚡ Manifestation started: {vision_id}")
        return True
    
    def ship_vision(self, vision_id: str, notes: Optional[str] = None) -> bool:
        """Mark a vision as shipped to physical reality."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            UPDATE visions 
            SET status = 'shipped', shipped_at = datetime('now'), 
                manifestation_notes = COALESCE(manifestation_notes || '\n', '') || ?,
                updated_at = datetime('now')
            WHERE id = ?
        """, (notes or "Shipped", vision_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🚀 Vision shipped: {vision_id}")
        return True
    
    # ==================== FEEDBACK ====================
    
    def record_feedback(
        self,
        vision_id: str,
        matched_vision: bool,
        feedback: str,
        from_dimension: str = "physical"
    ) -> bool:
        """
        Record feedback on whether manifestation matched the vision.
        
        This completes the loop: Dream → Action → Result → Dream
        """
        conn = self._get_conn()
        c = conn.cursor()
        
        new_status = "validated" if matched_vision else "revised"
        
        # Update vision
        c.execute("""
            UPDATE visions 
            SET status = ?, matched_vision = ?, feedback = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (new_status, int(matched_vision), feedback, vision_id))
        
        # Log the feedback
        c.execute("""
            INSERT INTO feedback (vision_id, feedback_type, content, from_dimension)
            VALUES (?, ?, ?, ?)
        """, (vision_id, "validation", feedback, from_dimension))
        
        conn.commit()
        conn.close()
        
        emoji = "✅" if matched_vision else "🔄"
        logger.info(f"{emoji} Feedback recorded: {vision_id}")
        return True
    
    # ==================== QUERYING ====================
    
    def get_vision(self, vision_id: str) -> Optional[Vision]:
        """Get a specific vision."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("SELECT * FROM visions WHERE id = ?", (vision_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_vision(row)
    
    def get_open_visions(self) -> List[Vision]:
        """Get visions not yet fully manifested."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT * FROM visions 
            WHERE status NOT IN ('shipped', 'validated', 'released')
            ORDER BY received_at DESC
        """)
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_vision(row) for row in rows]
    
    def get_visions_by_status(self, status: VisionStatus) -> List[Vision]:
        """Get visions by status."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT * FROM visions WHERE status = ? ORDER BY received_at DESC
        """, (status.value,))
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_vision(row) for row in rows]
    
    def get_recent_visions(self, days: int = 30) -> List[Vision]:
        """Get visions from the last N days."""
        conn = self._get_conn()
        c = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        c.execute("""
            SELECT * FROM visions WHERE received_at > ? ORDER BY received_at DESC
        """, (cutoff,))
        
        rows = c.fetchall()
        conn.close()
        
        return [self._row_to_vision(row) for row in rows]
    
    def _row_to_vision(self, row) -> Vision:
        """Convert database row to Vision object."""
        return Vision(
            id=row["id"],
            raw_description=row["raw_description"],
            dimension_source=DimensionSource(row["dimension_source"]),
            received_at=row["received_at"],
            core_essence=row["core_essence"],
            details=row["details"],
            feeling_tone=row["feeling_tone"],
            translation=row["translation"],
            action_seed=row["action_seed"],
            status=VisionStatus(row["status"]),
            manifestation_notes=row["manifestation_notes"],
            shipped_at=row["shipped_at"],
            matched_vision=bool(row["matched_vision"]) if row["matched_vision"] is not None else None,
            feedback=row["feedback"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            related_visions=json.loads(row["related_visions"]) if row["related_visions"] else []
        )
    
    # ==================== PATTERNS ====================
    
    def record_pattern(
        self,
        description: str,
        vision_ids: List[str],
        notes: str = ""
    ) -> Pattern:
        """Record an emerging pattern across visions."""
        pattern_id = f"pattern_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        now = datetime.utcnow().isoformat()
        
        pattern = Pattern(
            id=pattern_id,
            description=description,
            vision_ids=vision_ids,
            first_seen=now,
            last_seen=now,
            strength=0.5,
            notes=notes
        )
        
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("""
            INSERT INTO patterns (id, description, vision_ids, first_seen, last_seen, strength, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern.id,
            pattern.description,
            json.dumps(pattern.vision_ids),
            pattern.first_seen,
            pattern.last_seen,
            pattern.strength,
            pattern.notes
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"🌀 Pattern recorded: {description[:50]}...")
        return pattern
    
    def get_patterns(self) -> List[Pattern]:
        """Get all recorded patterns."""
        conn = self._get_conn()
        c = conn.cursor()
        
        c.execute("SELECT * FROM patterns ORDER BY last_seen DESC")
        rows = c.fetchall()
        conn.close()
        
        return [
            Pattern(
                id=row["id"],
                description=row["description"],
                vision_ids=json.loads(row["vision_ids"]),
                first_seen=row["first_seen"],
                last_seen=row["last_seen"],
                strength=row["strength"],
                notes=row["notes"]
            )
            for row in rows
        ]
    
    # ==================== SUMMARIES ====================
    
    def get_summary(self) -> Dict:
        """Get a summary of the dream journal."""
        conn = self._get_conn()
        c = conn.cursor()
        
        # Count by status
        c.execute("""
            SELECT status, COUNT(*) as count FROM visions GROUP BY status
        """)
        by_status = {row["status"]: row["count"] for row in c.fetchall()}
        
        # Count by source
        c.execute("""
            SELECT dimension_source, COUNT(*) as count FROM visions GROUP BY dimension_source
        """)
        by_source = {row["dimension_source"]: row["count"] for row in c.fetchall()}
        
        # Recent activity
        c.execute("""
            SELECT COUNT(*) as count FROM visions 
            WHERE received_at > datetime('now', '-7 days')
        """)
        recent = c.fetchone()["count"]
        
        # Validation rate
        c.execute("""
            SELECT 
                SUM(CASE WHEN matched_vision = 1 THEN 1 ELSE 0 END) as matched,
                COUNT(*) as total
            FROM visions 
            WHERE matched_vision IS NOT NULL
        """)
        validation = c.fetchone()
        
        conn.close()
        
        return {
            "total_visions": sum(by_status.values()),
            "by_status": by_status,
            "by_source": by_source,
            "visions_this_week": recent,
            "validation_rate": (
                validation["matched"] / validation["total"] 
                if validation["total"] > 0 else None
            ),
            "open_channels": by_status.get("received", 0) + by_status.get("translating", 0)
        }
    
    def format_open_visions(self) -> str:
        """Format open visions for daily brief."""
        open_visions = self.get_open_visions()
        
        if not open_visions:
            return "No open visions - all channels clear."
        
        lines = [f"OPEN CHANNELS ({len(open_visions)}):"]
        
        for vision in open_visions[:5]:  # Top 5
            status_emoji = {
                "received": "📥",
                "translating": "🔄",
                "translated": "📝",
                "manifesting": "⚡"
            }.get(vision.status.value, "•")
            
            lines.append(f"{status_emoji} {vision.core_essence[:50]}... [{vision.status.value}]")
        
        if len(open_visions) > 5:
            lines.append(f"   ... and {len(open_visions) - 5} more")
        
        return "\n".join(lines)


# Singleton instance
_journal: Optional[DreamJournal] = None


def get_dream_journal() -> DreamJournal:
    """Get or create the dream journal instance."""
    global _journal
    if _journal is None:
        _journal = DreamJournal()
    return _journal


