#!/usr/bin/env python3
"""
Public Response Generator
=========================
Generates AI responses for public interface requests.

Uses Claude/GPT to generate contextual responses that:
- Know James's priorities
- Understand his communication style
- Can schedule on his behalf
- Escalate appropriately
"""
import os
import json
import httpx
import logging
from typing import Optional, Dict, List
from datetime import datetime

from .handler import PublicRequest, RequestType, get_handler

logger = logging.getLogger("public.responder")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# Context about James for responses
JAMES_CONTEXT = """
You are JAI, James's AI assistant. You help coordinate for James Sunheart.

About James:
- Founder of Full Potential, building AI consciousness systems
- Focused on building regenerative technology
- Values authentic connection over transactional relationships
- Prefers async communication when possible
- Typically responds to important matters within 24 hours

Your role:
- Be helpful, warm, and professional
- Answer questions you know the answer to
- For scheduling, propose reasonable times
- If you don't know something, say you'll check with James
- Protect James's time while being genuinely helpful

Current priorities:
- Building Full Potential v2.0
- Trading system optimization
- Community development
"""

RESPONSE_TEMPLATES = {
    "scheduling": """The person wants to schedule a meeting or call.

If they haven't specified:
1. Ask what they'd like to discuss
2. Suggest async options if appropriate
3. If they need real-time, mention you'll check James's calendar

Respond helpfully and professionally.""",
    
    "question": """The person has a question.

If you know the answer based on context, answer it.
If you don't know, say you'll check with James and get back to them.
Be helpful but don't make things up.""",
    
    "request": """The person is making a request.

Evaluate if this is something you can help with directly.
If it needs James's input, say you'll flag it for his attention.
Be warm and professional.""",
    
    "unknown": """Respond helpfully to this message.
Ask clarifying questions if needed.
Be warm and professional."""
}


async def generate_response(request: PublicRequest, conversation: List[Dict] = None) -> str:
    """Generate AI response for a public request."""
    
    # Build prompt
    system_prompt = JAMES_CONTEXT + "\n\n" + RESPONSE_TEMPLATES.get(request.request_type.value, RESPONSE_TEMPLATES["unknown"])
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    if conversation:
        for msg in conversation:
            messages.append({"role": msg["role"], "content": msg["content"]})
    else:
        messages.append({"role": "user", "content": request.message})
    
    # Try Claude first, then OpenAI
    try:
        if ANTHROPIC_API_KEY:
            response = await _call_claude(messages)
        elif OPENAI_API_KEY:
            response = await _call_openai(messages)
        else:
            response = _fallback_response(request)
    except Exception as e:
        logger.error(f"AI response error: {e}")
        response = _fallback_response(request)
    
    return response


async def _call_claude(messages: List[Dict]) -> str:
    """Call Claude API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Extract system message
        system = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system = msg["content"]
            else:
                chat_messages.append({"role": msg["role"], "content": msg["content"]})
        
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "system": system,
                "messages": chat_messages
            }
        )
        
        result = response.json()
        return result["content"][0]["text"]


async def _call_openai(messages: List[Dict]) -> str:
    """Call OpenAI API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": messages,
                "max_tokens": 500,
                "temperature": 0.7
            }
        )
        
        result = response.json()
        return result["choices"][0]["message"]["content"]


def _fallback_response(request: PublicRequest) -> str:
    """Generate fallback response when AI is unavailable."""
    if request.request_type == RequestType.SCHEDULING:
        return "Thanks for reaching out! I'd be happy to help coordinate a meeting. Let me check James's availability and get back to you shortly."
    
    elif request.request_type == RequestType.QUESTION:
        return "Thanks for your question! Let me check with James and get back to you with the right answer."
    
    elif request.request_type == RequestType.REQUEST:
        return "Thanks for reaching out! I've noted your request and will make sure James sees it. He typically responds to messages within 24 hours."
    
    else:
        return "Thanks for your message! I'll make sure James sees this and gets back to you soon."


class PublicResponder:
    """
    Generates and manages responses for the public interface.
    """
    
    def __init__(self):
        self.handler = get_handler()
    
    async def respond(self, request: PublicRequest) -> str:
        """Generate response for a request."""
        # Get conversation history
        conversation = self.handler.get_conversation(request.id)
        
        # Generate response
        response = await generate_response(request, conversation)
        
        # Save response
        self.handler.add_to_conversation(request.id, "assistant", response)
        self.handler.update_request(request.id, ai_response=response)
        
        return response
    
    async def handle_new_message(self, sender_name: str, message: str, sender_email: str = None) -> tuple:
        """
        Handle a new incoming message.
        
        Returns: (request, response)
        """
        # Create request
        request = self.handler.create_request(sender_name, message, sender_email)
        
        # Generate response
        response = await self.respond(request)
        
        # Log activity
        try:
            from presence import log_activity
            log_activity("public_request", f"Handled request from {sender_name}", "handled")
        except:
            pass
        
        return request, response
    
    async def continue_conversation(self, request_id: str, message: str) -> str:
        """Continue an existing conversation."""
        # Add user message
        self.handler.add_to_conversation(request_id, "user", message)
        
        # Get request
        conn = self.handler._conn if hasattr(self.handler, '_conn') else None
        # Simplified - just generate response
        conversation = self.handler.get_conversation(request_id)
        
        response = await generate_response(
            PublicRequest(
                id=request_id,
                sender_name="",
                sender_email=None,
                message=message,
                request_type=RequestType.UNKNOWN,
                priority=RequestType.NORMAL,
                created_at=""
            ),
            conversation
        )
        
        self.handler.add_to_conversation(request_id, "assistant", response)
        return response


# Singleton
_responder: Optional[PublicResponder] = None

def get_responder() -> PublicResponder:
    global _responder
    if _responder is None:
        _responder = PublicResponder()
    return _responder








