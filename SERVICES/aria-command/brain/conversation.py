#!/usr/bin/env python3
"""
ARIA COMMAND CENTER - CONVERSATION MANAGER
============================================

Multi-turn conversation with full context.
Like Cursor's chat with memory and working files.
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger("aria.conversation")

# ============================================================================
# CONFIGURATION
# ============================================================================

STATE_DIR = Path(os.getenv("ARIA_STATE_DIR", "/tmp/aria-command")) / "conversations"
STATE_DIR.mkdir(parents=True, exist_ok=True)

MAX_HISTORY = 50  # Max messages to keep
MAX_CONTEXT_TOKENS = 100000  # Max tokens for context


@dataclass
class Message:
    """A conversation message."""
    role: str  # user, assistant, tool
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[Dict] = None
    tool_results: List[Dict] = None
    
    def to_dict(self) -> Dict:
        d = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        if self.tool_results:
            d["tool_results"] = self.tool_results
        return d
    
    def to_api_format(self) -> Dict:
        """Convert to API message format."""
        msg = {"role": self.role, "content": self.content}
        # Note: tool_calls are NOT included - Anthropic API rejects them
        # Tool calls/results are handled separately in opus_brain.py
        return msg


@dataclass
class WorkingFile:
    """A file currently being worked on."""
    path: str
    content: str
    original_content: str
    modified: bool = False
    last_accessed: datetime = field(default_factory=datetime.now)


@dataclass
class Plan:
    """A multi-step plan being executed."""
    id: str
    description: str
    steps: List[Dict]
    current_step: int = 0
    completed: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class Conversation:
    """
    A conversation session with full context.
    
    Features:
    - Message history
    - Working files
    - Multi-step plans
    - Context building
    """
    
    def __init__(self, conversation_id: str):
        self.id = conversation_id
        self.messages: List[Message] = []
        self.working_files: Dict[str, WorkingFile] = {}
        self.current_plan: Optional[Plan] = None
        self.metadata: Dict = {}
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
        # Load existing conversation
        self._load()
    
    def add_message(self, role: str, content: str, **kwargs) -> Message:
        """Add a message to the conversation."""
        msg = Message(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.last_activity = datetime.now()
        
        # Trim if too long
        if len(self.messages) > MAX_HISTORY:
            self.messages = self.messages[-MAX_HISTORY:]
        
        self._save()
        return msg
    
    def get_history(self, limit: int = None) -> List[Message]:
        """Get message history."""
        if limit:
            return self.messages[-limit:]
        return self.messages
    
    def get_history_for_api(self, limit: int = None) -> List[Dict]:
        """Get history in API format."""
        history = self.get_history(limit)
        return [m.to_api_format() for m in history]
    
    def add_working_file(self, path: str, content: str):
        """Add or update a working file."""
        if path in self.working_files:
            wf = self.working_files[path]
            wf.content = content
            wf.modified = content != wf.original_content
            wf.last_accessed = datetime.now()
        else:
            self.working_files[path] = WorkingFile(
                path=path,
                content=content,
                original_content=content
            )
        self._save()
    
    def get_working_file(self, path: str) -> Optional[WorkingFile]:
        """Get a working file."""
        return self.working_files.get(path)
    
    def update_working_file(self, path: str, new_content: str):
        """Update content of a working file."""
        if path in self.working_files:
            wf = self.working_files[path]
            wf.content = new_content
            wf.modified = True
            wf.last_accessed = datetime.now()
            self._save()
    
    def get_modified_files(self) -> List[WorkingFile]:
        """Get all modified working files."""
        return [wf for wf in self.working_files.values() if wf.modified]
    
    def clear_working_files(self):
        """Clear all working files."""
        self.working_files = {}
        self._save()
    
    def set_plan(self, description: str, steps: List[str]) -> Plan:
        """Set a multi-step plan."""
        self.current_plan = Plan(
            id=hashlib.md5(description.encode()).hexdigest()[:8],
            description=description,
            steps=[{"step": s, "completed": False} for s in steps]
        )
        self._save()
        return self.current_plan
    
    def advance_plan(self) -> Optional[Dict]:
        """Advance to next plan step."""
        if not self.current_plan:
            return None
        
        if self.current_plan.current_step < len(self.current_plan.steps):
            step = self.current_plan.steps[self.current_plan.current_step]
            step["completed"] = True
            self.current_plan.current_step += 1
            
            if self.current_plan.current_step >= len(self.current_plan.steps):
                self.current_plan.completed = True
            
            self._save()
            return step
        
        return None
    
    def get_current_step(self) -> Optional[Dict]:
        """Get current plan step."""
        if not self.current_plan:
            return None
        if self.current_plan.current_step < len(self.current_plan.steps):
            return self.current_plan.steps[self.current_plan.current_step]
        return None
    
    def build_full_context(self, codebase_context: str = "") -> str:
        """Build full context for LLM."""
        parts = []
        
        # Add working files
        if self.working_files:
            parts.append("## Currently Working On:\n")
            for path, wf in self.working_files.items():
                status = " (MODIFIED)" if wf.modified else ""
                parts.append(f"### {path}{status}\n```\n{wf.content[:5000]}\n```\n")
        
        # Add current plan
        if self.current_plan and not self.current_plan.completed:
            parts.append(f"\n## Current Plan: {self.current_plan.description}\n")
            for i, step in enumerate(self.current_plan.steps):
                status = "✅" if step["completed"] else "⬜" if i == self.current_plan.current_step else "⏳"
                parts.append(f"{status} {step['step']}\n")
        
        # Add codebase context
        if codebase_context:
            parts.append(f"\n## Relevant Codebase Context:\n{codebase_context}\n")
        
        return "\n".join(parts)
    
    def get_summary(self) -> str:
        """Get conversation summary."""
        msg_count = len(self.messages)
        file_count = len(self.working_files)
        modified_count = len(self.get_modified_files())
        
        summary = f"Conversation {self.id[:8]}: {msg_count} messages"
        if file_count:
            summary += f", {file_count} files ({modified_count} modified)"
        if self.current_plan:
            progress = f"{self.current_plan.current_step}/{len(self.current_plan.steps)}"
            summary += f", Plan: {progress}"
        
        return summary
    
    def _save(self):
        """Save conversation to disk."""
        file_path = STATE_DIR / f"{self.id}.json"
        
        data = {
            "id": self.id,
            "messages": [m.to_dict() for m in self.messages],
            "working_files": {
                path: {
                    "path": wf.path,
                    "content": wf.content,
                    "original_content": wf.original_content,
                    "modified": wf.modified
                }
                for path, wf in self.working_files.items()
            },
            "current_plan": {
                "id": self.current_plan.id,
                "description": self.current_plan.description,
                "steps": self.current_plan.steps,
                "current_step": self.current_plan.current_step,
                "completed": self.current_plan.completed
            } if self.current_plan else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat()
        }
        
        file_path.write_text(json.dumps(data, indent=2))
    
    def _load(self):
        """Load conversation from disk."""
        file_path = STATE_DIR / f"{self.id}.json"
        
        if not file_path.exists():
            return
        
        try:
            data = json.loads(file_path.read_text())
            
            self.messages = [
                Message(
                    role=m["role"],
                    content=m["content"],
                    timestamp=datetime.fromisoformat(m["timestamp"]),
                    tool_calls=m.get("tool_calls"),
                    tool_results=m.get("tool_results")
                )
                for m in data.get("messages", [])
            ]
            
            for path, wf_data in data.get("working_files", {}).items():
                self.working_files[path] = WorkingFile(
                    path=wf_data["path"],
                    content=wf_data["content"],
                    original_content=wf_data["original_content"],
                    modified=wf_data["modified"]
                )
            
            if data.get("current_plan"):
                p = data["current_plan"]
                self.current_plan = Plan(
                    id=p["id"],
                    description=p["description"],
                    steps=p["steps"],
                    current_step=p["current_step"],
                    completed=p["completed"]
                )
            
            self.metadata = data.get("metadata", {})
            self.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
            self.last_activity = datetime.fromisoformat(data.get("last_activity", datetime.now().isoformat()))
            
        except Exception as e:
            logger.warning(f"Failed to load conversation {self.id}: {e}")


class ConversationManager:
    """
    Manage multiple conversations.
    
    Each chat_id gets its own conversation.
    """
    
    def __init__(self):
        self.conversations: Dict[str, Conversation] = {}
    
    def get_conversation(self, chat_id: int) -> Conversation:
        """Get or create conversation for a chat."""
        conv_id = str(chat_id)
        
        if conv_id not in self.conversations:
            self.conversations[conv_id] = Conversation(conv_id)
        
        return self.conversations[conv_id]
    
    def clear_conversation(self, chat_id: int):
        """Clear a conversation."""
        conv_id = str(chat_id)
        
        if conv_id in self.conversations:
            del self.conversations[conv_id]
        
        # Delete from disk
        file_path = STATE_DIR / f"{conv_id}.json"
        if file_path.exists():
            file_path.unlink()
    
    def list_conversations(self) -> List[Dict]:
        """List all conversations."""
        convos = []
        
        for file in STATE_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                convos.append({
                    "id": data["id"],
                    "messages": len(data.get("messages", [])),
                    "last_activity": data.get("last_activity")
                })
            except:
                pass
        
        return sorted(convos, key=lambda c: c.get("last_activity", ""), reverse=True)


# ============================================================================
# CONVENIENCE
# ============================================================================

_manager: Optional[ConversationManager] = None


def get_manager() -> ConversationManager:
    """Get global conversation manager."""
    global _manager
    if _manager is None:
        _manager = ConversationManager()
    return _manager


def get_conversation(chat_id: int) -> Conversation:
    """Get conversation for a chat."""
    return get_manager().get_conversation(chat_id)

