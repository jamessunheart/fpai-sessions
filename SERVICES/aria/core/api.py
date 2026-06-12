"""
ARIA CORE API
=============

The unified API that all Aria interfaces call.

POST /aria/chat - Single endpoint for all conversation
GET /aria/status - System status  
GET /aria/memory/{user_id} - User context
POST /aria/approve/{decision_id} - Approve pending decisions

All channels (Telegram, Dashboard, API) call this same core.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .memory import AriaMemory, get_memory
from .personality import AriaPersonality, get_personality, CommunicationStyle
from .router import AriaRouter, get_router, RouteResult
from .approvals import ApprovalSystem, get_approval_system, DecisionCategory

logger = logging.getLogger("aria.core")

# ==================== REQUEST/RESPONSE MODELS ====================

class ChatRequest(BaseModel):
    """Chat request from any channel."""
    user_id: str
    channel: str = "telegram"  # telegram, dashboard, api
    message: str
    context: Optional[Dict[str, Any]] = None
    
    # Optional overrides
    force_model: Optional[str] = None
    response_style: Optional[str] = None  # brief, detailed


class ChatResponse(BaseModel):
    """Chat response to any channel."""
    response: str
    model_used: str
    backend: str
    latency_ms: float
    tokens: int
    session_id: str
    
    # For transparency
    memory_used: bool = False
    personality_applied: bool = True


class StatusResponse(BaseModel):
    """System status response."""
    status: str
    backends: Dict[str, Any]
    stats: Dict[str, Any]
    pending_approvals: int


# ==================== ARIA CORE ====================

class AriaCore:
    """
    The unified brain for Aria.
    
    Integrates:
    - Memory: Persistent conversation context
    - Personality: Consistent voice and style
    - Router: Intelligent AI backend selection
    - Approvals: Smart decision-making
    """
    
    def __init__(self):
        self.memory = get_memory()
        self.personality = get_personality()
        self.router: Optional[AriaRouter] = None
        self.approvals = get_approval_system()
        
        self.stats = {
            "started_at": datetime.utcnow().isoformat(),
            "total_chats": 0,
            "by_channel": {"telegram": 0, "dashboard": 0, "api": 0}
        }
        
        logger.info("🤖 AriaCore initialized")
    
    async def initialize(self):
        """Initialize async components."""
        self.router = await get_router()
        await self.router.check_health()
        logger.info("✅ AriaCore ready")
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat request from any channel.
        
        This is THE main entry point for all Aria interactions.
        """
        self.stats["total_chats"] += 1
        self.stats["by_channel"][request.channel] = self.stats["by_channel"].get(request.channel, 0) + 1
        
        user_id = request.user_id
        message = request.message
        channel = request.channel
        
        # 1. Store user message in memory
        self.memory.add_message(
            user_id=user_id,
            role="user",
            content=message,
            channel=channel
        )
        
        # 2. Get user context
        user_context = self.memory.build_context(user_id)
        
        # 3. Determine user's communication style
        profile = self.memory.get_profile(user_id)
        user_style = CommunicationStyle(profile.communication_style)
        if request.response_style == "brief":
            user_style = CommunicationStyle.BRIEF
        
        # 4. Build system prompt with personality and context
        task_type = self._detect_task_type(message)
        system_prompt = self.personality.get_system_prompt(
            context=task_type,
            user_style=user_style,
            include_user_context=True
        )
        
        # Add user context to prompt
        context_text = self.memory.format_context_for_prompt(user_id)
        if context_text:
            system_prompt += f"\n\n{context_text}"
        
        # 5. Route to AI backend
        if not self.router:
            await self.initialize()
        
        result = await self.router.route(
            prompt=message,
            system_prompt=system_prompt,
            task_type=task_type,
            max_tokens=1000,
            temperature=0.7
        )
        
        # 6. Handle failure
        if not result.success:
            error_response = self.personality.format_error(
                f"I couldn't process that right now. {result.error or 'Please try again.'}"
            )
            return ChatResponse(
                response=error_response,
                model_used="error",
                backend="none",
                latency_ms=result.latency_ms,
                tokens=0,
                session_id=user_id,
                memory_used=bool(context_text),
                personality_applied=True
            )
        
        # 7. Format response based on personality
        response_length = self.personality.determine_response_length(message, task_type)
        formatted_response = self.personality.format_response(
            result.response,
            channel=channel,
            response_length=response_length
        )
        
        # 8. Store assistant response in memory
        self.memory.add_message(
            user_id=user_id,
            role="assistant",
            content=formatted_response,
            channel=channel,
            model_used=result.model
        )
        
        return ChatResponse(
            response=formatted_response,
            model_used=result.model,
            backend=result.backend,
            latency_ms=result.latency_ms,
            tokens=result.tokens,
            session_id=user_id,
            memory_used=bool(context_text),
            personality_applied=True
        )
    
    def _detect_task_type(self, message: str) -> str:
        """Detect task type for routing and personality."""
        message_lower = message.lower()
        
        # Trading
        if any(w in message_lower for w in ["trade", "signal", "position", "long", "short", "btc", "sol", "eth"]):
            return "trading"
        
        # Technical
        if any(w in message_lower for w in ["error", "debug", "deploy", "server", "service", "log"]):
            return "technical"
        
        # Brief queries
        if len(message) < 30 and message.count(" ") < 5:
            return "brief"
        
        return "general"
    
    async def get_status(self) -> StatusResponse:
        """Get system status."""
        if not self.router:
            await self.initialize()
        
        router_status = self.router.get_status()
        approval_stats = self.approvals.get_stats()
        pending = len(self.approvals.get_pending())
        
        return StatusResponse(
            status="healthy" if any(b["healthy"] for b in router_status["backends"].values()) else "degraded",
            backends=router_status["backends"],
            stats={
                **self.stats,
                "router": router_status["stats"],
                "approvals": approval_stats
            },
            pending_approvals=pending
        )
    
    async def get_user_memory(self, user_id: str) -> Dict:
        """Get user's context and history."""
        return self.memory.build_context(user_id)
    
    async def approve_decision(self, decision_id: str, approved_by: str = "user") -> Dict:
        """Approve a pending decision."""
        decision = await self.approvals.approve(decision_id, approved_by)
        if decision:
            return {"status": "approved", "decision": decision.action}
        return {"status": "not_found"}
    
    async def deny_decision(self, decision_id: str, denied_by: str = "user") -> Dict:
        """Deny a pending decision."""
        decision = await self.approvals.deny(decision_id, denied_by)
        if decision:
            return {"status": "denied", "decision": decision.action}
        return {"status": "not_found"}
    
    async def get_pending_decisions(self) -> List[Dict]:
        """Get all pending decisions."""
        decisions = self.approvals.get_pending()
        return [
            {
                "id": d.id,
                "category": d.category.value,
                "action": d.action,
                "reason": d.reason,
                "cost": d.estimated_cost,
                "risk": d.risk_level,
                "created_at": d.created_at
            }
            for d in decisions
        ]


# ==================== FASTAPI APP ====================

# Create app
app = FastAPI(
    title="Aria Core API",
    description="The unified AI assistant API for Full Potential",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global core instance
core: Optional[AriaCore] = None


@app.on_event("startup")
async def startup():
    """Initialize Aria Core on startup."""
    global core
    core = AriaCore()
    await core.initialize()
    logger.info("🚀 Aria Core API ready")


@app.get("/")
def root():
    """API root."""
    return {
        "service": "Aria Core API",
        "version": "2.0.0",
        "description": "Unified AI assistant for Full Potential",
        "endpoints": {
            "chat": "POST /aria/chat",
            "status": "GET /aria/status",
            "memory": "GET /aria/memory/{user_id}",
            "approve": "POST /aria/approve/{decision_id}",
            "deny": "POST /aria/deny/{decision_id}",
            "pending": "GET /aria/pending"
        }
    }


@app.get("/health")
async def health():
    """Health check."""
    status = await core.get_status() if core else StatusResponse(
        status="starting", backends={}, stats={}, pending_approvals=0
    )
    return {
        "status": status.status,
        "service": "aria-core",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/aria/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with Aria.
    
    This is the main entry point for all Aria interactions.
    Works for Telegram, Dashboard, and API clients.
    """
    if not core:
        raise HTTPException(503, "Aria Core not initialized")
    return await core.chat(request)


@app.get("/aria/status", response_model=StatusResponse)
async def status():
    """Get Aria status."""
    if not core:
        raise HTTPException(503, "Aria Core not initialized")
    return await core.get_status()


@app.get("/aria/memory/{user_id}")
async def get_memory(user_id: str):
    """Get user context and memory."""
    if not core:
        raise HTTPException(503, "Aria Core not initialized")
    return await core.get_user_memory(user_id)


@app.post("/aria/approve/{decision_id}")
async def approve(decision_id: str):
    """Approve a pending decision."""
    if not core:
        raise HTTPException(503, "Aria Core not initialized")
    return await core.approve_decision(decision_id)


@app.post("/aria/deny/{decision_id}")
async def deny(decision_id: str):
    """Deny a pending decision."""
    if not core:
        raise HTTPException(503, "Aria Core not initialized")
    return await core.deny_decision(decision_id)


@app.get("/aria/pending")
async def pending():
    """Get pending decisions."""
    if not core:
        raise HTTPException(503, "Aria Core not initialized")
    return {"pending": await core.get_pending_decisions()}


# ==================== PROACTIVE ENDPOINTS ====================

@app.get("/aria/proactive/status")
async def proactive_status():
    """Get proactive daemon status."""
    from .proactive import get_daemon
    daemon = get_daemon()
    return daemon.get_status()


@app.post("/aria/proactive/cycle")
async def force_proactive_cycle():
    """Force a proactive sensing cycle."""
    from .proactive import get_daemon
    daemon = get_daemon()
    return await daemon.force_cycle()


@app.get("/aria/proactive/digest")
async def get_digest_preview():
    """Get preview of pending digest items."""
    from .notifications import get_notifications
    notifications = get_notifications()
    return {
        "pending_count": notifications.get_pending_digest_count(),
        "preview": notifications.format_digest_preview()
    }


@app.post("/aria/proactive/digest/send")
async def send_digest_now():
    """Send the daily digest now."""
    from .proactive import get_daemon
    from .digest import generate_digest
    
    daemon = get_daemon()
    
    digest = await generate_digest(
        actions=daemon.actions_today,
        stats=daemon.stats,
        sensors=daemon.sensors
    )
    
    from .notifications import get_notifications
    notifications = get_notifications()
    await notifications.send_digest(digest)
    
    return {"status": "sent", "digest": digest}


@app.get("/aria/quick-status")
async def quick_status():
    """Get a quick system status check."""
    from .digest import generate_quick_status
    status = await generate_quick_status()
    return {"status": status}


@app.get("/aria/curiosity/insights")
async def get_insights():
    """Get recent curiosity insights."""
    from .curiosity import get_curiosity
    curiosity = get_curiosity()
    insights = curiosity.get_recent_insights(10)
    return {
        "insights": [
            {
                "id": i.id,
                "category": i.category,
                "observation": i.observation,
                "suggestion": i.suggestion,
                "confidence": i.confidence,
                "discovered_at": i.discovered_at
            }
            for i in insights
        ]
    }


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ARIA_CORE_PORT", "8180"))
    uvicorn.run(app, host="0.0.0.0", port=port)

