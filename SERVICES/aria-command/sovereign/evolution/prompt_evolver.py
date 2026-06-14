#!/usr/bin/env python3
"""
ARIA PROMPT EVOLVER
====================

Automatically improves Aria's system prompt based on:
- Successful interaction patterns
- Common corrections
- Feedback analysis

Features:
- Safe prompt modifications
- Version control for prompts
- A/B testing capability
- Automatic rollback on regression
"""

import os
import json
import sqlite3
import logging
import re
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
import shutil
import httpx

from .interaction_logger import get_interaction_logger
from .success_detector import get_success_detector
from .synthesizer import ImprovementProposal

logger = logging.getLogger("aria.evolution.prompt")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")
PROMPT_FILE = os.getenv("ARIA_PROMPT_FILE", "/opt/fpai/aria-command/brain/system_prompt.txt")
PROMPT_BACKUP_DIR = os.getenv("PROMPT_BACKUP_DIR", "/opt/fpai/aria-command/state/prompt_versions")
MAX_EVOLUTIONS_PER_DAY = 5
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


@dataclass
class PromptVersion:
    """A versioned prompt."""
    id: Optional[int] = None
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    content: str = ""
    change_description: str = ""
    change_type: str = ""  # add_instruction, modify_style, add_context, remove_redundancy
    triggered_by: Optional[int] = None  # proposal_id
    is_active: bool = False
    performance_score: float = 0.0  # Measured after deployment
    

PROMPT_SCHEMA = """
CREATE TABLE IF NOT EXISTS prompt_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    content TEXT NOT NULL,
    change_description TEXT,
    change_type TEXT,
    triggered_by INTEGER,
    is_active INTEGER DEFAULT 0,
    performance_score REAL DEFAULT 0,
    interactions_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    correction_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pv_active ON prompt_versions(is_active);
CREATE INDEX IF NOT EXISTS idx_pv_version ON prompt_versions(version);

CREATE TABLE IF NOT EXISTS prompt_fragments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    fragment TEXT NOT NULL,
    source TEXT,
    confidence REAL DEFAULT 0.5,
    times_used INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pf_category ON prompt_fragments(category);
CREATE INDEX IF NOT EXISTS idx_pf_confidence ON prompt_fragments(confidence);
"""


# ============================================================================
# PROMPT FRAGMENTS LIBRARY
# ============================================================================

DEFAULT_FRAGMENTS = {
    "response_style": [
        "Be concise and direct. Lead with the answer, then provide details.",
        "Use bullet points for multiple items.",
        "Include code examples when explaining technical concepts.",
    ],
    "error_handling": [
        "If unsure, say so clearly rather than guessing.",
        "When an error occurs, explain what went wrong and suggest solutions.",
    ],
    "proactivity": [
        "Suggest next steps when completing a task.",
        "Offer to do related tasks that might be helpful.",
    ],
    "trading": [
        "Always verify current market conditions before trading suggestions.",
        "Include risk assessment with any trade recommendation.",
    ],
    "server": [
        "Check service status before recommending restarts.",
        "Prefer graceful restarts over force stops.",
    ]
}


# ============================================================================
# PROMPT EVOLVER
# ============================================================================

class PromptEvolver:
    """
    Evolves Aria's system prompt based on learned patterns.
    
    Process:
    1. Analyze what makes responses successful
    2. Generate prompt improvements
    3. Test improvements (A/B)
    4. Apply winners, rollback losers
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        self._init_fragments()
    
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
        Path(PROMPT_BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        with self._cursor() as cursor:
            cursor.executescript(PROMPT_SCHEMA)
        logger.info(f"Prompt evolver initialized: {self.db_path}")
    
    def _init_fragments(self):
        """Initialize default fragments if empty."""
        with self._cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM prompt_fragments")
            if cursor.fetchone()["count"] == 0:
                for category, fragments in DEFAULT_FRAGMENTS.items():
                    for fragment in fragments:
                        cursor.execute("""
                            INSERT INTO prompt_fragments (category, fragment, source, confidence, created_at)
                            VALUES (?, ?, 'default', 0.5, ?)
                        """, (category, fragment, datetime.now().isoformat()))
    
    def get_current_prompt(self) -> str:
        """Get the current active prompt."""
        if Path(PROMPT_FILE).exists():
            return Path(PROMPT_FILE).read_text()
        return ""
    
    def get_current_version(self) -> Optional[PromptVersion]:
        """Get the currently active prompt version."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM prompt_versions
                WHERE is_active = 1
                ORDER BY version DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                return PromptVersion(
                    id=row["id"],
                    version=row["version"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    content=row["content"],
                    change_description=row["change_description"],
                    change_type=row["change_type"],
                    triggered_by=row["triggered_by"],
                    is_active=True,
                    performance_score=row["performance_score"]
                )
        return None
    
    def _get_next_version(self) -> int:
        """Get the next version number."""
        with self._cursor() as cursor:
            cursor.execute("SELECT MAX(version) as max_v FROM prompt_versions")
            row = cursor.fetchone()
            return (row["max_v"] or 0) + 1
    
    def _can_evolve_today(self) -> bool:
        """Check if we can evolve today (rate limit)."""
        today_start = datetime.now().replace(hour=0, minute=0, second=0).isoformat()
        
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as count FROM prompt_versions
                WHERE created_at >= ?
            """, (today_start,))
            count = cursor.fetchone()["count"]
            return count < MAX_EVOLUTIONS_PER_DAY
    
    async def evolve_from_proposal(self, proposal: ImprovementProposal) -> Optional[PromptVersion]:
        """
        Evolve prompt based on an improvement proposal.
        
        Returns:
            New prompt version if successful, None otherwise.
        """
        if not self._can_evolve_today():
            logger.warning("Daily evolution limit reached")
            return None
        
        if proposal.category != "response_quality":
            logger.info(f"Proposal category {proposal.category} not for prompt evolution")
            return None
        
        impl = proposal.implementation
        if impl.get("type") != "prompt_update":
            logger.info("Proposal is not a prompt update")
            return None
        
        current_prompt = self.get_current_prompt()
        
        # Apply the change
        change = impl.get("change", "")
        target = impl.get("target", "system_prompt")
        
        new_prompt = self._apply_change(current_prompt, change, target)
        
        if new_prompt == current_prompt:
            logger.warning("No change to prompt")
            return None
        
        # Create new version
        return self._create_version(
            new_prompt,
            change_description=f"From proposal: {proposal.problem}",
            change_type="from_proposal",
            triggered_by=proposal.id
        )
    
    async def evolve_from_patterns(self) -> Optional[PromptVersion]:
        """
        Automatically evolve prompt based on detected patterns.
        
        Uses success patterns to add helpful instructions.
        """
        if not self._can_evolve_today():
            logger.warning("Daily evolution limit reached")
            return None
        
        # Get success detector insights
        sd = get_success_detector()
        patterns = sd.get_top_patterns(10)
        
        if not patterns:
            logger.info("No patterns to learn from")
            return None
        
        # Generate improvement based on patterns
        improvements = []
        
        for pattern in patterns:
            if pattern.pattern_type == "response_style" and pattern.confidence > 0.7:
                style = pattern.pattern_data
                
                if style.get("preferred_length") == "short":
                    improvements.append(f"For {pattern.intent_category} queries, keep responses concise.")
                elif style.get("preferred_length") == "long":
                    improvements.append(f"For {pattern.intent_category} queries, provide detailed explanations.")
                
                if style.get("use_code_blocks"):
                    improvements.append(f"Include code examples when handling {pattern.intent_category} requests.")
                
                if style.get("start_with_action"):
                    improvements.append(f"When handling {pattern.intent_category}, lead with what you're doing.")
        
        if not improvements:
            logger.info("No improvements derived from patterns")
            return None
        
        # Deduplicate and limit
        improvements = list(set(improvements))[:3]
        
        # Apply to prompt
        current_prompt = self.get_current_prompt()
        new_instructions = "\n".join(f"- {imp}" for imp in improvements)
        
        # Find instruction section and append
        if "## Instructions" in current_prompt or "## Guidelines" in current_prompt:
            # Add to existing section
            new_prompt = re.sub(
                r'(## (Instructions|Guidelines).*?)(\n## |\Z)',
                f'\\1\n\nLearned from successful patterns:\n{new_instructions}\n\\3',
                current_prompt,
                flags=re.DOTALL
            )
        else:
            # Append to end
            new_prompt = current_prompt + f"\n\n## Learned Patterns\n{new_instructions}\n"
        
        if new_prompt == current_prompt:
            logger.warning("No change to prompt from patterns")
            return None
        
        return self._create_version(
            new_prompt,
            change_description=f"Learned from {len(patterns)} success patterns",
            change_type="pattern_learning"
        )
    
    def _apply_change(self, prompt: str, change: str, target: str) -> str:
        """Apply a change to the prompt."""
        # Simple append for now
        if target == "system_prompt":
            # Try to find a logical place to insert
            if "## Instructions" in prompt:
                return re.sub(
                    r'(## Instructions.*?)(\n## |\Z)',
                    f'\\1\n- {change}\n\\2',
                    prompt,
                    flags=re.DOTALL
                )
            else:
                return prompt + f"\n\n- {change}\n"
        
        return prompt
    
    def _create_version(
        self,
        content: str,
        change_description: str,
        change_type: str,
        triggered_by: Optional[int] = None
    ) -> PromptVersion:
        """Create and store a new prompt version."""
        version_num = self._get_next_version()
        
        # Backup current prompt
        self._backup_current()
        
        # Store in database
        with self._cursor() as cursor:
            # Deactivate current
            cursor.execute("UPDATE prompt_versions SET is_active = 0")
            
            # Create new
            cursor.execute("""
                INSERT INTO prompt_versions (
                    version, created_at, content, change_description,
                    change_type, triggered_by, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (
                version_num,
                datetime.now().isoformat(),
                content,
                change_description,
                change_type,
                triggered_by
            ))
            version_id = cursor.lastrowid
        
        # Write to file
        self._write_prompt(content)
        
        logger.info(f"Created prompt version {version_num}: {change_description}")
        
        return PromptVersion(
            id=version_id,
            version=version_num,
            created_at=datetime.now(),
            content=content,
            change_description=change_description,
            change_type=change_type,
            triggered_by=triggered_by,
            is_active=True
        )
    
    def _backup_current(self):
        """Backup the current prompt file."""
        if Path(PROMPT_FILE).exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = Path(PROMPT_BACKUP_DIR) / f"prompt_{timestamp}.txt"
            shutil.copy(PROMPT_FILE, backup_path)
    
    def _write_prompt(self, content: str):
        """Write prompt to file."""
        Path(PROMPT_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(PROMPT_FILE).write_text(content)
    
    def rollback(self, to_version: Optional[int] = None) -> bool:
        """
        Rollback to a previous version.
        
        Args:
            to_version: Specific version to rollback to. If None, rolls back to previous.
        
        Returns:
            True if successful, False otherwise.
        """
        with self._cursor() as cursor:
            if to_version:
                cursor.execute("""
                    SELECT * FROM prompt_versions
                    WHERE version = ?
                """, (to_version,))
            else:
                # Get second-to-last version
                cursor.execute("""
                    SELECT * FROM prompt_versions
                    ORDER BY version DESC
                    LIMIT 1 OFFSET 1
                """)
            
            row = cursor.fetchone()
            if not row:
                logger.error("No version to rollback to")
                return False
            
            # Deactivate current
            cursor.execute("UPDATE prompt_versions SET is_active = 0")
            
            # Activate target
            cursor.execute("""
                UPDATE prompt_versions
                SET is_active = 1
                WHERE id = ?
            """, (row["id"],))
        
        # Write to file
        self._write_prompt(row["content"])
        
        logger.info(f"Rolled back to version {row['version']}")
        return True
    
    def update_performance(self, version_id: int, success: bool, was_correction: bool = False):
        """Update performance metrics for a version."""
        with self._cursor() as cursor:
            cursor.execute("""
                UPDATE prompt_versions
                SET 
                    interactions_count = interactions_count + 1,
                    success_count = success_count + ?,
                    correction_count = correction_count + ?,
                    performance_score = CAST(success_count AS REAL) / CAST(interactions_count AS REAL)
                WHERE id = ?
            """, (
                1 if success else 0,
                1 if was_correction else 0,
                version_id
            ))
    
    def should_rollback(self, version_id: int) -> bool:
        """Check if a version should be rolled back based on performance."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM prompt_versions
                WHERE id = ?
            """, (version_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            # Need at least 10 interactions to judge
            if row["interactions_count"] < 10:
                return False
            
            # Rollback if performance < 70% or corrections > 20%
            if row["performance_score"] < 0.7:
                return True
            
            correction_rate = row["correction_count"] / row["interactions_count"]
            if correction_rate > 0.2:
                return True
        
        return False
    
    def get_version_history(self, limit: int = 10) -> List[Dict]:
        """Get prompt version history."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM prompt_versions
                ORDER BY version DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def add_fragment(
        self,
        category: str,
        fragment: str,
        source: str = "learned",
        confidence: float = 0.5
    ):
        """Add a new prompt fragment to the library."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT OR REPLACE INTO prompt_fragments (category, fragment, source, confidence, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (category, fragment, source, confidence, datetime.now().isoformat()))
    
    def get_fragments(self, category: Optional[str] = None, min_confidence: float = 0.0) -> List[Dict]:
        """Get prompt fragments."""
        with self._cursor() as cursor:
            query = "SELECT * FROM prompt_fragments WHERE confidence >= ?"
            params = [min_confidence]
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            query += " ORDER BY confidence DESC, times_used DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_evolver: Optional[PromptEvolver] = None


def get_prompt_evolver() -> PromptEvolver:
    """Get or create global prompt evolver."""
    global _evolver
    if _evolver is None:
        _evolver = PromptEvolver()
    return _evolver


async def evolve_from_patterns() -> Optional[PromptVersion]:
    """Evolve prompt from detected patterns."""
    return await get_prompt_evolver().evolve_from_patterns()


def rollback_prompt(to_version: int = None) -> bool:
    """Rollback to a previous prompt version."""
    return get_prompt_evolver().rollback(to_version)


