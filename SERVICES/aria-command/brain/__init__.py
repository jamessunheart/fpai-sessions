"""
ARIA COMMAND CENTER - OPUS BRAIN
==================================

Intelligent agent with full codebase awareness.
"""

from .opus_router import (
    OpusRouter,
    get_router,
    ask_opus,
    ModelResponse,
    TaskComplexity,
    MODELS
)

from .codebase_index import (
    CodebaseIndex,
    get_index,
    search_codebase,
    build_context_for_query,
    ensure_indexed,
    IndexedFile,
    SearchResult
)

from .conversation import (
    Conversation,
    ConversationManager,
    get_conversation,
    get_manager,
    Message,
    WorkingFile,
    Plan
)

from .tools import (
    ToolExecutor,
    get_tools,
    execute_tool,
    ToolResult,
    TOOLS
)

from .opus_brain import (
    OpusBrain,
    get_brain,
    think,
    quick_think,
    get_brain_status,
    BrainResponse
)

__all__ = [
    # Router
    "OpusRouter",
    "get_router",
    "ask_opus",
    "ModelResponse",
    "TaskComplexity",
    "MODELS",
    # Codebase
    "CodebaseIndex",
    "get_index",
    "search_codebase",
    "build_context_for_query",
    "ensure_indexed",
    "IndexedFile",
    "SearchResult",
    # Conversation
    "Conversation",
    "ConversationManager",
    "get_conversation",
    "get_manager",
    "Message",
    "WorkingFile",
    "Plan",
    # Tools
    "ToolExecutor",
    "get_tools",
    "execute_tool",
    "ToolResult",
    "TOOLS",
    # Brain
    "OpusBrain",
    "get_brain",
    "think",
    "quick_think",
    "get_brain_status",
    "BrainResponse"
]


