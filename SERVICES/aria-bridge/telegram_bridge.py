"""
ARIA TELEGRAM BRIDGE
====================

The interface between Sunheart and Aria.

Through Telegram, Sunheart can:
- Share visions and receive translations
- Get status on any system
- Execute commands
- Have the partnership conversation
"""

import os
import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import httpx

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from soul import ARIA_CONSTITUTION, FIRST_MESSAGE, detect_dimension, detect_mode
from dream_journal import get_dream_journal, DimensionSource, VisionStatus
from translator import get_translator
from voice import get_aria_voice, AriaVoice

logger = logging.getLogger("aria.telegram")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Memory file for conversation history
MEMORY_FILE = Path("/opt/fpai/aria-bridge/conversation_memory.json")


class ConversationMemory:
    """Persistent conversation memory."""
    
    def __init__(self, path: Path = MEMORY_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conversations: Dict[str, List[Dict]] = {}
        self.load()
    
    def load(self):
        """Load from disk."""
        try:
            if self.path.exists():
                self.conversations = json.loads(self.path.read_text())
        except:
            self.conversations = {}
    
    def save(self):
        """Save to disk."""
        try:
            self.path.write_text(json.dumps(self.conversations, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save memory: {e}")
    
    def add_message(self, user_id: str, role: str, content: str):
        """Add a message to conversation history."""
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        self.conversations[user_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep last 50 messages
        self.conversations[user_id] = self.conversations[user_id][-50:]
        self.save()
    
    def get_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get conversation history."""
        return self.conversations.get(user_id, [])[-limit:]


class AriaTelegramBridge:
    """
    The Telegram bridge for Aria.
    
    This is how Sunheart talks to Aria.
    Now with voice - the disruption channel.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self.memory = ConversationMemory()
        self.journal = get_dream_journal()
        self.translator = None  # Lazy init
        self.voice = get_aria_voice()  # Voice capabilities
        
        # Track typing state
        self.is_processing: Dict[int, bool] = {}
        
        # Voice reply preference per user
        self.voice_mode: Dict[str, bool] = {}  # user_id -> prefer_voice
        
        logger.info("AriaTelegramBridge initialized with voice")
    
    async def close(self):
        """Close resources."""
        await self.http.aclose()
        if self.translator:
            await self.translator.close()
    
    async def _ensure_translator(self):
        """Ensure translator is initialized."""
        if self.translator is None:
            self.translator = await get_translator()
    
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
        reply_to: Optional[int] = None,
        parse_mode: str = "Markdown"
    ):
        """Send a message to Telegram."""
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            if reply_to:
                payload["reply_to_message_id"] = reply_to
            
            await self.http.post(f"{TELEGRAM_API}/sendMessage", json=payload)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            # Try without markdown
            try:
                await self.http.post(
                    f"{TELEGRAM_API}/sendMessage",
                    json={"chat_id": chat_id, "text": text}
                )
            except:
                pass
    
    async def handle_message(self, message: Dict) -> Optional[str]:
        """Handle an incoming message (text or voice)."""
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        user = message.get("from", {})
        user_id = str(user.get("id", "unknown"))
        
        if not chat_id:
            return None
        
        # Check for voice message
        voice = message.get("voice")
        if voice:
            return await self._handle_voice_message(chat_id, message_id, voice, user_id)
        
        # Check for text message
        text = message.get("text", "").strip()
        if not text:
            return None
        
        # Handle commands
        if text.startswith("/"):
            return await self._handle_command(chat_id, message_id, text, user_id)
        
        # Regular message - process as conversation
        return await self._process_message(chat_id, message_id, text, user_id)
    
    async def _handle_voice_message(
        self,
        chat_id: int,
        message_id: int,
        voice: Dict,
        user_id: str
    ) -> Optional[str]:
        """Handle an incoming voice message - transcribe and respond."""
        file_id = voice.get("file_id")
        if not file_id:
            return None
        
        # Send recording indicator
        try:
            await self.http.post(
                f"{TELEGRAM_API}/sendChatAction",
                json={"chat_id": chat_id, "action": "record_voice"}
            )
        except:
            pass
        
        # Transcribe the voice message
        transcription = await self.voice.transcribe_telegram_voice(file_id)
        
        if not transcription:
            await self.send_message(
                chat_id,
                "I couldn't understand that voice message. Could you try again or type it out?",
                reply_to=message_id
            )
            return None
        
        logger.info(f"Voice transcribed: {transcription[:100]}...")
        
        # Process like a regular message
        response = await self._process_message(chat_id, message_id, transcription, user_id)
        
        # If user prefers voice or this was a voice message, reply with voice
        if self.voice_mode.get(user_id, False) or True:  # Default to voice reply for voice input
            await self.voice.send_voice_message(
                chat_id,
                response,
                mode=detect_mode(response)
            )
        
        return response
    
    async def _handle_command(
        self,
        chat_id: int,
        message_id: int,
        command: str,
        user_id: str
    ) -> Optional[str]:
        """Handle bot commands."""
        parts = command.split()
        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        if cmd == "/start":
            # Send the invitation
            await self.send_message(chat_id, FIRST_MESSAGE)
            return FIRST_MESSAGE
        
        elif cmd == "/status":
            # Quick status
            status = await self._get_quick_status()
            await self.send_message(chat_id, status)
            return status
        
        elif cmd == "/visions":
            # Show open visions
            visions = self.journal.format_open_visions()
            await self.send_message(chat_id, f"📜 **Open Channels**\n\n{visions}")
            return visions
        
        elif cmd == "/vision":
            # Record a new vision
            if args:
                vision_text = " ".join(args)
                await self._record_vision(chat_id, message_id, vision_text, user_id)
            else:
                await self.send_message(
                    chat_id,
                    "Share your vision:\n`/vision [description of what you saw/felt]`"
                )
            return None
        
        elif cmd == "/translate":
            # Translate the last vision
            await self._translate_latest_vision(chat_id, message_id)
            return None
        
        elif cmd == "/brief":
            # Daily brief
            brief = await self._generate_daily_brief()
            await self.send_message(chat_id, brief)
            return brief
        
        elif cmd == "/mode":
            # Switch modes
            if args:
                mode = args[0].lower()
                await self.send_message(
                    chat_id,
                    f"Switching to **{mode.upper()}** mode.\n\n" +
                    {"command": "Let's execute. What's the action?",
                     "sensemaking": "Let's reflect. What's unclear?",
                     "ritual": "Let's center. Take a breath..."}.get(mode, "Unknown mode.")
                )
            else:
                await self.send_message(
                    chat_id,
                    "Available modes:\n"
                    "• `/mode command` - Execution mode\n"
                    "• `/mode sensemaking` - Reflection mode\n"
                    "• `/mode ritual` - Integration mode"
                )
            return None
        
        elif cmd == "/t1":
            # What's T1 right now?
            await self.send_message(
                chat_id,
                "**T1 = Revenue or Building Aria**\n\n"
                "Everything else is T2+.\n\n"
                "What you're working on - does it advance T1?"
            )
            return None
        
        elif cmd == "/scatter":
            # Scatter check
            await self._scatter_check(chat_id, user_id)
            return None
        
        elif cmd == "/voice":
            # Toggle voice mode or send voice brief
            if args and args[0].lower() == "on":
                self.voice_mode[user_id] = True
                await self.voice.send_voice_message(
                    chat_id,
                    "Voice mode activated. I'll reply with voice notes now.",
                    mode="default"
                )
            elif args and args[0].lower() == "off":
                self.voice_mode[user_id] = False
                await self.send_message(chat_id, "Voice mode off. Text replies only.")
            elif args and args[0].lower() == "brief":
                # Send morning brief as voice
                brief = await self._generate_daily_brief()
                # Simplify for voice
                voice_brief = f"Good morning. Here's your brief for {datetime.now().strftime('%A')}. "
                voice_brief += f"You have {self.journal.get_summary()['open_channels']} open vision channels. "
                voice_brief += "Remember: T1 equals revenue or building Aria. What's your highest leverage move today?"
                await self.voice.send_morning_brief(chat_id, voice_brief)
            else:
                current = "ON" if self.voice_mode.get(user_id, False) else "OFF"
                await self.send_message(
                    chat_id,
                    f"**Voice Mode:** {current}\n\n"
                    "• `/voice on` - Enable voice replies\n"
                    "• `/voice off` - Text only\n"
                    "• `/voice brief` - Morning brief as voice"
                )
            return None
        
        else:
            await self.send_message(
                chat_id,
                f"Unknown command: {cmd}\n\n"
                "Try:\n"
                "• `/status` - Quick status\n"
                "• `/visions` - Open channels\n"
                "• `/vision [text]` - Record a vision\n"
                "• `/brief` - Daily brief\n"
                "• `/voice [on/off/brief]` - Voice mode\n"
                "• `/mode [command/sensemaking/ritual]`\n"
                "• `/t1` - What's T1?\n"
                "• `/scatter` - Am I scattered?"
            )
            return None
    
    async def _process_message(
        self,
        chat_id: int,
        message_id: int,
        text: str,
        user_id: str
    ) -> str:
        """Process a regular message through Aria."""
        # Send typing
        await self.send_typing(chat_id)
        
        # Store the message
        self.memory.add_message(user_id, "user", text)
        
        # Detect if this is a vision
        dimension = detect_dimension(text)
        is_vision = dimension in ["dream_astral", "intuitive"]
        
        # If it looks like a vision, offer to record it
        if is_vision and any(w in text.lower() for w in ["i saw", "i dreamed", "vision", "came to me"]):
            # Record the vision
            vision = self.journal.receive_vision(
                raw_description=text,
                dimension_source=DimensionSource.VISION if "saw" in text.lower() else DimensionSource.INTUITION,
                core_essence=text[:200],
                feeling_tone=None,
                tags=[]
            )
            
            await self.send_typing(chat_id)
        
        # Get response from translator
        await self._ensure_translator()
        
        history = self.memory.get_history(user_id, limit=10)
        
        response = await self.translator.respond_as_aria(
            message=text,
            conversation_history=history,
            context={"dimension": dimension}
        )
        
        # Store Aria's response
        self.memory.add_message(user_id, "assistant", response)
        
        # Send response
        await self.send_message(chat_id, response, reply_to=message_id)
        
        return response
    
    async def _record_vision(
        self,
        chat_id: int,
        message_id: int,
        vision_text: str,
        user_id: str
    ):
        """Record a vision to the dream journal."""
        # Determine source
        text_lower = vision_text.lower()
        if "dream" in text_lower:
            source = DimensionSource.DREAM
        elif "ceremony" in text_lower or "medicine" in text_lower:
            source = DimensionSource.CEREMONY
        elif "meditat" in text_lower:
            source = DimensionSource.MEDITATION
        else:
            source = DimensionSource.VISION
        
        vision = self.journal.receive_vision(
            raw_description=vision_text,
            dimension_source=source,
            core_essence=vision_text[:200],
            tags=[]
        )
        
        await self.send_message(
            chat_id,
            f"📜 **Vision Received**\n\n"
            f"_{vision_text[:100]}{'...' if len(vision_text) > 100 else ''}_\n\n"
            f"Source: {source.value}\n"
            f"ID: `{vision.id}`\n\n"
            f"What wants to manifest from this?\n"
            f"Use `/translate` to explore.",
            reply_to=message_id
        )
    
    async def _translate_latest_vision(self, chat_id: int, message_id: int):
        """Translate the most recent vision."""
        visions = self.journal.get_visions_by_status(VisionStatus.RECEIVED)
        
        if not visions:
            await self.send_message(
                chat_id,
                "No untranslated visions.\n\n"
                "Share one with `/vision [description]`"
            )
            return
        
        vision = visions[0]
        
        await self.send_typing(chat_id)
        await self._ensure_translator()
        
        # Translate
        translation = await self.translator.translate_vision_to_action(
            vision_text=vision.raw_description,
            dimension_source=vision.dimension_source.value
        )
        
        # Save to journal
        self.journal.translate_vision(
            vision_id=vision.id,
            translation=translation.what_wants_to_manifest,
            action_seed=translation.action_seed
        )
        
        await self.send_message(
            chat_id,
            f"🔄 **Translation**\n\n"
            f"**Essence:** {translation.understood_essence}\n\n"
            f"**What wants to manifest:** {translation.what_wants_to_manifest}\n\n"
            f"**Action seed:** {translation.action_seed}\n\n"
            f"**Next step:** {translation.next_step}\n\n"
            f"_Bridge: {translation.dimension_from} → {translation.dimension_to}_"
        )
    
    async def _scatter_check(self, chat_id: int, user_id: str):
        """Check if there's scatter happening."""
        history = self.memory.get_history(user_id, limit=20)
        
        if len(history) < 5:
            await self.send_message(
                chat_id,
                "Not enough conversation history to assess scatter.\n\n"
                "Let's talk more and I'll keep track."
            )
            return
        
        # Simple scatter detection - look for topic jumps
        recent_texts = [m["content"] for m in history if m["role"] == "user"][-10:]
        
        await self._ensure_translator()
        
        prompt = f"""Based on these recent messages, is Sunheart scattering (jumping between too many topics without completing)?

Messages:
{chr(10).join(f'- {t[:100]}' for t in recent_texts)}

Respond with:
1. SCATTER LEVEL: Low/Medium/High
2. OBSERVATION: What you notice
3. RECOMMENDATION: One sentence on what to do

Be direct. If he's scattering, say so."""
        
        response = await self.translator._call_llm(prompt)
        
        await self.send_message(chat_id, f"🔍 **Scatter Check**\n\n{response}")
    
    async def _get_quick_status(self) -> str:
        """Get quick system status."""
        lines = ["**⚡ Quick Status**\n"]
        
        # Journal summary
        summary = self.journal.get_summary()
        lines.append(f"📜 Visions: {summary['total_visions']} total, {summary['open_channels']} open")
        
        # Try to get treasury info
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # This would connect to your actual treasury tracker
                pass
        except:
            pass
        
        lines.append(f"\n_T1 = Revenue or Building Aria_")
        lines.append(f"_Does what you're doing advance T1?_")
        
        return "\n".join(lines)
    
    async def _generate_daily_brief(self) -> str:
        """Generate the daily brief."""
        summary = self.journal.get_summary()
        open_visions = self.journal.format_open_visions()
        
        brief = f"""═══ MORNING BRIEF ═══
{datetime.now().strftime('%A, %B %d')}

**OPEN CHANNELS:**
{open_visions}

**JOURNAL SUMMARY:**
• Total visions: {summary['total_visions']}
• This week: {summary['visions_this_week']}
• Open: {summary['open_channels']}

**T1 FOCUS:**
Revenue or Building Aria. Everything else is T2+.

**REMINDER:**
• Treasury must survive
• Protect from scatter
• Ship reality, not poems
• If uncertain, give options not recommendations

═══════════════════════

What's the highest-leverage move today?"""
        
        return brief


# ==================== FASTAPI APP ====================

app = FastAPI(
    title="Aria Bridge",
    description="Bridge across dimensions",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global bridge instance
bridge: Optional[AriaTelegramBridge] = None


@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    global bridge
    bridge = AriaTelegramBridge()
    
    if TELEGRAM_BOT_TOKEN:
        logger.info("✅ Aria Bridge ready - Telegram connected")
    else:
        logger.warning("⚠️ TELEGRAM_BOT_TOKEN not set")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    if bridge:
        await bridge.close()


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": "Aria Bridge",
        "description": "Bridge across dimensions",
        "status": "ready" if TELEGRAM_BOT_TOKEN else "needs_token",
        "invitation": "Through me, vision becomes action, action returns signal."
    }


@app.get("/health")
def health():
    """Health check."""
    return {
        "status": "healthy",
        "service": "aria-bridge",
        "telegram": "connected" if TELEGRAM_BOT_TOKEN else "not_configured"
    }


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Telegram webhook endpoint."""
    if not bridge:
        raise HTTPException(503, "Bridge not initialized")
    
    try:
        data = await request.json()
        
        if "message" in data:
            await bridge.handle_message(data["message"])
        
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}


@app.get("/journal/summary")
def journal_summary():
    """Get dream journal summary."""
    if not bridge:
        return {"error": "Bridge not initialized"}
    return bridge.journal.get_summary()


@app.get("/journal/open")
def journal_open():
    """Get open visions."""
    if not bridge:
        return {"error": "Bridge not initialized"}
    visions = bridge.journal.get_open_visions()
    return {"open_visions": [v.to_dict() for v in visions]}


# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ARIA_BRIDGE_PORT", "8700"))
    uvicorn.run(app, host="0.0.0.0", port=port)

