#!/usr/bin/env python3
"""
ARIA ASCENSION - ORCHESTRATOR
=============================

Routes requests to appropriate agents and manages consensus:
- Routes requests to appropriate agent(s)
- Combines outputs for complex queries
- Manages agent voting for significant decisions

Consensus Protocol:
- Low stakes: Single agent decides
- Medium stakes: 2 agents must agree
- High stakes: All relevant agents + human approval
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .base import BaseAgent, AgentResponse, AgentCapability
from .trader import TraderAgent
from .builder import BuilderAgent
from .monitor import MonitorAgent
from .researcher import ResearcherAgent

logger = logging.getLogger("aria.agents.orchestrator")


class StakeLevel(str, Enum):
    """Stakes level for decisions."""
    LOW = "low"           # Single agent
    MEDIUM = "medium"     # 2 agents agree
    HIGH = "high"         # All + human approval


@dataclass
class OrchestratorResult:
    """Result from the orchestrator."""
    query: str
    primary_response: AgentResponse
    supporting_responses: List[AgentResponse] = field(default_factory=list)
    consensus_reached: bool = True
    stake_level: StakeLevel = StakeLevel.LOW
    requires_approval: bool = False
    final_content: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "query": self.query,
            "primary_response": self.primary_response.to_dict(),
            "supporting_responses": [r.to_dict() for r in self.supporting_responses],
            "consensus_reached": self.consensus_reached,
            "stake_level": self.stake_level.value,
            "requires_approval": self.requires_approval,
            "final_content": self.final_content
        }


class Orchestrator:
    """
    Orchestrates multiple agents for complex queries.
    """
    
    # High-stakes keywords that require approval
    HIGH_STAKES_KEYWORDS = [
        "deploy", "restart", "delete", "remove",
        "trade", "buy", "sell", "execute",
        "payment", "send money", "transfer"
    ]
    
    # Medium-stakes keywords
    MEDIUM_STAKES_KEYWORDS = [
        "build", "create", "modify", "change",
        "configure", "update", "fix"
    ]
    
    def __init__(self):
        # Initialize all agents
        self.agents: Dict[str, BaseAgent] = {
            "trader": TraderAgent(),
            "builder": BuilderAgent(),
            "monitor": MonitorAgent(),
            "researcher": ResearcherAgent(),
        }
        
        self.logger = logging.getLogger("aria.orchestrator")
    
    async def process(
        self,
        query: str,
        context: Dict = None,
        require_consensus: bool = False
    ) -> OrchestratorResult:
        """
        Process a query through the appropriate agent(s).
        """
        # Determine stake level
        stake_level = self._determine_stake_level(query)
        
        # Get agent scores
        scores = await self._score_agents(query, context)
        
        # Sort by score
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        self.logger.debug(f"Agent scores: {sorted_agents}")
        
        if not sorted_agents or sorted_agents[0][1] < 0.3:
            # No agent confident enough - use researcher as fallback
            primary_agent = self.agents["researcher"]
            primary_response = await primary_agent.process(query, context)
        else:
            # Use the most confident agent
            primary_name, primary_score = sorted_agents[0]
            primary_agent = self.agents[primary_name]
            primary_response = await primary_agent.process(query, context)
        
        # For medium/high stakes, get supporting opinions
        supporting_responses = []
        consensus_reached = True
        
        if stake_level in [StakeLevel.MEDIUM, StakeLevel.HIGH]:
            supporting_responses = await self._get_supporting_responses(
                query, context, sorted_agents[1:3]  # Top 2-3 other agents
            )
            
            # Check consensus
            if stake_level == StakeLevel.MEDIUM:
                consensus_reached = self._check_consensus(
                    primary_response, supporting_responses, min_agree=1
                )
            else:  # HIGH
                consensus_reached = self._check_consensus(
                    primary_response, supporting_responses, min_agree=2
                )
        
        # Determine if approval needed
        requires_approval = (
            stake_level == StakeLevel.HIGH or
            (stake_level == StakeLevel.MEDIUM and not consensus_reached)
        )
        
        # Generate final content
        final_content = self._generate_final_response(
            primary_response,
            supporting_responses,
            consensus_reached,
            requires_approval
        )
        
        return OrchestratorResult(
            query=query,
            primary_response=primary_response,
            supporting_responses=supporting_responses,
            consensus_reached=consensus_reached,
            stake_level=stake_level,
            requires_approval=requires_approval,
            final_content=final_content
        )
    
    def _determine_stake_level(self, query: str) -> StakeLevel:
        """Determine the stake level of a query."""
        query_lower = query.lower()
        
        # Check for high stakes
        for keyword in self.HIGH_STAKES_KEYWORDS:
            if keyword in query_lower:
                return StakeLevel.HIGH
        
        # Check for medium stakes
        for keyword in self.MEDIUM_STAKES_KEYWORDS:
            if keyword in query_lower:
                return StakeLevel.MEDIUM
        
        return StakeLevel.LOW
    
    async def _score_agents(
        self,
        query: str,
        context: Dict = None
    ) -> Dict[str, float]:
        """Get confidence scores from all agents."""
        scores = {}
        
        # Score all agents in parallel
        tasks = [
            self._score_agent(name, agent, query, context)
            for name, agent in self.agents.items()
        ]
        
        results = await asyncio.gather(*tasks)
        
        for name, score in results:
            scores[name] = score
        
        return scores
    
    async def _score_agent(
        self,
        name: str,
        agent: BaseAgent,
        query: str,
        context: Dict = None
    ) -> Tuple[str, float]:
        """Score a single agent."""
        try:
            score = await agent.can_handle(query, context)
            return (name, score)
        except Exception as e:
            self.logger.error(f"Error scoring agent {name}: {e}")
            return (name, 0.0)
    
    async def _get_supporting_responses(
        self,
        query: str,
        context: Dict,
        supporting_agents: List[Tuple[str, float]]
    ) -> List[AgentResponse]:
        """Get supporting responses from other agents."""
        responses = []
        
        for name, score in supporting_agents:
            if score < 0.3:  # Skip low-confidence agents
                continue
            
            try:
                agent = self.agents[name]
                response = await agent.process(query, context)
                responses.append(response)
            except Exception as e:
                self.logger.error(f"Error getting supporting response from {name}: {e}")
        
        return responses
    
    def _check_consensus(
        self,
        primary: AgentResponse,
        supporting: List[AgentResponse],
        min_agree: int = 1
    ) -> bool:
        """
        Check if agents agree.
        
        Agreement criteria:
        - All successful responses
        - No contradictory recommendations
        """
        if not supporting:
            return True  # No one to disagree
        
        # Count agreements
        agreements = 0
        
        for response in supporting:
            if response.success == primary.success:
                agreements += 1
        
        return agreements >= min_agree
    
    def _generate_final_response(
        self,
        primary: AgentResponse,
        supporting: List[AgentResponse],
        consensus: bool,
        requires_approval: bool
    ) -> str:
        """Generate the final response content."""
        content = primary.content
        
        # Add supporting insights if any
        if supporting:
            insights = []
            for response in supporting:
                if response.reasoning:
                    insights.append(f"• {response.agent_name}: {response.reasoning}")
            
            if insights:
                content += f"\n\n**Additional Insights:**\n" + "\n".join(insights)
        
        # Add consensus notice
        if not consensus:
            content += "\n\n⚠️ **Note:** Agents did not fully agree on this response."
        
        # Add approval notice
        if requires_approval:
            content += "\n\n🔐 **Approval Required:** This action needs your confirmation."
        
        return content
    
    # ========================================================================
    # CONVENIENCE METHODS
    # ========================================================================
    
    async def quick_route(self, query: str) -> AgentResponse:
        """Quick single-agent routing without consensus."""
        result = await self.process(query, require_consensus=False)
        return result.primary_response
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get a specific agent."""
        return self.agents.get(name)
    
    def list_agents(self) -> List[Dict]:
        """List all available agents."""
        return [agent.info for agent in self.agents.values()]
    
    async def ask_all(
        self,
        query: str,
        context: Dict = None
    ) -> Dict[str, AgentResponse]:
        """Ask all agents the same query."""
        tasks = [
            self._ask_agent(name, agent, query, context)
            for name, agent in self.agents.items()
        ]
        
        results = await asyncio.gather(*tasks)
        
        return {name: response for name, response in results}
    
    async def _ask_agent(
        self,
        name: str,
        agent: BaseAgent,
        query: str,
        context: Dict = None
    ) -> Tuple[str, AgentResponse]:
        """Ask a single agent."""
        try:
            response = await agent.process(query, context)
            return (name, response)
        except Exception as e:
            return (name, AgentResponse(
                agent_name=name,
                success=False,
                confidence=0,
                content=f"Error: {str(e)}"
            ))


# ============================================================================
# SINGLETON
# ============================================================================

_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    """Get global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


async def route_query(query: str, context: Dict = None) -> OrchestratorResult:
    """Route a query through the orchestrator."""
    return await get_orchestrator().process(query, context)


async def quick_answer(query: str) -> AgentResponse:
    """Get a quick answer from the best agent."""
    return await get_orchestrator().quick_route(query)


