#!/usr/bin/env python3
"""
Full Potential Server
=====================
Unified server for all Full Potential v2.0 components.

Components:
- Presence Engine (green dot)
- Proactive Reports
- Public Interface (Talk to my AI)
- Signal Consolidation
- AI-to-AI Protocol
- Dashboard
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fullpotential")

# === Lifespan ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    logger.info("🚀 Full Potential v2.0 starting...")
    
    # Initialize presence
    try:
        from presence import get_presence_engine
        engine = get_presence_engine()
        engine.go_online("System started")
        engine.register_channel("Telegram", "messaging")
        engine.register_channel("Public", "web")
        logger.info("✅ Presence Engine ready")
    except Exception as e:
        logger.error(f"Presence init error: {e}")
    
    # Start background tasks
    asyncio.create_task(proactive_loop())
    logger.info("✅ Proactive loop started")
    
    yield
    
    logger.info("👋 Full Potential shutting down")


# === App ===

app = FastAPI(
    title="Full Potential",
    description="Your AI handles the world. You handle what matters.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Mount Routers ===

try:
    from presence.api import router as presence_router
    app.include_router(presence_router)
    logger.info("Mounted: /presence")
except Exception as e:
    logger.warning(f"Presence router not loaded: {e}")

try:
    from public.interface import router as public_router
    app.include_router(public_router)
    logger.info("Mounted: /talk")
except Exception as e:
    logger.warning(f"Public router not loaded: {e}")

try:
    from dashboard.app import router as dashboard_router
    app.include_router(dashboard_router)
    logger.info("Mounted: /dashboard")
except Exception as e:
    logger.warning(f"Dashboard router not loaded: {e}")


# === Health ===

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "service": "Full Potential v2.0",
        "components": {
            "presence": True,
            "reports": True,
            "public": True,
            "signals": True,
            "ai_protocol": True,
            "dashboard": True
        }
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Full Potential",
        "tagline": "Your AI handles the world. You handle what matters.",
        "version": "2.0.0",
        "endpoints": {
            "dashboard": "/dashboard",
            "talk_to_jai": "/talk",
            "presence": "/presence",
            "health": "/health"
        }
    }


# === AI-to-AI Endpoint ===

@app.post("/ai/protocol")
async def ai_protocol(request: Request):
    """Handle AI-to-AI protocol requests."""
    try:
        from ai_protocol import get_protocol_engine
        engine = get_protocol_engine()
        
        data = await request.json()
        response = engine.handle_incoming(data)
        return response
        
    except Exception as e:
        logger.error(f"AI protocol error: {e}")
        return {"error": str(e)}


# === Message Endpoint ===

@app.post("/api/message")
async def send_message(request: Request):
    """Send a message to JAI."""
    try:
        data = await request.json()
        message = data.get("message", "")
        
        # Process through smart brain
        from smart_brain import think
        response = await think(message, [])
        
        return {"response": response}
        
    except Exception as e:
        logger.error(f"Message error: {e}")
        return {"response": f"Error: {str(e)[:100]}"}


# === Proactive Loop ===

async def proactive_loop():
    """Background loop for proactive actions."""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            
            # Check for scheduled reports
            try:
                from reports import check_scheduled_reports
                sent = await check_scheduled_reports()
                if sent:
                    logger.info(f"Sent reports: {sent}")
            except Exception as e:
                logger.debug(f"Report check error: {e}")
            
            # Check for heads-up events
            try:
                from signals.calendar import get_heads_up_events
                from reports import send_quick
                
                events = await get_heads_up_events()
                for event in events:
                    await send_quick(
                        f"Upcoming: {event['name']} in {event['time_until']}",
                        "status"
                    )
            except Exception as e:
                logger.debug(f"Calendar check error: {e}")
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Proactive loop error: {e}")


# === Run ===

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8800"))
    uvicorn.run(app, host="0.0.0.0", port=port)








