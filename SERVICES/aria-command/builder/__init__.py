#!/usr/bin/env python3
"""
ARIA UNIFIED BUILDER MODULE
===========================

The most powerful builder setup combining:
- AI code generation (Claude)
- AI verification (Gemini)
- Backup/rollback system
- Build queue with complexity gating
- Module scaffolding for apprentices
- Full Telegram interface with inline buttons

Usage:
    from builder import get_unified_builder, build_from_request
    
    # AI-powered builds
    result = await build_from_request(
        request="Create a health check endpoint",
        user_id="123",
        scope="steward"
    )
    
    # Direct builder access
    builder = get_unified_builder()
    status = builder.get_queue_status()
"""

# Apprentice module builder tools
from .tools import (
    scaffold_module,
    update_module_code,
    test_module,
    list_my_modules,
    submit_module,
    get_builder_tools,
    get_module_code,
    delete_module,
    ai_create_module
)
from .sandbox import SandboxExecutor
from .templates import ModuleTemplates

# Unified builder engine
from .unified_engine import (
    UnifiedBuilder,
    get_unified_builder,
    build_from_request,
    FileChange,
    BuildJob,
    BuildStatus,
    RiskLevel,
    Complexity,
    SCOPE_DEFINITIONS,
    BuildNotifier,
    get_notifier
)

# Telegram interface
from .telegram_interface import (
    BuilderTelegramInterface,
    get_builder_interface,
    handle_builder_update,
    InlineButton
)

__all__ = [
    # Apprentice tools
    'scaffold_module',
    'update_module_code', 
    'test_module',
    'list_my_modules',
    'submit_module',
    'get_builder_tools',
    'get_module_code',
    'delete_module',
    'ai_create_module',
    'SandboxExecutor',
    'ModuleTemplates',
    
    # Unified engine
    'UnifiedBuilder',
    'get_unified_builder',
    'build_from_request',
    'FileChange',
    'BuildJob',
    'BuildStatus',
    'RiskLevel',
    'Complexity',
    'SCOPE_DEFINITIONS',
    'BuildNotifier',
    'get_notifier',
    
    # Telegram interface
    'BuilderTelegramInterface',
    'get_builder_interface',
    'handle_builder_update',
    'InlineButton'
]

