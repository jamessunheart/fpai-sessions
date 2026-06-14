"""
ARIA MEMORY COMPRESSION
=======================

Compresses old conversations into summaries.

Timeline:
- Week 1-2: Full conversation history
- Week 3-4: Key exchanges + summaries
- Month 2+: Themes + decisions + outcomes only

This keeps memory useful without exploding in size.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

from .store import (
    get_memory_store, Memory, MemoryStore,
    MemoryCategory, MemoryImportance
)

logger = logging.getLogger("aria.memory.compress")


class MemoryCompressor:
    """
    Compresses old memories into summaries.
    
    Preserves important information while reducing storage.
    """
    
    def __init__(self):
        self.store = get_memory_store()
        
        # Compression thresholds (in days)
        self.summarize_after = 14      # Summarize after 2 weeks
        self.archive_after = 60        # Archive after 2 months
        
        logger.info("MemoryCompressor initialized")
    
    def run_compression(self) -> Dict:
        """
        Run the full compression cycle.
        
        Returns stats about what was compressed.
        """
        stats = {
            "memories_summarized": 0,
            "memories_archived": 0,
            "summaries_created": 0
        }
        
        # First, create summaries for old conversations
        summary_stats = self._create_weekly_summaries()
        stats["summaries_created"] = summary_stats.get("created", 0)
        stats["memories_summarized"] = summary_stats.get("memories_processed", 0)
        
        # Then archive very old memories
        archive_stats = self._archive_old_memories()
        stats["memories_archived"] = archive_stats.get("archived", 0)
        
        logger.info(f"Compression complete: {stats}")
        return stats
    
    def _create_weekly_summaries(self) -> Dict:
        """Create summaries for conversations older than threshold."""
        conn = self.store._get_conn()
        c = conn.cursor()
        
        stats = {"created": 0, "memories_processed": 0}
        
        # Find weeks that need summarizing
        cutoff = (datetime.utcnow() - timedelta(days=self.summarize_after)).isoformat()
        
        c.execute("""
            SELECT DISTINCT strftime('%Y-%W', created_at) as week
            FROM memories
            WHERE category = 'conversation'
            AND compressed = 0
            AND created_at < ?
            ORDER BY week ASC
        """, (cutoff,))
        
        weeks = [row["week"] for row in c.fetchall()]
        
        for week in weeks:
            # Get memories for this week
            c.execute("""
                SELECT * FROM memories
                WHERE category = 'conversation'
                AND compressed = 0
                AND strftime('%Y-%W', created_at) = ?
                ORDER BY created_at ASC
            """, (week,))
            
            memories = c.fetchall()
            if not memories:
                continue
            
            # Create summary
            summary = self._summarize_memories(memories)
            
            # Store summary
            period_start = memories[0]["created_at"]
            period_end = memories[-1]["created_at"]
            
            summary_id = f"summary_{week}"
            
            c.execute("""
                INSERT OR REPLACE INTO summaries
                (id, period_start, period_end, summary, themes, decisions, outcomes, memory_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                summary_id,
                period_start,
                period_end,
                summary["summary"],
                json.dumps(summary["themes"]),
                json.dumps(summary["decisions"]),
                json.dumps(summary["outcomes"]),
                len(memories)
            ))
            
            # Mark memories as compressed
            memory_ids = [m["id"] for m in memories]
            placeholders = ",".join("?" * len(memory_ids))
            c.execute(f"""
                UPDATE memories SET compressed = 1
                WHERE id IN ({placeholders})
            """, memory_ids)
            
            stats["created"] += 1
            stats["memories_processed"] += len(memories)
        
        conn.commit()
        conn.close()
        
        return stats
    
    def _summarize_memories(self, memories: List) -> Dict:
        """Create a summary from a list of memories."""
        # Extract themes
        all_content = " ".join(m["content"] or "" for m in memories)
        themes = self._extract_themes(all_content)
        
        # Extract decisions
        decisions = []
        for m in memories:
            content = m["content"] or ""
            if "decision" in content.lower() or "decided" in content.lower():
                decisions.append(content[:200])
        
        # Extract outcomes
        outcomes = []
        for m in memories:
            if m["outcome"]:
                outcomes.append(m["outcome"][:200])
        
        # Create summary text
        summary_parts = []
        summary_parts.append(f"Period: {memories[0]['created_at'][:10]} to {memories[-1]['created_at'][:10]}")
        summary_parts.append(f"Exchanges: {len(memories)}")
        
        if themes:
            summary_parts.append(f"Main themes: {', '.join(themes[:5])}")
        
        if decisions:
            summary_parts.append(f"Decisions: {len(decisions)}")
        
        if outcomes:
            summary_parts.append(f"Outcomes recorded: {len(outcomes)}")
        
        # Include a few key exchanges
        important_exchanges = [
            m for m in memories 
            if m["importance"] in ["critical", "high"]
        ][:3]
        
        if important_exchanges:
            summary_parts.append("\nKey exchanges:")
            for m in important_exchanges:
                if m["user_message"] and m["aria_response"]:
                    summary_parts.append(
                        f"- Q: {m['user_message'][:50]}... A: {m['aria_response'][:50]}..."
                    )
        
        return {
            "summary": "\n".join(summary_parts),
            "themes": themes,
            "decisions": decisions[:10],
            "outcomes": outcomes[:10]
        }
    
    def _extract_themes(self, text: str) -> List[str]:
        """Extract main themes from text."""
        # Simple keyword extraction
        theme_words = {
            "trading": ["trade", "sol", "btc", "eth", "position", "signal", "market"],
            "vision": ["vision", "dream", "saw", "intuition", "manifest"],
            "building": ["build", "code", "deploy", "system", "aria"],
            "revenue": ["revenue", "money", "income", "payment", "customer"],
            "treasury": ["treasury", "fund", "protect", "runway", "burn"],
            "decision": ["decide", "decision", "choice", "option"],
            "learning": ["learn", "insight", "pattern", "understand"]
        }
        
        text_lower = text.lower()
        themes = []
        
        for theme, keywords in theme_words.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count >= 2:
                themes.append(theme)
        
        return themes
    
    def _archive_old_memories(self) -> Dict:
        """Archive very old memories."""
        conn = self.store._get_conn()
        c = conn.cursor()
        
        cutoff = (datetime.utcnow() - timedelta(days=self.archive_after)).isoformat()
        
        # Archive old, low-importance, compressed memories
        c.execute("""
            UPDATE memories 
            SET archived = 1
            WHERE compressed = 1
            AND importance IN ('low', 'medium')
            AND created_at < ?
        """, (cutoff,))
        
        archived = c.rowcount
        
        conn.commit()
        conn.close()
        
        return {"archived": archived}
    
    def get_summaries(self, limit: int = 10) -> List[Dict]:
        """Get recent summaries."""
        conn = self.store._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT * FROM summaries
            ORDER BY period_end DESC
            LIMIT ?
        """, (limit,))
        
        rows = c.fetchall()
        conn.close()
        
        return [
            {
                "id": row["id"],
                "period_start": row["period_start"],
                "period_end": row["period_end"],
                "summary": row["summary"],
                "themes": json.loads(row["themes"]) if row["themes"] else [],
                "decisions": json.loads(row["decisions"]) if row["decisions"] else [],
                "outcomes": json.loads(row["outcomes"]) if row["outcomes"] else [],
                "memory_count": row["memory_count"]
            }
            for row in rows
        ]
    
    def get_summary_for_period(self, start_date: str, end_date: str) -> Optional[Dict]:
        """Get summary covering a date range."""
        conn = self.store._get_conn()
        c = conn.cursor()
        
        c.execute("""
            SELECT * FROM summaries
            WHERE period_start <= ? AND period_end >= ?
            ORDER BY period_end DESC
            LIMIT 1
        """, (end_date, start_date))
        
        row = c.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row["id"],
                "period_start": row["period_start"],
                "period_end": row["period_end"],
                "summary": row["summary"],
                "themes": json.loads(row["themes"]) if row["themes"] else [],
                "memory_count": row["memory_count"]
            }
        return None


# Singleton
_compressor: Optional[MemoryCompressor] = None


def get_memory_compressor() -> MemoryCompressor:
    """Get or create memory compressor instance."""
    global _compressor
    if _compressor is None:
        _compressor = MemoryCompressor()
    return _compressor


def run_compression() -> Dict:
    """Convenience function to run compression."""
    return get_memory_compressor().run_compression()


