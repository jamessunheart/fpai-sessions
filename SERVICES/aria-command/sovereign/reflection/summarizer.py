#!/usr/bin/env python3
"""
ARIA INTERACTION SUMMARIZER
===========================

Uses cost-efficient models to summarize interaction logs into themes:
- What worked well
- What failed or caused frustration
- User patterns and preferences
- Capability gaps identified

Compresses hours of logs into ~500 token summary for dialogue phase.
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from contextlib import contextmanager
import threading
import httpx

logger = logging.getLogger("aria.reflection.summarizer")

# ============================================================================
# CONFIGURATION
# ============================================================================

EVOLUTION_DB = os.getenv("EVOLUTION_DB", "/opt/fpai/aria-command/state/evolution.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Use cheap model for summarization
SUMMARIZER_MODEL = os.getenv("SUMMARIZER_MODEL", "gpt-4o-mini")
MAX_INTERACTIONS = int(os.getenv("SUMMARIZER_MAX_INTERACTIONS", "100"))


@dataclass
class InteractionSummary:
    """Summary of recent interactions."""
    period_start: datetime
    period_end: datetime
    interaction_count: int
    
    # Themes
    what_worked: List[str] = field(default_factory=list)
    what_failed: List[str] = field(default_factory=list)
    user_frustrations: List[str] = field(default_factory=list)
    capability_gaps: List[str] = field(default_factory=list)
    common_queries: List[str] = field(default_factory=list)
    
    # Metrics
    avg_response_time_ms: float = 0.0
    success_rate: float = 0.0
    correction_count: int = 0
    
    # Patterns detected
    detected_patterns: List[Dict] = field(default_factory=list)
    
    # Cost
    summarization_cost: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "interaction_count": self.interaction_count,
            "what_worked": self.what_worked,
            "what_failed": self.what_failed,
            "user_frustrations": self.user_frustrations,
            "capability_gaps": self.capability_gaps,
            "common_queries": self.common_queries,
            "avg_response_time_ms": self.avg_response_time_ms,
            "success_rate": self.success_rate,
            "correction_count": self.correction_count,
            "detected_patterns": self.detected_patterns,
            "summarization_cost": self.summarization_cost
        }
    
    def to_prompt_text(self) -> str:
        """Convert to text for dialogue phase."""
        lines = [
            f"## Interaction Summary ({self.period_start.strftime('%Y-%m-%d %H:%M')} to {self.period_end.strftime('%Y-%m-%d %H:%M')})",
            f"",
            f"**Interactions analyzed:** {self.interaction_count}",
            f"**Success rate:** {self.success_rate:.1%}",
            f"**Average response time:** {self.avg_response_time_ms:.0f}ms",
            f"**Corrections needed:** {self.correction_count}",
            f"",
        ]
        
        if self.what_worked:
            lines.append("### What Worked Well")
            for item in self.what_worked:
                lines.append(f"- {item}")
            lines.append("")
        
        if self.what_failed:
            lines.append("### What Failed")
            for item in self.what_failed:
                lines.append(f"- {item}")
            lines.append("")
        
        if self.user_frustrations:
            lines.append("### User Frustrations")
            for item in self.user_frustrations:
                lines.append(f"- {item}")
            lines.append("")
        
        if self.capability_gaps:
            lines.append("### Capability Gaps")
            for item in self.capability_gaps:
                lines.append(f"- {item}")
            lines.append("")
        
        if self.common_queries:
            lines.append("### Most Common Query Types")
            for item in self.common_queries:
                lines.append(f"- {item}")
            lines.append("")
        
        if self.detected_patterns:
            lines.append("### Detected Patterns")
            for p in self.detected_patterns:
                lines.append(f"- [{p.get('severity', 'unknown')}] {p.get('detector', 'unknown')}: {p.get('problem', '')}")
            lines.append("")
        
        return "\n".join(lines)


# ============================================================================
# SUMMARIZATION PROMPT
# ============================================================================

SUMMARIZATION_PROMPT = """You are analyzing chat interactions between a user (James) and an AI assistant (Aria) to identify patterns and improvement opportunities.

Here are the recent interactions:

{interactions}

And here are any detected patterns from the system:

{patterns}

Please analyze these interactions and provide a structured summary:

1. **What Worked Well** (2-4 bullet points)
   - What types of requests did Aria handle effectively?
   - Where was the user satisfied?

2. **What Failed** (2-4 bullet points)
   - Where did Aria fail to complete a task?
   - What errors occurred?

3. **User Frustrations** (2-4 bullet points)
   - Signs of user frustration (e.g., "?", "no", repeated requests)
   - Long delays or confusion

4. **Capability Gaps** (2-4 bullet points)
   - What did the user want that Aria couldn't do?
   - What would have made the interaction better?

5. **Common Queries** (3-5 bullet points)
   - What are the most frequent types of requests?
   - Any patterns in timing or context?

Output as JSON:
```json
{
  "what_worked": ["item1", "item2"],
  "what_failed": ["item1", "item2"],
  "user_frustrations": ["item1", "item2"],
  "capability_gaps": ["item1", "item2"],
  "common_queries": ["item1", "item2"]
}
```

Be specific and actionable. Focus on patterns, not individual incidents."""


# ============================================================================
# INTERACTION SUMMARIZER
# ============================================================================

class InteractionSummarizer:
    """
    Summarizes recent interactions for reflection.
    
    Uses GPT-4o-mini for cost efficiency (~$0.01 per summary).
    """
    
    def __init__(self):
        self._local = threading.local()
        self.http = httpx.AsyncClient(timeout=60.0)
    
    def _get_evolution_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'evo_conn') or self._local.evo_conn is None:
            self._local.evo_conn = sqlite3.connect(EVOLUTION_DB)
            self._local.evo_conn.row_factory = sqlite3.Row
        return self._local.evo_conn
    
    @contextmanager
    def _evo_cursor(self):
        conn = self._get_evolution_conn()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            pass  # Read-only
    
    async def close(self):
        await self.http.aclose()
    
    # ========================================================================
    # DATA GATHERING
    # ========================================================================
    
    def get_recent_interactions(self, hours: int = 24, limit: int = MAX_INTERACTIONS) -> List[Dict]:
        """Get recent interactions from evolution DB."""
        with self._evo_cursor() as cursor:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute("""
                SELECT id, timestamp, user_message, response, tools_called,
                       total_time_ms, success, model_used
                FROM interactions
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (since, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_detected_patterns(self, hours: int = 24) -> List[Dict]:
        """Get detected patterns from evolution DB."""
        with self._evo_cursor() as cursor:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            cursor.execute("""
                SELECT detector, severity, problem_description, suggested_fix
                FROM detected_patterns
                WHERE detected_at > ?
                ORDER BY severity DESC, detected_at DESC
                LIMIT 10
            """, (since,))
            
            return [
                {
                    "detector": row["detector"],
                    "severity": row["severity"],
                    "problem": row["problem_description"],
                    "fix": row["suggested_fix"]
                }
                for row in cursor.fetchall()
            ]
    
    def get_interaction_metrics(self, interactions: List[Dict]) -> Dict[str, Any]:
        """Calculate metrics from interactions."""
        if not interactions:
            return {
                "count": 0,
                "avg_time_ms": 0,
                "success_rate": 0,
                "correction_count": 0
            }
        
        total_time = sum(i.get("total_time_ms", 0) or 0 for i in interactions)
        successes = sum(1 for i in interactions if i.get("success"))
        
        # Count corrections (messages that are "?", "no", etc.)
        correction_indicators = ["?", "no,", "wrong", "not that", "i meant"]
        correction_count = sum(
            1 for i in interactions
            if any(ind in (i.get("user_message") or "").lower() for ind in correction_indicators)
        )
        
        return {
            "count": len(interactions),
            "avg_time_ms": total_time / len(interactions) if interactions else 0,
            "success_rate": successes / len(interactions) if interactions else 0,
            "correction_count": correction_count
        }
    
    # ========================================================================
    # AI SUMMARIZATION
    # ========================================================================
    
    def _format_interactions_for_prompt(self, interactions: List[Dict]) -> str:
        """Format interactions for the summarization prompt."""
        lines = []
        
        for i in interactions[:50]:  # Limit to 50 for prompt size
            ts = i.get("timestamp", "")[:16] if i.get("timestamp") else "?"
            user_msg = (i.get("user_message") or "")[:200]
            response = (i.get("response") or "")[:200]
            tools = i.get("tools_called") or "none"
            time_ms = i.get("total_time_ms") or 0
            success = "✓" if i.get("success") else "✗"
            
            lines.append(f"[{ts}] {success} ({time_ms:.0f}ms)")
            lines.append(f"  User: {user_msg}")
            lines.append(f"  Aria: {response}...")
            if tools != "none":
                lines.append(f"  Tools: {tools[:50]}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_patterns_for_prompt(self, patterns: List[Dict]) -> str:
        """Format patterns for the summarization prompt."""
        if not patterns:
            return "No patterns detected."
        
        lines = []
        for p in patterns:
            lines.append(f"- [{p.get('severity', '?')}] {p.get('detector', '?')}: {p.get('problem', '')}")
            if p.get('fix'):
                lines.append(f"  Suggested fix: {p.get('fix')}")
        
        return "\n".join(lines)
    
    async def _call_openai(self, prompt: str) -> tuple[str, float]:
        """Call OpenAI API for summarization."""
        if not OPENAI_API_KEY:
            raise ValueError("No OpenAI API key configured")
        
        response = await self.http.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": SUMMARIZER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 1000
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.text}")
        
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        
        # Calculate cost (GPT-4o-mini pricing)
        input_tokens = data.get("usage", {}).get("prompt_tokens", 0)
        output_tokens = data.get("usage", {}).get("completion_tokens", 0)
        cost = (input_tokens * 0.00015 + output_tokens * 0.0006) / 1000
        
        return content, cost
    
    async def _call_anthropic(self, prompt: str) -> tuple[str, float]:
        """Call Anthropic API for summarization (fallback)."""
        if not ANTHROPIC_API_KEY:
            raise ValueError("No Anthropic API key configured")
        
        response = await self.http.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": "claude-3-haiku-20240307",
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}]
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Anthropic API error: {response.text}")
        
        data = response.json()
        content = data["content"][0]["text"]
        
        # Calculate cost (Haiku pricing)
        input_tokens = data.get("usage", {}).get("input_tokens", 0)
        output_tokens = data.get("usage", {}).get("output_tokens", 0)
        cost = (input_tokens * 0.00025 + output_tokens * 0.00125) / 1000
        
        return content, cost
    
    def _parse_summary_response(self, response: str) -> Dict[str, List[str]]:
        """Parse JSON from LLM response."""
        # Try to extract JSON from response
        import re
        
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try raw JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass
        
        # Fallback: empty summary
        logger.warning("Could not parse summary response")
        return {
            "what_worked": ["Unable to parse summary"],
            "what_failed": [],
            "user_frustrations": [],
            "capability_gaps": [],
            "common_queries": []
        }
    
    # ========================================================================
    # MAIN SUMMARIZE METHOD
    # ========================================================================
    
    async def summarize(self, hours: int = 24) -> InteractionSummary:
        """
        Generate summary of recent interactions.
        
        Returns InteractionSummary ready for dialogue phase.
        """
        logger.info(f"Summarizing last {hours} hours of interactions...")
        
        # Gather data
        interactions = self.get_recent_interactions(hours)
        patterns = self.get_detected_patterns(hours)
        metrics = self.get_interaction_metrics(interactions)
        
        if not interactions:
            logger.info("No interactions to summarize")
            return InteractionSummary(
                period_start=datetime.now() - timedelta(hours=hours),
                period_end=datetime.now(),
                interaction_count=0
            )
        
        # Determine time range
        timestamps = [datetime.fromisoformat(i["timestamp"]) for i in interactions if i.get("timestamp")]
        period_start = min(timestamps) if timestamps else datetime.now() - timedelta(hours=hours)
        period_end = max(timestamps) if timestamps else datetime.now()
        
        # Build prompt
        interactions_text = self._format_interactions_for_prompt(interactions)
        patterns_text = self._format_patterns_for_prompt(patterns)
        
        prompt = SUMMARIZATION_PROMPT.format(
            interactions=interactions_text,
            patterns=patterns_text
        )
        
        # Call AI
        cost = 0.0
        try:
            response, cost = await self._call_openai(prompt)
        except Exception as e:
            logger.warning(f"OpenAI failed, trying Anthropic: {e}")
            try:
                response, cost = await self._call_anthropic(prompt)
            except Exception as e2:
                logger.error(f"Both APIs failed: {e2}")
                response = "{}"
        
        # Parse response
        parsed = self._parse_summary_response(response)
        
        # Build summary
        summary = InteractionSummary(
            period_start=period_start,
            period_end=period_end,
            interaction_count=metrics["count"],
            what_worked=parsed.get("what_worked", []),
            what_failed=parsed.get("what_failed", []),
            user_frustrations=parsed.get("user_frustrations", []),
            capability_gaps=parsed.get("capability_gaps", []),
            common_queries=parsed.get("common_queries", []),
            avg_response_time_ms=metrics["avg_time_ms"],
            success_rate=metrics["success_rate"],
            correction_count=metrics["correction_count"],
            detected_patterns=patterns,
            summarization_cost=cost
        )
        
        logger.info(f"Summary generated: {metrics['count']} interactions, ${cost:.4f}")
        
        return summary


# ============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ============================================================================

_summarizer: Optional[InteractionSummarizer] = None


def get_summarizer() -> InteractionSummarizer:
    """Get global summarizer instance."""
    global _summarizer
    if _summarizer is None:
        _summarizer = InteractionSummarizer()
    return _summarizer


async def summarize_interactions(hours: int = 24) -> InteractionSummary:
    """Summarize recent interactions."""
    return await get_summarizer().summarize(hours)


