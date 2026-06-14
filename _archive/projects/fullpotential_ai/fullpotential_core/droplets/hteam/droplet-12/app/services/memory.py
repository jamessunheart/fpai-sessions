"""
Conversation Memory Management
Per Spec requirements - maintain conversation context
Located in services/ per CODE_STANDARDS.md
"""

from typing import Dict, Optional, List, Any
from datetime import datetime
from enum import Enum
from app.utils.logging import get_logger

log = get_logger(__name__)


class MessageSource(Enum):
    """Message source tracking"""
    CHAT = "chat"
    VOICE = "voice"


class ConversationMemory:
    """
    Maintains conversation context for better AI reasoning.
    Per Spec - conversation memory requirement.
    """
    
    def __init__(self, max_history: int = 10):
        """
        Initialize conversation memory.
        
        Args:
            max_history: Maximum number of messages to keep in history
        """
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history
        self.pending_action: Optional[Dict[str, Any]] = None
        self.source: Optional[MessageSource] = None
        self.source_metadata: Dict[str, Any] = {}
        
        log.debug("conversation_memory_initialized", max_history=max_history)
    
    def set_source(self, source: MessageSource, metadata: Dict[str, Any] = None):
        """
        Set the source of messages in this conversation.
        
        Args:
            source: MessageSource enum (CHAT or VOICE)
            metadata: Additional metadata about the source
        """
        self.source = source
        self.source_metadata = metadata or {}
        
        log.debug(
            "conversation_source_set",
            source=source.value,
            metadata_keys=list(self.source_metadata.keys())
        )
    
    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Add a message to conversation history.
        
        Args:
            role: Message role ("user" or "assistant")
            content: Message content
            metadata: Optional metadata
        """
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": self.source.value if self.source else "unknown"
        }
        
        if metadata:
            msg["metadata"] = metadata
        
        self.history.append(msg)
        
        # Keep only recent messages
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        log.debug(
            "message_added",
            role=role,
            content_length=len(content),
            history_size=len(self.history)
        )
    
    def get_context(self) -> str:
        """
        Get formatted conversation history for AI reasoning.
        
        Returns:
            Formatted conversation context string
        """
        if not self.history:
            return "No previous conversation."
        
        context = "## Recent Conversation:\n"
        
        # Include last 5 messages
        for msg in self.history[-5:]:
            role = msg['role'].upper()
            content = msg['content'][:200]  # Truncate long messages
            context += f"{role}: {content}\n"
        
        if self.pending_action:
            context += f"\n## Pending Action:\n"
            context += f"Droplet: {self.pending_action.get('droplet', 'unknown')}\n"
            context += f"Endpoint: {self.pending_action.get('endpoint', 'unknown')}\n"
            context += f"Method: {self.pending_action.get('method', 'unknown')}\n"
        
        return context
    
    def set_pending_action(self, action: Dict[str, Any]):
        """
        Set a pending action that needs more information.
        
        Args:
            action: Action details (droplet, endpoint, method)
        """
        self.pending_action = action
        
        log.info(
            "pending_action_set",
            droplet=action.get('droplet'),
            endpoint=action.get('endpoint'),
            method=action.get('method')
        )
    
    def get_pending_action(self) -> Optional[Dict[str, Any]]:
        """
        Get and clear pending action.
        
        Returns:
            Pending action dict or None
        """
        action = self.pending_action
        self.pending_action = None
        
        if action:
            log.info("pending_action_retrieved", action=action)
        
        return action
    
    def clear_pending(self):
        """Clear pending action."""
        self.pending_action = None
        log.debug("pending_action_cleared")
    
    def reset(self):
        """Reset conversation memory."""
        self.history = []
        self.pending_action = None
        log.info("conversation_memory_reset")
    
    def get_message_count(self) -> int:
        """Get total message count."""
        return len(self.history)


class SessionManager:
    """
    Manages conversation sessions per source.
    Per Spec - session management requirement.
    """
    
    def __init__(self):
        """Initialize session manager."""
        self.sessions: Dict[str, ConversationMemory] = {}
        log.info("session_manager_initialized")
    
    def get_session(self, session_id: str) -> ConversationMemory:
        """
        Get or create a session for a given ID.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            ConversationMemory instance for this session
        """
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationMemory()
            log.info("session_created", session_id=session_id)
        
        return self.sessions[session_id]
    
    def list_sessions(self) -> List[str]:
        """
        List all active session IDs.
        
        Returns:
            List of session IDs
        """
        return list(self.sessions.keys())
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear a specific session.
        
        Args:
            session_id: Session ID to clear
            
        Returns:
            True if session was cleared, False if not found
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            log.info("session_cleared", session_id=session_id)
            return True
        
        log.warning("session_not_found", session_id=session_id)
        return False
    
    def get_session_count(self) -> int:
        """Get total number of active sessions."""
        return len(self.sessions)
    
    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session info dict or None if not found
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        return {
            "session_id": session_id,
            "source": session.source.value if session.source else "unknown",
            "message_count": session.get_message_count(),
            "has_pending_action": session.pending_action is not None
        }


# Global session manager instance
SESSION_MANAGER = SessionManager()