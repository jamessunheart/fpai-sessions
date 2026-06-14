#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - VOICE OUTPUT (TTS)
=========================================

Text-to-speech using OpenAI TTS API.
Context-aware voice selection.
"""

import os
import io
import logging
from typing import Optional
from enum import Enum
import httpx

logger = logging.getLogger("aria.voice.speak")

# ============================================================================
# CONFIGURATION
# ============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TTS_MODEL = "tts-1"  # or "tts-1-hd" for higher quality


class Voice(str, Enum):
    """Available TTS voices with their contexts."""
    NOVA = "nova"       # Default, warm and friendly
    ONYX = "onyx"       # Urgent, authoritative (alerts)
    SHIMMER = "shimmer" # Calm, professional (trading)
    ALLOY = "alloy"     # Neutral, technical (code)
    ECHO = "echo"       # Clear, explanatory (help)
    FABLE = "fable"     # Storytelling (briefs)


# Context to voice mapping
CONTEXT_VOICES = {
    "default": Voice.NOVA,
    "urgent": Voice.ONYX,
    "alert": Voice.ONYX,
    "error": Voice.ONYX,
    "trading": Voice.SHIMMER,
    "market": Voice.SHIMMER,
    "code": Voice.ALLOY,
    "technical": Voice.ALLOY,
    "help": Voice.ECHO,
    "brief": Voice.FABLE,
    "summary": Voice.FABLE,
    "morning": Voice.FABLE,
}


class VoiceSpeaker:
    """
    Text-to-speech with context-aware voice selection.
    
    Features:
    - Multiple voice personalities
    - Context-based voice selection
    - Telegram voice message sending
    - Code-friendly speech patterns
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=60.0)
        self.available = bool(OPENAI_API_KEY)
        
        if not self.available:
            logger.warning("OpenAI API key not configured - TTS disabled")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    def select_voice(self, context: str = "default") -> Voice:
        """
        Select appropriate voice based on context.
        
        Args:
            context: Message context (urgent, trading, code, etc.)
        
        Returns:
            Voice enum
        """
        return CONTEXT_VOICES.get(context.lower(), Voice.NOVA)
    
    def detect_context(self, text: str) -> str:
        """
        Detect context from text content.
        
        Returns:
            Context string for voice selection
        """
        text_lower = text.lower()
        
        # Check for urgent indicators
        if any(w in text_lower for w in ["urgent", "critical", "error", "failed", "alert", "warning"]):
            return "urgent"
        
        # Check for trading context
        if any(w in text_lower for w in ["signal", "trade", "position", "market", "sol", "btc", "price"]):
            return "trading"
        
        # Check for code context
        if any(w in text_lower for w in ["def ", "class ", "function", "code", "import", "```"]):
            return "code"
        
        # Check for brief/summary
        if any(w in text_lower for w in ["brief", "summary", "morning", "daily", "report"]):
            return "brief"
        
        return "default"
    
    def prepare_for_speech(self, text: str) -> str:
        """
        Prepare text for speech synthesis.
        
        Transforms code elements into speech-friendly text.
        """
        # Remove markdown formatting
        text = text.replace("**", "")
        text = text.replace("*", "")
        text = text.replace("`", "")
        text = text.replace("```", "")
        
        # Transform code elements
        text = text.replace("def ", "function ")
        text = text.replace("()", " with no arguments")
        text = text.replace("->", " returns ")
        text = text.replace("==", " equals ")
        text = text.replace("!=", " not equals ")
        text = text.replace(">=", " greater than or equal to ")
        text = text.replace("<=", " less than or equal to ")
        
        # Add pauses
        text = text.replace("\n\n", ". . . ")
        text = text.replace("\n", ". ")
        
        # Pronounce common symbols
        text = text.replace("@", " at ")
        text = text.replace("#", " hash ")
        text = text.replace("$", " dollar ")
        text = text.replace("%", " percent ")
        
        # Limit length
        if len(text) > 4000:
            text = text[:3900] + ". . . Message truncated."
        
        return text
    
    async def generate_speech(
        self,
        text: str,
        voice: Optional[Voice] = None,
        context: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Generate speech audio from text.
        
        Args:
            text: Text to speak
            voice: Optional voice override
            context: Optional context for voice selection
        
        Returns:
            Audio bytes (OGG format) or None
        """
        if not self.available:
            return None
        
        # Select voice
        if not voice:
            if context:
                voice = self.select_voice(context)
            else:
                detected_context = self.detect_context(text)
                voice = self.select_voice(detected_context)
        
        # Prepare text
        prepared_text = self.prepare_for_speech(text)
        
        try:
            response = await self.http.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": TTS_MODEL,
                    "input": prepared_text,
                    "voice": voice.value,
                    "response_format": "opus"  # Good for Telegram
                }
            )
            
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"TTS API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return None
    
    async def send_voice_telegram(
        self,
        chat_id: int,
        text: str,
        voice: Optional[Voice] = None,
        context: Optional[str] = None
    ) -> bool:
        """
        Send text as voice message via Telegram.
        
        Args:
            chat_id: Telegram chat ID
            text: Text to speak
            voice: Optional voice override
            context: Optional context for voice selection
        
        Returns:
            True if sent successfully
        """
        if not TELEGRAM_TOKEN:
            logger.warning("Telegram token not configured")
            return False
        
        # Generate audio
        audio = await self.generate_speech(text, voice, context)
        if not audio:
            return False
        
        try:
            # Send voice message
            response = await self.http.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVoice",
                files={"voice": ("message.ogg", io.BytesIO(audio), "audio/ogg")},
                data={"chat_id": chat_id}
            )
            
            if response.status_code == 200:
                logger.info(f"Voice message sent to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send voice: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Voice send failed: {e}")
            return False
    
    async def send_morning_brief(self, chat_id: int, brief: str) -> bool:
        """
        Send morning brief as voice message.
        
        Uses FABLE voice for storytelling quality.
        """
        return await self.send_voice_telegram(
            chat_id,
            brief,
            voice=Voice.FABLE,
            context="morning"
        )
    
    async def send_urgent_alert(self, chat_id: int, alert: str) -> bool:
        """
        Send urgent alert as voice message.
        
        Uses ONYX voice for authority.
        """
        return await self.send_voice_telegram(
            chat_id,
            f"Urgent. {alert}",
            voice=Voice.ONYX,
            context="urgent"
        )
    
    async def send_trading_update(self, chat_id: int, update: str) -> bool:
        """
        Send trading update as voice message.
        
        Uses SHIMMER voice for calm professionalism.
        """
        return await self.send_voice_telegram(
            chat_id,
            update,
            voice=Voice.SHIMMER,
            context="trading"
        )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_speaker: Optional[VoiceSpeaker] = None


def get_speaker() -> VoiceSpeaker:
    """Get or create global speaker."""
    global _speaker
    if _speaker is None:
        _speaker = VoiceSpeaker()
    return _speaker


async def speak(text: str, context: str = "default") -> Optional[bytes]:
    """Generate speech audio."""
    return await get_speaker().generate_speech(text, context=context)


async def send_voice(chat_id: int, text: str, context: str = "default") -> bool:
    """Send voice message via Telegram."""
    return await get_speaker().send_voice_telegram(chat_id, text, context=context)


async def send_alert(chat_id: int, text: str) -> bool:
    """Send urgent voice alert."""
    return await get_speaker().send_urgent_alert(chat_id, text)


async def send_brief(chat_id: int, text: str) -> bool:
    """Send morning brief."""
    return await get_speaker().send_morning_brief(chat_id, text)


