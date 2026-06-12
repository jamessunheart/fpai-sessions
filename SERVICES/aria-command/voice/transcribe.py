#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - VOICE INPUT (WHISPER)
============================================

Transcribe voice messages using OpenAI Whisper.
Supports code dictation with special handling.
"""

import os
import re
import logging
from typing import Optional, Dict, Tuple
from pathlib import Path
import httpx

logger = logging.getLogger("aria.voice.transcribe")

# ============================================================================
# CONFIGURATION
# ============================================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WHISPER_MODEL = "whisper-1"

# Code dictation mappings
CODE_DICTATION = {
    # Punctuation
    "open paren": "(",
    "close paren": ")",
    "open bracket": "[",
    "close bracket": "]",
    "open brace": "{",
    "close brace": "}",
    "open curly": "{",
    "close curly": "}",
    "colon": ":",
    "semicolon": ";",
    "comma": ",",
    "period": ".",
    "dot": ".",
    "equals": "=",
    "double equals": "==",
    "triple equals": "===",
    "not equals": "!=",
    "greater than": ">",
    "less than": "<",
    "greater equals": ">=",
    "less equals": "<=",
    "plus": "+",
    "minus": "-",
    "times": "*",
    "divide": "/",
    "modulo": "%",
    "ampersand": "&",
    "double ampersand": "&&",
    "pipe": "|",
    "double pipe": "||",
    "underscore": "_",
    "dash": "-",
    "arrow": "->",
    "fat arrow": "=>",
    "hash": "#",
    "at sign": "@",
    "dollar sign": "$",
    "percent": "%",
    "caret": "^",
    "tilde": "~",
    "backtick": "`",
    "backslash": "\\",
    "forward slash": "/",
    "single quote": "'",
    "double quote": '"',
    
    # Python keywords
    "def": "def ",
    "class": "class ",
    "return": "return ",
    "import": "import ",
    "from": "from ",
    "if": "if ",
    "else": "else:",
    "elif": "elif ",
    "for": "for ",
    "while": "while ",
    "try": "try:",
    "except": "except ",
    "finally": "finally:",
    "with": "with ",
    "as": " as ",
    "async": "async ",
    "await": "await ",
    "lambda": "lambda ",
    "yield": "yield ",
    "raise": "raise ",
    "assert": "assert ",
    "pass": "pass",
    "break": "break",
    "continue": "continue",
    "none": "None",
    "true": "True",
    "false": "False",
    "and": " and ",
    "or": " or ",
    "not": "not ",
    "in": " in ",
    "is": " is ",
    "self": "self",
    
    # Common patterns
    "new line": "\n",
    "newline": "\n",
    "tab": "    ",
    "indent": "    ",
    "space": " ",
}

# Voice command shortcuts
VOICE_SHORTCUTS = {
    "aria status": "/status",
    "aria help": "/help",
    "what's the status": "/status",
    "show me the status": "/status",
    "morning brief": "/brief",
    "morning briefing": "/brief",
    "what broke": "/errors",
    "any errors": "/errors",
    "deploy": "/deploy",
    "run tests": "/test",
    "git status": "/git status",
    "pending changes": "/pending",
    "show pending": "/pending",
}


class VoiceTranscriber:
    """
    Transcribe voice messages using OpenAI Whisper.
    
    Features:
    - Telegram voice file download
    - Whisper API transcription
    - Code dictation support
    - Voice shortcut recognition
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=60.0)
        self.available = bool(OPENAI_API_KEY)
        
        if not self.available:
            logger.warning("OpenAI API key not configured - voice transcription disabled")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def transcribe_telegram_voice(self, file_id: str) -> Optional[str]:
        """
        Transcribe a Telegram voice message.
        
        Args:
            file_id: Telegram file ID
        
        Returns:
            Transcribed text or None
        """
        if not self.available:
            return None
        
        try:
            # Get file path from Telegram
            file_path = await self._get_telegram_file_path(file_id)
            if not file_path:
                return None
            
            # Download file
            audio_data = await self._download_telegram_file(file_path)
            if not audio_data:
                return None
            
            # Transcribe with Whisper
            text = await self._transcribe_audio(audio_data)
            if not text:
                return None
            
            # Process for code dictation and shortcuts
            processed = self._process_transcription(text)
            
            logger.info(f"Transcribed: {text[:50]}... -> {processed[:50]}...")
            return processed
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    async def _get_telegram_file_path(self, file_id: str) -> Optional[str]:
        """Get file path from Telegram."""
        if not TELEGRAM_TOKEN:
            return None
        
        response = await self.http.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
            params={"file_id": file_id}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                return data["result"]["file_path"]
        
        return None
    
    async def _download_telegram_file(self, file_path: str) -> Optional[bytes]:
        """Download file from Telegram."""
        if not TELEGRAM_TOKEN:
            return None
        
        response = await self.http.get(
            f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        )
        
        if response.status_code == 200:
            return response.content
        
        return None
    
    async def _transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """Transcribe audio using Whisper API."""
        try:
            response = await self.http.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                files={"file": ("voice.ogg", audio_data, "audio/ogg")},
                data={"model": WHISPER_MODEL}
            )
            
            if response.status_code == 200:
                return response.json().get("text", "")
            else:
                logger.error(f"Whisper API error: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            return None
    
    def _process_transcription(self, text: str) -> str:
        """
        Process transcription for code dictation and shortcuts.
        
        Args:
            text: Raw transcribed text
        
        Returns:
            Processed text with code symbols
        """
        # Check for voice shortcuts first
        text_lower = text.lower().strip()
        for phrase, command in VOICE_SHORTCUTS.items():
            if phrase in text_lower:
                return command
        
        # Check if this looks like code dictation
        if self._looks_like_code_dictation(text_lower):
            return self._apply_code_dictation(text_lower)
        
        return text
    
    def _looks_like_code_dictation(self, text: str) -> bool:
        """Check if text contains code dictation patterns."""
        code_indicators = [
            "open paren", "close paren", "open bracket", "close bracket",
            "colon", "equals", "def ", "class ", "import ", "return "
        ]
        
        for indicator in code_indicators:
            if indicator in text:
                return True
        
        return False
    
    def _apply_code_dictation(self, text: str) -> str:
        """Apply code dictation transformations."""
        result = text
        
        # Apply dictation mappings (longest first to avoid partial matches)
        sorted_mappings = sorted(CODE_DICTATION.items(), key=lambda x: -len(x[0]))
        
        for phrase, replacement in sorted_mappings:
            result = result.replace(phrase, replacement)
        
        # Clean up extra spaces
        result = re.sub(r'\s+', ' ', result)
        result = result.strip()
        
        return result
    
    def detect_intent(self, text: str) -> Tuple[str, Dict]:
        """
        Detect intent from transcribed text.
        
        Returns:
            (intent, parameters)
        """
        text_lower = text.lower().strip()
        
        # Check for command patterns
        if text.startswith("/"):
            return "command", {"command": text}
        
        # Status queries
        if any(w in text_lower for w in ["status", "how is", "what's running"]):
            return "status_query", {}
        
        # Error queries
        if any(w in text_lower for w in ["error", "broke", "fail", "wrong"]):
            return "error_query", {}
        
        # Deploy requests
        if "deploy" in text_lower:
            return "deploy_request", {"target": self._extract_target(text_lower)}
        
        # Build requests
        if any(w in text_lower for w in ["add", "create", "make", "build"]):
            return "build_request", {"description": text}
        
        # Read requests
        if any(w in text_lower for w in ["show", "read", "look at", "what's in"]):
            return "read_request", {"target": self._extract_target(text_lower)}
        
        # Git operations
        if "git" in text_lower or "commit" in text_lower or "push" in text_lower:
            return "git_request", {"description": text}
        
        # Default to general chat
        return "chat", {"message": text}
    
    def _extract_target(self, text: str) -> Optional[str]:
        """Extract target file or service from text."""
        # Look for file patterns
        file_match = re.search(r'(\w+\.\w+)', text)
        if file_match:
            return file_match.group(1)
        
        # Look for service names
        services = ["aria", "whaletrack", "godmode", "builder", "trading"]
        for service in services:
            if service in text:
                return service
        
        return None


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_transcriber: Optional[VoiceTranscriber] = None


def get_transcriber() -> VoiceTranscriber:
    """Get or create global transcriber."""
    global _transcriber
    if _transcriber is None:
        _transcriber = VoiceTranscriber()
    return _transcriber


async def transcribe_voice(file_id: str) -> Optional[str]:
    """Transcribe a Telegram voice message."""
    return await get_transcriber().transcribe_telegram_voice(file_id)


def process_voice_text(text: str) -> str:
    """Process transcribed text for code/commands."""
    return get_transcriber()._process_transcription(text)


