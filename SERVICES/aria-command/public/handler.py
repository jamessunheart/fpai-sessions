#!/usr/bin/env python3
"""
Public Request Handler
======================
Processes incoming requests from the public interface.

Request Types:
- Scheduling: Meeting requests
- Question: Information inquiries
- Request: Asks for something
- Feedback: Responses to previous outreach
"""
import uuid
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("public.handler")


class RequestType(Enum):
    SCHEDULING = "scheduling"
    QUESTION = "question"
    REQUEST = "request"
    FEEDBACK = "feedback"
    UNKNOWN = "unknown"


class RequestPriority(Enum):
    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class PublicRequest:
    """A request from the public interface."""
    id: str
    sender_name: str
    sender_email: Optional[str]
    message: str
    request_type: RequestType
    priority: RequestPriority
    created_at: str
    status: str = "pending"  # pending, handled, escalated
    ai_response: Optional[str] = None
    escalated: bool = False


class PublicHandler:
    """
    Handles incoming public requests.
    """
    
    def __init__(self, db_path: str = "/opt/fpai/aria/public.db"):
        self.db_path = db_path
        self._ensure_tables()
    
    def _ensure_tables(self):
        """Create public interface tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Requests
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_requests (
                id TEXT PRIMARY KEY,
                sender_name TEXT,
                sender_email TEXT,
                message TEXT,
                request_type TEXT,
                priority INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                status TEXT DEFAULT 'pending',
                ai_response TEXT,
                escalated INTEGER DEFAULT 0
            )
        """)
        
        # Conversations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_conversations (
                id TEXT PRIMARY KEY,
                request_id TEXT,
                role TEXT,
                content TEXT,
                timestamp TEXT DEFAULT (datetime('now'))
            )
        """)
        
        # Known contacts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS known_contacts (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                relationship TEXT,
                priority_level INTEGER DEFAULT 2,
                notes TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def classify_request(self, message: str) -> tuple:
        """
        Classify the request type and priority.
        
        Returns: (RequestType, RequestPriority)
        """
        msg_lower = message.lower()
        
        # Scheduling keywords
        scheduling_keywords = ["meet", "meeting", "schedule", "call", "chat", "available", "time", "calendar"]
        if any(kw in msg_lower for kw in scheduling_keywords):
            return RequestType.SCHEDULING, RequestPriority.NORMAL
        
        # Question keywords
        question_keywords = ["what", "who", "how", "where", "when", "why", "?", "wondering", "curious"]
        if any(kw in msg_lower for kw in question_keywords):
            return RequestType.QUESTION, RequestPriority.NORMAL
        
        # Urgent keywords
        urgent_keywords = ["urgent", "emergency", "asap", "immediately", "critical"]
        if any(kw in msg_lower for kw in urgent_keywords):
            return RequestType.REQUEST, RequestPriority.URGENT
        
        # Request keywords
        request_keywords = ["could you", "would you", "can you", "please", "help", "need", "want"]
        if any(kw in msg_lower for kw in request_keywords):
            return RequestType.REQUEST, RequestPriority.NORMAL
        
        return RequestType.UNKNOWN, RequestPriority.LOW
    
    def get_known_contact(self, email: str) -> Optional[Dict]:
        """Check if this is a known contact."""
        if not email:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, relationship, priority_level, notes
            FROM known_contacts WHERE email = ?
        """, (email,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "relationship": row[2],
                "priority": row[3],
                "notes": row[4]
            }
        return None
    
    def create_request(self, sender_name: str, message: str, sender_email: str = None) -> PublicRequest:
        """Create a new public request."""
        request_type, priority = self.classify_request(message)
        
        # Adjust priority for known contacts
        contact = self.get_known_contact(sender_email)
        if contact:
            priority = RequestPriority(min(contact["priority"], priority.value))
        
        request = PublicRequest(
            id=str(uuid.uuid4()),
            sender_name=sender_name,
            sender_email=sender_email,
            message=message,
            request_type=request_type,
            priority=priority,
            created_at=datetime.now().isoformat()
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO public_requests (id, sender_name, sender_email, message, request_type, priority)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (request.id, request.sender_name, request.sender_email, request.message, 
              request.request_type.value, request.priority.value))
        
        # Add to conversation
        cursor.execute("""
            INSERT INTO public_conversations (id, request_id, role, content)
            VALUES (?, ?, 'user', ?)
        """, (str(uuid.uuid4()), request.id, message))
        
        conn.commit()
        conn.close()
        
        logger.info(f"New request: {request.request_type.value} from {sender_name}")
        return request
    
    def update_request(self, request_id: str, status: str = None, ai_response: str = None, escalated: bool = None):
        """Update a request."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if status:
            updates.append("status = ?")
            values.append(status)
        if ai_response:
            updates.append("ai_response = ?")
            values.append(ai_response)
        if escalated is not None:
            updates.append("escalated = ?")
            values.append(1 if escalated else 0)
        
        if updates:
            values.append(request_id)
            cursor.execute(f"""
                UPDATE public_requests SET {', '.join(updates)} WHERE id = ?
            """, values)
            conn.commit()
        
        conn.close()
    
    def get_pending_requests(self) -> List[PublicRequest]:
        """Get all pending requests."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, sender_name, sender_email, message, request_type, priority, created_at, status, ai_response, escalated
            FROM public_requests WHERE status = 'pending'
            ORDER BY priority ASC, created_at ASC
        """)
        
        requests = []
        for row in cursor.fetchall():
            requests.append(PublicRequest(
                id=row[0],
                sender_name=row[1],
                sender_email=row[2],
                message=row[3],
                request_type=RequestType(row[4]),
                priority=RequestPriority(row[5]),
                created_at=row[6],
                status=row[7],
                ai_response=row[8],
                escalated=bool(row[9])
            ))
        
        conn.close()
        return requests
    
    def add_to_conversation(self, request_id: str, role: str, content: str):
        """Add a message to the conversation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO public_conversations (id, request_id, role, content)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), request_id, role, content))
        
        conn.commit()
        conn.close()
    
    def get_conversation(self, request_id: str) -> List[Dict]:
        """Get conversation history for a request."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT role, content, timestamp
            FROM public_conversations WHERE request_id = ?
            ORDER BY timestamp ASC
        """, (request_id,))
        
        messages = [
            {"role": row[0], "content": row[1], "timestamp": row[2]}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return messages


# Singleton
_handler: Optional[PublicHandler] = None

def get_handler() -> PublicHandler:
    global _handler
    if _handler is None:
        _handler = PublicHandler()
    return _handler








