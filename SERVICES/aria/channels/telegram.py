"""
ARIA TELEGRAM CHANNEL
=====================

Telegram bot adapter that connects to Aria Core API.

Features:
- Webhook-based updates
- Typing indicators
- Quick response patterns
- Approval command handling
"""

import os
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict
import httpx

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("aria.telegram")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ARIA_CORE_URL = os.getenv("ARIA_CORE_URL", "http://localhost:8180")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Quick response patterns (respond instantly without AI)
QUICK_RESPONSES = {
    "hi": "Hey! 👋 What can I help you with?",
    "hello": "Hello! How can I assist you today?",
    "hey": "Hey! What's on your mind?",
    "thanks": "You're welcome! 😊",
    "thank you": "Happy to help! Let me know if you need anything else.",
    "?": "I'm here! What would you like to know?",
}


class TelegramUpdate(BaseModel):
    """Telegram update model."""
    update_id: int
    message: Optional[Dict] = None
    callback_query: Optional[Dict] = None


class TelegramChannel:
    """
    Telegram channel adapter for Aria.
    
    Connects Telegram webhook to Aria Core API.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self.stats = {
            "messages_received": 0,
            "messages_sent": 0,
            "quick_responses": 0,
            "core_requests": 0,
            "errors": 0
        }
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def send_typing(self, chat_id: int):
        """Send typing indicator."""
        try:
            await self.http.post(
                f"{TELEGRAM_API}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"}
            )
        except:
            pass
    
    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to: Optional[int] = None
    ):
        """Send a message to Telegram."""
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            if reply_to:
                payload["reply_to_message_id"] = reply_to
            
            await self.http.post(
                f"{TELEGRAM_API}/sendMessage",
                json=payload
            )
            self.stats["messages_sent"] += 1
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            self.stats["errors"] += 1
    
    async def handle_update(self, update: TelegramUpdate) -> Optional[str]:
        """Handle a Telegram update."""
        self.stats["messages_received"] += 1
        
        # Handle message
        if update.message:
            return await self._handle_message(update.message)
        
        # Handle callback query (button clicks)
        if update.callback_query:
            return await self._handle_callback(update.callback_query)
        
        return None
    
    async def _handle_message(self, message: Dict) -> Optional[str]:
        """Handle a text message."""
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        text = message.get("text", "").strip()
        user = message.get("from", {})
        user_id = str(user.get("id", "unknown"))
        user_name = user.get("first_name", "")
        
        if not chat_id or not text:
            return None
        
        # Handle commands
        if text.startswith("/"):
            return await self._handle_command(chat_id, text, user_id)
        
        # Check for quick response
        text_lower = text.lower()
        if text_lower in QUICK_RESPONSES:
            response = QUICK_RESPONSES[text_lower]
            await self.send_message(chat_id, response, reply_to=message_id)
            self.stats["quick_responses"] += 1
            return response
        
        # Send typing indicator
        await self.send_typing(chat_id)
        
        # Call Aria Core API
        try:
            self.stats["core_requests"] += 1
            
            r = await self.http.post(
                f"{ARIA_CORE_URL}/aria/chat",
                json={
                    "user_id": user_id,
                    "channel": "telegram",
                    "message": text,
                    "context": {
                        "chat_id": chat_id,
                        "user_name": user_name
                    }
                },
                timeout=30.0
            )
            
            if r.status_code == 200:
                data = r.json()
                response = data.get("response", "I couldn't process that. Please try again.")
                
                # Send response
                await self.send_message(chat_id, response, reply_to=message_id)
                return response
            else:
                error_msg = "Sorry, I'm having trouble right now. Please try again in a moment."
                await self.send_message(chat_id, error_msg)
                self.stats["errors"] += 1
                return None
                
        except Exception as e:
            logger.error(f"Core API error: {e}")
            self.stats["errors"] += 1
            await self.send_message(chat_id, "Sorry, something went wrong. Please try again.")
            return None
    
    async def _handle_command(self, chat_id: int, command: str, user_id: str) -> Optional[str]:
        """Handle bot commands."""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "/start":
            response = """🤖 **Welcome to Aria!**

I'm your intelligent assistant for Full Potential.

I can help you with:
• 💬 Conversation and questions
• 📊 Trading signals and analysis
• 🔧 System status and monitoring
• 💰 Cost optimization

Just send me a message to get started!

Commands:
• /status - System status
• /pending - Pending approvals
• /approve <id> - Approve a decision
• /deny <id> - Deny a decision"""
            await self.send_message(chat_id, response)
            return response
        
        elif cmd == "/status":
            try:
                r = await self.http.get(f"{ARIA_CORE_URL}/aria/status", timeout=10.0)
                if r.status_code == 200:
                    data = r.json()
                    response = f"""📊 **Aria Status**

Status: {data.get('status', 'unknown')}
Pending Approvals: {data.get('pending_approvals', 0)}

**Backends:**
"""
                    for backend, info in data.get("backends", {}).items():
                        status = "✅" if info.get("healthy") else "❌"
                        response += f"• {backend}: {status}\n"
                    
                    await self.send_message(chat_id, response)
                    return response
            except Exception as e:
                logger.error(f"Status check failed: {e}")
            
            await self.send_message(chat_id, "Failed to get status. Please try again.")
            return None
        
        elif cmd == "/pending":
            try:
                r = await self.http.get(f"{ARIA_CORE_URL}/aria/pending", timeout=10.0)
                if r.status_code == 200:
                    data = r.json()
                    pending = data.get("pending", [])
                    
                    if not pending:
                        response = "✅ No pending approvals"
                    else:
                        response = f"📋 **Pending Approvals ({len(pending)})**\n\n"
                        for p in pending:
                            response += f"**{p['id']}**\n"
                            response += f"Action: {p['action']}\n"
                            response += f"Reason: {p['reason']}\n"
                            if p['cost'] > 0:
                                response += f"Cost: ${p['cost']:.2f}\n"
                            response += f"Risk: {p['risk']}\n\n"
                    
                    await self.send_message(chat_id, response)
                    return response
            except Exception as e:
                logger.error(f"Pending check failed: {e}")
            
            await self.send_message(chat_id, "Failed to get pending approvals.")
            return None
        
        elif cmd == "/approve":
            if not args:
                await self.send_message(chat_id, "Usage: /approve <decision_id>")
                return None
            
            decision_id = args[0]
            try:
                r = await self.http.post(
                    f"{ARIA_CORE_URL}/aria/approve/{decision_id}",
                    timeout=10.0
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == "approved":
                        response = f"✅ Approved: {data.get('decision', decision_id)}"
                    else:
                        response = f"❌ Decision not found: {decision_id}"
                    await self.send_message(chat_id, response)
                    return response
            except Exception as e:
                logger.error(f"Approve failed: {e}")
            
            await self.send_message(chat_id, "Failed to approve. Please try again.")
            return None
        
        elif cmd == "/deny":
            if not args:
                await self.send_message(chat_id, "Usage: /deny <decision_id>")
                return None
            
            decision_id = args[0]
            try:
                r = await self.http.post(
                    f"{ARIA_CORE_URL}/aria/deny/{decision_id}",
                    timeout=10.0
                )
                if r.status_code == 200:
                    data = r.json()
                    if data.get("status") == "denied":
                        response = f"❌ Denied: {data.get('decision', decision_id)}"
                    else:
                        response = f"Decision not found: {decision_id}"
                    await self.send_message(chat_id, response)
                    return response
            except Exception as e:
                logger.error(f"Deny failed: {e}")
            
            await self.send_message(chat_id, "Failed to deny. Please try again.")
            return None
        
        else:
            await self.send_message(chat_id, f"Unknown command: {cmd}\n\nTry /start for help.")
            return None
    
    async def _handle_callback(self, callback: Dict) -> Optional[str]:
        """Handle callback queries (button clicks)."""
        # Future: Handle inline button clicks for approvals
        return None


# ==================== FASTAPI APP ====================

app = FastAPI(
    title="Aria Telegram Bot",
    description="Telegram interface for Aria",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global channel instance
channel: Optional[TelegramChannel] = None


@app.on_event("startup")
async def startup():
    """Initialize Telegram channel on startup."""
    global channel
    channel = TelegramChannel()
    
    if TELEGRAM_BOT_TOKEN:
        logger.info("✅ Telegram channel ready")
    else:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN not set")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    if channel:
        await channel.close()


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "Aria Telegram Bot",
        "version": "2.0.0",
        "status": "ready" if TELEGRAM_BOT_TOKEN else "missing_token"
    }


@app.get("/health")
def health():
    """Health check."""
    return {
        "status": "healthy" if TELEGRAM_BOT_TOKEN else "degraded",
        "service": "aria-telegram",
        "stats": channel.stats if channel else {}
    }


@app.post("/telegram/webhook")
async def webhook(request: Request):
    """
    Telegram webhook endpoint.
    
    This receives updates from Telegram and routes them to Aria Core.
    """
    if not channel:
        raise HTTPException(503, "Channel not initialized")
    
    try:
        data = await request.json()
        update = TelegramUpdate(**data)
        await channel.handle_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/telegram/stats")
def stats():
    """Get channel stats."""
    if not channel:
        return {"error": "Channel not initialized"}
    return channel.stats


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("TELEGRAM_PORT", "8710"))
    uvicorn.run(app, host="0.0.0.0", port=port)


