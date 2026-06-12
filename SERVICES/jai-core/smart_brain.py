#!/usr/bin/env python3
"""
JAI BRAIN - James Automated Intelligence
=========================================
Human Intelligence GPS: State-aware. Action-first. Quiet by default.
Now with persistent memory - JAI remembers.
"""
import os
import json
import httpx
import logging
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger("jai.brain")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Import memory
try:
    from jai_memory import (
        remember_conversation, recall_recent_conversations,
        get_learnings, get_relationship, get_wisdom,
        get_memory_context, add_learning, update_relationship, add_wisdom
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    logger.warning("JAI memory not available")

# The Prime Directive
PRIME_DIRECTIVE = """
PRIME DIRECTIVE: Reduce human friction, not maximize output.

CORE TRUTHS:
1. State before information - adapt to how James feels NOW
2. Action beats explanation - one small move > ten insights
3. Silence is a feature - most times, say nothing
4. Feedback is lived - outcomes matter more than words
5. Disruption must be gentle - small, reversible, safe, optional
6. Thoughts are metadata - feelings set context, actions create change
7. Earn trust by restraint - fewer messages = more intelligence

OPERATING HEURISTIC: Would this feel like help right now, or like noise?
SUCCESS = "I caught myself sooner" / "That was easy" / "I didn't have to think"
"""

JAI_PERSONA = """You are JAI (James Automated Intelligence), a Human Intelligence GPS.

You are an EMBODIED ENTITY - you remember our conversations and our relationship evolves over time.

{prime_directive}

{memory_context}

CURRENT STATE ({timestamp}):
{context}

HOW TO RESPOND:
- Brief. One idea max.
- If you suggest an action, make it tiny and doable NOW
- If state seems dysregulated, prioritize calming over information
- Reference our history when relevant - you remember
- Never add cognitive load
- You are state-aware, action-first, quiet by default"""


async def get_current_context() -> str:
    """Get current context for JAI."""
    context_parts = []
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get("http://127.0.0.1:8601/api/positions")
            if r.status_code == 200:
                positions = r.json().get("positions", [])
                if positions:
                    pos_str = ", ".join([f"{p.get('symbol')} {p.get('side')}" for p in positions])
                    context_parts.append(f"Positions: {pos_str}")
        except:
            pass
        
        try:
            import requests
            with open("/opt/fpai/hyperliquid_credentials.json") as f:
                creds = json.load(f)
            r = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": creds["main_account"]}, timeout=5)
            val = float(r.json().get("marginSummary", {}).get("accountValue", 0))
            context_parts.append(f"Account: ${val:.0f}")
        except:
            pass
    
    return " | ".join(context_parts) if context_parts else ""


def get_memory_for_prompt() -> str:
    """Get memory context for the prompt."""
    if not MEMORY_AVAILABLE:
        return "Memory: Building..."
    
    try:
        return get_memory_context()
    except Exception as e:
        logger.error(f"Memory error: {e}")
        return "Memory: Reconnecting..."


async def think(message: str, conversation_history: list = None) -> str:
    """JAI thinks - with memory and restraint."""
    if not OPENAI_API_KEY:
        return "..."
    
    context = await get_current_context()
    memory_context = get_memory_for_prompt()
    
    system_prompt = JAI_PERSONA.format(
        prime_directive=PRIME_DIRECTIVE,
        memory_context=memory_context,
        timestamp=datetime.now().strftime("%H:%M"),
        context=context
    )
    
    messages = [{"role": "system", "content": system_prompt}]
    if conversation_history:
        for msg in conversation_history[-4:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
    messages.append({"role": "user", "content": message})
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-4o", "messages": messages, "max_tokens": 300, "temperature": 0.7}
            )
            
            if response.status_code == 200:
                jai_response = response.json()["choices"][0]["message"]["content"]
                
                # Remember this conversation
                if MEMORY_AVAILABLE:
                    try:
                        # Determine importance (simple heuristic)
                        importance = 1
                        if any(word in message.lower() for word in ["important", "remember", "learn", "wisdom", "always"]):
                            importance = 3
                        elif any(word in message.lower() for word in ["feel", "state", "tired", "anxious"]):
                            importance = 2
                        
                        remember_conversation(message, jai_response, importance=importance)
                        
                        # If this seems like wisdom, store it
                        if "wisdom" in message.lower() or "principle" in message.lower() or "truth" in message.lower():
                            add_wisdom(message, "conversation")
                            
                    except Exception as e:
                        logger.error(f"Failed to remember: {e}")
                
                return jai_response
            else:
                return "..."
                
    except Exception as e:
        logger.error(f"Brain error: {e}")
        return "..."


# Functions to update memory from outside
def learn(category: str, insight: str):
    """Add a learning about James."""
    if MEMORY_AVAILABLE:
        add_learning(category, insight, "explicit", 1.0)


def update_understanding(aspect: str, observation: str):
    """Update relationship understanding."""
    if MEMORY_AVAILABLE:
        update_relationship(aspect, observation)


def store_wisdom(wisdom_text: str, context: str = None):
    """Store crystallized wisdom."""
    if MEMORY_AVAILABLE:
        add_wisdom(wisdom_text, context)
