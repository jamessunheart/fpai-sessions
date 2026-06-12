#!/usr/bin/env python3
"""
ARIA ASCENSION - BASE AGENT
===========================

Base class for all specialized agents.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("aria.agents.base")


class AgentCapability(str, Enum):
    """Capabilities that agents can have."""
    TRADING = "trading"
    MARKET_ANALYSIS = "market_analysis"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    ALERTING = "alerting"
    WEB_SEARCH = "web_search"
    DOCUMENTATION = "documentation"
    REASONING = "reasoning"


@dataclass
class AgentResponse:
    """Response from an agent."""
    agent_name: str
    success: bool
    confidence: float
    content: str
    reasoning: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "agent_name": self.agent_name,
            "success": self.success,
            "confidence": self.confidence,
            "content": self.content,
            "reasoning": self.reasoning,
            "data": self.data,
            "tool_calls": self.tool_calls,
            "timestamp": self.timestamp.isoformat()
        }


class BaseAgent(ABC):
    """
    Base class for specialized agents.
    
    Each agent has:
    - A name and description
    - A set of capabilities
    - Domain expertise
    - Ability to process queries and return responses
    """
    
    name: str = "base"
    description: str = "Base agent"
    capabilities: List[AgentCapability] = []
    priority: int = 50  # Lower = higher priority
    
    def __init__(self):
        self.logger = logging.getLogger(f"aria.agents.{self.name}")
    
    @property
    def info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "priority": self.priority
        }
    
    @abstractmethod
    async def can_handle(self, query: str, context: Dict = None) -> float:
        """
        Determine if this agent can handle the query.
        Returns confidence score 0-1.
        """
        pass
    
    @abstractmethod
    async def process(self, query: str, context: Dict = None) -> AgentResponse:
        """
        Process a query and return response.
        """
        pass
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability."""
        return capability in self.capabilities
    
    async def validate_response(self, response: AgentResponse) -> bool:
        """Validate a response before returning."""
        if not response.content:
            return False
        if response.confidence < 0 or response.confidence > 1:
            return False
        return True
    
    def _create_response(
        self,
        success: bool,
        content: str,
        confidence: float,
        **kwargs
    ) -> AgentResponse:
        """Helper to create a response."""
        return AgentResponse(
            agent_name=self.name,
            success=success,
            confidence=confidence,
            content=content,
            **kwargs
        )


