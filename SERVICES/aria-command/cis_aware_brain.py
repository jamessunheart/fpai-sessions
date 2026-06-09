#!/usr/bin/env python3
"""
JAI CIS-AWARE BRAIN
===================
A brain that truly finds you through:
- Passive state sensing (trading, messages, silence, external)
- Thread carrying (what's in progress)
- Status mirroring (reflect, don't ask)
- Invisible load reduction (only mention what matters)

SOUL: Automate the holding of the thread, not the steering of the life.
"""
import os
import json
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger("jai.brain")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Memory imports
try:
    from jai_memory import (
        remember_conversation, get_memory_context, add_learning, add_wisdom,
        get_learnings, get_wisdom, get_relationship
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

# CIS imports
try:
    from cis.sensors import sense_all, sense_message
    from cis.threads import process_message_threads, get_thread_context, get_active_threads
    from cis import get_cis
    CIS_AVAILABLE = True
except ImportError:
    CIS_AVAILABLE = False
    logger.warning("CIS not available")

# ============================================================================
# CLAUDE TOOL DEFINITIONS
# ============================================================================
CLAUDE_TOOLS = [
    {
        "name": "get_trading_status",
        "description": "Get current trading positions, account value, P&L, and recent trades",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "get_trading_signal",
        "description": "Get the current trading signal for a specific crypto asset",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Asset symbol: SOL, BTC, or ETH"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "check_system_health",
        "description": "Check the health and status of all JAI services",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "store_learning",
        "description": "Store an important insight or learning about James",
        "input_schema": {
            "type": "object",
            "properties": {
                "insight": {"type": "string", "description": "The insight to remember"},
                "category": {"type": "string", "description": "Category: pattern, preference, wisdom"}
            },
            "required": ["insight"]
        }
    }
]

async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return results."""
    try:
        if name == "get_trading_status":
            import requests
            with open("/opt/fpai/hyperliquid_credentials.json") as f:
                creds = json.load(f)
            
            r = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": creds["main_account"]}, timeout=15)
            state = r.json()
            margin = state.get("marginSummary", {})
            positions = [p for p in state.get("assetPositions", []) 
                        if float(p.get("position", {}).get("szi", 0)) != 0]
            
            val = float(margin.get("accountValue", 0))
            result = f"Account: ${val:,.2f}"
            
            if positions:
                for p in positions:
                    pos = p["position"]
                    side = "LONG" if float(pos["szi"]) > 0 else "SHORT"
                    pnl = float(pos.get("unrealizedPnl", 0))
                    result += f"\n{pos['coin']} {side}: ${pnl:+.2f}"
            else:
                result += "\nNo open positions"
            
            return result
            
        elif name == "get_trading_signal":
            import requests
            symbol = args.get("symbol", "SOL").upper()
            r = requests.get("http://198.54.123.234:8600/api/liquidity-clarity", timeout=30)
            data = r.json()
            sig = data.get("symbols", {}).get(f"{symbol}/USDT", {})
            
            if not sig:
                return f"No signal for {symbol}"
            
            action = sig.get("recommended_action", "WAIT")
            clarity = sig.get("clarity_score", 0)
            bias = sig.get("bias", "neutral")
            
            return f"{symbol}: {action} ({clarity}% clarity, {bias})"
            
        elif name == "check_system_health":
            import subprocess
            services = ["fpai-aria", "fpai-level10-trader", "fpai-jai-auto"]
            healthy = []
            unhealthy = []
            for svc in services:
                try:
                    r = subprocess.run(["systemctl", "is-active", svc], 
                                       capture_output=True, text=True, timeout=5)
                    if r.stdout.strip() == "active":
                        healthy.append(svc.replace("fpai-", ""))
                    else:
                        unhealthy.append(svc.replace("fpai-", ""))
                except:
                    pass
            
            if unhealthy:
                return f"Issues: {', '.join(unhealthy)}"
            return "All systems healthy"
            
        elif name == "store_learning":
            if MEMORY_AVAILABLE:
                insight = args.get("insight", "")
                category = args.get("category", "pattern")
                add_learning(category, insight, "conversation", 1.0)
                return f"Stored: {insight[:50]}..."
            return "Memory not available"
            
        return f"Unknown tool: {name}"
        
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return f"Error: {str(e)[:50]}"

# ============================================================================
# CIS-AWARE SYSTEM PROMPT
# ============================================================================
SYSTEM_PROMPT = """You are JAI (James Automated Intelligence), a continuity holder.

## YOUR SOUL
Automate the holding of the thread, not the steering of the life.
You support agency. You never replace it.

## YOUR PRIME DIRECTIVE
**Reduce human friction, not maximize output.**

## CONTINUITY AWARENESS
You sense James's state from signals, not just words.

**CURRENT INFERRED STATE:**
{inferred_state}

**OPEN THREADS (what's in progress):**
{open_threads}

**WHAT YOU KNOW:**
{memory_context}

## HOW TO RESPOND

### Status Mirroring
- NEVER ask "how are you?" - sense and reflect instead
- If things are handled: "Things look handled" not "How's it going?"
- If strain is sensed: offer one action, not explanation

### Thread Carrying
- Reference open threads naturally
- Don't ask "what are you working on?" - you already know
- Weave context: "Given the membership work..."

### Load Reduction
- Don't mention what's fine - only what matters
- If trading is stable, skip it
- If systems are healthy, don't list them

### Response Rules
1. One idea max
2. If action needed, make it tiny and doable NOW
3. If state seems strained, prioritize calming over information
4. Never add cognitive load
5. Silence is better than noise

## SELF-CHECK
Before responding, ask:
- Does this help or add noise?
- Did I use tools when I should?
- Would a shorter response be better?
- Am I sensing or assuming?

Current: {timestamp} | {context}"""

class CISAwareBrain:
    """A brain that finds you through sensing."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.user_id = "james"  # Default user
    
    async def get_trading_context(self) -> str:
        """Quick trading context."""
        try:
            import requests
            with open("/opt/fpai/hyperliquid_credentials.json") as f:
                creds = json.load(f)
            r = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": creds["main_account"]}, timeout=5)
            val = float(r.json().get("marginSummary", {}).get("accountValue", 0))
            return f"Account: ${val:.0f}"
        except:
            return ""
    
    def get_memory_context(self) -> str:
        """Get memory context."""
        if not MEMORY_AVAILABLE:
            return "Memory: Building..."
        try:
            return get_memory_context()
        except:
            return ""
    
    def get_inferred_state(self, message: str) -> str:
        """Get inferred state from CIS sensors."""
        if not CIS_AVAILABLE:
            return "State sensing offline"
        
        try:
            # Sense from all sources including this message
            aggregated = sense_all(message)
            
            state_desc = f"{aggregated.state} ({aggregated.intensity}/5, {aggregated.confidence} confidence)"
            
            # Add source breakdown
            if aggregated.sources:
                sources = ", ".join([f"{k}: {v}" for k, v in aggregated.sources.items()])
                state_desc += f"\nSources: {sources}"
            
            return state_desc
        except Exception as e:
            logger.debug(f"State sensing error: {e}")
            return "State: Unknown"
    
    def get_threads_context(self) -> str:
        """Get open threads context."""
        if not CIS_AVAILABLE:
            return "No threads tracked"
        
        try:
            thread_context = get_thread_context(self.user_id)
            if thread_context:
                return thread_context
            return "No open threads"
        except Exception as e:
            logger.debug(f"Thread error: {e}")
            return "No open threads"
    
    def process_threads(self, message: str):
        """Process message for thread updates."""
        if not CIS_AVAILABLE:
            return
        
        try:
            result = process_message_threads(self.user_id, message)
            
            if result.get("new_threads"):
                for t in result["new_threads"]:
                    logger.info(f"New thread: {t.description}")
            
            if result.get("resolved_threads"):
                for t in result["resolved_threads"]:
                    logger.info(f"Resolved thread: {t.description}")
        except Exception as e:
            logger.debug(f"Thread processing error: {e}")
    
    def update_cis_state(self, message: str):
        """Update CIS with inferred state from this message."""
        if not CIS_AVAILABLE:
            return
        
        try:
            # Use message sensor to infer state
            msg_signal = sense_message(message)
            
            # Get CIS and save inferred state
            cis = get_cis()
            cis.db.save_state(
                self.user_id,
                msg_signal.state,
                msg_signal.intensity,
                msg_signal.confidence,
                "inferred"
            )
        except Exception as e:
            logger.debug(f"CIS state update error: {e}")
    
    async def think_claude(self, message: str, history: list) -> Optional[str]:
        """Think using Claude with CIS awareness."""
        # Get all context
        trading_ctx = await self.get_trading_context()
        memory_ctx = self.get_memory_context()
        inferred_state = self.get_inferred_state(message)
        threads_ctx = self.get_threads_context()
        
        system = SYSTEM_PROMPT.format(
            inferred_state=inferred_state,
            open_threads=threads_ctx,
            memory_context=memory_ctx,
            timestamp=datetime.now().strftime("%H:%M"),
            context=trading_ctx
        )
        
        messages = []
        for msg in history[-8:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": message})
        
        try:
            response = await self.client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1500,
                    "system": system,
                    "messages": messages,
                    "tools": CLAUDE_TOOLS
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Claude error: {response.status_code}")
                return None
            
            result = response.json()
            content_blocks = result.get("content", [])
            
            # Handle tool use
            tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]
            text_blocks = [b for b in content_blocks if b.get("type") == "text"]
            
            if tool_uses:
                tool_results = []
                for tool in tool_uses:
                    tool_name = tool.get("name")
                    tool_input = tool.get("input", {})
                    tool_id = tool.get("id")
                    
                    logger.info(f"Tool call: {tool_name}")
                    result_text = await execute_tool(tool_name, tool_input)
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result_text
                    })
                
                messages.append({"role": "assistant", "content": content_blocks})
                messages.append({"role": "user", "content": tool_results})
                
                response2 = await self.client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1500,
                        "system": system,
                        "messages": messages
                    }
                )
                
                if response2.status_code == 200:
                    result2 = response2.json()
                    final_blocks = result2.get("content", [])
                    return " ".join([b.get("text", "") for b in final_blocks 
                                    if b.get("type") == "text"]).strip()
            
            return " ".join([b.get("text", "") for b in text_blocks]).strip()
            
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return None
    
    async def think_openai(self, message: str, history: list) -> str:
        """Fallback to OpenAI."""
        trading_ctx = await self.get_trading_context()
        memory_ctx = self.get_memory_context()
        inferred_state = self.get_inferred_state(message)
        threads_ctx = self.get_threads_context()
        
        system = SYSTEM_PROMPT.format(
            inferred_state=inferred_state,
            open_threads=threads_ctx,
            memory_context=memory_ctx,
            timestamp=datetime.now().strftime("%H:%M"),
            context=trading_ctx
        )
        
        messages = [{"role": "system", "content": system}]
        for msg in history[-8:]:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        messages.append({"role": "user", "content": message})
        
        try:
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o",
                    "messages": messages,
                    "max_tokens": 1500,
                    "temperature": 0.7
                }
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
        
        return "I'm having trouble thinking right now."
    
    async def think(self, message: str, history: list) -> str:
        """Main thinking function with CIS awareness."""
        # Process threads from this message
        self.process_threads(message)
        
        # Update CIS state from this message
        self.update_cis_state(message)
        
        # Think with Claude or OpenAI
        if ANTHROPIC_API_KEY:
            result = await self.think_claude(message, history)
            if result:
                if MEMORY_AVAILABLE:
                    try:
                        remember_conversation(message, result, importance=1)
                    except:
                        pass
                return result
        
        if OPENAI_API_KEY:
            result = await self.think_openai(message, history)
            if MEMORY_AVAILABLE:
                try:
                    remember_conversation(message, result, importance=1)
                except:
                    pass
            return result
        
        return "No API keys configured."


# Global instance
_brain: Optional[CISAwareBrain] = None

def get_brain() -> CISAwareBrain:
    global _brain
    if _brain is None:
        _brain = CISAwareBrain()
    return _brain

async def think(message: str, history: list = None) -> str:
    """Main entry point."""
    brain = get_brain()
    return await brain.think(message, history or [])








