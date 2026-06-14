#!/usr/bin/env python3
"""
ARIA ASCENSION - RESEARCHER AGENT
=================================

Specializes in knowledge gathering:
- Web search
- Documentation lookup
- Context retrieval
- Staying current
"""

import os
import re
import json
import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import BaseAgent, AgentCapability, AgentResponse

logger = logging.getLogger("aria.agents.researcher")


class ResearcherAgent(BaseAgent):
    """
    Researcher Agent - Expert in knowledge gathering and research.
    """
    
    name = "researcher"
    description = "Expert in web search, documentation, and knowledge retrieval"
    capabilities = [
        AgentCapability.WEB_SEARCH,
        AgentCapability.DOCUMENTATION,
        AgentCapability.REASONING
    ]
    priority = 40  # Lower priority - other agents handle specific domains
    
    # Research-related patterns
    RESEARCH_PATTERNS = [
        r'\b(search|find|lookup|research)\b',
        r'\b(what is|how to|why|explain|define)\b',
        r'\b(documentation|docs|guide|tutorial)\b',
        r'\b(news|update|latest|recent)\b',
        r'\b(learn|understand|know)\b',
    ]
    
    def __init__(self):
        super().__init__()
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def can_handle(self, query: str, context: Dict = None) -> float:
        """Determine if this is a research-related query."""
        query_lower = query.lower()
        
        # Count pattern matches
        matches = 0
        for pattern in self.RESEARCH_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                matches += 1
        
        # Direct research commands
        if query_lower.startswith(("/search", "/find", "/research", "/docs")):
            return 0.95
        
        # Questions are often research
        if query_lower.startswith(("what", "how", "why", "when", "where", "who")):
            return 0.6
        
        # Strong match
        if matches >= 2:
            return 0.8
        elif matches == 1:
            return 0.5
        
        return 0.2  # Researcher is a fallback for general queries
    
    async def process(self, query: str, context: Dict = None) -> AgentResponse:
        """Process a research-related query."""
        query_lower = query.lower()
        
        try:
            # Determine what type of research
            if "search" in query_lower:
                return await self._web_search(query)
            
            elif "docs" in query_lower or "documentation" in query_lower:
                return await self._documentation_search(query)
            
            elif query_lower.startswith(("what is", "what's", "define")):
                return await self._define_term(query)
            
            elif query_lower.startswith(("how to", "how do")):
                return await self._how_to_guide(query)
            
            else:
                return await self._general_research(query)
        
        except Exception as e:
            logger.error(f"Researcher agent error: {e}")
            return self._create_response(
                success=False,
                content=f"Error during research: {str(e)}",
                confidence=0.3
            )
    
    async def _web_search(self, query: str) -> AgentResponse:
        """Perform a web search."""
        # Extract search term
        search_match = re.search(r'search\s+(?:for\s+)?(.+)', query, re.IGNORECASE)
        search_term = search_match.group(1) if search_match else query
        
        content = f"""
🔍 **Web Search: {search_term}**

I can search the web for information about "{search_term}".

**Search Options:**
1. General web search
2. News articles
3. Technical documentation
4. GitHub repositories

Note: Web search requires API access. Would you like me to search?
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.6,
            data={"search_term": search_term},
            reasoning="Web search ready - needs confirmation"
        )
    
    async def _documentation_search(self, query: str) -> AgentResponse:
        """Search documentation."""
        content = """
📚 **Documentation Search**

I can search the following documentation:

**Internal Docs:**
- FPAI system documentation
- Service specifications
- API references
- Deployment guides

**External Docs:**
- Python documentation
- FastAPI docs
- Telegram Bot API
- Trading APIs

What documentation would you like to find?
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.7
        )
    
    async def _define_term(self, query: str) -> AgentResponse:
        """Define a term or concept."""
        # Extract term to define
        term_match = re.search(r'(?:what is|what\'s|define)\s+(.+?)(?:\?|$)', query, re.IGNORECASE)
        term = term_match.group(1).strip() if term_match else "the term"
        
        # Check if it's an internal concept
        internal_definitions = {
            "whaletrack": "WhaleTrack is the trading signal and analysis system. It has two components: Magnet (signal generation) and Live (trade execution).",
            "aria": "Aria is the AI assistant system that handles communication, automation, and system management.",
            "ascension": "Ascension is the system for evolving Aria into an autonomous, self-improving AI partner.",
            "clarity score": "A measure from 0-100 indicating how clear a trading signal is. Higher scores mean more confidence in the direction.",
            "bias strength": "A percentage indicating how strong the bullish or bearish sentiment is for an asset.",
        }
        
        term_lower = term.lower()
        for key, definition in internal_definitions.items():
            if key in term_lower:
                return self._create_response(
                    success=True,
                    content=f"📖 **{key.title()}**\n\n{definition}",
                    confidence=0.9,
                    data={"term": key, "definition": definition}
                )
        
        # General response for unknown terms
        content = f"""
📖 **Looking up: {term}**

I don't have a specific definition for "{term}" in my knowledge base.

Would you like me to:
1. Search the web for information
2. Check technical documentation
3. Look in the codebase

Or provide more context about what you're looking for?
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.5,
            data={"term": term}
        )
    
    async def _how_to_guide(self, query: str) -> AgentResponse:
        """Provide a how-to guide."""
        # Extract the task
        task_match = re.search(r'how (?:to|do I)\s+(.+?)(?:\?|$)', query, re.IGNORECASE)
        task = task_match.group(1).strip() if task_match else "do that"
        
        content = f"""
📝 **How To: {task}**

I'll help you figure out how to {task}.

To give you the best guidance, please tell me:
1. **Context** - What are you trying to achieve?
2. **Current state** - What have you tried so far?
3. **Environment** - What tools/systems are involved?

Or I can:
- Search for tutorials
- Check our documentation
- Look at similar implementations in the codebase
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.6,
            data={"task": task}
        )
    
    async def _general_research(self, query: str) -> AgentResponse:
        """Handle general research queries."""
        content = f"""
🔬 **Research Assistant**

I can help research: "{query}"

**My capabilities:**
- 🔍 Web search
- 📚 Documentation lookup
- 💻 Codebase search
- 📰 News and updates
- 📖 Definitions and explanations

What approach would work best for your question?
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.5,
            reasoning="Need more direction to provide specific research"
        )


