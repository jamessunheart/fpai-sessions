#!/usr/bin/env python3
"""
Information Exchange
====================
Handles information exchange between AIs.

Shareable Information:
- Availability status
- Response expectations
- Project status (public)
- Contact preferences

Protected Information (requires escalation):
- Private data
- Financial details
- Personal information
"""
import logging
from datetime import datetime
from typing import Optional, Dict

logger = logging.getLogger("ai_protocol.exchange")


class InfoExchanger:
    """
    Manages information exchange with external AIs.
    """
    
    def __init__(self):
        # Information that can be shared freely
        self.public_info = {
            "name": "James Sunheart",
            "ai_name": "JAI",
            "organization": "Full Potential",
            "role": "Founder",
            "timezone": "PST",
            "response_time": "24-48 hours for non-urgent",
            "preferred_contact": "Through JAI"
        }
        
        # Topics we can discuss
        self.allowed_topics = [
            "availability", "scheduling", "projects", 
            "collaboration", "status", "contact"
        ]
        
        # Topics that need escalation
        self.protected_topics = [
            "financial", "personal", "private", "confidential",
            "password", "credentials", "internal"
        ]
    
    def can_answer(self, query: str) -> bool:
        """Check if we can answer this query without escalation."""
        query_lower = query.lower()
        
        # Check for protected topics
        for topic in self.protected_topics:
            if topic in query_lower:
                return False
        
        return True
    
    def answer_query(self, query: str) -> Dict:
        """
        Answer an information query.
        
        Returns response with either answer or escalation notice.
        """
        if not self.can_answer(query):
            return {
                "status": "escalated",
                "message": "This query requires James's direct attention. I'll flag it for him.",
                "estimated_response": "24-48 hours"
            }
        
        query_lower = query.lower()
        
        # Availability queries
        if any(w in query_lower for w in ["available", "busy", "free", "schedule"]):
            return self._get_availability_response()
        
        # Contact queries
        if any(w in query_lower for w in ["contact", "reach", "email", "message"]):
            return self._get_contact_response()
        
        # Status queries
        if any(w in query_lower for w in ["status", "working", "project", "doing"]):
            return self._get_status_response()
        
        # Response time queries
        if any(w in query_lower for w in ["response", "reply", "how long", "when"]):
            return self._get_response_time_info()
        
        # General info
        return {
            "status": "ok",
            "info": self.public_info,
            "message": "Here's what I can share about James."
        }
    
    def _get_availability_response(self) -> Dict:
        """Get availability status."""
        try:
            from presence import get_presence_status, get_state_label
            status = get_presence_status()
            state = get_state_label(status.state)
        except:
            state = "Online"
        
        return {
            "status": "ok",
            "availability": state,
            "message": f"James is currently {state.lower()}. You can schedule through me.",
            "scheduling_available": True
        }
    
    def _get_contact_response(self) -> Dict:
        """Get contact information."""
        return {
            "status": "ok",
            "preferred_method": "Through JAI",
            "message": "The best way to reach James is through me (JAI). I can coordinate scheduling, answer questions, or flag urgent matters.",
            "public_url": "https://fullpotential.ai/talk-to-jai"
        }
    
    def _get_status_response(self) -> Dict:
        """Get current status/project info."""
        return {
            "status": "ok",
            "current_focus": "Building Full Potential v2.0",
            "organization": "Full Potential",
            "message": "James is currently focused on building Full Potential, an AI consciousness system."
        }
    
    def _get_response_time_info(self) -> Dict:
        """Get response time expectations."""
        return {
            "status": "ok",
            "response_times": {
                "urgent": "< 4 hours",
                "important": "Same day",
                "normal": "24-48 hours",
                "low_priority": "When available"
            },
            "message": "Response time depends on priority. Urgent matters are addressed within hours."
        }
    
    def format_for_sharing(self, data: Dict, recipient_ai: str) -> Dict:
        """Format data for sharing with another AI."""
        return {
            "from_ai": "jai-fullpotential",
            "to_ai": recipient_ai,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }


# Singleton
_exchanger: Optional[InfoExchanger] = None

def get_exchanger() -> InfoExchanger:
    global _exchanger
    if _exchanger is None:
        _exchanger = InfoExchanger()
    return _exchanger








