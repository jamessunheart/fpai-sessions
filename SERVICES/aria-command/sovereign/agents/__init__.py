#!/usr/bin/env python3
"""
ARIA ASCENSION - MULTI-AGENT SWARM
==================================

Specialized agents that collaborate on complex tasks:
- Trader Agent: Market analysis, signals
- Builder Agent: Code changes, deployments
- Monitor Agent: System health, alerts
- Researcher Agent: Web search, knowledge
- Orchestrator: Routes requests, manages consensus

Consensus Protocol:
- Low stakes: Single agent decides
- Medium stakes: 2 agents must agree
- High stakes: All relevant agents + human approval
"""

from .base import BaseAgent, AgentCapability, AgentResponse
from .trader import TraderAgent
from .builder import BuilderAgent
from .monitor import MonitorAgent
from .researcher import ResearcherAgent
from .orchestrator import Orchestrator, get_orchestrator

__all__ = [
    "BaseAgent",
    "AgentCapability",
    "AgentResponse",
    "TraderAgent",
    "BuilderAgent",
    "MonitorAgent",
    "ResearcherAgent",
    "Orchestrator",
    "get_orchestrator"
]


