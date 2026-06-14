"""
Voice layer - Whisper transcription and TTS output.
"""

from .transcribe import (
    VoiceTranscriber,
    get_transcriber,
    transcribe_voice,
    process_voice_text
)

from .speak import (
    VoiceSpeaker,
    get_speaker,
    speak,
    send_voice,
    send_alert,
    send_brief,
    Voice
)

__all__ = [
    "VoiceTranscriber",
    "get_transcriber",
    "transcribe_voice",
    "process_voice_text",
    "VoiceSpeaker",
    "get_speaker",
    "speak",
    "send_voice",
    "send_alert",
    "send_brief",
    "Voice"
]


