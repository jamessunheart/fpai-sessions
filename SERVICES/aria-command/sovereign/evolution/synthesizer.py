#!/usr/bin/env python3
"""
ARIA PATTERN SYNTHESIZER
=========================

AI-powered analysis of interaction data to:
1. Find improvement opportunities
2. Design concrete improvements
3. Generate implementation plans

Uses Claude Opus for deep analysis.
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
import threading
import httpx

from .interaction_logger import get_interaction_logger, get_evolution_data
from .success_detector import get_success_detector, SuccessPattern

logger = logging.getLogger("aria.evolution.synthesizer")

# ============================================================================
# CONFIGURATION
# ============================================================================

DB_PATH = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPUS_MODEL = "claude-sonnet-4-20250514"  # Use Sonnet for cost efficiency
DAILY_IMPROVEMENT_BUDGET = float(os.getenv("EVOLUTION_DAILY_BUDGET", "1.0"))  # $1/day


@dataclass
class ImprovementProposal:
    """A proposed improvement from pattern analysis."""
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    # What we found
    category: str = ""  # response_quality, capability, proactivity, efficiency
    problem: str = ""
    evidence: List[Dict] = field(default_factory=list)
    
    # What we propose
    solution: str = ""
    implementation: Dict[str, Any] = field(default_factory=dict)
    
    # Assessment
    confidence: float = 0.5
    expected_impact: str = "medium"  # low, medium, high
    risk_level: str = "low"  # low, medium, high
    
    # Status
    status: str = "pending"  # pending, approved, applied, rejected, failed
    applied_at: Optional[datetime] = None
    outcome: Optional[str] = None


PROPOSAL_SCHEMA = """
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
);

CREATE INDEX IF NOT EXISTS idx_prop_status ON improvement_proposals(status);
CREATE INDEX IF NOT EXISTS idx_prop_category ON improvement_proposals(category);
CREATE INDEX IF NOT EXISTS idx_prop_confidence ON improvement_proposals(confidence);
"""


# ============================================================================
# ANALYSIS PROMPTS
# ============================================================================

ANALYSIS_PROMPT = """You are analyzing Aria's interaction logs to find improvement opportunities.

Here is the evolution data from the last {hours} hours:

## Performance Summary
{summary}

## Failed/Corrected Interactions (Aria made mistakes here)
{failures}

## Successful Interactions (These went well)
{successes}

## Intent Distribution
{intents}

## Satisfaction Distribution
{satisfaction}

Your task: Identify 1-3 concrete improvements that would make Aria better.

For each improvement, provide:
1. **Category**: One of: response_quality, capability, proactivity, efficiency
2. **Problem**: What specific issue did you observe?
3. **Evidence**: Which specific interactions show this problem?
4. **Solution**: What concrete change would fix this?
5. **Implementation**: How exactly should we implement this? (prompt change, code change, new tool, etc.)
6. **Confidence**: 0.0-1.0, how confident are you this will help?
7. **Impact**: low/medium/high - how much will this improve Aria?
8. **Risk**: low/medium/high - what's the risk of this change causing problems?

Focus on:
- Patterns in corrections (user had to clarify)
- Repeated similar errors
- Response quality issues (too verbose, too terse, missing info)
- Missed automation opportunities
- Slow responses that could be faster

Output as JSON array:
```json
[
  {{
    "category": "response_quality",
    "problem": "Specific problem observed",
    "evidence": ["interaction_id_1", "interaction_id_2"],
    "solution": "What to change",
    "implementation": {{
      "type": "prompt_update",
      "target": "system_prompt",
      "change": "Add instruction: ..."
    }},
    "confidence": 0.8,
    "impact": "medium",
    "risk": "low"
  }}
]
```

If you don't find any clear improvements needed, return an empty array: []
"""


# ============================================================================
# PATTERN SYNTHESIZER
# ============================================================================

class PatternSynthesizer:
    """
    AI-powered pattern analysis and improvement design.
    
    Process:
    1. Gather evolution data
    2. Send to AI for analysis
    3. Parse improvement proposals
    4. Store and prioritize
    """
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
        self.interaction_logger = get_interaction_logger()
        self.success_detector = get_success_detector()
    
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
            cursor.executescript(PROPOSAL_SCHEMA)
        logger.info(f"Pattern synthesizer initialized: {self.db_path}")
    
    async def analyze_and_propose(self, hours: int = 24) -> List[ImprovementProposal]:
        """
        Analyze recent data and propose improvements.
        
        Returns:
            List of improvement proposals.
        """
        # Check budget
        if not self._check_budget():
            logger.warning("Evolution budget exhausted for today")
            return []
        
        # Gather data
        data = get_evolution_data(hours)
        
        # Skip if not enough data
        total = data["summary"].get("total_interactions", 0)
        if total < 10:
            logger.info(f"Only {total} interactions, skipping analysis")
            return []
        
        # Analyze with AI
        proposals = await self._ai_analyze(data, hours)
        
        # Store proposals
        for proposal in proposals:
            self._store_proposal(proposal)
        
        logger.info(f"Generated {len(proposals)} improvement proposals")
        return proposals
    
    def _check_budget(self) -> bool:
        """Check if we have budget for analysis."""
        # Simple check - track in daily file
        today = datetime.now().strftime("%Y%m%d")
        budget_file = Path(f"/opt/fpai/aria-command/state/evolution_budget_{today}.json")
        
        if budget_file.exists():
            with open(budget_file) as f:
                data = json.load(f)
                spent = data.get("spent", 0)
                return spent < DAILY_IMPROVEMENT_BUDGET
        
        return True
    
    def _record_spend(self, amount: float):
        """Record spending for today."""
        today = datetime.now().strftime("%Y%m%d")
        budget_file = Path(f"/opt/fpai/aria-command/state/evolution_budget_{today}.json")
        
        data = {"spent": 0}
        if budget_file.exists():
            with open(budget_file) as f:
                data = json.load(f)
        
        data["spent"] = data.get("spent", 0) + amount
        
        budget_file.parent.mkdir(parents=True, exist_ok=True)
        with open(budget_file, "w") as f:
            json.dump(data, f)
    
    async def _ai_analyze(
        self,
        data: Dict[str, Any],
        hours: int
    ) -> List[ImprovementProposal]:
        """Use AI to analyze data and propose improvements."""
        if not ANTHROPIC_API_KEY:
            logger.warning("No Anthropic API key, skipping AI analysis")
            return []
        
        # Format data for prompt
        summary = json.dumps(data["summary"], indent=2)
        
        # Limit failures to 10 most recent
        failures = data.get("failures", [])[:10]
        failures_str = json.dumps([
            {
                "id": f["id"],
                "message": f.get("user_message", "")[:200],
                "response": f.get("response", "")[:200],
                "error": f.get("error_message", ""),
                "satisfaction": f.get("satisfaction", "")
            }
            for f in failures
        ], indent=2)
        
        # Limit successes to 5 samples
        successes = data.get("successes", [])[:5]
        successes_str = json.dumps([
            {
                "id": s["id"],
                "message": s.get("user_message", "")[:200],
                "response": s.get("response", "")[:200]
            }
            for s in successes
        ], indent=2)
        
        intents = json.dumps(data.get("intents", {}), indent=2)
        satisfaction = json.dumps(data.get("satisfaction", {}), indent=2)
        
        prompt = ANALYSIS_PROMPT.format(
            hours=hours,
            summary=summary,
            failures=failures_str,
            successes=successes_str,
            intents=intents,
            satisfaction=satisfaction
        )
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": OPUS_MODEL,
                        "max_tokens": 2000,
                        "messages": [{"role": "user", "content": prompt}]
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"AI analysis failed: {response.status_code}")
                    return []
                
                result = response.json()
                
                # Record cost (approximate)
                input_tokens = result.get("usage", {}).get("input_tokens", 0)
                output_tokens = result.get("usage", {}).get("output_tokens", 0)
                cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000  # Sonnet pricing
                self._record_spend(cost)
                
                # Parse response
                content = result.get("content", [{}])[0].get("text", "")
                return self._parse_proposals(content)
                
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return []
    
    def _parse_proposals(self, content: str) -> List[ImprovementProposal]:
        """Parse AI response into proposals."""
        proposals = []
        
        # Find JSON in response
        import re
        json_match = re.search(r'\[[\s\S]*\]', content)
        
        if not json_match:
            logger.warning("No JSON found in AI response")
            return []
        
        try:
            items = json.loads(json_match.group())
            
            for item in items:
                proposal = ImprovementProposal(
                    category=item.get("category", "unknown"),
                    problem=item.get("problem", ""),
                    evidence=item.get("evidence", []),
                    solution=item.get("solution", ""),
                    implementation=item.get("implementation", {}),
                    confidence=float(item.get("confidence", 0.5)),
                    expected_impact=item.get("impact", "medium"),
                    risk_level=item.get("risk", "low")
                )
                proposals.append(proposal)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI proposals: {e}")
        
        return proposals
    
    def _store_proposal(self, proposal: ImprovementProposal):
        """Store a proposal in the database."""
        with self._cursor() as cursor:
            cursor.execute("""
                INSERT INTO improvement_proposals (
                    created_at, category, problem, evidence,
                    solution, implementation, confidence,
                    expected_impact, risk_level, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                proposal.category,
                proposal.problem,
                json.dumps(proposal.evidence),
                proposal.solution,
                json.dumps(proposal.implementation),
                proposal.confidence,
                proposal.expected_impact,
                proposal.risk_level,
                "pending"
            ))
            proposal.id = cursor.lastrowid
    
    def get_pending_proposals(self) -> List[ImprovementProposal]:
        """Get all pending proposals."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT * FROM improvement_proposals
                WHERE status = 'pending'
                ORDER BY confidence DESC, created_at DESC
            """)
            
            return [
                ImprovementProposal(
                    id=row["id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    category=row["category"],
                    problem=row["problem"],
                    evidence=json.loads(row["evidence"]) if row["evidence"] else [],
                    solution=row["solution"],
                    implementation=json.loads(row["implementation"]) if row["implementation"] else {},
                    confidence=row["confidence"],
                    expected_impact=row["expected_impact"],
                    risk_level=row["risk_level"],
                    status=row["status"]
                )
                for row in cursor.fetchall()
            ]
    
    def get_high_confidence_proposals(self, min_confidence: float = 0.8) -> List[ImprovementProposal]:
        """Get proposals with high confidence for auto-execution."""
        proposals = self.get_pending_proposals()
        return [p for p in proposals if p.confidence >= min_confidence and p.risk_level == "low"]
    
    def mark_proposal(self, proposal_id: int, status: str, outcome: str = None):
        """Update proposal status."""
        with self._cursor() as cursor:
            if status == "applied":
                cursor.execute("""
                    UPDATE improvement_proposals
                    SET status = ?, applied_at = ?, outcome = ?
                    WHERE id = ?
                """, (status, datetime.now().isoformat(), outcome, proposal_id))
            else:
                cursor.execute("""
                    UPDATE improvement_proposals
                    SET status = ?, outcome = ?
                    WHERE id = ?
                """, (status, outcome, proposal_id))
    
    def get_proposal_stats(self) -> Dict[str, Any]:
        """Get proposal statistics."""
        with self._cursor() as cursor:
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(confidence) as avg_confidence
                FROM improvement_proposals
                GROUP BY status
            """)
            by_status = {
                row["status"]: {
                    "count": row["count"],
                    "avg_confidence": row["avg_confidence"]
                }
                for row in cursor.fetchall()
            }
            
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM improvement_proposals
                GROUP BY category
            """)
            by_category = {row["category"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM improvement_proposals
                WHERE status = 'applied' AND outcome = 'success'
            """)
            successful = cursor.fetchone()["count"]
            
            cursor.execute("""
                SELECT COUNT(*) as count FROM improvement_proposals
                WHERE status = 'applied'
            """)
            total_applied = cursor.fetchone()["count"]
        
        return {
            "by_status": by_status,
            "by_category": by_category,
            "success_rate": successful / total_applied if total_applied > 0 else 0
        }
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


# ============================================================================
# SINGLETON
# ============================================================================

_synthesizer: Optional[PatternSynthesizer] = None


def get_synthesizer() -> PatternSynthesizer:
    """Get or create global synthesizer."""
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = PatternSynthesizer()
    return _synthesizer


async def analyze_and_propose(hours: int = 24) -> List[ImprovementProposal]:
    """Analyze data and propose improvements."""
    return await get_synthesizer().analyze_and_propose(hours)


def get_pending_proposals() -> List[ImprovementProposal]:
    """Get pending proposals."""
    return get_synthesizer().get_pending_proposals()


