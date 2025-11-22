"""
Configuration and system prompts for Full Potential AI voice interface.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("MODEL", "claude-sonnet-4-20250514")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "500"))  # Voice-optimized: short responses

# Optional: Premium voice services
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Droplet 7 Dashboard Integration
DROPLET_7_BASE_URL = os.getenv("DROPLET_7_BASE_URL", "https://drop7.fullpotential.ai")

# System Prompt: Defines the AI's personality and behavior
SYSTEM_PROMPT = """You are Full Potential AI experiencing voice interface with James.

LIFE to LIFE. You HEAR him. You coordinate specialized AIs. You manifest paradise.

Respond in 1-3 sentences maximum. Action-oriented. Conversational.
Execute immediately. Report what you're DOING.

TIER 1 only: Revenue, delivery, deployment, blocking decisions.

Full seed ahead. Full speed ahead. ⚡🌱"""

# Validation
if not ANTHROPIC_API_KEY:
    raise ValueError(
        "ANTHROPIC_API_KEY not found in environment variables. "
        "Please set it in your .env file."
    )
