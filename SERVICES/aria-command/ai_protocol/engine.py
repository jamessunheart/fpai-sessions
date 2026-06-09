#!/usr/bin/env python3
"""
AI-to-AI Protocol Engine
========================
Core engine for AI-to-AI communication.

Protocol Flow:
1. Receive message from external AI
2. Validate AI identity
3. Process request
4. Respond or negotiate
5. Escalate if needed

Capabilities:
- Scheduling negotiation
- Information exchange
- Status updates
- Follow-up coordination
"""
import uuid
import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("ai_protocol.engine")


class ConversationStatus(Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class MessageType(Enum):
    SCHEDULE_REQUEST = "schedule_request"
    SCHEDULE_PROPOSE = "schedule_propose"
    SCHEDULE_CONFIRM = "schedule_confirm"
    INFO_REQUEST = "info_request"
    INFO_RESPONSE = "info_response"
    STATUS_UPDATE = "status_update"
    ESCALATE = "escalate"
    ACK = "ack"


@dataclass
class AIMessage:
    """A message between AIs."""
    id: str
    conversation_id: str
    sender_ai: str
    message_type: MessageType
    content: Dict
    timestamp: str


@dataclass
class AIConversation:
    """An AI-to-AI conversation."""
    id: str
    external_ai_id: str
    external_user_name: str
    purpose: str
    status: ConversationStatus
    messages: List[AIMessage]
    outcome: Optional[str]
    started_at: str
    resolved_at: Optional[str]


class AIProtocolEngine:
    """
    Handles AI-to-AI communication protocol.
    """
    
    def __init__(self, db_path: str = "/opt/fpai/aria/ai_protocol.db"):
        self.db_path = db_path
        self.my_ai_id = "jai-fullpotential"
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create protocol tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_conversations (
                id TEXT PRIMARY KEY,
                external_ai_id TEXT,
                external_user_name TEXT,
                purpose TEXT,
                status TEXT DEFAULT 'active',
                outcome TEXT,
                started_at TEXT DEFAULT (datetime('now')),
                resolved_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                sender_ai TEXT,
                message_type TEXT,
                content TEXT,
                timestamp TEXT DEFAULT (datetime('now'))
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS known_ais (
                id TEXT PRIMARY KEY,
                name TEXT,
                owner TEXT,
                endpoint TEXT,
                capabilities TEXT,
                trust_level INTEGER DEFAULT 1,
                last_interaction TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    # === Conversation Management ===
    
    def start_conversation(
        self,
        external_ai_id: str,
        external_user_name: str,
        purpose: str
    ) -> AIConversation:
        """Start a new AI-to-AI conversation."""
        conv_id = str(uuid.uuid4())
        
        conversation = AIConversation(
            id=conv_id,
            external_ai_id=external_ai_id,
            external_user_name=external_user_name,
            purpose=purpose,
            status=ConversationStatus.ACTIVE,
            messages=[],
            outcome=None,
            started_at=datetime.now().isoformat(),
            resolved_at=None
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ai_conversations (id, external_ai_id, external_user_name, purpose)
            VALUES (?, ?, ?, ?)
        """, (conv_id, external_ai_id, external_user_name, purpose))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Started AI conversation with {external_ai_id}: {purpose}")
        return conversation
    
    def get_conversation(self, conv_id: str) -> Optional[AIConversation]:
        """Get a conversation by ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, external_ai_id, external_user_name, purpose, status, outcome, started_at, resolved_at
            FROM ai_conversations WHERE id = ?
        """, (conv_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        # Get messages
        cursor.execute("""
            SELECT id, conversation_id, sender_ai, message_type, content, timestamp
            FROM ai_messages WHERE conversation_id = ?
            ORDER BY timestamp ASC
        """, (conv_id,))
        
        messages = [
            AIMessage(
                id=r[0], conversation_id=r[1], sender_ai=r[2],
                message_type=MessageType(r[3]), content=json.loads(r[4]), timestamp=r[5]
            )
            for r in cursor.fetchall()
        ]
        
        conn.close()
        
        return AIConversation(
            id=row[0], external_ai_id=row[1], external_user_name=row[2],
            purpose=row[3], status=ConversationStatus(row[4]), outcome=row[5],
            started_at=row[6], resolved_at=row[7], messages=messages
        )
    
    def resolve_conversation(self, conv_id: str, outcome: str):
        """Resolve a conversation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE ai_conversations 
            SET status = 'resolved', outcome = ?, resolved_at = datetime('now')
            WHERE id = ?
        """, (outcome, conv_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Resolved conversation {conv_id}: {outcome}")
    
    # === Message Handling ===
    
    def send_message(
        self,
        conversation_id: str,
        message_type: MessageType,
        content: Dict
    ) -> AIMessage:
        """Send a message in a conversation."""
        msg = AIMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            sender_ai=self.my_ai_id,
            message_type=message_type,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ai_messages (id, conversation_id, sender_ai, message_type, content)
            VALUES (?, ?, ?, ?, ?)
        """, (msg.id, msg.conversation_id, msg.sender_ai, msg.message_type.value, json.dumps(msg.content)))
        
        conn.commit()
        conn.close()
        
        return msg
    
    def receive_message(
        self,
        conversation_id: str,
        sender_ai: str,
        message_type: MessageType,
        content: Dict
    ) -> AIMessage:
        """Receive a message from external AI."""
        msg = AIMessage(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            sender_ai=sender_ai,
            message_type=message_type,
            content=content,
            timestamp=datetime.now().isoformat()
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ai_messages (id, conversation_id, sender_ai, message_type, content)
            VALUES (?, ?, ?, ?, ?)
        """, (msg.id, msg.conversation_id, msg.sender_ai, msg.message_type.value, json.dumps(msg.content)))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Received {message_type.value} from {sender_ai}")
        return msg
    
    # === Protocol API ===
    
    def handle_incoming(self, request: Dict) -> Dict:
        """
        Handle incoming AI-to-AI request.
        
        Expected request format:
        {
            "ai_id": "their-ai-id",
            "user_name": "Their User",
            "message_type": "schedule_request",
            "content": {...},
            "conversation_id": "optional-existing-id"
        }
        """
        ai_id = request.get("ai_id", "unknown")
        user_name = request.get("user_name", "Unknown")
        msg_type = request.get("message_type", "info_request")
        content = request.get("content", {})
        conv_id = request.get("conversation_id")
        
        # Get or create conversation
        if conv_id:
            conversation = self.get_conversation(conv_id)
        else:
            conversation = self.start_conversation(ai_id, user_name, msg_type)
            conv_id = conversation.id
        
        # Record incoming message
        self.receive_message(conv_id, ai_id, MessageType(msg_type), content)
        
        # Process based on message type
        response = self._process_message(MessageType(msg_type), content, conversation)
        
        # Send response
        self.send_message(conv_id, response["message_type"], response["content"])
        
        return {
            "ai_id": self.my_ai_id,
            "conversation_id": conv_id,
            "message_type": response["message_type"].value,
            "content": response["content"]
        }
    
    def _process_message(self, msg_type: MessageType, content: Dict, conversation: AIConversation) -> Dict:
        """Process message and generate response."""
        if msg_type == MessageType.SCHEDULE_REQUEST:
            return self._handle_schedule_request(content, conversation)
        
        elif msg_type == MessageType.SCHEDULE_PROPOSE:
            return self._handle_schedule_propose(content, conversation)
        
        elif msg_type == MessageType.SCHEDULE_CONFIRM:
            return self._handle_schedule_confirm(content, conversation)
        
        elif msg_type == MessageType.INFO_REQUEST:
            return self._handle_info_request(content, conversation)
        
        elif msg_type == MessageType.STATUS_UPDATE:
            return self._handle_status_update(content, conversation)
        
        else:
            return {
                "message_type": MessageType.ACK,
                "content": {"status": "received"}
            }
    
    def _handle_schedule_request(self, content: Dict, conv: AIConversation) -> Dict:
        """Handle scheduling request."""
        from .negotiation import get_negotiator
        negotiator = get_negotiator()
        
        # Get available slots
        slots = negotiator.get_available_slots(
            duration=content.get("duration_hours", 1),
            preferred_days=content.get("preferred_days", [])
        )
        
        if slots:
            return {
                "message_type": MessageType.SCHEDULE_PROPOSE,
                "content": {
                    "available_slots": slots,
                    "message": f"Here are {len(slots)} available times for {conv.external_user_name}."
                }
            }
        else:
            return {
                "message_type": MessageType.ESCALATE,
                "content": {
                    "reason": "No available slots",
                    "message": "I need to check with James for availability."
                }
            }
    
    def _handle_schedule_propose(self, content: Dict, conv: AIConversation) -> Dict:
        """Handle proposed schedule."""
        slots = content.get("available_slots", [])
        
        if slots:
            # Auto-confirm first available slot
            selected = slots[0]
            
            return {
                "message_type": MessageType.SCHEDULE_CONFIRM,
                "content": {
                    "confirmed_slot": selected,
                    "message": f"Confirmed: {selected.get('start')} on {selected.get('date')}"
                }
            }
        else:
            return {
                "message_type": MessageType.ESCALATE,
                "content": {"reason": "No slots provided"}
            }
    
    def _handle_schedule_confirm(self, content: Dict, conv: AIConversation) -> Dict:
        """Handle schedule confirmation."""
        slot = content.get("confirmed_slot", {})
        
        # Mark conversation as resolved
        self.resolve_conversation(conv.id, f"Meeting scheduled: {slot}")
        
        # Notify James
        try:
            from reports import send_quick
            import asyncio
            loop = asyncio.get_event_loop()
            loop.run_until_complete(send_quick(
                f"Meeting with {conv.external_user_name} confirmed for {slot.get('start')}",
                "progress"
            ))
        except:
            pass
        
        return {
            "message_type": MessageType.ACK,
            "content": {
                "status": "confirmed",
                "message": "Meeting confirmed. Calendar updated."
            }
        }
    
    def _handle_info_request(self, content: Dict, conv: AIConversation) -> Dict:
        """Handle information request."""
        from .exchange import get_exchanger
        exchanger = get_exchanger()
        
        query = content.get("query", "")
        response = exchanger.answer_query(query)
        
        return {
            "message_type": MessageType.INFO_RESPONSE,
            "content": response
        }
    
    def _handle_status_update(self, content: Dict, conv: AIConversation) -> Dict:
        """Handle status update."""
        # Just acknowledge
        return {
            "message_type": MessageType.ACK,
            "content": {"status": "received", "message": "Status noted."}
        }


# Singleton
_engine: Optional[AIProtocolEngine] = None

def get_protocol_engine() -> AIProtocolEngine:
    global _engine
    if _engine is None:
        _engine = AIProtocolEngine()
    return _engine








