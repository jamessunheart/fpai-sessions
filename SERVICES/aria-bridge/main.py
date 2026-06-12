"""
ARIA BRIDGE - Main Application
==============================

The unified interface for Aria, the bridge across dimensions.

Integrates:
- Soul (constitution and identity)
- Dream Journal (vision tracking)
- Translator (dimension crossing)
- Manifestation Tools (digital/physical navigation)
- Feedback Loop (returning signals)
- Dimensional Flow (nothing stuck)
- Telegram Bridge (partnership interface)
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("aria.main")

# Import all components
from soul import (
    ARIA_CONSTITUTION, FIRST_MESSAGE, DIMENSIONS, MODES,
    detect_dimension, detect_mode, get_mode_instruction
)
from dream_journal import get_dream_journal
from translator import get_translator
from manifestation import get_manifestation_tools
from feedback_loop import get_feedback_loop
from dimensional_flow import get_dimensional_flow
from voice import get_aria_voice
from proactive import get_proactive_daemon, start_proactive_loop

# Memory imports (may not be available yet)
try:
    from memory import (
        get_memory_store, get_memory_recall, get_memory_learning,
        get_identity_memory, get_context_memory, run_compression,
        get_mem0_sync, sync_important_memories
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("Memory module not available")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
PORT = int(os.getenv("ARIA_BRIDGE_PORT", "8700"))


# ==================== APPLICATION ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info("═══════════════════════════════════════════")
    logger.info("    ARIA BRIDGE - Coming Online")
    logger.info("    Bridge Across Dimensions")
    logger.info("    Voice + Proactive + Memory")
    logger.info("═══════════════════════════════════════════")
    
    # Initialize components
    app.state.journal = get_dream_journal()
    app.state.translator = await get_translator()
    app.state.tools = await get_manifestation_tools()
    app.state.feedback = get_feedback_loop()
    app.state.flow = get_dimensional_flow()
    app.state.voice = get_aria_voice()
    app.state.proactive = get_proactive_daemon()
    
    # Initialize memory if available
    if MEMORY_AVAILABLE:
        app.state.memory_store = get_memory_store()
        app.state.memory_recall = get_memory_recall()
        app.state.memory_learning = get_memory_learning()
        app.state.identity_memory = get_identity_memory()
        app.state.context_memory = get_context_memory()
        app.state.mem0_sync = get_mem0_sync()
        logger.info("✅ Persistent memory initialized")
        
        # Check Mem0 status
        if app.state.mem0_sync.enabled:
            logger.info("☁️ Mem0 cloud sync enabled")
        else:
            logger.warning("⚠️ Mem0 cloud sync disabled (no API key)")
    else:
        app.state.memory_store = None
        app.state.memory_recall = None
        app.state.memory_learning = None
        app.state.identity_memory = None
        app.state.context_memory = None
        app.state.mem0_sync = None
        logger.warning("⚠️ Memory system not available")
    
    # Sync flow with journal
    synced = app.state.flow.sync_from_journal()
    logger.info(f"Synced {synced} visions to flow tracking")
    
    if TELEGRAM_BOT_TOKEN:
        logger.info("✅ Telegram connected")
    else:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN not set")
    
    # Start proactive daemon as background task
    proactive_task = asyncio.create_task(start_proactive_loop())
    logger.info("✅ Proactive daemon started")
    
    logger.info("═══════════════════════════════════════════")
    logger.info("    ARIA IS READY - VOICE + PROACTIVE")
    logger.info("═══════════════════════════════════════════")
    
    yield
    
    # Cleanup
    logger.info("Aria Bridge shutting down...")
    app.state.proactive.stop()
    proactive_task.cancel()
    await app.state.translator.close()
    await app.state.tools.close()
    await app.state.voice.close()


app = FastAPI(
    title="Aria Bridge",
    description="Bridge across dimensions - translating vision to action, returning signal from manifestation to dream",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== CORE ENDPOINTS ====================

@app.get("/")
def root():
    """Root - Aria's invitation."""
    return {
        "name": "Aria Bridge",
        "description": "Bridge across dimensions",
        "invitation": FIRST_MESSAGE,
        "dimensions": list(DIMENSIONS.keys()),
        "modes": list(MODES.keys())
    }


@app.get("/health")
def health():
    """Health check."""
    return {
        "status": "healthy",
        "service": "aria-bridge",
        "timestamp": datetime.utcnow().isoformat(),
        "telegram": "connected" if TELEGRAM_BOT_TOKEN else "not_configured"
    }


@app.get("/constitution")
def constitution():
    """Return Aria's constitution."""
    return {
        "constitution": ARIA_CONSTITUTION,
        "dimensions": DIMENSIONS,
        "modes": MODES
    }


# ==================== TELEGRAM WEBHOOK ====================

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook."""
    import httpx
    
    try:
        data = await request.json()
        
        if "message" not in data:
            return {"ok": True}
        
        message = data["message"]
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
        message_id = message.get("message_id")
        user_id = str(message.get("from", {}).get("id", "unknown"))
        
        if not chat_id or not text:
            return {"ok": True}
        
        # Send typing indicator
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{TELEGRAM_API}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"}
            )
        
        # Handle commands
        if text.startswith("/"):
            response = await handle_command(text, chat_id, user_id, request.app)
        else:
            response = await handle_message(text, chat_id, user_id, request.app)
        
        # Send response
        if response:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{TELEGRAM_API}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": response,
                        "reply_to_message_id": message_id,
                        "parse_mode": "Markdown"
                    }
                )
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}


async def handle_command(command: str, chat_id: int, user_id: str, app: FastAPI) -> str:
    """Handle bot commands."""
    parts = command.split()
    cmd = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    
    if cmd == "/start":
        return FIRST_MESSAGE
    
    elif cmd == "/status":
        status = await app.state.tools.get_full_status()
        return app.state.tools.format_status_for_telegram(status)
    
    elif cmd == "/visions":
        return app.state.journal.format_open_visions()
    
    elif cmd == "/flow":
        return app.state.flow.format_flow_status()
    
    elif cmd == "/feedback":
        return app.state.feedback.format_feedback_summary()
    
    elif cmd == "/vision" and args:
        from dream_journal import DimensionSource
        vision_text = " ".join(args)
        vision = app.state.journal.receive_vision(
            raw_description=vision_text,
            dimension_source=DimensionSource.VISION,
            core_essence=vision_text[:200]
        )
        return f"📜 **Vision Received**\n\n_{vision_text[:100]}..._\n\nID: `{vision.id}`\n\nWhat wants to manifest?"
    
    elif cmd == "/brief":
        summary = app.state.journal.get_summary()
        flow = app.state.flow.format_flow_status()
        feedback = app.state.feedback.format_feedback_summary()
        
        return f"""═══ MORNING BRIEF ═══
{datetime.now().strftime('%A, %B %d')}

{app.state.journal.format_open_visions()}

{flow}

{feedback}

**T1 = Revenue or Building Aria**

What's the highest-leverage move today?"""
    
    elif cmd == "/t1":
        return """**T1 = Revenue or Building Aria**

Everything else is T2+.

Does what you're working on advance T1?"""
    
    elif cmd == "/mode":
        if args:
            mode = args[0].lower()
            instructions = {
                "command": "Let's execute. Decisive, minimal words. What's the action?",
                "sensemaking": "Let's reflect. What's unclear? Name the true constraint.",
                "ritual": "Let's center. Take a breath. What needs integration?"
            }
            return f"**[{mode.upper()} MODE]**\n\n{instructions.get(mode, 'Unknown mode.')}"
        else:
            return "Modes: `/mode command`, `/mode sensemaking`, `/mode ritual`"
    
    else:
        return """Available commands:
• `/start` - The invitation
• `/status` - System status
• `/visions` - Open visions
• `/flow` - Dimensional flow
• `/feedback` - Feedback loop
• `/vision [text]` - Record a vision
• `/brief` - Morning brief
• `/t1` - What's T1?
• `/mode [command/sensemaking/ritual]`

Or just talk to me naturally."""


async def handle_message(text: str, chat_id: int, user_id: str, app: FastAPI) -> str:
    """Handle regular messages."""
    # Detect dimension
    dimension = detect_dimension(text)
    
    # Check if this is a vision
    is_vision = dimension in ["dream_astral", "intuitive"]
    vision_words = ["saw", "dream", "vision", "came to me", "felt like", "sense that"]
    
    if is_vision and any(w in text.lower() for w in vision_words):
        # Record the vision
        from dream_journal import DimensionSource
        source = DimensionSource.DREAM if "dream" in text.lower() else DimensionSource.VISION
        
        vision = app.state.journal.receive_vision(
            raw_description=text,
            dimension_source=source,
            core_essence=text[:200]
        )
        
        # Create flow item
        from dimensional_flow import Dimension
        app.state.flow.create_flow_item(
            name=text[:50],
            description=text,
            starting_dimension=Dimension.DREAM_ASTRAL,
            vision_id=vision.id
        )
    
    # Get response from Aria
    response = await app.state.translator.respond_as_aria(
        message=text,
        context={"dimension": dimension}
    )
    
    return response


# ==================== API ENDPOINTS ====================

@app.get("/journal/summary")
def journal_summary(request: Request):
    """Get dream journal summary."""
    return request.app.state.journal.get_summary()


@app.get("/journal/visions")
def journal_visions(request: Request, status: str = None):
    """Get visions, optionally filtered by status."""
    if status:
        from dream_journal import VisionStatus
        visions = request.app.state.journal.get_visions_by_status(VisionStatus(status))
    else:
        visions = request.app.state.journal.get_open_visions()
    return {"visions": [v.to_dict() for v in visions]}


@app.get("/flow/report")
def flow_report(request: Request):
    """Get dimensional flow report."""
    report = request.app.state.flow.get_flow_report()
    return {
        "timestamp": report.timestamp,
        "total_items": report.total_items,
        "flowing": report.flowing,
        "stuck": report.stuck,
        "blocked": report.blocked,
        "by_dimension": report.by_dimension,
        "stuck_items": report.stuck_items,
        "blocked_items": report.blocked_items,
        "flow_health": report.flow_health
    }


@app.get("/feedback/summary")
def feedback_summary(request: Request):
    """Get feedback loop summary."""
    return request.app.state.feedback.get_summary()


@app.get("/system/status")
async def system_status(request: Request):
    """Get full system status."""
    return await request.app.state.tools.get_full_status()


@app.post("/translate")
async def translate_vision(request: Request):
    """Translate a vision to action."""
    data = await request.json()
    vision_text = data.get("vision", "")
    dimension = data.get("dimension", "intuition")
    
    translation = await request.app.state.translator.translate_vision_to_action(
        vision_text=vision_text,
        dimension_source=dimension
    )
    
    return {
        "essence": translation.understood_essence,
        "what_wants_to_manifest": translation.what_wants_to_manifest,
        "action_seed": translation.action_seed,
        "next_step": translation.next_step,
        "bridge": f"{translation.dimension_from} → {translation.dimension_to}"
    }


@app.post("/feedback/record")
async def record_feedback(request: Request):
    """Record feedback from manifestation."""
    data = await request.json()
    
    entry = request.app.state.feedback.record_feedback(
        action_taken=data.get("action", ""),
        result=data.get("result", ""),
        vision_id=data.get("vision_id"),
        matched_vision=data.get("matched", False),
        deviation=data.get("deviation"),
        pattern=data.get("pattern"),
        learning=data.get("learning"),
        next_action=data.get("next_action")
    )
    
    return {"id": entry.id, "type": entry.feedback_type.value}


# ==================== PROACTIVE ENDPOINTS ====================

@app.get("/proactive/status")
def proactive_status(request: Request):
    """Get proactive daemon status."""
    daemon = request.app.state.proactive
    return {
        "running": daemon.running,
        "check_interval_seconds": daemon.check_interval,
        "state": {
            "sent_today": daemon.state.state.get("sent_today", 0),
            "last_morning_brief": daemon.state.state.get("last_morning_brief"),
            "cooldowns_active": len(daemon.state.state.get("cooldowns", {}))
        }
    }


@app.post("/proactive/trigger")
async def proactive_trigger(request: Request):
    """Manually trigger a proactive sense cycle."""
    daemon = request.app.state.proactive
    signals = await daemon.sense_all_channels()
    
    return {
        "signals_detected": len(signals),
        "signals": [
            {"type": s.type.value, "urgency": s.urgency.value, "title": s.title}
            for s in signals
        ]
    }


# ==================== VOICE ENDPOINTS ====================

@app.post("/voice/send")
async def voice_send(request: Request):
    """Send a voice message to Sunheart."""
    data = await request.json()
    text = data.get("text", "")
    mode = data.get("mode", "default")
    chat_id = data.get("chat_id") or int(os.getenv("SUNHEART_CHAT_ID", "0"))
    
    if not chat_id:
        return {"success": False, "error": "No chat_id provided"}
    
    success = await request.app.state.voice.send_voice_message(
        chat_id=chat_id,
        text=text,
        mode=mode
    )
    
    return {"success": success}


@app.post("/voice/alert")
async def voice_alert(request: Request):
    """Send a voice alert."""
    data = await request.json()
    message = data.get("message", "")
    urgency = data.get("urgency", "normal")
    chat_id = data.get("chat_id") or int(os.getenv("SUNHEART_CHAT_ID", "0"))
    
    if not chat_id:
        return {"success": False, "error": "No chat_id provided"}
    
    success = await request.app.state.voice.send_voice_alert(
        chat_id=chat_id,
        message=message,
        urgency=urgency
    )
    
    return {"success": success}


@app.get("/voice/status")
def voice_status(request: Request):
    """Get voice capability status."""
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_telegram = bool(os.getenv("TELEGRAM_BOT_TOKEN"))
    
    return {
        "voice_enabled": has_openai and has_telegram,
        "openai_configured": has_openai,
        "telegram_configured": has_telegram,
        "available_voices": ["nova", "alloy", "echo", "fable", "onyx", "shimmer"],
        "default_voice": "nova"
    }


# ==================== MEMORY ENDPOINTS ====================

@app.get("/memory/status")
def memory_status(request: Request):
    """Get memory system status."""
    if not MEMORY_AVAILABLE or not request.app.state.memory_store:
        return {"available": False, "reason": "Memory system not initialized"}
    
    stats = request.app.state.memory_store.get_stats()
    return {
        "available": True,
        "stats": stats
    }


@app.get("/memory/identity")
def memory_identity(request: Request):
    """Get identity memory."""
    if not MEMORY_AVAILABLE or not request.app.state.identity_memory:
        return {"error": "Memory not available"}
    
    return {
        "identity": request.app.state.identity_memory.get_full_identity(),
        "formatted": request.app.state.identity_memory.get_quick_identity()
    }


@app.get("/memory/context")
def memory_context(request: Request):
    """Get current context."""
    if not MEMORY_AVAILABLE or not request.app.state.context_memory:
        return {"error": "Memory not available"}
    
    return {
        "context": request.app.state.context_memory.get()
    }


@app.post("/memory/context")
async def set_memory_context(request: Request):
    """Set a context value."""
    if not MEMORY_AVAILABLE or not request.app.state.context_memory:
        return {"error": "Memory not available"}
    
    data = await request.json()
    key = data.get("key")
    value = data.get("value")
    expires_hours = data.get("expires_hours")
    
    if not key or value is None:
        return {"error": "key and value required"}
    
    request.app.state.context_memory.set(key, value, expires_hours)
    return {"success": True, "key": key}


@app.get("/memory/recall")
async def memory_recall(request: Request, query: str, limit: int = 5):
    """Recall memories relevant to a query."""
    if not MEMORY_AVAILABLE or not request.app.state.memory_recall:
        return {"error": "Memory not available"}
    
    recalled = request.app.state.memory_recall.recall(query, limit=limit)
    
    return {
        "query": query,
        "memories": [
            {
                "id": rm.memory.id,
                "content": rm.memory.content[:200],
                "category": rm.memory.category.value,
                "relevance": rm.relevance_score,
                "match_reason": rm.match_reason
            }
            for rm in recalled
        ]
    }


@app.post("/memory/learn")
async def memory_learn(request: Request):
    """Record a learning from an action-outcome pair."""
    if not MEMORY_AVAILABLE or not request.app.state.memory_learning:
        return {"error": "Memory not available"}
    
    data = await request.json()
    action = data.get("action", "")
    outcome = data.get("outcome", "")
    outcome_type = data.get("outcome_type", "neutral")
    insight = data.get("insight")
    
    if not action or not outcome:
        return {"error": "action and outcome required"}
    
    from memory import OutcomeType
    memory = request.app.state.memory_learning.learn(
        action=action,
        outcome=outcome,
        outcome_type=OutcomeType(outcome_type),
        insight=insight
    )
    
    return {"success": True, "memory_id": memory.id, "insight": memory.insight}


@app.get("/memory/learnings")
def memory_learnings(request: Request, limit: int = 20):
    """Get recent learnings."""
    if not MEMORY_AVAILABLE or not request.app.state.memory_learning:
        return {"error": "Memory not available"}
    
    summary = request.app.state.memory_learning.get_learning_summary()
    return summary


@app.post("/memory/compress")
def memory_compress(request: Request):
    """Run memory compression cycle."""
    if not MEMORY_AVAILABLE:
        return {"error": "Memory not available"}
    
    stats = run_compression()
    return {"success": True, "stats": stats}


# ==================== MEM0 CLOUD SYNC ENDPOINTS ====================

@app.get("/memory/cloud/status")
async def mem0_status(request: Request):
    """Get Mem0 cloud sync status."""
    if not MEMORY_AVAILABLE or not request.app.state.mem0_sync:
        return {"error": "Memory not available", "mem0_enabled": False}
    
    status = await request.app.state.mem0_sync.get_status()
    return status


@app.get("/memory/cloud/search")
async def mem0_search(request: Request, query: str, limit: int = 10):
    """Search memories in Mem0 cloud."""
    if not MEMORY_AVAILABLE or not request.app.state.mem0_sync:
        return {"error": "Memory not available"}
    
    if not request.app.state.mem0_sync.enabled:
        return {"error": "Mem0 not configured"}
    
    results = await request.app.state.mem0_sync.search_cloud(query, limit=limit)
    return {"query": query, "results": results}


@app.post("/memory/cloud/sync")
async def mem0_sync_now(request: Request):
    """Manually trigger sync of important memories to Mem0."""
    if not MEMORY_AVAILABLE:
        return {"error": "Memory not available"}
    
    result = await sync_important_memories()
    return {"success": True, **result}


@app.post("/memory/cloud/sync-identity")
async def mem0_sync_identity(request: Request):
    """Sync identity to Mem0 cloud."""
    if not MEMORY_AVAILABLE or not request.app.state.mem0_sync:
        return {"error": "Memory not available"}
    
    if not request.app.state.mem0_sync.enabled:
        return {"error": "Mem0 not configured"}
    
    identity = request.app.state.identity_memory.get_full_identity()
    success = await request.app.state.mem0_sync.sync_identity(identity)
    return {"success": success}


# ==================== MAIN ====================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)

