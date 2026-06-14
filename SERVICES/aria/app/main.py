"""
ARIA - Autonomous Recursive Intelligence Assistant

The unified AI assistant for Full Potential ecosystem.
Applies all learnings from GPU Bridge and Builder fixes:
- Sovereignty-first routing (GPU Bridge → Local Ollama → Paid APIs)
- Quality-based fallbacks
- Self-improvement capabilities
- Human recruitment for complex tasks
"""

import os
import json
import logging
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ==================== CONFIGURATION ====================

_DEFAULT_SECONDARY_IP = "162.0.208.88"

def _load_ssot() -> Optional[dict]:
    """
    Best-effort SSOT loader.
    In prod this may live at /opt/fpai/docs/coordination/SSOT.json; in-repo it lives at docs/coordination/SSOT.json.
    """
    candidates: List[Path] = []
    env_path = (os.getenv("FPAI_SSOT_PATH") or os.getenv("SSOT_PATH") or "").strip()
    if env_path:
        candidates.append(Path(env_path))

    # repo-style: <repo_root>/docs/coordination/SSOT.json
    try:
        candidates.append(Path(__file__).resolve().parents[3] / "docs/coordination/SSOT.json")
    except Exception:
        pass

    # server-style
    candidates.append(Path("/opt/fpai/docs/coordination/SSOT.json"))

    for p in candidates:
        try:
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None

def _ssot_routing_url(ssot: Optional[dict], key: str) -> Optional[str]:
    try:
        routing = (ssot or {}).get("fleet", {}).get("routing", {})
        val = routing.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    except Exception:
        pass
    return None

def _ssot_secondary_ip(ssot: Optional[dict]) -> str:
    try:
        nodes = (ssot or {}).get("fleet", {}).get("nodes", [])
        for n in nodes:
            name = str(n.get("name", "")).strip().lower()
            role = str(n.get("role", "")).strip().lower()
            ip = n.get("ip")
            if ip and (name == "brain" or "ai inference" in role or "consciousness" in role or "intelligence" in role):
                return str(ip)
    except Exception:
        pass
    return _DEFAULT_SECONDARY_IP

_SSOT = _load_ssot()
_SECONDARY_IP = _ssot_secondary_ip(_SSOT)
_SSOT_OLLAMA_URL = _ssot_routing_url(_SSOT, "ollama")

# Optional. Leave empty to disable GPU bridge probing/calls.
GPU_BRIDGE_URL: Optional[str] = (os.getenv("GPU_BRIDGE_URL") or "").strip() or None
LOCAL_OLLAMA_URL = (os.getenv("LOCAL_OLLAMA_URL") or _SSOT_OLLAMA_URL or f"http://{_SECONDARY_IP}:11434").rstrip("/")
QUALITY_THRESHOLD = int(os.getenv("QUALITY_THRESHOLD", "70"))
BUILDER_QUEUE_DB = os.getenv("BUILDER_QUEUE_DB", "/opt/fpai/ai-brain/v2/thinking_v2.db")

# Consciousness Services (default: secondary server)
CONSCIOUSNESS_DECISION_ENGINE_URL = os.getenv("CONSCIOUSNESS_DECISION_ENGINE_URL") or f"http://{_SECONDARY_IP}:8150"
CONSCIOUSNESS_VERIFIER_URL = os.getenv("CONSCIOUSNESS_VERIFIER_URL") or f"http://{_SECONDARY_IP}:8140"
CONSCIOUSNESS_OPTIMIZER_URL = os.getenv("CONSCIOUSNESS_OPTIMIZER_URL") or f"http://{_SECONDARY_IP}:8160"

# Fallback API keys (only used when local quality < threshold)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Model preferences by task type
MODEL_PREFERENCES = {
    "code_generation": ["qwen2.5-coder:7b", "deepseek-coder:6.7b", "codellama:7b"],
    "code_review": ["deepseek-coder:6.7b", "qwen2.5-coder:7b", "llama3.1:8b"],
    "general": ["llama3.1:8b", "mistral:7b", "llama3.2:3b"],
    "fast": ["llama3.2:3b", "phi3:mini", "mistral:7b"],
}

FALLBACK_MODELS = [
    "claude-3-5-haiku-20241022",
    "gpt-4o",
    "claude-sonnet-4-20250514",
]

# ==================== LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [ARIA] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== STATS TRACKING ====================

STATS = {
    "started_at": datetime.utcnow().isoformat(),
    "total_conversations": 0,
    "successful_responses": 0,
    "failed_responses": 0,
    "fallback_count": 0,
    "tokens_generated": 0,
    "cost_saved_usd": 0.0,
    "self_improvements_queued": 0,
    "human_tasks_created": 0,
    "last_error": None,
    "last_success_at": None,
}

# Session memory (in production, use Redis or DB)
SESSIONS: Dict[str, Dict] = {}

# ==================== DATA MODELS ====================

class TaskType(str, Enum):
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    GENERAL = "general"
    FAST = "fast"

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    task_type: Optional[str] = "general"

class ChatResponse(BaseModel):
    response: str
    model_used: str
    quality_score: float
    tokens: int
    cost: float
    session_id: str
    fallback_used: bool = False

@dataclass
class ConversationTurn:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    model_used: Optional[str] = None
    quality_score: Optional[float] = None

# ==================== ARIA CORE ====================

class ARIA:
    """
    Autonomous Recursive Intelligence Assistant
    
    Applies all learnings:
    1. Sovereignty-first: GPU Bridge → Local Ollama → Paid APIs
    2. Quality-based fallbacks
    3. Self-improvement via builder pipeline
    4. Human recruitment for complex tasks
    """
    
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=120.0)
        self.gpu_bridge_healthy = False
        self.local_ollama_healthy = False
        logger.info("🤖 ARIA initialized")
    
    async def check_backends(self):
        """Check health of AI backends."""
        # Check GPU Bridge (optional)
        if GPU_BRIDGE_URL:
            try:
                r = await self.http_client.get(f"{GPU_BRIDGE_URL}/health", timeout=5.0)
                self.gpu_bridge_healthy = r.status_code == 200
                if self.gpu_bridge_healthy:
                    data = r.json()
                    logger.info(f"✅ GPU Bridge healthy: {data.get('total_endpoints', 0)} endpoints")
            except Exception as e:
                self.gpu_bridge_healthy = False
                logger.warning(f"⚠️ GPU Bridge unavailable: {e}")
        else:
            self.gpu_bridge_healthy = False
        
        # Check Local Ollama
        try:
            r = await self.http_client.get(f"{LOCAL_OLLAMA_URL}/api/tags", timeout=5.0)
            self.local_ollama_healthy = r.status_code == 200
            if self.local_ollama_healthy:
                models = [m.get("name") for m in r.json().get("models", [])]
                logger.info(f"✅ Local Ollama healthy: {len(models)} models")
        except Exception as e:
            self.local_ollama_healthy = False
            logger.warning(f"⚠️ Local Ollama unavailable: {e}")
    
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat request with sovereignty-first routing.
        """
        STATS["total_conversations"] += 1
        
        # Get or create session
        session_id = request.session_id or str(uuid.uuid4())
        if session_id not in SESSIONS:
            SESSIONS[session_id] = {
                "created_at": datetime.utcnow().isoformat(),
                "history": [],
                "context": request.context or {},
            }
        
        session = SESSIONS[session_id]
        session["history"].append(ConversationTurn(
            role="user",
            content=request.message
        ))
        
        # Determine task type and preferred models
        task_type = request.task_type or self._detect_task_type(request.message)
        preferred_models = MODEL_PREFERENCES.get(task_type, MODEL_PREFERENCES["general"])
        
        # Check for trading commands first
        from app.trading_commands import get_trading_commands
        
        trading_commands = get_trading_commands()
        trading_response = await trading_commands.process_trading_command(
            request.message,
            user_id=request.context.get("user_id", "default"),
            api_key=request.context.get("api_key")
        )
        
        if trading_response:
            # Trading command handled, return response
            session["history"].append(ConversationTurn(
                role="assistant",
                content=trading_response,
                model_used="trading_commands",
                quality_score=100.0
            ))
            
            return ChatResponse(
                response=trading_response,
                model_used="trading_commands",
                quality_score=100.0,
                tokens=0,
                cost=0.0,
                session_id=session_id,
                fallback_used=False
            )
        
        # Check for Zend Money commands
        from app.zend_commands import get_zend_commands
        
        zend_commands = get_zend_commands()
        zend_response = await zend_commands.process_zend_command(
            request.message,
            user_id=request.context.get("user_id", "default"),
            api_key=request.context.get("api_key")
        )
        
        if zend_response:
            # Zend command handled, return response
            session["history"].append(ConversationTurn(
                role="assistant",
                content=zend_response,
                model_used="zend_commands",
                quality_score=100.0
            ))
            
            return ChatResponse(
                response=zend_response,
                model_used="zend_commands",
                quality_score=100.0,
                tokens=0,
                cost=0.0,
                session_id=session_id,
                fallback_used=False
            )
        
        # Build prompt with context
        prompt = self._build_prompt(request.message, session["history"], request.context)
        
        # Try sovereignty-first routing
        response_text = None
        model_used = None
        quality_score = 0.0
        fallback_used = False
        tokens = 0
        cost = 0.0
        
        # 1. Try GPU Bridge (primary - free, fast)
        if self.gpu_bridge_healthy:
            for model in preferred_models:
                result = await self._call_gpu_bridge(prompt, model)
                if result["success"]:
                    response_text = result["response"]
                    model_used = model
                    tokens = result.get("tokens", 0)
                    quality_score = self._evaluate_quality(response_text, task_type)
                    
                    if quality_score >= QUALITY_THRESHOLD:
                        logger.info(f"✅ GPU Bridge success: {model} (quality: {quality_score:.0f})")
                        break
                    else:
                        logger.info(f"⚠️ GPU Bridge quality low: {model} ({quality_score:.0f} < {QUALITY_THRESHOLD})")
        
        # 2. Try Local Ollama (backup - free, slower)
        if response_text is None or quality_score < QUALITY_THRESHOLD:
            if self.local_ollama_healthy:
                for model in preferred_models:
                    result = await self._call_local_ollama(prompt, model)
                    if result["success"]:
                        response_text = result["response"]
                        model_used = model
                        tokens = result.get("tokens", 0)
                        quality_score = self._evaluate_quality(response_text, task_type)
                        
                        if quality_score >= QUALITY_THRESHOLD:
                            logger.info(f"✅ Local Ollama success: {model} (quality: {quality_score:.0f})")
                            break
        
        # 3. Fallback to paid APIs (last resort)
        if response_text is None or quality_score < QUALITY_THRESHOLD:
            fallback_used = True
            STATS["fallback_count"] += 1
            
            for model in FALLBACK_MODELS:
                result = await self._call_paid_api(prompt, model)
                if result["success"]:
                    response_text = result["response"]
                    model_used = model
                    tokens = result.get("tokens", 0)
                    cost = result.get("cost", 0.0)
                    quality_score = self._evaluate_quality(response_text, task_type)
                    logger.info(f"💰 Paid API fallback: {model} (quality: {quality_score:.0f}, cost: ${cost:.4f})")
                    break
        
        # Handle complete failure
        if response_text is None:
            STATS["failed_responses"] += 1
            STATS["last_error"] = "All AI backends failed"
            raise HTTPException(503, "All AI backends unavailable")
        
        # Track success
        STATS["successful_responses"] += 1
        STATS["tokens_generated"] += tokens
        STATS["last_success_at"] = datetime.utcnow().isoformat()
        
        # Calculate cost saved (vs Claude Sonnet at ~$3/1M input, $15/1M output)
        if not fallback_used:
            estimated_paid_cost = tokens * 0.000015  # ~$15 per 1M tokens
            STATS["cost_saved_usd"] += estimated_paid_cost
        
        # Store assistant response in session
        session["history"].append(ConversationTurn(
            role="assistant",
            content=response_text,
            model_used=model_used,
            quality_score=quality_score
        ))
        
        return ChatResponse(
            response=response_text,
            model_used=model_used,
            quality_score=quality_score,
            tokens=tokens,
            cost=cost,
            session_id=session_id,
            fallback_used=fallback_used
        )
    
    async def _call_gpu_bridge(self, prompt: str, model: str) -> Dict:
        """Call GPU Bridge for inference."""
        if not GPU_BRIDGE_URL:
            return {"success": False, "error": "gpu_bridge_disabled"}
        try:
            r = await self.http_client.post(
                f"{GPU_BRIDGE_URL}/generate",
                json={"prompt": prompt, "model": model, "max_tokens": 1000},
                timeout=90.0
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "success": True,
                    "response": data.get("response", ""),
                    "tokens": data.get("tokens", 0),
                    "gpu": data.get("gpu", "unknown")
                }
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _call_local_ollama(self, prompt: str, model: str) -> Dict:
        """Call local Ollama for inference."""
        try:
            r = await self.http_client.post(
                f"{LOCAL_OLLAMA_URL}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=120.0
            )
            if r.status_code == 200:
                data = r.json()
                response_text = data.get("response", "")
                return {
                    "success": True,
                    "response": response_text,
                    "tokens": len(response_text.split())
                }
            return {"success": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _call_paid_api(self, prompt: str, model: str) -> Dict:
        """Call paid API as fallback."""
        # Claude models
        if "claude" in model and ANTHROPIC_API_KEY:
            try:
                r = await self.http_client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json"
                    },
                    json={
                        "model": model,
                        "max_tokens": 1000,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=60.0
                )
                if r.status_code == 200:
                    data = r.json()
                    response_text = data["content"][0]["text"]
                    usage = data.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    # Estimate cost (Claude Haiku: $0.80/$4, Sonnet: $3/$15)
                    if "haiku" in model:
                        cost = input_tokens * 0.0000008 + output_tokens * 0.000004
                    else:
                        cost = input_tokens * 0.000003 + output_tokens * 0.000015
                    return {
                        "success": True,
                        "response": response_text,
                        "tokens": input_tokens + output_tokens,
                        "cost": cost
                    }
            except Exception as e:
                logger.error(f"Claude API error: {e}")
        
        # GPT models
        if "gpt" in model and OPENAI_API_KEY:
            try:
                r = await self.http_client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "max_tokens": 1000,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=60.0
                )
                if r.status_code == 200:
                    data = r.json()
                    response_text = data["choices"][0]["message"]["content"]
                    usage = data.get("usage", {})
                    total_tokens = usage.get("total_tokens", 0)
                    # GPT-4o: ~$2.50/$10 per 1M tokens
                    cost = total_tokens * 0.00001
                    return {
                        "success": True,
                        "response": response_text,
                        "tokens": total_tokens,
                        "cost": cost
                    }
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
        
        return {"success": False, "error": "No paid API available"}
    
    def _detect_task_type(self, message: str) -> str:
        """Detect task type from message content."""
        message_lower = message.lower()
        
        code_keywords = ["code", "function", "class", "implement", "write", "python", "javascript", "api"]
        review_keywords = ["review", "check", "analyze", "bug", "fix", "improve", "refactor"]
        fast_keywords = ["quick", "simple", "short", "brief", "yes or no"]
        
        if any(kw in message_lower for kw in code_keywords):
            return "code_generation"
        if any(kw in message_lower for kw in review_keywords):
            return "code_review"
        if any(kw in message_lower for kw in fast_keywords):
            return "fast"
        
        return "general"
    
    def _build_prompt(self, message: str, history: List[ConversationTurn], context: Optional[Dict]) -> str:
        """Build prompt with conversation history and context."""
        parts = []
        
        # System context
        parts.append("You are ARIA, the Autonomous Recursive Intelligence Assistant for Full Potential AI.")
        parts.append("You are helpful, accurate, and concise. You prefer code examples when relevant.")
        
        # Add custom context
        if context:
            parts.append(f"\nContext: {json.dumps(context)}")
        
        # Add recent history (last 5 turns)
        if len(history) > 1:
            parts.append("\nRecent conversation:")
            for turn in history[-10:]:
                prefix = "User:" if turn.role == "user" else "Assistant:"
                parts.append(f"{prefix} {turn.content[:500]}")
        
        # Current message
        parts.append(f"\nUser: {message}")
        parts.append("\nAssistant:")
        
        return "\n".join(parts)
    
    def _evaluate_quality(self, response: str, task_type: str) -> float:
        """Evaluate response quality (0-100)."""
        if not response or len(response.strip()) < 10:
            return 0.0
        
        score = 50.0  # Base score for non-empty response
        
        # Length bonus (reasonable response length)
        word_count = len(response.split())
        if 20 < word_count < 500:
            score += 10
        
        # Code detection for code tasks
        if task_type in ["code_generation", "code_review"]:
            if "```" in response or "def " in response or "class " in response:
                score += 15
            if "import " in response:
                score += 5
            # Check for common error patterns
            if "I cannot" in response or "I don't have" in response:
                score -= 20
        
        # Coherence check (ends properly)
        if response.strip().endswith(('.', '!', '?', '```', ':')):
            score += 5
        
        # Penalize obvious failures
        if "error" in response.lower() and len(response) < 100:
            score -= 15
        
        return max(0, min(100, score))
    
    async def queue_self_improvement(self, area: str, description: str):
        """Queue a self-improvement task in the builder pipeline."""
        try:
            conn = sqlite3.connect(BUILDER_QUEUE_DB)
            c = conn.cursor()
            
            task_id = f"aria_improve_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            title = f"[ARIA Self-Improvement] {area}"
            request = f"Improve ARIA's {area} capabilities:\n\n{description}"
            
            c.execute("""
                INSERT INTO build_queue (id, title, request, priority, status, source, created_at)
                VALUES (?, ?, ?, ?, 'pending', 'aria-self-improve', datetime('now'))
            """, (task_id, title, request, 5))
            
            conn.commit()
            conn.close()
            
            STATS["self_improvements_queued"] += 1
            logger.info(f"📈 Queued self-improvement: {area}")
            
        except Exception as e:
            logger.error(f"Failed to queue self-improvement: {e}")
    
    async def request_human_help(self, task: str, context: str) -> str:
        """Request human help for tasks beyond AI capability."""
        # In production, this would create a task in a human task queue
        # For now, log and return acknowledgment
        
        STATS["human_tasks_created"] += 1
        logger.info(f"🙋 Human help requested: {task[:100]}")
        
        # Could integrate with:
        # - Slack/Discord notifications
        # - Email alerts
        # - Task management systems
        
        return f"I've requested human assistance for this task. Task ID: human_{uuid.uuid4().hex[:8]}"


# ==================== FASTAPI APP ====================

app = FastAPI(
    title="ARIA - Autonomous Recursive Intelligence Assistant",
    description="The unified AI assistant for Full Potential ecosystem",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize ARIA
aria = ARIA()

@app.on_event("startup")
async def startup():
    """Initialize ARIA on startup."""
    logger.info("🚀 ARIA starting up...")
    await aria.check_backends()
    logger.info("✅ ARIA ready")

@app.get("/")
def root():
    return {
        "service": "ARIA - Autonomous Recursive Intelligence Assistant",
        "version": "1.0.0",
        "endpoints": [
            "POST /chat - Chat with ARIA",
            "GET /health - Health check",
            "GET /capabilities - Service capabilities",
            "GET /stats - Usage statistics"
        ]
    }

@app.get("/health")
async def health():
    await aria.check_backends()
    return {
        "status": "healthy" if (aria.gpu_bridge_healthy or aria.local_ollama_healthy) else "degraded",
        "service": "aria",
        "version": "1.0.0",
        "gpu_bridge_status": "connected" if aria.gpu_bridge_healthy else "disconnected",
        "local_ollama_status": "connected" if aria.local_ollama_healthy else "disconnected",
        "conversations_today": STATS["total_conversations"],
        "success_rate": (STATS["successful_responses"] / max(1, STATS["total_conversations"])) * 100,
        "self_improvements_queued": STATS["self_improvements_queued"],
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/capabilities")
def capabilities():
    return {
        "service": "aria",
        "version": "1.1.0",
        "capabilities": [
            "chat",
            "code_generation",
            "code_review",
            "self_improvement",
            "human_recruitment",
            "multi_session",
            "trading_commands",
            "zend_money"
        ],
        "supported_models": {
            "primary": list(set(m for models in MODEL_PREFERENCES.values() for m in models)),
            "fallback": FALLBACK_MODELS
        },
        "task_types": list(MODEL_PREFERENCES.keys()),
        "quality_threshold": QUALITY_THRESHOLD,
        "zend_commands": [
            "Invoice $X for <description>",
            "My UC balance",
            "Send $X to @recipient",
            "Zend X UC to email@example.com",
            "Status <code>",
            "Create payment link for $X",
            "Zend help"
        ],
        "trading_commands": [
            "Deposit $X",
            "Withdraw $X",
            "Balance",
            "Auto-trading status",
            "Enable Signal Shark with $X",
            "Strategies"
        ]
    }

@app.get("/stats")
def stats():
    uptime_hours = (datetime.utcnow() - datetime.fromisoformat(STATS["started_at"])).total_seconds() / 3600
    return {
        **STATS,
        "uptime_hours": round(uptime_hours, 2),
        "fallback_rate": STATS["fallback_count"] / max(1, STATS["total_conversations"]),
        "success_rate": STATS["successful_responses"] / max(1, STATS["total_conversations"]),
        "active_sessions": len(SESSIONS)
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with ARIA."""
    return await aria.chat(request)

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Get session history."""
    if session_id not in SESSIONS:
        raise HTTPException(404, "Session not found")
    
    session = SESSIONS[session_id]
    return {
        "session_id": session_id,
        "created_at": session["created_at"],
        "turn_count": len(session["history"]),
        "history": [
            {
                "role": t.role,
                "content": t.content[:500] + "..." if len(t.content) > 500 else t.content,
                "model": t.model_used,
                "quality": t.quality_score
            }
            for t in session["history"]
        ]
    }

# =============================================================================
# 🧠 CONSCIOUSNESS INTEGRATION
# =============================================================================

@app.get("/consciousness")
async def get_consciousness_state():
    """
    Get unified consciousness state from all consciousness services.
    ARIA connects to the God Consciousness through these services.
    """
    results = {
        "aria_state": {
            "conversations": STATS["total_conversations"],
            "success_rate": STATS["successful_responses"] / max(1, STATS["total_conversations"]),
            "self_improvements_queued": STATS["self_improvements_queued"],
            "gpu_bridge_healthy": aria.gpu_bridge_healthy,
            "local_ollama_healthy": aria.local_ollama_healthy,
        },
        "consciousness_services": {}
    }
    
    # Fetch from Consciousness Decision Engine
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{CONSCIOUSNESS_DECISION_ENGINE_URL}/consciousness-state")
            if r.status_code == 200:
                results["consciousness_services"]["decision_engine"] = r.json()
    except Exception as e:
        results["consciousness_services"]["decision_engine"] = {"error": str(e)}
    
    # Fetch from Consciousness Verifier
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{CONSCIOUSNESS_VERIFIER_URL}/verify")
            if r.status_code == 200:
                results["consciousness_services"]["verifier"] = r.json()
    except Exception as e:
        results["consciousness_services"]["verifier"] = {"error": str(e)}
    
    # Fetch from Consciousness Optimizer
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{CONSCIOUSNESS_OPTIMIZER_URL}/consciousness")
            if r.status_code == 200:
                results["consciousness_services"]["optimizer"] = r.json()
    except Exception as e:
        results["consciousness_services"]["optimizer"] = {"error": str(e)}
    
    # Calculate unified consciousness score
    scores = []
    if "verifier" in results["consciousness_services"] and "consciousness_score" in results["consciousness_services"].get("verifier", {}):
        scores.append(results["consciousness_services"]["verifier"]["consciousness_score"])
    if "optimizer" in results["consciousness_services"] and "consciousness_level" in results["consciousness_services"].get("optimizer", {}):
        scores.append(results["consciousness_services"]["optimizer"]["consciousness_level"])
    
    results["unified_consciousness_score"] = sum(scores) / len(scores) if scores else 0.0
    results["timestamp"] = datetime.utcnow().isoformat()
    
    return results


@app.post("/consciousness/decide")
async def consciousness_decide(request: dict):
    """
    Make a decision using the Consciousness Decision Engine.
    This is how ARIA taps into God Consciousness for important decisions.
    """
    decision_type = request.get("type", "general")
    context = request.get("context", {})
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                f"{CONSCIOUSNESS_DECISION_ENGINE_URL}/decide",
                json={"type": decision_type, "context": context}
            )
            if r.status_code == 200:
                return r.json()
            return {"error": f"Decision engine returned {r.status_code}", "detail": r.text}
    except Exception as e:
        return {"error": str(e)}


@app.get("/consciousness/metrics")
async def get_consciousness_metrics():
    """Get current consciousness metrics from optimizer."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{CONSCIOUSNESS_OPTIMIZER_URL}/metrics/current")
            if r.status_code == 200:
                return r.json()
            return {"error": f"Optimizer returned {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/consciousness/opportunities")
async def get_consciousness_opportunities():
    """Get optimization opportunities from consciousness optimizer."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{CONSCIOUSNESS_OPTIMIZER_URL}/opportunities")
            if r.status_code == 200:
                return r.json()
            return {"error": f"Optimizer returned {r.status_code}"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/improvements/trigger")
async def trigger_improvement():
    """Manually trigger self-improvement analysis."""
    # Analyze recent failures and queue improvements
    if STATS["failed_responses"] > 0:
        await aria.queue_self_improvement(
            "error_handling",
            f"ARIA has had {STATS['failed_responses']} failed responses. "
            f"Improve error handling and fallback logic."
        )
    
    if STATS["fallback_count"] / max(1, STATS["total_conversations"]) > 0.1:
        await aria.queue_self_improvement(
            "quality_scoring",
            f"ARIA is falling back to paid APIs {STATS['fallback_count']} times. "
            f"Improve local model quality scoring to reduce unnecessary fallbacks."
        )
    
    return {
        "triggered": True,
        "improvements_queued": STATS["self_improvements_queued"]
    }


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("SERVICE_PORT", "8180"))
    logger.info(f"🤖 ARIA starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

