#!/usr/bin/env python3
"""
Escalation Engine
=================
Decides when to involve James directly.

Escalation triggers:
- Urgent priority
- Complex decisions
- Inner circle contacts
- AI uncertainty
- Explicit request for James
"""
import logging
from typing import Optional, Dict
from datetime import datetime

from .handler import PublicRequest, RequestType, RequestPriority, get_handler

logger = logging.getLogger("public.escalation")


class EscalationReason:
    URGENT = "urgent"
    DECISION_NEEDED = "decision_needed"
    INNER_CIRCLE = "inner_circle"
    AI_UNCERTAIN = "ai_uncertain"
    EXPLICIT_REQUEST = "explicit_request"
    MULTIPLE_ATTEMPTS = "multiple_attempts"


class EscalationEngine:
    """
    Determines when to escalate to James.
    """
    
    def __init__(self):
        self.handler = get_handler()
        
        # Escalation thresholds
        self.urgent_keywords = ["urgent", "emergency", "asap", "critical", "important"]
        self.james_keywords = ["talk to james", "speak with james", "reach james", "contact james"]
    
    def should_escalate(self, request: PublicRequest, ai_confidence: float = 0.8) -> tuple:
        """
        Determine if this request should be escalated.
        
        Returns: (should_escalate, reason)
        """
        message_lower = request.message.lower()
        
        # Priority-based escalation
        if request.priority == RequestPriority.URGENT:
            return True, EscalationReason.URGENT
        
        # Explicit request for James
        if any(kw in message_lower for kw in self.james_keywords):
            return True, EscalationReason.EXPLICIT_REQUEST
        
        # Inner circle contacts
        contact = self.handler.get_known_contact(request.sender_email) if request.sender_email else None
        if contact and contact.get("relationship") == "inner_circle":
            return True, EscalationReason.INNER_CIRCLE
        
        # Decision-heavy requests
        decision_keywords = ["approve", "decide", "choice", "permission", "authorize"]
        if any(kw in message_lower for kw in decision_keywords):
            return True, EscalationReason.DECISION_NEEDED
        
        # AI uncertainty (low confidence)
        if ai_confidence < 0.5:
            return True, EscalationReason.AI_UNCERTAIN
        
        # Multiple back-and-forth (more than 3 exchanges)
        conversation = self.handler.get_conversation(request.id)
        if len(conversation) > 6:  # 3 exchanges = 6 messages
            return True, EscalationReason.MULTIPLE_ATTEMPTS
        
        return False, None
    
    async def escalate(self, request: PublicRequest, reason: str) -> bool:
        """
        Escalate a request to James.
        
        This sends a notification to James with context.
        """
        try:
            # Build escalation message
            escalation_msg = self._format_escalation(request, reason)
            
            # Send via Telegram
            from reports import deliver_report
            success = await deliver_report(escalation_msg, "decision", priority=1)
            
            if success:
                # Update request status
                self.handler.update_request(request.id, status="escalated", escalated=True)
                
                # Log activity
                try:
                    from presence import log_activity
                    log_activity("escalation", f"Escalated request from {request.sender_name}", "escalated")
                except:
                    pass
                
                logger.info(f"Escalated request {request.id} to James: {reason}")
            
            return success
            
        except Exception as e:
            logger.error(f"Escalation error: {e}")
            return False
    
    def _format_escalation(self, request: PublicRequest, reason: str) -> str:
        """Format escalation message for James."""
        reason_labels = {
            EscalationReason.URGENT: "⚠️ Urgent",
            EscalationReason.DECISION_NEEDED: "❓ Decision needed",
            EscalationReason.INNER_CIRCLE: "👋 Inner circle",
            EscalationReason.AI_UNCERTAIN: "🤔 AI uncertain",
            EscalationReason.EXPLICIT_REQUEST: "📢 Requested you",
            EscalationReason.MULTIPLE_ATTEMPTS: "🔄 Ongoing thread"
        }
        
        reason_label = reason_labels.get(reason, reason)
        
        lines = [
            f"📬 {reason_label}",
            "───────────────────────",
            f"From: {request.sender_name}",
        ]
        
        if request.sender_email:
            lines.append(f"Email: {request.sender_email}")
        
        lines.append("")
        lines.append(f'"{request.message}"')
        lines.append("")
        lines.append("[Reply] [Ignore] [I'll handle]")
        
        return "\n".join(lines)
    
    def get_pending_escalations(self) -> list:
        """Get requests that need escalation review."""
        pending = self.handler.get_pending_requests()
        
        to_review = []
        for req in pending:
            should, reason = self.should_escalate(req)
            if should:
                to_review.append({
                    "request": req,
                    "reason": reason
                })
        
        return to_review


# Singleton
_engine: Optional[EscalationEngine] = None

def get_escalation_engine() -> EscalationEngine:
    global _engine
    if _engine is None:
        _engine = EscalationEngine()
    return _engine








