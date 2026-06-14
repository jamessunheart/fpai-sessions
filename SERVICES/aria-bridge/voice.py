"""
ARIA VOICE
==========

Voice capabilities for Aria Bridge.
Integrates Whisper transcription and OpenAI TTS.

Voice is the disruption channel - unexpected, personal, immediate.
"""

import os
import io
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import httpx

logger = logging.getLogger("aria.voice")

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Voice settings
DEFAULT_VOICE = "nova"  # Warm, clear, direct
VOICE_OPTIONS = ["nova", "alloy", "echo", "fable", "onyx", "shimmer"]


@dataclass
class VoiceMessage:
    """A voice message received or to be sent."""
    text: str
    audio_bytes: Optional[bytes] = None
    duration_seconds: float = 0
    voice: str = DEFAULT_VOICE


class AriaVoice:
    """
    Aria's voice capabilities.
    
    - Transcribe incoming voice messages (Whisper)
    - Generate voice responses (OpenAI TTS)
    - Send voice messages to Telegram
    """
    
    def __init__(self):
        self.telegram_token = TELEGRAM_BOT_TOKEN
        self.openai_key = OPENAI_API_KEY
        self.http: Optional[httpx.AsyncClient] = None
        
        # Voice personality per mode
        self.voice_modes = {
            "command": {
                "voice": "onyx",  # Deep, authoritative
                "style": "crisp and action-oriented"
            },
            "sensemaking": {
                "voice": "nova",  # Warm, thoughtful
                "style": "thoughtful and questioning"
            },
            "ritual": {
                "voice": "shimmer",  # Soft, grounding
                "style": "calm and present"
            },
            "alert": {
                "voice": "echo",  # Clear, urgent
                "style": "clear and direct"
            },
            "default": {
                "voice": "nova",
                "style": "warm but direct"
            }
        }
        
        logger.info("AriaVoice initialized")
    
    async def _get_http(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.http is None:
            self.http = httpx.AsyncClient(timeout=60.0)
        return self.http
    
    async def close(self):
        """Close HTTP client."""
        if self.http:
            await self.http.aclose()
            self.http = None
    
    # ==================== TRANSCRIPTION ====================
    
    async def transcribe_telegram_voice(self, file_id: str) -> Optional[str]:
        """
        Transcribe a Telegram voice message using Whisper.
        
        Args:
            file_id: Telegram file_id for the voice message
            
        Returns:
            Transcribed text or None
        """
        if not self.telegram_token:
            logger.error("No Telegram token configured")
            return None
        
        if not self.openai_key:
            logger.error("No OpenAI API key configured")
            return None
        
        try:
            http = await self._get_http()
            
            # Step 1: Get file path from Telegram
            file_resp = await http.get(
                f"{TELEGRAM_API}/getFile",
                params={"file_id": file_id}
            )
            file_resp.raise_for_status()
            file_path = file_resp.json()["result"]["file_path"]
            
            # Step 2: Download the voice file
            voice_resp = await http.get(
                f"https://api.telegram.org/file/bot{self.telegram_token}/{file_path}"
            )
            voice_resp.raise_for_status()
            voice_data = voice_resp.content
            
            logger.info(f"Downloaded voice: {len(voice_data)} bytes")
            
            # Step 3: Transcribe with Whisper
            files = {
                "file": ("voice.ogg", io.BytesIO(voice_data), "audio/ogg"),
                "model": (None, "whisper-1"),
            }
            
            whisper_resp = await http.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.openai_key}"},
                files=files,
                timeout=30.0
            )
            whisper_resp.raise_for_status()
            
            transcription = whisper_resp.json().get("text", "")
            logger.info(f"Transcribed: {transcription[:100]}...")
            
            return transcription
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    # ==================== TEXT TO SPEECH ====================
    
    async def text_to_speech(
        self,
        text: str,
        voice: str = None,
        mode: str = "default"
    ) -> Optional[bytes]:
        """
        Convert text to speech using OpenAI TTS.
        
        Args:
            text: Text to convert (max 4096 chars)
            voice: Voice model (nova, alloy, echo, fable, onyx, shimmer)
            mode: Aria's mode (command, sensemaking, ritual, alert)
            
        Returns:
            Audio bytes (opus format) or None
        """
        if not self.openai_key:
            logger.error("No OpenAI API key configured")
            return None
        
        # Select voice based on mode if not specified
        if voice is None:
            voice = self.voice_modes.get(mode, self.voice_modes["default"])["voice"]
        
        # Truncate if too long
        text = text[:4096]
        
        try:
            http = await self._get_http()
            
            resp = await http.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "tts-1",
                    "input": text,
                    "voice": voice,
                    "response_format": "opus"  # Good for Telegram
                },
                timeout=60.0
            )
            resp.raise_for_status()
            
            audio = resp.content
            logger.info(f"Generated TTS: {len(audio)} bytes, voice={voice}")
            
            return audio
            
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            return None
    
    # ==================== SEND VOICE ====================
    
    async def send_voice_message(
        self,
        chat_id: int,
        text: str,
        mode: str = "default",
        caption: str = None
    ) -> bool:
        """
        Send a voice message to Telegram.
        
        Args:
            chat_id: Telegram chat ID
            text: Text to convert to voice
            mode: Aria's mode for voice selection
            caption: Optional text caption
            
        Returns:
            True if successful
        """
        if not self.telegram_token:
            logger.error("No Telegram token configured")
            return False
        
        try:
            # Generate audio
            audio = await self.text_to_speech(text, mode=mode)
            if not audio:
                return False
            
            http = await self._get_http()
            
            # Prepare form data
            data = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption[:1024]
            
            # Send to Telegram
            resp = await http.post(
                f"{TELEGRAM_API}/sendVoice",
                files={"voice": ("aria.ogg", io.BytesIO(audio), "audio/ogg")},
                data=data
            )
            resp.raise_for_status()
            
            logger.info(f"Voice sent to {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send voice: {e}")
            return False
    
    async def send_voice_alert(
        self,
        chat_id: int,
        message: str,
        urgency: str = "normal"
    ) -> bool:
        """
        Send an urgent voice alert.
        
        Args:
            chat_id: Telegram chat ID
            message: Alert message
            urgency: "low", "normal", "high", "critical"
        """
        # Add urgency prefix
        prefixes = {
            "low": "Hey, quick note.",
            "normal": "Aria here.",
            "high": "Important.",
            "critical": "Urgent - need your attention."
        }
        prefix = prefixes.get(urgency, "")
        full_message = f"{prefix} {message}"
        
        # Use alert voice mode for high/critical
        mode = "alert" if urgency in ["high", "critical"] else "default"
        
        return await self.send_voice_message(chat_id, full_message, mode=mode)
    
    # ==================== VOICE BRIEFS ====================
    
    async def send_morning_brief(
        self,
        chat_id: int,
        brief_content: str
    ) -> bool:
        """
        Send the morning brief as a voice message.
        
        Uses a warm, grounding tone to start the day.
        """
        intro = "Good morning. Here's your brief for today."
        full_brief = f"{intro} {brief_content}"
        
        return await self.send_voice_message(
            chat_id,
            full_brief,
            mode="ritual",
            caption="☀️ Morning Brief"
        )
    
    async def send_insight(
        self,
        chat_id: int,
        insight: str
    ) -> bool:
        """
        Send a pattern insight as voice.
        
        Uses thoughtful, questioning tone.
        """
        intro = "I'm noticing something."
        full_message = f"{intro} {insight}"
        
        return await self.send_voice_message(
            chat_id,
            full_message,
            mode="sensemaking",
            caption="💡 Pattern Detected"
        )
    
    async def send_nudge(
        self,
        chat_id: int,
        topic: str,
        context: str
    ) -> bool:
        """
        Send a gentle nudge about something stuck.
        """
        message = f"Hey, just checking in about {topic}. {context} Want to move on this, or should I mark it dormant?"
        
        return await self.send_voice_message(
            chat_id,
            message,
            mode="default",
            caption=f"🔄 Nudge: {topic[:30]}"
        )


# Singleton
_voice: Optional[AriaVoice] = None


def get_aria_voice() -> AriaVoice:
    """Get or create AriaVoice instance."""
    global _voice
    if _voice is None:
        _voice = AriaVoice()
    return _voice


async def transcribe_voice(file_id: str) -> Optional[str]:
    """Convenience: transcribe a voice message."""
    return await get_aria_voice().transcribe_telegram_voice(file_id)


async def send_voice(chat_id: int, text: str, mode: str = "default") -> bool:
    """Convenience: send a voice message."""
    return await get_aria_voice().send_voice_message(chat_id, text, mode)


