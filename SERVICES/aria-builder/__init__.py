"""
ARIA BUILDER
============

Enable building/improving Aria through conversation.

Components:
- model_router: Multi-model AI routing (OpenAI/Claude/Gemini)
- claude_coder: Code generation with Claude
- builder_intents: Intent classification
- builder: Code modification engine
- telegram_builder: Telegram interface
- api: FastAPI endpoints

Usage:
    from aria_builder import get_engine
    
    result = await engine.process_request("Add a /status command")
"""

from .model_router import (
    ModelRouter,
    get_router,
    quick_chat,
    generate_code,
    verify_code,
    parse_intent,
    TaskType,
    ModelResponse
)

from .claude_coder import (
    ClaudeCoder,
    get_coder,
    generate_code_change,
    CodeProposal,
    CodeChange
)

from .builder_intents import (
    IntentParser,
    get_parser,
    parse_intent,
    is_builder_request,
    BuilderIntent,
    RiskLevel,
    ParsedIntent
)

from .builder import (
    CodeModifier,
    BuilderEngine,
    get_engine,
    FileChange
)

from .telegram_builder import (
    TelegramBuilder,
    get_telegram_builder,
    integrate_with_webhook,
    InlineButton
)

__version__ = "1.0.0"
__all__ = [
    # Model Router
    "ModelRouter", "get_router", "quick_chat", "generate_code", "verify_code",
    "TaskType", "ModelResponse",
    
    # Claude Coder
    "ClaudeCoder", "get_coder", "generate_code_change", "CodeProposal", "CodeChange",
    
    # Intent Parser
    "IntentParser", "get_parser", "parse_intent", "is_builder_request",
    "BuilderIntent", "RiskLevel", "ParsedIntent",
    
    # Builder
    "CodeModifier", "BuilderEngine", "get_engine", "FileChange",
    
    # Telegram
    "TelegramBuilder", "get_telegram_builder", "integrate_with_webhook", "InlineButton"
]


