"""
Conversational Voice Development - Voice-first coding interface.

Enables voice-driven development with narration, code reading,
and conversational interaction.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger("aria.voice.conversational")


@dataclass
class VoiceContext:
    """Context for a voice conversation."""
    session_id: str
    current_file: Optional[str] = None
    recent_changes: List[Dict[str, Any]] = None
    last_action: Optional[str] = None
    mode: str = "chat"  # "chat", "coding", "review", "debug"
    
    def __post_init__(self):
        if self.recent_changes is None:
            self.recent_changes = []


class ConversationalVoice:
    """
    Voice-driven development interface.
    
    Capabilities:
    - Narrate code changes as they happen
    - Read code snippets aloud
    - Explain recent actions
    - Accept voice commands
    - Interrupt mid-execution
    """
    
    # Voice personas
    PERSONAS = {
        "aria": {
            "voice": "nova",  # OpenAI TTS voice
            "style": "warm and professional",
            "speed": 1.0
        },
        "technical": {
            "voice": "onyx",
            "style": "precise and technical",
            "speed": 0.95
        },
        "casual": {
            "voice": "shimmer",
            "style": "friendly and conversational",
            "speed": 1.05
        }
    }
    
    def __init__(self, persona: str = "aria"):
        self.persona = self.PERSONAS.get(persona, self.PERSONAS["aria"])
        self.contexts: Dict[str, VoiceContext] = {}
        self.is_speaking = False
        self.interrupt_requested = False
        
        # TTS configuration
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.tts_enabled = bool(self.openai_api_key)
    
    async def narrate_change(
        self,
        change_description: str,
        file_path: str,
        session_id: str = "default"
    ) -> Optional[bytes]:
        """
        Narrate a code change as it happens.
        
        Returns audio bytes for playback.
        """
        context = self._get_or_create_context(session_id)
        context.current_file = file_path
        context.recent_changes.append({
            "description": change_description,
            "file": file_path,
            "timestamp": datetime.now().isoformat()
        })
        
        # Generate narration
        narration = self._format_narration(change_description, file_path)
        
        if self.tts_enabled:
            return await self._text_to_speech(narration)
        
        logger.info(f"[VOICE] {narration}")
        return None
    
    async def read_code(
        self,
        code: str,
        filename: str,
        context: str = "",
        session_id: str = "default"
    ) -> Optional[bytes]:
        """
        Read code aloud with natural phrasing.
        """
        # Format code for speaking
        spoken_code = self._format_code_for_speaking(code, filename)
        
        if context:
            spoken_code = f"{context}\n\n{spoken_code}"
        
        if self.tts_enabled:
            return await self._text_to_speech(spoken_code)
        
        logger.info(f"[VOICE READ] {spoken_code}")
        return None
    
    async def read_diff(
        self,
        original: str,
        modified: str,
        filename: str,
        session_id: str = "default"
    ) -> Optional[bytes]:
        """
        Read a diff aloud, explaining the changes.
        """
        explanation = self._explain_diff(original, modified, filename)
        
        if self.tts_enabled:
            return await self._text_to_speech(explanation)
        
        logger.info(f"[VOICE DIFF] {explanation}")
        return None
    
    async def explain_action(
        self,
        action: str,
        result: Dict[str, Any],
        session_id: str = "default"
    ) -> Optional[bytes]:
        """
        Explain what Aria just did.
        """
        context = self._get_or_create_context(session_id)
        context.last_action = action
        
        explanation = self._format_action_explanation(action, result)
        
        if self.tts_enabled:
            return await self._text_to_speech(explanation)
        
        logger.info(f"[VOICE EXPLAIN] {explanation}")
        return None
    
    async def handle_voice_command(
        self,
        transcribed_text: str,
        session_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Handle a voice command and return appropriate response.
        """
        context = self._get_or_create_context(session_id)
        text_lower = transcribed_text.lower().strip()
        
        # Check for interrupt
        if "stop" in text_lower or "cancel" in text_lower or "wait" in text_lower:
            self.interrupt_requested = True
            return {
                "type": "interrupt",
                "message": "Stopping. What would you like to do?",
                "audio": await self._text_to_speech("Stopping. What would you like to do?") if self.tts_enabled else None
            }
        
        # Check for read commands
        if "read" in text_lower:
            if "the changes" in text_lower or "what changed" in text_lower:
                return await self._handle_read_changes(context)
            if "the file" in text_lower or context.current_file:
                return await self._handle_read_file(context)
        
        # Check for explain commands
        if "what did you do" in text_lower or "explain" in text_lower:
            return await self._handle_explain(context)
        
        # Check for status commands
        if "status" in text_lower or "where are we" in text_lower:
            return await self._handle_status(context)
        
        # Default: treat as general query
        return {
            "type": "query",
            "text": transcribed_text,
            "context": {
                "current_file": context.current_file,
                "mode": context.mode,
                "recent_actions": len(context.recent_changes)
            }
        }
    
    def _get_or_create_context(self, session_id: str) -> VoiceContext:
        """Get or create a voice context for a session."""
        if session_id not in self.contexts:
            self.contexts[session_id] = VoiceContext(session_id=session_id)
        return self.contexts[session_id]
    
    def _format_narration(self, change: str, file_path: str) -> str:
        """Format a change for natural narration."""
        filename = os.path.basename(file_path)
        
        # Keep it concise but informative
        return f"In {filename}: {change}"
    
    def _format_code_for_speaking(self, code: str, filename: str) -> str:
        """Format code for natural speech."""
        lines = code.strip().split('\n')
        
        if len(lines) > 20:
            # Summarize long code
            return (
                f"This file has {len(lines)} lines. "
                f"It starts with: {self._code_to_speech(lines[0])}. "
                f"And ends with: {self._code_to_speech(lines[-1])}."
            )
        
        # Read shorter code
        spoken_lines = [self._code_to_speech(line) for line in lines if line.strip()]
        return f"Reading {os.path.basename(filename)}:\n" + "\n".join(spoken_lines[:10])
    
    def _code_to_speech(self, line: str) -> str:
        """Convert a code line to speakable text."""
        # Replace common symbols with words
        replacements = {
            "def ": "define function ",
            "class ": "class ",
            "import ": "import ",
            "from ": "from ",
            "return ": "return ",
            "if ": "if ",
            "else:": "else",
            "elif ": "else if ",
            "for ": "for loop ",
            "while ": "while loop ",
            "try:": "try block",
            "except": "except ",
            "async ": "async ",
            "await ": "await ",
            "==": " equals ",
            "!=": " not equals ",
            "<=": " less than or equal ",
            ">=": " greater than or equal ",
            "=>": " arrow ",
            "->": " returns ",
            "+=": " plus equals ",
            "-=": " minus equals ",
            "**": " power ",
            "//": " integer division ",
            "()": " empty parentheses",
            "[]": " empty list",
            "{}": " empty dictionary",
            "None": " none",
            "True": " true",
            "False": " false",
            "_": " underscore ",
            "self.": "self dot ",
            "cls.": "class dot ",
        }
        
        result = line.strip()
        for old, new in replacements.items():
            result = result.replace(old, new)
        
        # Clean up multiple spaces
        result = ' '.join(result.split())
        return result
    
    def _explain_diff(self, original: str, modified: str, filename: str) -> str:
        """Generate a spoken explanation of a diff."""
        orig_lines = set(original.split('\n'))
        mod_lines = set(modified.split('\n'))
        
        added = mod_lines - orig_lines
        removed = orig_lines - mod_lines
        
        parts = [f"Changes in {os.path.basename(filename)}:"]
        
        if removed:
            parts.append(f"Removed {len(removed)} lines.")
        if added:
            parts.append(f"Added {len(added)} lines.")
        
        if len(added) <= 3:
            for line in list(added)[:3]:
                if line.strip():
                    parts.append(f"Added: {self._code_to_speech(line)}")
        
        return " ".join(parts)
    
    def _format_action_explanation(self, action: str, result: Dict[str, Any]) -> str:
        """Format an action explanation for speech."""
        success = result.get("success", True)
        
        if success:
            output = result.get("output", "")
            files = result.get("files_modified", [])
            
            if files:
                files_str = ", ".join(os.path.basename(f) for f in files[:3])
                return f"Done. {action}. Modified: {files_str}."
            else:
                return f"Done. {action}."
        else:
            error = result.get("error", "Unknown error")
            return f"That didn't work. {error[:100]}"
    
    async def _handle_read_changes(self, context: VoiceContext) -> Dict[str, Any]:
        """Handle request to read recent changes."""
        if not context.recent_changes:
            message = "No recent changes to report."
        else:
            recent = context.recent_changes[-3:]
            changes = [f"{c['description']} in {os.path.basename(c['file'])}" for c in recent]
            message = "Recent changes: " + ". ".join(changes)
        
        return {
            "type": "narration",
            "message": message,
            "audio": await self._text_to_speech(message) if self.tts_enabled else None
        }
    
    async def _handle_read_file(self, context: VoiceContext) -> Dict[str, Any]:
        """Handle request to read current file."""
        if not context.current_file:
            message = "No file is currently open."
            return {
                "type": "error",
                "message": message,
                "audio": await self._text_to_speech(message) if self.tts_enabled else None
            }
        
        # Read file content
        try:
            with open(context.current_file, 'r') as f:
                content = f.read()
            
            audio = await self.read_code(content, context.current_file)
            return {
                "type": "read",
                "file": context.current_file,
                "audio": audio
            }
        except Exception as e:
            message = f"Couldn't read the file: {str(e)[:50]}"
            return {
                "type": "error",
                "message": message,
                "audio": await self._text_to_speech(message) if self.tts_enabled else None
            }
    
    async def _handle_explain(self, context: VoiceContext) -> Dict[str, Any]:
        """Handle request to explain last action."""
        if not context.last_action:
            message = "I haven't done anything yet in this session."
        else:
            message = f"My last action was: {context.last_action}"
        
        return {
            "type": "explanation",
            "message": message,
            "audio": await self._text_to_speech(message) if self.tts_enabled else None
        }
    
    async def _handle_status(self, context: VoiceContext) -> Dict[str, Any]:
        """Handle request for current status."""
        parts = [f"Mode: {context.mode}"]
        if context.current_file:
            parts.append(f"Working on: {os.path.basename(context.current_file)}")
        parts.append(f"Changes made: {len(context.recent_changes)}")
        
        message = ". ".join(parts)
        
        return {
            "type": "status",
            "message": message,
            "audio": await self._text_to_speech(message) if self.tts_enabled else None
        }
    
    async def _text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using OpenAI TTS."""
        if not self.tts_enabled:
            return None
        
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "tts-1",
                        "voice": self.persona["voice"],
                        "input": text,
                        "speed": self.persona["speed"]
                    }
                )
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.error(f"TTS failed: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None


# Singleton instance
_voice: Optional[ConversationalVoice] = None

def get_conversational_voice() -> ConversationalVoice:
    """Get or create conversational voice instance."""
    global _voice
    if _voice is None:
        _voice = ConversationalVoice()
    return _voice


