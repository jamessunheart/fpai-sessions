#!/usr/bin/env python3
"""
ARIA AI DIALOGUE ENGINE
=======================

Two-agent dialogue system for improvement proposals:

**Analyst Agent**: Proposes improvements based on summary
**Critic Agent**: Challenges proposals for specificity and value

Runs 2-4 rounds until consensus or max rounds reached.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import httpx

from .summarizer import InteractionSummary

logger = logging.getLogger("aria.reflection.dialogue")

# ============================================================================
# CONFIGURATION
# ============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DIALOGUE_MODEL = os.getenv("DIALOGUE_MODEL", "claude-sonnet-4-20250514")
MAX_DIALOGUE_ROUNDS = int(os.getenv("MAX_DIALOGUE_ROUNDS", "4"))
MIN_DIALOGUE_ROUNDS = int(os.getenv("MIN_DIALOGUE_ROUNDS", "2"))


class DialogueRole(str, Enum):
    ANALYST = "analyst"
    CRITIC = "critic"


@dataclass
class DialogueMessage:
    """A message in the dialogue."""
    role: DialogueRole
    content: str
    round_number: int
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "role": self.role.value,
            "content": self.content,
            "round_number": self.round_number,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ImprovementProposal:
    """A proposed improvement from dialogue."""
    title: str
    description: str
    rationale: str
    complexity: str  # low, medium, high
    risk: str  # low, medium, high
    estimated_impact: str  # low, medium, high
    files_affected: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "complexity": self.complexity,
            "risk": self.risk,
            "estimated_impact": self.estimated_impact,
            "files_affected": self.files_affected
        }


@dataclass
class DialogueResult:
    """Result of a dialogue session."""
    messages: List[DialogueMessage] = field(default_factory=list)
    proposals: List[ImprovementProposal] = field(default_factory=list)
    consensus_reached: bool = False
    rounds_completed: int = 0
    total_cost: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "messages": [m.to_dict() for m in self.messages],
            "proposals": [p.to_dict() for p in self.proposals],
            "consensus_reached": self.consensus_reached,
            "rounds_completed": self.rounds_completed,
            "total_cost": self.total_cost
        }
    
    def get_dialogue_transcript(self) -> str:
        """Get formatted transcript for spec generation."""
        lines = []
        for msg in self.messages:
            role_label = "ANALYST" if msg.role == DialogueRole.ANALYST else "CRITIC"
            lines.append(f"[{role_label} → Round {msg.round_number}]")
            lines.append(msg.content)
            lines.append("")
        return "\n".join(lines)


# ============================================================================
# PROMPTS
# ============================================================================

ANALYST_SYSTEM_PROMPT = """You are the ANALYST agent in a reflection dialogue about improving an AI assistant called Aria.

Your role:
1. Propose specific, actionable improvements based on the interaction summary
2. Defend your proposals against the Critic's challenges
3. Refine proposals based on valid criticism
4. Focus on HIGH-VALUE, LOW-RISK improvements

When proposing improvements:
- Be SPECIFIC (not "improve responses" but "add 60s cache for trading API calls")
- Consider implementation effort vs benefit
- Identify which files would need to change
- Estimate complexity (low/medium/high) and risk

When responding to criticism:
- Acknowledge valid points
- Refine or defend your proposal
- Be willing to drop low-value ideas

Signal consensus by saying "CONSENSUS:" followed by your final proposal(s)."""

CRITIC_SYSTEM_PROMPT = """You are the CRITIC agent in a reflection dialogue about improving an AI assistant called Aria.

Your role:
1. Challenge proposals for specificity and value
2. Ask "Is this worth the effort?"
3. Identify potential problems or risks
4. Push for CONCRETE, ACTIONABLE improvements

Good challenges:
- "How exactly would this be implemented?"
- "What could go wrong?"
- "Is this addressing the root cause?"
- "Would a simpler solution work?"

Bad challenges:
- Blocking without alternative suggestions
- Demanding perfection
- Ignoring valid improvements

When satisfied with a proposal, say "APPROVED:" and summarize what you approve.
You can approve some proposals while continuing to challenge others."""

ANALYST_INITIAL_PROMPT = """Based on the following interaction summary, propose 2-3 specific improvements for Aria:

{summary}

For each improvement, provide:
1. **Title**: Short name
2. **Description**: What exactly to change
3. **Rationale**: Why this helps (reference specific issues from summary)
4. **Complexity**: low/medium/high
5. **Risk**: low/medium/high
6. **Files affected**: Which files would change

Focus on improvements that:
- Address the most impactful issues
- Are feasible to implement
- Have clear success criteria"""

CRITIC_CHALLENGE_PROMPT = """The Analyst proposes:

{analyst_message}

Challenge these proposals. For each one:
1. Is it specific enough to implement?
2. Is it worth the effort?
3. What could go wrong?
4. Is there a simpler alternative?

If a proposal is solid, say "APPROVED: [proposal name]".
If it needs refinement, explain what's missing."""

ANALYST_RESPONSE_PROMPT = """The Critic responds:

{critic_message}

Address the criticism:
1. Acknowledge valid points
2. Refine your proposals if needed
3. Defend if the criticism is unfair
4. Drop low-value proposals

If you've reached agreement on proposals, start with "CONSENSUS:" and list final proposals.

Remember: The goal is HIGH-VALUE, LOW-RISK improvements."""


# ============================================================================
# DIALOGUE ENGINE
# ============================================================================

class DialogueEngine:
    """
    Orchestrates AI-to-AI dialogue for improvement proposals.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=120.0)
    
    async def close(self):
        await self.http.aclose()
    
    async def _call_claude(
        self, 
        system_prompt: str, 
        user_prompt: str,
        conversation_history: List[Dict] = None
    ) -> tuple[str, float]:
        """Call Claude API."""
        if not ANTHROPIC_API_KEY:
            raise ValueError("No Anthropic API key configured")
        
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_prompt})
        
        response = await self.http.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json={
                "model": DIALOGUE_MODEL,
                "max_tokens": 2000,
                "system": system_prompt,
                "messages": messages
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Anthropic API error: {response.text}")
        
        data = response.json()
        content = data["content"][0]["text"]
        
        # Calculate cost (Sonnet pricing)
        input_tokens = data.get("usage", {}).get("input_tokens", 0)
        output_tokens = data.get("usage", {}).get("output_tokens", 0)
        cost = (input_tokens * 0.003 + output_tokens * 0.015) / 1000
        
        return content, cost
    
    def _check_consensus(self, message: str) -> bool:
        """Check if message signals consensus."""
        indicators = ["CONSENSUS:", "APPROVED:", "agree with", "final proposal"]
        return any(ind.lower() in message.lower() for ind in indicators)
    
    def _extract_proposals(self, dialogue_messages: List[DialogueMessage]) -> List[ImprovementProposal]:
        """Extract final proposals from dialogue."""
        proposals = []
        
        # Look for consensus message
        for msg in reversed(dialogue_messages):
            if "CONSENSUS:" in msg.content.upper() or "APPROVED:" in msg.content.upper():
                # Parse proposals from this message
                content = msg.content
                
                # Simple extraction - look for numbered items or bullet points
                import re
                
                # Try to find structured proposals
                proposal_blocks = re.split(r'\n(?=\d+\.|[-*])', content)
                
                for block in proposal_blocks:
                    if len(block.strip()) < 20:
                        continue
                    
                    # Extract title (first line or bold text)
                    title_match = re.search(r'\*\*([^*]+)\*\*|^(.+?):', block)
                    title = title_match.group(1) or title_match.group(2) if title_match else "Improvement"
                    title = title.strip()[:100]
                    
                    # Default values
                    proposal = ImprovementProposal(
                        title=title,
                        description=block.strip()[:500],
                        rationale="From dialogue consensus",
                        complexity="medium",
                        risk="low",
                        estimated_impact="medium"
                    )
                    
                    # Try to extract complexity/risk
                    if "low complexity" in block.lower() or "simple" in block.lower():
                        proposal.complexity = "low"
                    elif "high complexity" in block.lower() or "complex" in block.lower():
                        proposal.complexity = "high"
                    
                    if "low risk" in block.lower() or "safe" in block.lower():
                        proposal.risk = "low"
                    elif "high risk" in block.lower() or "risky" in block.lower():
                        proposal.risk = "high"
                    
                    proposals.append(proposal)
                
                break
        
        return proposals[:3]  # Max 3 proposals
    
    async def run_dialogue(self, summary: InteractionSummary) -> DialogueResult:
        """
        Run a complete dialogue session.
        
        Returns DialogueResult with proposals.
        """
        logger.info("Starting AI-to-AI dialogue...")
        
        result = DialogueResult()
        summary_text = summary.to_prompt_text()
        
        # Round 1: Analyst proposes
        logger.info("Round 1: Analyst proposing...")
        analyst_prompt = ANALYST_INITIAL_PROMPT.format(summary=summary_text)
        analyst_response, cost1 = await self._call_claude(
            ANALYST_SYSTEM_PROMPT,
            analyst_prompt
        )
        
        result.messages.append(DialogueMessage(
            role=DialogueRole.ANALYST,
            content=analyst_response,
            round_number=1
        ))
        result.total_cost += cost1
        result.rounds_completed = 1
        
        # Dialogue loop
        analyst_history = [{"role": "assistant", "content": analyst_response}]
        critic_history = []
        
        for round_num in range(2, MAX_DIALOGUE_ROUNDS + 1):
            # Critic challenges
            logger.info(f"Round {round_num}: Critic challenging...")
            critic_prompt = CRITIC_CHALLENGE_PROMPT.format(
                analyst_message=analyst_response
            )
            critic_response, cost = await self._call_claude(
                CRITIC_SYSTEM_PROMPT,
                critic_prompt,
                critic_history
            )
            
            result.messages.append(DialogueMessage(
                role=DialogueRole.CRITIC,
                content=critic_response,
                round_number=round_num
            ))
            result.total_cost += cost
            critic_history.append({"role": "assistant", "content": critic_response})
            
            # Check if critic approved
            if self._check_consensus(critic_response) and round_num >= MIN_DIALOGUE_ROUNDS:
                result.consensus_reached = True
                result.rounds_completed = round_num
                logger.info(f"Consensus reached at round {round_num}")
                break
            
            # Analyst responds
            logger.info(f"Round {round_num}: Analyst responding...")
            analyst_prompt = ANALYST_RESPONSE_PROMPT.format(
                critic_message=critic_response
            )
            analyst_response, cost = await self._call_claude(
                ANALYST_SYSTEM_PROMPT,
                analyst_prompt,
                analyst_history
            )
            
            result.messages.append(DialogueMessage(
                role=DialogueRole.ANALYST,
                content=analyst_response,
                round_number=round_num
            ))
            result.total_cost += cost
            analyst_history.append({"role": "user", "content": critic_response})
            analyst_history.append({"role": "assistant", "content": analyst_response})
            result.rounds_completed = round_num
            
            # Check if analyst signals consensus
            if self._check_consensus(analyst_response):
                result.consensus_reached = True
                logger.info(f"Consensus reached at round {round_num}")
                break
        
        # Extract proposals
        result.proposals = self._extract_proposals(result.messages)
        
        logger.info(f"Dialogue complete: {result.rounds_completed} rounds, "
                   f"{len(result.proposals)} proposals, ${result.total_cost:.4f}")
        
        return result


# ============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# ============================================================================

_engine: Optional[DialogueEngine] = None


def get_dialogue_engine() -> DialogueEngine:
    """Get global dialogue engine instance."""
    global _engine
    if _engine is None:
        _engine = DialogueEngine()
    return _engine


async def run_dialogue(summary: InteractionSummary) -> DialogueResult:
    """Run dialogue on summary."""
    return await get_dialogue_engine().run_dialogue(summary)


