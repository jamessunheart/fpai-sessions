#!/usr/bin/env python3
"""
📔 TRADING JOURNAL
===================

AI-powered trading journal that:
- Records trades with context
- Captures lessons learned
- Identifies patterns
- Provides coaching insights
"""

import os
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("aria.trading.journal")

DATA_DIR = Path(os.getenv("ARIA_DATA_DIR", "/opt/fpai/aria-command/data"))
DB_PATH = DATA_DIR / "trading_journal.db"


@dataclass
class JournalEntry:
    """A trading journal entry."""
    id: str
    trade_id: str
    timestamp: datetime
    symbol: str
    side: str
    outcome: str  # win, loss, breakeven
    pnl: float
    
    # Context
    market_conditions: str
    entry_reasoning: str
    exit_reasoning: str
    emotional_state: str
    
    # Lessons
    what_went_well: str
    what_could_improve: str
    lesson_learned: str
    
    # Rating
    execution_rating: int  # 1-5
    patience_rating: int  # 1-5
    discipline_rating: int  # 1-5


class TradingJournal:
    """
    AI-powered trading journal.
    """
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """Initialize journal database."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                trade_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                outcome TEXT NOT NULL,
                pnl REAL NOT NULL,
                market_conditions TEXT,
                entry_reasoning TEXT,
                exit_reasoning TEXT,
                emotional_state TEXT,
                what_went_well TEXT,
                what_could_improve TEXT,
                lesson_learned TEXT,
                execution_rating INTEGER DEFAULT 3,
                patience_rating INTEGER DEFAULT 3,
                discipline_rating INTEGER DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                lesson TEXT NOT NULL,
                occurrences INTEGER DEFAULT 1,
                last_seen TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule TEXT NOT NULL,
                category TEXT,
                active BOOLEAN DEFAULT TRUE,
                violations INTEGER DEFAULT 0,
                follows INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def create_entry_from_trade(
        self,
        trade_id: str,
        symbol: str,
        side: str,
        pnl: float,
        entry_time: datetime,
        exit_time: datetime,
        confidence: float,
        exit_reason: str
    ) -> JournalEntry:
        """
        Auto-generate journal entry from trade data.
        Uses AI to analyze and learn.
        """
        outcome = "win" if pnl > 0 else "loss" if pnl < 0 else "breakeven"
        
        # Generate AI analysis
        analysis = await self._analyze_trade(
            symbol=symbol,
            side=side,
            pnl=pnl,
            entry_time=entry_time,
            exit_time=exit_time,
            confidence=confidence,
            exit_reason=exit_reason
        )
        
        entry = JournalEntry(
            id=f"J_{trade_id}",
            trade_id=trade_id,
            timestamp=exit_time,
            symbol=symbol,
            side=side,
            outcome=outcome,
            pnl=pnl,
            market_conditions=analysis.get("market_conditions", "Unknown"),
            entry_reasoning=analysis.get("entry_reasoning", f"Confidence: {confidence}%"),
            exit_reasoning=analysis.get("exit_reasoning", exit_reason),
            emotional_state=analysis.get("emotional_state", "Neutral"),
            what_went_well=analysis.get("what_went_well", ""),
            what_could_improve=analysis.get("what_could_improve", ""),
            lesson_learned=analysis.get("lesson_learned", ""),
            execution_rating=analysis.get("execution_rating", 3),
            patience_rating=analysis.get("patience_rating", 3),
            discipline_rating=analysis.get("discipline_rating", 3)
        )
        
        self._save_entry(entry)
        
        # Extract and save lesson
        if entry.lesson_learned:
            self._record_lesson(outcome, entry.lesson_learned)
        
        return entry
    
    async def _analyze_trade(
        self,
        symbol: str,
        side: str,
        pnl: float,
        entry_time: datetime,
        exit_time: datetime,
        confidence: float,
        exit_reason: str
    ) -> Dict[str, Any]:
        """
        Use AI to analyze trade and extract insights.
        """
        hold_time = exit_time - entry_time
        outcome = "win" if pnl > 0 else "loss"
        
        # Determine time of day patterns
        hour = entry_time.hour
        if 8 <= hour < 12:
            session = "morning session"
        elif 12 <= hour < 17:
            session = "afternoon session"
        elif 17 <= hour < 22:
            session = "evening session"
        else:
            session = "overnight session"
        
        # Generate analysis based on trade characteristics
        analysis = {
            "market_conditions": f"Trade during {session}",
            "entry_reasoning": f"Entered with {confidence:.0f}% confidence signal",
            "exit_reasoning": exit_reason,
            "emotional_state": "Disciplined" if confidence >= 75 else "Opportunistic",
        }
        
        # Generate lessons based on outcome
        if pnl > 0:
            if confidence >= 80:
                analysis["what_went_well"] = "High confidence setup executed properly"
                analysis["lesson_learned"] = "Trust high-confidence signals"
            else:
                analysis["what_went_well"] = "Risk managed correctly"
                analysis["lesson_learned"] = "Even lower confidence can work with good execution"
            
            if hold_time < timedelta(hours=1):
                analysis["what_could_improve"] = "Consider holding winners longer"
            else:
                analysis["what_could_improve"] = "Stay consistent with current approach"
            
            analysis["execution_rating"] = 4
            analysis["patience_rating"] = 4 if hold_time > timedelta(hours=1) else 3
            analysis["discipline_rating"] = 4
        else:
            if confidence < 70:
                analysis["what_went_well"] = "Kept position size reasonable"
                analysis["lesson_learned"] = "Wait for higher confidence signals"
                analysis["what_could_improve"] = "Be more selective on entries"
            else:
                analysis["what_went_well"] = "Followed the system"
                analysis["lesson_learned"] = "Losses are part of trading, move on"
                analysis["what_could_improve"] = "Review stop loss placement"
            
            if exit_reason == "stop":
                analysis["execution_rating"] = 4  # Good that stop was hit, means discipline
                analysis["discipline_rating"] = 5
            else:
                analysis["execution_rating"] = 3
                analysis["discipline_rating"] = 3
            
            analysis["patience_rating"] = 3
        
        return analysis
    
    def _save_entry(self, entry: JournalEntry):
        """Save journal entry to database."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO journal_entries
            (id, trade_id, timestamp, symbol, side, outcome, pnl,
             market_conditions, entry_reasoning, exit_reasoning, emotional_state,
             what_went_well, what_could_improve, lesson_learned,
             execution_rating, patience_rating, discipline_rating)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id, entry.trade_id, entry.timestamp.isoformat(),
            entry.symbol, entry.side, entry.outcome, entry.pnl,
            entry.market_conditions, entry.entry_reasoning, entry.exit_reasoning,
            entry.emotional_state, entry.what_went_well, entry.what_could_improve,
            entry.lesson_learned, entry.execution_rating, entry.patience_rating,
            entry.discipline_rating
        ))
        
        conn.commit()
        conn.close()
    
    def _record_lesson(self, category: str, lesson: str):
        """Record a lesson from a trade."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Check if lesson exists
        cursor.execute("""
            SELECT id, occurrences FROM lessons 
            WHERE lesson = ? AND category = ?
        """, (lesson, category))
        
        row = cursor.fetchone()
        
        if row:
            cursor.execute("""
                UPDATE lessons SET occurrences = ?, last_seen = ? WHERE id = ?
            """, (row[1] + 1, datetime.now().isoformat(), row[0]))
        else:
            cursor.execute("""
                INSERT INTO lessons (category, lesson, last_seen)
                VALUES (?, ?, ?)
            """, (category, lesson, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_lessons(self, category: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Get top lessons learned."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        if category:
            cursor.execute("""
                SELECT lesson, category, occurrences FROM lessons
                WHERE category = ?
                ORDER BY occurrences DESC LIMIT ?
            """, (category, limit))
        else:
            cursor.execute("""
                SELECT lesson, category, occurrences FROM lessons
                ORDER BY occurrences DESC LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {"lesson": row[0], "category": row[1], "occurrences": row[2]}
            for row in rows
        ]
    
    def get_coaching_insights(self) -> str:
        """Generate coaching insights from journal data."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Get recent entries
        cursor.execute("""
            SELECT outcome, pnl, execution_rating, patience_rating, discipline_rating,
                   what_could_improve, lesson_learned
            FROM journal_entries
            ORDER BY timestamp DESC LIMIT 20
        """)
        
        entries = cursor.fetchall()
        conn.close()
        
        if not entries:
            return "📔 **No journal entries yet**\n\nStart trading to receive coaching insights!"
        
        # Analyze patterns
        wins = [e for e in entries if e[0] == "win"]
        losses = [e for e in entries if e[0] == "loss"]
        
        avg_execution = sum(e[2] for e in entries) / len(entries)
        avg_patience = sum(e[3] for e in entries) / len(entries)
        avg_discipline = sum(e[4] for e in entries) / len(entries)
        
        # Find common improvement areas
        improvements = [e[5] for e in entries if e[5]]
        
        insights = f"""📔 **COACHING INSIGHTS**

**Recent Performance:**
• Last 20 trades: {len(wins)}W / {len(losses)}L
• Win rate: {len(wins)/len(entries)*100:.0f}%

**Skill Ratings (1-5):**
• Execution: **{avg_execution:.1f}** {"⭐" * int(avg_execution)}
• Patience: **{avg_patience:.1f}** {"⭐" * int(avg_patience)}
• Discipline: **{avg_discipline:.1f}** {"⭐" * int(avg_discipline)}

**Top Lessons:**"""
        
        lessons = self.get_lessons(limit=3)
        for lesson in lessons:
            insights += f"\n• {lesson['lesson']} ({lesson['occurrences']}x)"
        
        if avg_patience < 3:
            insights += "\n\n💡 **Focus Area:** Work on patience - let trades develop"
        if avg_discipline < 3:
            insights += "\n\n💡 **Focus Area:** Follow your rules more strictly"
        if avg_execution < 3:
            insights += "\n\n💡 **Focus Area:** Improve entry and exit timing"
        
        return insights
    
    def add_trading_rule(self, rule: str, category: str = "general"):
        """Add a trading rule to follow."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO trading_rules (rule, category) VALUES (?, ?)
        """, (rule, category))
        
        conn.commit()
        conn.close()
    
    def get_trading_rules(self) -> List[Dict]:
        """Get active trading rules."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rule, category, violations, follows FROM trading_rules
            WHERE active = 1
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "rule": row[0],
                "category": row[1],
                "violations": row[2],
                "follows": row[3],
                "compliance": row[3] / (row[2] + row[3]) * 100 if (row[2] + row[3]) > 0 else 100
            }
            for row in rows
        ]


# Singleton
_journal: Optional[TradingJournal] = None


def get_journal() -> TradingJournal:
    """Get or create global journal instance."""
    global _journal
    if _journal is None:
        _journal = TradingJournal()
    return _journal









