#!/usr/bin/env python3
"""
Public Interface
================
FastAPI routes for the "Talk to my AI" public interface.

Endpoints:
- GET /talk - Chat interface
- POST /talk/message - Send a message
- GET /talk/status - Get JAI status
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import logging

from .handler import get_handler
from .responder import get_responder
from .escalation import get_escalation_engine

logger = logging.getLogger("public.interface")

router = APIRouter(tags=["public"])


class MessageRequest(BaseModel):
    name: str
    message: str
    email: Optional[str] = None
    request_id: Optional[str] = None  # For continuing conversations


class MessageResponse(BaseModel):
    request_id: str
    response: str
    escalated: bool = False


# Chat interface HTML
CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Talk to JAI</title>
    <style>
        :root {
            --bg: #0a0a0f;
            --card: #12121a;
            --border: #2a2a3a;
            --text: #e8e8f0;
            --text-dim: #8888aa;
            --accent: #4ade80;
            --accent-dim: #22c55e20;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            width: 100%;
            max-width: 480px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 32px;
        }
        
        .status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: var(--accent-dim);
            border-radius: 20px;
            margin-bottom: 16px;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            background: var(--accent);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .status-text {
            font-size: 14px;
            color: var(--accent);
        }
        
        h1 {
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .subtitle {
            color: var(--text-dim);
            font-size: 15px;
        }
        
        .chat-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
        }
        
        .messages {
            padding: 24px;
            min-height: 200px;
            max-height: 400px;
            overflow-y: auto;
        }
        
        .message {
            margin-bottom: 16px;
            padding: 12px 16px;
            border-radius: 12px;
            max-width: 85%;
        }
        
        .message.assistant {
            background: var(--accent-dim);
            border: 1px solid var(--accent);
            color: var(--text);
        }
        
        .message.user {
            background: var(--border);
            margin-left: auto;
        }
        
        .welcome {
            color: var(--text-dim);
            text-align: center;
            padding: 40px 20px;
        }
        
        .input-area {
            border-top: 1px solid var(--border);
            padding: 16px;
        }
        
        .name-row {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }
        
        .name-row input {
            flex: 1;
            padding: 12px 16px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 14px;
        }
        
        .message-row {
            display: flex;
            gap: 8px;
        }
        
        .message-row textarea {
            flex: 1;
            padding: 12px 16px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text);
            font-size: 14px;
            resize: none;
            min-height: 48px;
        }
        
        .message-row textarea:focus,
        .name-row input:focus {
            outline: none;
            border-color: var(--accent);
        }
        
        button {
            padding: 12px 24px;
            background: var(--accent);
            color: var(--bg);
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        
        button:hover {
            opacity: 0.9;
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .footer {
            text-align: center;
            margin-top: 24px;
            color: var(--text-dim);
            font-size: 13px;
        }
        
        .typing {
            display: none;
            align-items: center;
            gap: 6px;
            padding: 12px 16px;
            background: var(--accent-dim);
            border-radius: 12px;
            max-width: 100px;
        }
        
        .typing.active {
            display: flex;
        }
        
        .typing span {
            width: 6px;
            height: 6px;
            background: var(--accent);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
        }
        
        .typing span:nth-child(1) { animation-delay: -0.32s; }
        .typing span:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="status">
                <div class="status-dot"></div>
                <span class="status-text">JAI is online</span>
            </div>
            <h1>Talk to JAI</h1>
            <p class="subtitle">James's AI assistant</p>
        </div>
        
        <div class="chat-card">
            <div class="messages" id="messages">
                <div class="welcome">
                    Hi, I help coordinate for James.<br>
                    What can I help you with?
                </div>
            </div>
            
            <div class="input-area">
                <div class="name-row">
                    <input type="text" id="name" placeholder="Your name" required>
                    <input type="email" id="email" placeholder="Email (optional)">
                </div>
                <div class="message-row">
                    <textarea id="message" placeholder="Your message..." rows="1"></textarea>
                    <button id="send" onclick="sendMessage()">Send</button>
                </div>
            </div>
        </div>
        
        <div class="footer">
            James typically responds to important matters within 24 hours.
        </div>
    </div>
    
    <script>
        let requestId = null;
        
        async function sendMessage() {
            const name = document.getElementById('name').value.trim();
            const email = document.getElementById('email').value.trim();
            const message = document.getElementById('message').value.trim();
            
            if (!name || !message) {
                alert('Please enter your name and message');
                return;
            }
            
            const btn = document.getElementById('send');
            btn.disabled = true;
            
            // Add user message to chat
            addMessage(message, 'user');
            document.getElementById('message').value = '';
            
            // Remove welcome message
            const welcome = document.querySelector('.welcome');
            if (welcome) welcome.remove();
            
            // Show typing indicator
            const typing = document.createElement('div');
            typing.className = 'typing active';
            typing.innerHTML = '<span></span><span></span><span></span>';
            document.getElementById('messages').appendChild(typing);
            
            try {
                const response = await fetch('/talk/message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name,
                        email: email || null,
                        message: message,
                        request_id: requestId
                    })
                });
                
                const data = await response.json();
                requestId = data.request_id;
                
                // Remove typing indicator
                typing.remove();
                
                // Add AI response
                addMessage(data.response, 'assistant');
                
            } catch (error) {
                typing.remove();
                addMessage('Sorry, there was an error. Please try again.', 'assistant');
            }
            
            btn.disabled = false;
        }
        
        function addMessage(text, role) {
            const messages = document.getElementById('messages');
            const msg = document.createElement('div');
            msg.className = 'message ' + role;
            msg.textContent = text;
            messages.appendChild(msg);
            messages.scrollTop = messages.scrollHeight;
        }
        
        // Send on Enter
        document.getElementById('message').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>
"""


@router.get("/talk", response_class=HTMLResponse)
async def talk_page():
    """Serve the public chat interface."""
    return CHAT_HTML


@router.get("/talk-to-jai", response_class=HTMLResponse)
async def talk_to_jai():
    """Alternative URL for the chat interface."""
    return CHAT_HTML


@router.post("/talk/message", response_model=MessageResponse)
async def send_message(request: MessageRequest):
    """Handle an incoming message."""
    responder = get_responder()
    escalation = get_escalation_engine()
    
    try:
        if request.request_id:
            # Continue existing conversation
            response = await responder.continue_conversation(request.request_id, request.message)
            return MessageResponse(
                request_id=request.request_id,
                response=response,
                escalated=False
            )
        else:
            # New conversation
            req, response = await responder.handle_new_message(
                request.name, 
                request.message, 
                request.email
            )
            
            # Check for escalation
            should_escalate, reason = escalation.should_escalate(req)
            if should_escalate:
                await escalation.escalate(req, reason)
            
            return MessageResponse(
                request_id=req.id,
                response=response,
                escalated=should_escalate
            )
            
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/talk/status")
async def get_jai_status():
    """Get JAI's current status."""
    try:
        from presence import get_presence_status
        status = get_presence_status()
        
        return {
            "online": status.state.value == "online",
            "state": status.state.value,
            "activities_today": status.activities_today,
            "message": "JAI is online and ready to help"
        }
    except:
        return {
            "online": True,
            "state": "online",
            "activities_today": 0,
            "message": "JAI is online and ready to help"
        }


@router.get("/talk/pending")
async def get_pending():
    """Get pending requests (for admin view)."""
    handler = get_handler()
    pending = handler.get_pending_requests()
    
    return {
        "count": len(pending),
        "requests": [
            {
                "id": r.id,
                "sender": r.sender_name,
                "message": r.message[:100],
                "type": r.request_type.value,
                "priority": r.priority.value,
                "created_at": r.created_at
            }
            for r in pending
        ]
    }








