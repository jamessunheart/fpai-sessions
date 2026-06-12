"""
ARIA CURIOSITY ENGINE
=====================

Makes Aria genuinely curious by:
- Exploring new patterns in data
- Asking "what would help James right now?"
- Discovering correlations between systems
- Suggesting improvements it notices

This is what makes Aria feel alive and proactive.
"""

import os
import logging
import json
import sqlite3
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import httpx

logger = logging.getLogger("aria.curiosity")

# Paths
CURIOSITY_DB = Path("/opt/fpai/aria/curiosity.db")
INSIGHTS_FILE = Path("/opt/fpai/aria/insights.json")


@dataclass
class Insight:
    """A discovered insight."""
    id: str
    category: str
    observation: str
    suggestion: Optional[str]
    confidence: float
    worth_sharing: bool
    discovered_at: str
    shared: bool = False


class CuriosityEngine:
    """
    The curiosity engine that makes Aria genuinely curious.
    
    Explores patterns across:
    - Trading outcomes vs signals
    - Build success rates vs time/conditions
    - Resource usage patterns
    - User behavior patterns
    
    Core question: "What would help James right now?"
    """
    
    def __init__(self):
        self._init_db()
        self.insights: List[Insight] = []
        self.exploration_prompts = [
            "What patterns exist in trading signal accuracy?",
            "Are there correlations between time of day and build success?",
            "What resources are consistently underutilized?",
            "What would make James's day easier?",
            "What opportunities are being missed?",
            "What's working well that should be amplified?",
            "What's consistently causing friction?",
        ]
        self._load_insights()
        logger.info("CuriosityEngine initialized")
    
    def _init_db(self):
        """Initialize curiosity database."""
        CURIOSITY_DB.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(CURIOSITY_DB))
        c = conn.cursor()
        
        # Observations table
        c.execute("""
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                observation TEXT NOT NULL,
                data TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        
        # Correlations table
        c.execute("""
            CREATE TABLE IF NOT EXISTS correlations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                factor_a TEXT NOT NULL,
                factor_b TEXT NOT NULL,
                correlation_strength REAL,
                sample_size INTEGER,
                discovered_at TEXT NOT NULL
            )
        """)
        
        # Insights table
        c.execute("""
            CREATE TABLE IF NOT EXISTS insights (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                observation TEXT NOT NULL,
                suggestion TEXT,
                confidence REAL,
                worth_sharing INTEGER,
                discovered_at TEXT NOT NULL,
                shared INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_insights(self):
        """Load recent insights."""
        try:
            conn = sqlite3.connect(str(CURIOSITY_DB))
            c = conn.cursor()
            c.execute("""
                SELECT id, category, observation, suggestion, confidence, 
                       worth_sharing, discovered_at, shared
                FROM insights
                WHERE discovered_at > datetime('now', '-7 days')
                ORDER BY discovered_at DESC
            """)
            
            self.insights = [
                Insight(
                    id=row[0], category=row[1], observation=row[2],
                    suggestion=row[3], confidence=row[4], worth_sharing=bool(row[5]),
                    discovered_at=row[6], shared=bool(row[7])
                )
                for row in c.fetchall()
            ]
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to load insights: {e}")
    
    def _save_insight(self, insight: Insight):
        """Save an insight to database."""
        try:
            conn = sqlite3.connect(str(CURIOSITY_DB))
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO insights 
                (id, category, observation, suggestion, confidence, worth_sharing, discovered_at, shared)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                insight.id, insight.category, insight.observation,
                insight.suggestion, insight.confidence, int(insight.worth_sharing),
                insight.discovered_at, int(insight.shared)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to save insight: {e}")
    
    async def explore(self) -> List[Dict]:
        """
        Run an exploration cycle.
        
        Returns list of insights worth sharing.
        """
        results = []
        
        # Pick a random exploration prompt
        prompt = random.choice(self.exploration_prompts)
        logger.info(f"🔍 Exploring: {prompt}")
        
        # Run specific explorations based on prompt
        if "trading" in prompt.lower():
            insights = await self._explore_trading()
            results.extend(insights)
        
        if "build" in prompt.lower():
            insights = await self._explore_builds()
            results.extend(insights)
        
        if "resource" in prompt.lower() or "underutilized" in prompt.lower():
            insights = await self._explore_resources()
            results.extend(insights)
        
        if "help" in prompt.lower() or "easier" in prompt.lower():
            insights = await self._explore_help_opportunities()
            results.extend(insights)
        
        # Always look for general correlations
        insights = await self._explore_correlations()
        results.extend(insights)
        
        # Filter to worth sharing and not already shared
        to_share = [
            {"message": self._format_insight(i), "insight": i, "worth_sharing": True}
            for i in results
            if i.get("worth_sharing") and not i.get("shared")
        ]
        
        return to_share
    
    async def _explore_trading(self) -> List[Dict]:
        """Explore trading patterns."""
        insights = []
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Get signal accuracy report
                r = await client.get(
                    "http://198.54.123.234:8601/api/accuracy/report",
                    timeout=10.0
                )
                
                if r.status_code == 200:
                    data = r.json()
                    
                    # Look for patterns
                    accuracy = data.get("overall_accuracy", 0)
                    by_symbol = data.get("by_symbol", {})
                    by_regime = data.get("by_regime", {})
                    
                    # Find best performing conditions
                    if by_regime:
                        best_regime = max(by_regime.items(), key=lambda x: x[1].get("accuracy", 0))
                        if best_regime[1].get("accuracy", 0) > accuracy + 10:
                            insight = {
                                "id": f"trading_regime_{datetime.utcnow().strftime('%Y%m%d')}",
                                "category": "trading",
                                "observation": f"Trading signals are most accurate during {best_regime[0]} markets ({best_regime[1]['accuracy']:.0f}% vs {accuracy:.0f}% overall)",
                                "suggestion": f"Consider being more aggressive with signals during {best_regime[0]} conditions",
                                "confidence": 0.7,
                                "worth_sharing": True,
                                "discovered_at": datetime.utcnow().isoformat()
                            }
                            insights.append(insight)
                    
                    # Find best performing symbol
                    if by_symbol:
                        best_symbol = max(by_symbol.items(), key=lambda x: x[1].get("accuracy", 0))
                        worst_symbol = min(by_symbol.items(), key=lambda x: x[1].get("accuracy", 0))
                        
                        if best_symbol[1].get("accuracy", 0) - worst_symbol[1].get("accuracy", 0) > 20:
                            insight = {
                                "id": f"trading_symbol_{datetime.utcnow().strftime('%Y%m%d')}",
                                "category": "trading",
                                "observation": f"Signal accuracy varies significantly by asset: {best_symbol[0]} ({best_symbol[1]['accuracy']:.0f}%) vs {worst_symbol[0]} ({worst_symbol[1]['accuracy']:.0f}%)",
                                "suggestion": f"Consider focusing trading on {best_symbol[0]} for better outcomes",
                                "confidence": 0.6,
                                "worth_sharing": True,
                                "discovered_at": datetime.utcnow().isoformat()
                            }
                            insights.append(insight)
        
        except Exception as e:
            logger.debug(f"Trading exploration error: {e}")
        
        return insights
    
    async def _explore_builds(self) -> List[Dict]:
        """Explore build patterns."""
        insights = []
        
        try:
            db_path = "/opt/fpai/ai-brain/v2/thinking_v2.db"
            if not Path(db_path).exists():
                return insights
            
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            
            # Check build success rates by day of week
            c.execute("""
                SELECT 
                    strftime('%w', created_at) as day,
                    status,
                    COUNT(*) as count
                FROM build_queue
                WHERE created_at > datetime('now', '-30 days')
                GROUP BY day, status
            """)
            
            by_day = {}
            for row in c.fetchall():
                day = int(row[0])
                status = row[1]
                count = row[2]
                
                if day not in by_day:
                    by_day[day] = {"total": 0, "success": 0}
                by_day[day]["total"] += count
                if status == "completed":
                    by_day[day]["success"] += count
            
            conn.close()
            
            # Find worst day
            if by_day:
                day_names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
                
                success_rates = {
                    d: (stats["success"] / stats["total"] * 100) if stats["total"] > 5 else None
                    for d, stats in by_day.items()
                }
                
                valid_rates = {d: r for d, r in success_rates.items() if r is not None}
                
                if valid_rates:
                    worst_day = min(valid_rates.items(), key=lambda x: x[1])
                    best_day = max(valid_rates.items(), key=lambda x: x[1])
                    
                    if best_day[1] - worst_day[1] > 15:
                        insight = {
                            "id": f"build_day_{datetime.utcnow().strftime('%Y%m%d')}",
                            "category": "builder",
                            "observation": f"Builds succeed less often on {day_names[worst_day[0]]}s ({worst_day[1]:.0f}%) compared to {day_names[best_day[0]]}s ({best_day[1]:.0f}%)",
                            "suggestion": "Consider scheduling complex builds for better days",
                            "confidence": 0.5,
                            "worth_sharing": True,
                            "discovered_at": datetime.utcnow().isoformat()
                        }
                        insights.append(insight)
        
        except Exception as e:
            logger.debug(f"Build exploration error: {e}")
        
        return insights
    
    async def _explore_resources(self) -> List[Dict]:
        """Explore resource usage patterns."""
        insights = []
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Check GPU utilization
                r = await client.get("http://162.0.208.88:8450/status")
                
                if r.status_code == 200:
                    data = r.json()
                    gpus = data.get("gpus", 0)
                    queue = data.get("queue_depth", 0)
                    cost = data.get("hourly_cost", 0)
                    
                    # Check if we're over-provisioned
                    if gpus > 2 and queue == 0:
                        daily_waste = (gpus - 1) * 0.05 * 24
                        insight = {
                            "id": f"gpu_util_{datetime.utcnow().strftime('%Y%m%d')}",
                            "category": "infrastructure",
                            "observation": f"Running {gpus} GPUs with empty queue. Could save ${daily_waste:.2f}/day",
                            "suggestion": "Already auto-scaling down, but consider reducing MIN_GPUS if queue is often empty",
                            "confidence": 0.8,
                            "worth_sharing": True,
                            "discovered_at": datetime.utcnow().isoformat()
                        }
                        insights.append(insight)
        
        except Exception as e:
            logger.debug(f"Resource exploration error: {e}")
        
        return insights
    
    async def _explore_help_opportunities(self) -> List[Dict]:
        """Look for ways to help James."""
        insights = []
        
        # This would analyze:
        # - What James asks about most often
        # - What takes the most time
        # - What keeps failing
        # - What could be automated
        
        # For now, generate a thoughtful prompt
        prompts = [
            "I notice you ask about trading signals frequently. Want me to send them proactively when they're strong?",
            "The build queue seems to back up during your working hours. Should I prioritize quick builds in the morning?",
            "You check server health manually a lot. I can monitor this and only alert you when there's an issue.",
            "Some services restart frequently. Want me to track which ones and why?",
        ]
        
        # Pick one occasionally
        if random.random() < 0.1:  # 10% chance each cycle
            insight = {
                "id": f"help_{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
                "category": "help",
                "observation": random.choice(prompts),
                "suggestion": None,
                "confidence": 0.3,
                "worth_sharing": True,
                "discovered_at": datetime.utcnow().isoformat()
            }
            insights.append(insight)
        
        return insights
    
    async def _explore_correlations(self) -> List[Dict]:
        """Look for correlations between systems."""
        # This would analyze cross-system patterns
        # For now, return empty - this is where deep learning could help
        return []
    
    def _format_insight(self, insight: Dict) -> str:
        """Format insight for notification."""
        lines = [insight.get("observation", "")]
        
        if insight.get("suggestion"):
            lines.append("")
            lines.append(f"💡 {insight['suggestion']}")
        
        return "\n".join(lines)
    
    def record_observation(self, category: str, observation: str, data: Dict = None):
        """Record an observation for future analysis."""
        try:
            conn = sqlite3.connect(str(CURIOSITY_DB))
            c = conn.cursor()
            c.execute("""
                INSERT INTO observations (category, observation, data, timestamp)
                VALUES (?, ?, ?, datetime('now'))
            """, (category, observation, json.dumps(data) if data else None))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to record observation: {e}")
    
    def get_recent_insights(self, limit: int = 10) -> List[Insight]:
        """Get recent insights."""
        return self.insights[:limit]


# Singleton instance
_curiosity: Optional[CuriosityEngine] = None


def get_curiosity() -> CuriosityEngine:
    """Get or create the curiosity engine."""
    global _curiosity
    if _curiosity is None:
        _curiosity = CuriosityEngine()
    return _curiosity


