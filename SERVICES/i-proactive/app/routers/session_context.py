"""
Session Context API - Provides unified context for Claude sessions
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, List
import json
import os
from pathlib import Path

router = APIRouter(prefix="/session", tags=["session"])


class ContextUpdate(BaseModel):
    """Model for context update requests"""
    decisions: List[str] = []
    accomplishments: List[str] = []
    pending: List[str] = []
    insights: List[str] = []


@router.get("/context")
async def get_session_context() -> Dict[str, Any]:
    """
    Get unified session context for Claude.

    Returns everything a new Claude session needs to know:
    - Current system state
    - Pending work
    - Key decisions
    - Common commands
    - Architecture overview
    """

    # Load unified knowledge if it exists
    knowledge_path = Path.home() / "Development/docs/sessions/UNIFIED_KNOWLEDGE.json"
    unified_knowledge = {}
    if knowledge_path.exists():
        with open(knowledge_path) as f:
            unified_knowledge = json.load(f)

    # Load session context if it exists
    context_path = Path.home() / ".claude-context/SESSION_CONTEXT.md"
    context_md = ""
    if context_path.exists():
        with open(context_path) as f:
            context_md = f.read()

    return {
        "session_context": {
            "unified_knowledge": unified_knowledge,
            "context_markdown": context_md,
            "last_updated": unified_knowledge.get("last_updated", "unknown")
        },
        "quick_reference": {
            "services": {
                "i_proactive": "http://198.54.123.234:8400",
                "i_match": "http://198.54.123.234:8401",
                "ollama": "http://localhost:11434"
            },
            "key_endpoints": [
                "/health",
                "/autonomous/status",
                "/optimization/report",
                "/tasks/execute",
                "/session/context"
            ],
            "documentation": [
                "~/Development/SERVICES/FULL_SOVEREIGNTY_ACHIEVED.md",
                "~/Development/SERVICES/OPTIMIZATION_STRATEGY_COMPLETE.md",
                "~/Development/SERVICES/QUICK_START_GUIDE.md"
            ]
        },
        "pending_work": unified_knowledge.get("pending_work", []),
        "next_priorities": unified_knowledge.get("next_session_priorities", []),
        "usage": {
            "curl": "curl http://198.54.123.234:8400/session/context",
            "tell_claude": "Load context from http://198.54.123.234:8400/session/context before we start"
        }
    }


@router.get("/context/summary")
async def get_context_summary() -> str:
    """
    Get a concise text summary for Claude to load.
    Returns plain text that can be directly pasted into Claude.
    """

    context_path = Path.home() / ".claude-context/SESSION_CONTEXT.md"
    if context_path.exists():
        with open(context_path) as f:
            return f.read()

    return """# No Session Context Found

Please create session context first:
1. Read ~/Development/docs/sessions/UNIFIED_KNOWLEDGE.json
2. Read latest session handoff in ~/Development/docs/sessions/SESSION_HANDOFFS/

Or run the context creation script.
"""


@router.post("/context/update")
async def update_session_context(update: ContextUpdate) -> Dict[str, Any]:
    """
    Update session context with new information.
    Called at end of each session to maintain continuity.
    """

    knowledge_path = Path.home() / "Development/docs/sessions/UNIFIED_KNOWLEDGE.json"

    if knowledge_path.exists():
        with open(knowledge_path) as f:
            knowledge = json.load(f)
    else:
        knowledge = {"total_sessions": 0}

    # Update session count
    knowledge["total_sessions"] = knowledge.get("total_sessions", 0) + 1

    # Add new decisions
    if update.decisions:
        knowledge.setdefault("core_decisions", []).extend(update.decisions)

    # Update pending work
    if update.pending:
        knowledge["pending_work"] = update.pending

    # Add insights to best practices
    if update.insights:
        knowledge.setdefault("best_practices", []).extend(update.insights)

    # Save back
    with open(knowledge_path, 'w') as f:
        json.dump(knowledge, f, indent=2)

    return {
        "status": "updated",
        "sessions_total": knowledge["total_sessions"],
        "message": "Session context updated successfully"
    }
