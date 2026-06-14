"""
BRICK 2 AI Integration Layer
============================

Provides unified access to multiple AI providers:
- Claude (Anthropic) - Strategic content, complex reasoning
- GPT-4 (OpenAI) - Conversational AI, function calling
- Gemini (Google) - Multimodal content, data analysis

Uses the core API Gateway client when available for metering,
or falls back to direct API calls.
"""

from .gateway import AIGateway, AIProvider, AIResponse
from .providers.claude import ClaudeProvider
from .providers.openai import OpenAIProvider
from .providers.gemini import GeminiProvider

__all__ = [
    "AIGateway",
    "AIProvider", 
    "AIResponse",
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
]




