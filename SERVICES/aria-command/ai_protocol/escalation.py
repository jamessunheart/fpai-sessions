#!/usr/bin/env python3
"""
AI-to-AI Escalation
===================
Determines when to involve humans in AI-to-AI conversations.

Escalation Triggers:
- Conflict that can't be resolved
- Decision outside AI authority
- Relationship-sensitive matters
- Explicit request for human
- Protected information requested
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger("ai_protocol.escalation")


class AIEscalationReason:
    CONFLICT = "conflict"
    AUTHORITY = "authority"
    SENSITIVE = "sensitive"
    EXPLICIT = "explicit_request"
    PROTECTED = "protected_info"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class AIEscalation:
    """
    Handles escalation logic for AI-to-AI conversations.
    """
    
    def __init__(self):
        # Maximum back-and-forth before escalating
        self.max_exchanges = 5
        
        # Keywords that trigger escalation
        self.escalation_keywords = [
            "speak to james", "talk to james", "need james",
            "human decision", "human approval", "urgent"
        ]
        
        # Sensitive topics
        self.sensitive_topics = [
            "legal", "financial", "contract", "personal",
            "medical", "relationship", "family"
        ]
    
    def should_escalate(self, conversation: Dict, latest_message: str = "") -> tuple:
        """
        Determine if conversation should escalate to human.
        
        Returns: (should_escalate, reason)
        """
        message_lower = latest_message.lower()
        
        # Explicit request for human
        if any(kw in message_lower for kw in self.escalation_keywords):
            return True, AIEscalationReason.EXPLICIT
        
        # Sensitive topics
        if any(topic in message_lower for topic in self.sensitive_topics):
            return True, AIEscalationReason.SENSITIVE
        
        # Too many exchanges
        exchange_count = conversation.get("exchange_count", 0)
        if exchange_count > self.max_exchanges:
            return True, AIEscalationReason.TIMEOUT
        
        # Check for conflict patterns
        if self._detect_conflict(conversation):
            return True, AIEscalationReason.CONFLICT
        
        return False, None
    
    def _detect_conflict(self, conversation: Dict) -> bool:
        """Detect if conversation shows conflict patterns."""
        messages = conversation.get("messages", [])
        
        if len(messages) < 4:
            return False
        
        # Look for repeated back-and-forth on same topic
        recent = messages[-4:]
        topics = set()
        
        for msg in recent:
            content = msg.get("content", {})
            msg_type = msg.get("message_type", "")
            
            # Same message type repeated = potential conflict
            topics.add(msg_type)
        
        # If only 1-2 unique types in last 4 messages, likely stuck
        return len(topics) <= 2
    
    async def escalate_to_human(self, conversation: Dict, reason: str) -> bool:
        """
        Escalate conversation to James.
        """
        try:
            external_user = conversation.get("external_user_name", "Unknown")
            external_ai = conversation.get("external_ai_id", "Unknown AI")
            purpose = conversation.get("purpose", "")
            
            # Format escalation message
            reason_labels = {
                AIEscalationReason.CONFLICT: "AI negotiation stuck",
                AIEscalationReason.AUTHORITY: "Needs your decision",
                AIEscalationReason.SENSITIVE: "Sensitive topic",
                AIEscalationReason.EXPLICIT: "Requested human",
                AIEscalationReason.PROTECTED: "Protected info request",
                AIEscalationReason.TIMEOUT: "Taking too long"
            }
            
            reason_label = reason_labels.get(reason, reason)
            
            message = f"""🤖 AI-to-AI Escalation
───────────────────────
From: {external_user}'s AI ({external_ai})
Topic: {purpose}
Reason: {reason_label}

[Review] [Delegate back] [Join conversation]"""
            
            # Send via reports
            from reports import deliver_report
            success = await deliver_report(message, "decision", priority=1)
            
            if success:
                logger.info(f"Escalated AI conversation to James: {reason}")
            
            return success
            
        except Exception as e:
            logger.error(f"Escalation error: {e}")
            return False
    
    def format_escalation_response(self, reason: str) -> Dict:
        """Format response to external AI when escalating."""
        messages = {
            AIEscalationReason.CONFLICT: "We seem to have different requirements. Let me involve our humans to resolve this.",
            AIEscalationReason.AUTHORITY: "This decision requires James's direct input. I'll get back to you.",
            AIEscalationReason.SENSITIVE: "Given the sensitive nature of this topic, I'm involving James directly.",
            AIEscalationReason.EXPLICIT: "Connecting you with James as requested.",
            AIEscalationReason.PROTECTED: "I can't share that information without James's approval.",
            AIEscalationReason.TIMEOUT: "Let me involve James to help move this forward.",
        }
        
        return {
            "status": "escalated",
            "message": messages.get(reason, "I'm escalating this to James."),
            "expected_response": "24-48 hours"
        }


# Singleton
_escalation: Optional[AIEscalation] = None

def get_ai_escalation() -> AIEscalation:
    global _escalation
    if _escalation is None:
        _escalation = AIEscalation()
    return _escalation








