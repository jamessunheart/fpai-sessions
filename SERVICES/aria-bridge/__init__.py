"""
ARIA BRIDGE
===========

Bridge across dimensions.
Translating vision to action, returning signal from manifestation to dream.
Now with voice + proactive outreach + persistent memory.

Components:
- soul.py: Aria's constitution and identity
- dream_journal.py: Vision tracking and recording
- translator.py: Dimension crossing translation
- manifestation.py: Digital/physical navigation tools
- feedback_loop.py: Returning signals from manifestation
- dimensional_flow.py: Ensuring nothing stays stuck
- voice.py: Voice in/out (Whisper + TTS)
- proactive.py: Proactive sensing and outreach
- memory/: Persistent memory system
- telegram_bridge.py: Partnership interface
- main.py: Unified application
"""

from soul import ARIA_CONSTITUTION, FIRST_MESSAGE, detect_dimension, detect_mode
from dream_journal import get_dream_journal
from translator import get_translator
from manifestation import get_manifestation_tools
from feedback_loop import get_feedback_loop
from dimensional_flow import get_dimensional_flow
from voice import get_aria_voice
from proactive import get_proactive_daemon

# Memory imports
try:
    from memory import (
        get_memory_store, get_memory_recall, get_memory_learning,
        get_identity_memory, get_context_memory, run_compression
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

__all__ = [
    "ARIA_CONSTITUTION",
    "FIRST_MESSAGE",
    "detect_dimension",
    "detect_mode",
    "get_dream_journal",
    "get_translator",
    "get_manifestation_tools",
    "get_feedback_loop",
    "get_dimensional_flow",
    "get_aria_voice",
    "get_proactive_daemon"
]

if MEMORY_AVAILABLE:
    __all__.extend([
        "get_memory_store",
        "get_memory_recall",
        "get_memory_learning",
        "get_identity_memory",
        "get_context_memory",
        "run_compression"
    ])

