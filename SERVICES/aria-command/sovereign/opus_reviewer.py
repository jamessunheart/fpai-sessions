#!/usr/bin/env python3
"""
ARIA CLAUDE OPUS REVIEWER DAEMON
=================================

A dedicated Claude Opus instance that reviews Aria's logs and proposes
improvements. Runs on a schedule (default: daily) and generates
actionable improvement proposals.

Features:
- Analyzes error patterns and recurring issues
- Identifies slow responses and performance bottlenecks
- Proposes code fixes with actual diffs
- Assesses risk of each proposed change
- Estimates impact and cost
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
import hashlib
import httpx

logger = logging.getLogger("aria.sovereign.opus_reviewer")

# ============================================================================
# CONFIGURATION
# ============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
REVIEW_MODEL = os.getenv("ARIA_REVIEW_MODEL", "claude-sonnet-4-20250514")
WORKSPACE_ROOT = os.getenv("WORKSPACE_ROOT", "/opt/fpai/aria-command")

# How often to run reviews (in hours)
REVIEW_INTERVAL_HOURS = int(os.getenv("ARIA_REVIEW_INTERVAL", "24"))


@dataclass
class ImprovementProposal:
    """A proposed improvement from the reviewer."""
    id: str
    created_at: datetime = field(default_factory=datetime.now)
    
    # Problem
    problem_type: str = ""  # error, performance, reliability, feature
    problem_description: str = ""
    evidence: List[str] = field(default_factory=list)  # Log excerpts
    
    # Solution
    solution_description: str = ""
    file_path: str = ""
    code_diff: str = ""
    
    # Assessment
    risk_level: int = 3  # 1-5 scale
    risk_factors: List[str] = field(default_factory=list)
    expected_impact: str = ""
    estimated_effort: str = ""  # low, medium, high
    
    # Status
    status: str = "pending"  # pending, approved, rejected, applied
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d


class OpusReviewer:
    """
    AI-powered code reviewer using Claude Opus.
    
    Reviews Aria's logs and proposes improvements.
    """
    
    def __init__(self, api_key: str = ANTHROPIC_API_KEY):
        self.api_key = api_key
        self.http = httpx.AsyncClient(timeout=120.0)
        self.proposals: Dict[str, ImprovementProposal] = {}
        self._proposal_counter = 0
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    def _generate_proposal_id(self) -> str:
        """Generate unique proposal ID."""
        self._proposal_counter += 1
        return f"IMP-{datetime.now().strftime('%Y%m%d')}-{self._proposal_counter:04d}"
    
    async def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4000
    ) -> tuple[str, int, int]:
        """
        Call Claude API.
        
        Returns:
            (response_text, input_tokens, output_tokens)
        """
        try:
            response = await self.http.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": REVIEW_MODEL,
                    "max_tokens": max_tokens,
                    "system": system_prompt,
                    "messages": [{"role": "user", "content": user_prompt}]
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Claude API error: {response.text}")
                return "", 0, 0
            
            data = response.json()
            text = data["content"][0]["text"]
            input_tokens = data["usage"]["input_tokens"]
            output_tokens = data["usage"]["output_tokens"]
            
            return text, input_tokens, output_tokens
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            return "", 0, 0
    
    async def analyze_logs(self, improvement_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze logs and identify issues.
        
        Returns a list of identified issues.
        """
        # Import cost tracker
        try:
            from .cost_tracker import get_cost_tracker, can_spend
        except ImportError:
            from sovereign.cost_tracker import get_cost_tracker, can_spend
        
        # Check budget
        estimated_cost = 0.50  # Rough estimate for analysis
        if not can_spend(estimated_cost):
            logger.warning("Insufficient budget for log analysis")
            return []
        
        system_prompt = """You are an expert code reviewer and systems analyst. 
Your job is to analyze logs from an AI assistant system called Aria and identify 
issues that could be fixed or improved.

Focus on:
1. Recurring errors that indicate bugs
2. Slow response times that could be optimized
3. Failed operations that need better error handling
4. Patterns suggesting missing features or capabilities

For each issue, provide:
- Type: error, performance, reliability, or feature
- Description: What the problem is
- Evidence: Specific log entries showing the issue
- Severity: 1 (minor) to 5 (critical)

Output your findings as a JSON array."""

        user_prompt = f"""Analyze these logs from the last 24 hours:

ERROR SUMMARY:
{json.dumps(improvement_data.get('errors', {}), indent=2)}

PERFORMANCE METRICS:
{json.dumps(improvement_data.get('performance', {}), indent=2)}

RECENT LOG SAMPLES (last 50):
{json.dumps(improvement_data.get('recent_logs', [])[:50], indent=2)}

Identify issues that should be fixed. Output as JSON array."""

        response, input_tokens, output_tokens = await self._call_claude(
            system_prompt, user_prompt, max_tokens=2000
        )
        
        # Log cost
        cost_tracker = get_cost_tracker()
        cost_tracker.log_cost(
            category="analysis",
            model=REVIEW_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            description="Log analysis for issues"
        )
        
        # Parse response
        try:
            # Extract JSON from response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            
            issues = json.loads(json_str.strip())
            logger.info(f"Identified {len(issues)} issues from logs")
            return issues
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse issues: {e}")
            return []
    
    async def generate_fix(
        self,
        issue: Dict[str, Any],
        file_content: str,
        file_path: str
    ) -> Optional[ImprovementProposal]:
        """
        Generate a fix for an identified issue.
        
        Returns an ImprovementProposal or None if no fix could be generated.
        """
        try:
            from .cost_tracker import get_cost_tracker, can_spend
        except ImportError:
            from sovereign.cost_tracker import get_cost_tracker, can_spend
        
        # Check budget
        estimated_cost = 0.30
        if not can_spend(estimated_cost):
            logger.warning("Insufficient budget for fix generation")
            return None
        
        system_prompt = """You are an expert Python developer. Given a code file and 
an issue description, generate a fix.

Your output MUST be valid JSON with these fields:
{
    "solution_description": "What the fix does",
    "risk_level": 1-5 (1=safe config change, 5=critical system change),
    "risk_factors": ["list", "of", "risks"],
    "expected_impact": "What improvement to expect",
    "estimated_effort": "low/medium/high",
    "code_diff": "The unified diff to apply"
}

For the code_diff, use unified diff format:
--- a/file.py
+++ b/file.py
@@ -line,count +line,count @@
 context
-old line
+new line
 context

Be conservative - prefer small, focused fixes over large refactors."""

        user_prompt = f"""Fix this issue in {file_path}:

ISSUE TYPE: {issue.get('type', 'unknown')}
DESCRIPTION: {issue.get('description', '')}
EVIDENCE: {json.dumps(issue.get('evidence', []))}
SEVERITY: {issue.get('severity', 3)}

CURRENT FILE CONTENT:
```python
{file_content[:10000]}  # Truncate if needed
```

Generate a fix. Output as JSON."""

        response, input_tokens, output_tokens = await self._call_claude(
            system_prompt, user_prompt, max_tokens=3000
        )
        
        # Log cost
        cost_tracker = get_cost_tracker()
        cost_tracker.log_cost(
            category="fix_generation",
            model=REVIEW_MODEL,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            description=f"Generate fix for {issue.get('type', 'issue')}"
        )
        
        # Parse response
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            else:
                json_str = response
            
            fix_data = json.loads(json_str.strip())
            
            proposal = ImprovementProposal(
                id=self._generate_proposal_id(),
                problem_type=issue.get("type", "unknown"),
                problem_description=issue.get("description", ""),
                evidence=issue.get("evidence", []),
                solution_description=fix_data.get("solution_description", ""),
                file_path=file_path,
                code_diff=fix_data.get("code_diff", ""),
                risk_level=fix_data.get("risk_level", 3),
                risk_factors=fix_data.get("risk_factors", []),
                expected_impact=fix_data.get("expected_impact", ""),
                estimated_effort=fix_data.get("estimated_effort", "medium")
            )
            
            self.proposals[proposal.id] = proposal
            return proposal
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse fix: {e}")
            return None
    
    async def run_review(self, improvement_data: Dict[str, Any]) -> List[ImprovementProposal]:
        """
        Run a full review cycle.
        
        1. Analyze logs for issues
        2. For each issue, try to generate a fix
        3. Return all proposals
        """
        logger.info("Starting Opus review cycle...")
        
        # Step 1: Analyze logs
        issues = await self.analyze_logs(improvement_data)
        
        if not issues:
            logger.info("No issues identified in logs")
            return []
        
        proposals = []
        
        # Step 2: Generate fixes for top issues
        for issue in issues[:5]:  # Limit to top 5 issues
            # Determine which file to fix
            file_path = self._identify_file_to_fix(issue)
            if not file_path:
                continue
            
            # Read file content
            full_path = Path(WORKSPACE_ROOT) / file_path
            if not full_path.exists():
                continue
            
            try:
                file_content = full_path.read_text()
            except Exception as e:
                logger.error(f"Failed to read {file_path}: {e}")
                continue
            
            # Generate fix
            proposal = await self.generate_fix(issue, file_content, file_path)
            if proposal:
                proposals.append(proposal)
        
        logger.info(f"Review complete: {len(proposals)} proposals generated")
        return proposals
    
    def _identify_file_to_fix(self, issue: Dict[str, Any]) -> Optional[str]:
        """
        Identify which file an issue relates to.
        
        Uses evidence and description to determine the file.
        """
        # Look for file paths in evidence
        evidence = issue.get("evidence", [])
        description = issue.get("description", "")
        
        # Common patterns
        import re
        file_patterns = [
            r"([a-zA-Z_/]+\.py)",
            r"File \"([^\"]+)\"",
            r"in ([a-zA-Z_]+\.py)",
        ]
        
        all_text = description + " " + " ".join(str(e) for e in evidence)
        
        for pattern in file_patterns:
            matches = re.findall(pattern, all_text)
            for match in matches:
                # Validate it's a real file
                if "/" not in match:
                    # Try common locations
                    for prefix in ["telegram/", "brain/", "trading/", "sovereign/", ""]:
                        check_path = prefix + match
                        if (Path(WORKSPACE_ROOT) / check_path).exists():
                            return check_path
                elif (Path(WORKSPACE_ROOT) / match).exists():
                    return match
        
        return None
    
    def get_pending_proposals(self) -> List[ImprovementProposal]:
        """Get all pending proposals."""
        return [p for p in self.proposals.values() if p.status == "pending"]
    
    def get_proposal(self, proposal_id: str) -> Optional[ImprovementProposal]:
        """Get a specific proposal."""
        return self.proposals.get(proposal_id)
    
    def approve_proposal(self, proposal_id: str) -> bool:
        """Mark a proposal as approved."""
        if proposal_id in self.proposals:
            self.proposals[proposal_id].status = "approved"
            return True
        return False
    
    def reject_proposal(self, proposal_id: str, reason: str = "") -> bool:
        """Mark a proposal as rejected."""
        if proposal_id in self.proposals:
            self.proposals[proposal_id].status = "rejected"
            return True
        return False


# ============================================================================
# REVIEW DAEMON
# ============================================================================

class ReviewDaemon:
    """
    Background daemon that runs periodic reviews.
    """
    
    def __init__(self, interval_hours: int = REVIEW_INTERVAL_HOURS):
        self.interval_hours = interval_hours
        self.reviewer = OpusReviewer()
        self.running = False
        self._last_review: Optional[datetime] = None
    
    async def start(self):
        """Start the review daemon."""
        self.running = True
        logger.info(f"Review daemon started (interval: {self.interval_hours}h)")
        
        while self.running:
            try:
                # Check if it's time for a review
                if self._should_review():
                    await self._run_review()
                    self._last_review = datetime.now()
                
                # Sleep for an hour before checking again
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Review daemon error: {e}")
                await asyncio.sleep(300)  # Retry in 5 minutes
    
    def _should_review(self) -> bool:
        """Check if it's time for a review."""
        if self._last_review is None:
            return True
        
        elapsed = datetime.now() - self._last_review
        return elapsed.total_seconds() >= self.interval_hours * 3600
    
    async def _run_review(self):
        """Run a review cycle."""
        try:
            from ..aria_logging import get_logger
        except ImportError:
            from aria_logging.structured_logger import get_logger
        
        logger.info("Running scheduled review...")
        
        # Get improvement data from structured logger
        struct_logger = get_logger()
        improvement_data = struct_logger.get_improvement_data(hours=24)
        
        # Run review
        proposals = await self.reviewer.run_review(improvement_data)
        
        if proposals:
            # Notify about new proposals
            await self._notify_proposals(proposals)
    
    async def _notify_proposals(self, proposals: List[ImprovementProposal]):
        """Send notification about new proposals."""
        try:
            import httpx
            
            message = f"**New Improvement Proposals ({len(proposals)})**\n\n"
            
            for p in proposals:
                risk_emoji = ["", "🟢", "🟡", "🟠", "🔴", "⛔"][p.risk_level]
                message += f"{risk_emoji} `{p.id}`: {p.problem_description[:50]}...\n"
            
            message += f"\nUse `/improvements` to review."
            
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.getenv("SUNHEART_CHAT_ID", "")
            
            if bot_token and chat_id:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{bot_token}/sendMessage",
                        json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
                    )
                    
        except Exception as e:
            logger.error(f"Failed to notify proposals: {e}")
    
    def stop(self):
        """Stop the review daemon."""
        self.running = False


# ============================================================================
# SINGLETON
# ============================================================================

_reviewer: Optional[OpusReviewer] = None
_daemon: Optional[ReviewDaemon] = None


def get_reviewer() -> OpusReviewer:
    """Get or create global reviewer."""
    global _reviewer
    if _reviewer is None:
        _reviewer = OpusReviewer()
    return _reviewer


def get_daemon() -> ReviewDaemon:
    """Get or create global review daemon."""
    global _daemon
    if _daemon is None:
        _daemon = ReviewDaemon()
    return _daemon


async def run_manual_review() -> List[ImprovementProposal]:
    """Run a manual review (for testing)."""
    try:
        from ..aria_logging import get_logger
    except ImportError:
        from aria_logging.structured_logger import get_logger
    
    reviewer = get_reviewer()
    struct_logger = get_logger()
    improvement_data = struct_logger.get_improvement_data(hours=24)
    return await reviewer.run_review(improvement_data)


