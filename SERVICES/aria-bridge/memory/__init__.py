"""
ARIA MEMORY SYSTEM
==================

Persistent memory that survives restarts and learns over time.

Layers:
- Identity: Who Sunheart is (permanent)
- Context: Current state (daily/weekly)
- Conversation: Recent exchanges (rolling)
- Learning: Patterns and insights (grows)

Components:
- store.py: Core SQLite storage (fast, local)
- recall.py: Semantic search and context building
- learn.py: Learning from outcomes
- identity.py: Identity and context memory
- compress.py: Conversation compression
- mem0_sync.py: Cloud sync to Mem0 API
"""

from .store import (
    get_memory_store,
    Memory,
    MemoryCategory,
    MemoryImportance
)

from .recall import get_memory_recall

from .learn import (
    get_memory_learning,
    OutcomeType
)

from .identity import (
    get_identity_memory,
    get_context_memory
)

from .compress import (
    get_memory_compressor,
    run_compression
)

from .mem0_sync import (
    get_mem0_sync,
    sync_important_memories
)


__all__ = [
    # Store
    "get_memory_store",
    "Memory",
    "MemoryCategory",
    "MemoryImportance",
    
    # Recall
    "get_memory_recall",
    
    # Learn
    "get_memory_learning",
    "OutcomeType",
    
    # Identity
    "get_identity_memory",
    "get_context_memory",
    
    # Compress
    "get_memory_compressor",
    "run_compression",
    
    # Cloud Sync
    "get_mem0_sync",
    "sync_important_memories"
]

