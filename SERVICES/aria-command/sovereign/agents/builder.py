#!/usr/bin/env python3
"""
ARIA ASCENSION - BUILDER AGENT
==============================

Specializes in code changes and development:
- Spec generation
- Code implementation
- Testing
- Deployment
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from .base import BaseAgent, AgentCapability, AgentResponse

logger = logging.getLogger("aria.agents.builder")


class BuilderAgent(BaseAgent):
    """
    Builder Agent - Expert in code changes and development.
    """
    
    name = "builder"
    description = "Expert in code generation, implementation, testing, and deployment"
    capabilities = [
        AgentCapability.CODE_GENERATION,
        AgentCapability.CODE_REVIEW,
        AgentCapability.DEPLOYMENT,
        AgentCapability.REASONING
    ]
    priority = 30
    
    # Build-related patterns
    BUILD_PATTERNS = [
        r'\b(build|create|implement|develop|code)\b',
        r'\b(fix|bug|error|issue|patch)\b',
        r'\b(feature|function|class|module|component)\b',
        r'\b(deploy|release|ship|launch)\b',
        r'\b(refactor|optimize|improve|enhance)\b',
        r'\b(file|code|script|function)\b',
    ]
    
    def __init__(self):
        super().__init__()
        self.workspace_root = Path(os.getenv("WORKSPACE_ROOT", "/opt/fpai"))
    
    async def can_handle(self, query: str, context: Dict = None) -> float:
        """Determine if this is a build-related query."""
        query_lower = query.lower()
        
        # Count pattern matches
        matches = 0
        for pattern in self.BUILD_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                matches += 1
        
        # Direct build commands
        if query_lower.startswith(("/build", "/deploy", "/fix", "/create")):
            return 0.95
        
        # Strong match
        if matches >= 2:
            return 0.85
        elif matches == 1:
            return 0.6
        
        return 0.1
    
    async def process(self, query: str, context: Dict = None) -> AgentResponse:
        """Process a build-related query."""
        query_lower = query.lower()
        
        try:
            # Determine what's being asked
            if "build" in query_lower or "create" in query_lower:
                return await self._handle_build_request(query, context)
            
            elif "deploy" in query_lower:
                return await self._handle_deploy_request(query, context)
            
            elif "fix" in query_lower or "bug" in query_lower:
                return await self._handle_fix_request(query, context)
            
            elif "status" in query_lower or "queue" in query_lower:
                return await self._get_build_status()
            
            else:
                return await self._general_build_response(query)
        
        except Exception as e:
            logger.error(f"Builder agent error: {e}")
            return self._create_response(
                success=False,
                content=f"Error processing build request: {str(e)}",
                confidence=0.3
            )
    
    async def _handle_build_request(self, query: str, context: Dict = None) -> AgentResponse:
        """Handle a build/create request."""
        # Generate a spec for what to build
        spec = self._generate_spec(query)
        
        content = f"""
🔨 **Build Request Received**

**Interpreted Task:**
{spec['description']}

**Proposed Changes:**
- Files to create/modify: {len(spec.get('files', []))} files
- Estimated complexity: {spec.get('complexity', 'medium')}

**Next Steps:**
1. Review the spec
2. Approve to begin implementation
3. Monitor progress

Do you want me to proceed with this build?
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.75,
            data={"spec": spec},
            reasoning="Generated build specification from request"
        )
    
    async def _handle_deploy_request(self, query: str, context: Dict = None) -> AgentResponse:
        """Handle a deployment request."""
        # Extract what to deploy
        service_match = re.search(r'deploy\s+(\w+)', query.lower())
        service = service_match.group(1) if service_match else "unknown"
        
        content = f"""
🚀 **Deployment Request: {service}**

**Pre-deployment Checklist:**
- [ ] Service health check
- [ ] Backup current version
- [ ] Configuration validation
- [ ] Dependencies verified

**Deployment Options:**
1. `/deploy {service} --dry-run` - Preview changes
2. `/deploy {service} --backup` - Deploy with backup
3. `/deploy {service} --rollback` - Rollback to previous

⚠️ Deployment requires approval. Would you like to proceed?
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.7,
            data={"service": service, "action": "deploy"},
            reasoning="Deployment requires human approval"
        )
    
    async def _handle_fix_request(self, query: str, context: Dict = None) -> AgentResponse:
        """Handle a fix/bug request."""
        content = """
🔧 **Fix Request Received**

To fix an issue, I need:
1. **Description** - What's broken?
2. **Location** - Which file/service?
3. **Expected behavior** - What should happen?
4. **Actual behavior** - What's happening?

You can also:
- Share an error message
- Point me to a log file
- Describe when the issue occurs

What details can you provide?
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.6,
            reasoning="Need more details to proceed with fix"
        )
    
    async def _get_build_status(self) -> AgentResponse:
        """Get current build queue status."""
        # Check for pending builds (would integrate with actual build system)
        
        content = """
📋 **Build Queue Status**

**Active:** None
**Pending:** 0
**Completed Today:** 0

**Recent Activity:**
- No recent builds

Use `/build <description>` to start a new build.
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.9,
            data={"queue": [], "active": None}
        )
    
    async def _general_build_response(self, query: str) -> AgentResponse:
        """Handle general build queries."""
        content = """
🔨 **Builder Agent**

I can help with development tasks:

**Commands:**
- `/build <description>` - Create something new
- `/fix <issue>` - Fix a bug or issue
- `/deploy <service>` - Deploy a service
- `/status` - Check build queue

**Examples:**
- "Build a new API endpoint for user stats"
- "Fix the login timeout issue"
- "Deploy whaletrack-live"

What would you like to build?
"""
        
        return self._create_response(
            success=True,
            content=content.strip(),
            confidence=0.7
        )
    
    def _generate_spec(self, query: str) -> Dict:
        """Generate a build specification from a query."""
        # Simple spec generation (in production, would use AI)
        return {
            "description": query,
            "files": [],
            "complexity": "medium",
            "estimated_time": "1-2 hours",
            "requires_approval": True
        }


