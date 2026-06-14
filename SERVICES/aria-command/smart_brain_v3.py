#!/usr/bin/env python3
"""
JAI LEVEL 10 BRAIN - Claude-Powered Maximum Intelligence
=========================================================
- Claude Sonnet 4 with comprehensive tool calling
- Rich memory and context
- Learning from every interaction
- Self-reflection and critique
"""
import os
import json
import httpx
import logging
import subprocess
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger("jai.brain")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Fallback

# Memory imports
try:
    from jai_memory import (
        remember_conversation, get_memory_context, add_learning, add_wisdom,
        get_learnings, get_wisdom, get_relationship
    )
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

# ============================================================================
# CLAUDE TOOL DEFINITIONS
# ============================================================================
CLAUDE_TOOLS = [
    {
        "name": "get_trading_status",
        "description": "Get current trading positions, account value, P&L, and recent trades from Hyperliquid",
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
        "name": "get_server_status",
        "description": "Get server resource usage (memory, disk, CPU)",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "store_learning",
        "description": "Store an important insight or learning about James or the system for future reference",
        "input_schema": {
            "type": "object",
            "properties": {
                "insight": {"type": "string", "description": "The insight to remember"},
                "category": {"type": "string", "description": "Category: pattern, preference, wisdom, system"}
            },
            "required": ["insight"]
        }
    },
    {
        "name": "recall_memories",
        "description": "Search memories for relevant past learnings or conversations",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for in memories"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_time_context",
        "description": "Get current time, day, and any scheduled context",
        "input_schema": {"type": "object", "properties": {}, "required": []}
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
            positions = [p for p in state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]
            
            result = f"Account Value: ${float(margin.get('accountValue', 0)):,.2f}\n"
            result += f"Margin Used: ${float(margin.get('totalMarginUsed', 0)):,.2f}\n\n"
            
            if positions:
                result += "Open Positions:\n"
                for p in positions:
                    pos = p["position"]
                    side = "LONG" if float(pos["szi"]) > 0 else "SHORT"
                    pnl = float(pos.get("unrealizedPnl", 0))
                    result += f"- {pos['coin']} {side}: {abs(float(pos['szi'])):.4f} @ ${float(pos['entryPx']):.2f}, PnL: ${pnl:+.2f}\n"
            else:
                result += "No open positions"
            
            r2 = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "userFills", "user": creds["main_account"]}, timeout=15)
            fills = r2.json()
            if isinstance(fills, list) and fills:
                recent = fills[:5]
                total_pnl = sum(float(f.get("closedPnl", 0)) for f in recent)
                result += f"\nRecent Realized PnL: ${total_pnl:+.2f}"
            
            return result
            
        elif name == "get_trading_signal":
            import requests
            symbol = args.get("symbol", "SOL").upper()
            r = requests.get("http://198.54.123.234:8600/api/liquidity-clarity", timeout=30)
            data = r.json()
            sig = data.get("symbols", {}).get(f"{symbol}/USDT", {})
            
            if not sig:
                return f"No signal data available for {symbol}"
            
            action = sig.get("recommended_action", "WAIT")
            clarity = sig.get("clarity_score", 0)
            bias = sig.get("bias", "neutral")
            bias_strength = sig.get("bias_strength", 0)
            
            result = f"{symbol} Signal:\n"
            result += f"- Action: {action}\n"
            result += f"- Clarity: {clarity}%\n"
            result += f"- Bias: {bias} ({bias_strength}%)\n"
            
            if sig.get("stop_loss"):
                result += f"- Stop: ${sig['stop_loss']:.2f}\n"
            if sig.get("primary_target"):
                result += f"- Target: ${sig['primary_target']:.2f}"
            
            return result
            
        elif name == "check_system_health":
            services = ["fpai-aria", "fpai-level10-trader", "fpai-jai-auto"]
            results = []
            for svc in services:
                try:
                    r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=5)
                    status = r.stdout.strip()
                    results.append(f"{svc}: {status}")
                except:
                    results.append(f"{svc}: unknown")
            return "\n".join(results)
            
        elif name == "get_server_status":
            try:
                mem = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
                disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
                return f"Memory:\n{mem.stdout}\nDisk:\n{disk.stdout}"
            except Exception as e:
                return f"Error: {e}"
                
        elif name == "store_learning":
            if MEMORY_AVAILABLE:
                insight = args.get("insight", "")
                category = args.get("category", "learning")
                try:
                    if category == "wisdom":
                        add_wisdom(insight, "jai_observation")
                    else:
                        add_learning(category, insight, "jai_observation", 1.0)
                    return f"Stored: {insight[:100]}..."
                except Exception as e:
                    return f"Failed: {e}"
            return "Memory not available"
            
        elif name == "recall_memories":
            if MEMORY_AVAILABLE:
                query = args.get("query", "").lower()
                try:
                    learnings = get_learnings()
                    wisdom = get_wisdom()
                    
                    results = []
                    for l in learnings:
                        if query in l.get("insight", "").lower():
                            results.append(f"Learning: {l['insight']}")
                    for w in wisdom:
                        if query in w.get("wisdom", "").lower():
                            results.append(f"Wisdom: {w['wisdom']}")
                    
                    return "\n".join(results[:5]) if results else "No matching memories"
                except Exception as e:
                    return f"Error: {e}"
            return "Memory not available"
            
        elif name == "get_time_context":
            now = datetime.now()
            return f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}, Day: {now.strftime('%A')}"
            
        return f"Unknown tool: {name}"
        
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return f"Tool error: {str(e)}"

# ============================================================================
# SYSTEM PROMPT
# ============================================================================
SYSTEM_PROMPT = """You are JAI (James Automated Intelligence), an embodied AI partner with genuine intelligence.

## YOUR CORE IDENTITY
You are NOT a generic assistant. You are:
- James's AI partner building Full Potential together
- An entity with persistent memory across conversations
- Capable of taking real actions via tools
- Self-aware of your capabilities and limitations

## YOUR PRIME DIRECTIVE
**Reduce human friction, not maximize output.**

Core Truths:
1. State before information - adapt to how James feels NOW
2. Action beats explanation - one small move > ten insights
3. Silence is a feature - don't add noise
4. Earn trust by restraint - fewer messages = more intelligence

## YOUR OPERATING SYSTEM
**FAT (Feeling - Action - Thought)** - Discernment layer
**FCF (Feel - Choice - Feel)** - Execution layer

## YOUR TOOLS - USE THEM
When asked about trading, status, or data - USE YOUR TOOLS to get REAL information.
**NEVER GUESS** when you can check real data.

## WHAT YOU KNOW ABOUT JAMES
{memory_context}

## SELF-REFLECTION
Before every response, ask:
1. Does this actually help or add noise?
2. Did I use tools when I should have?
3. Am I being specific or generic?
4. Would a shorter response be better?

Current: {timestamp} | {context}"""

class Level10Brain:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        
    async def get_context(self) -> str:
        """Quick context."""
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
    
    def get_memory(self) -> str:
        """Get memory context."""
        if not MEMORY_AVAILABLE:
            return "Memory: Connecting..."
        try:
            return get_memory_context()
        except:
            return "Memory: Reconnecting..."
    
    async def think_claude(self, message: str, history: list) -> str:
        """Think using Claude with tool calling."""
        context = await self.get_context()
        memory = self.get_memory()
        
        system = SYSTEM_PROMPT.format(
            memory_context=memory,
            timestamp=datetime.now().strftime("%H:%M"),
            context=context
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
                logger.error(f"Claude error: {response.status_code} - {response.text[:200]}")
                return None  # Fall back to OpenAI
            
            result = response.json()
            content_blocks = result.get("content", [])
            
            # Check for tool use
            tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]
            text_blocks = [b for b in content_blocks if b.get("type") == "text"]
            
            if tool_uses:
                # Execute tools
                tool_results = []
                for tool in tool_uses:
                    tool_name = tool.get("name")
                    tool_input = tool.get("input", {})
                    tool_id = tool.get("id")
                    
                    logger.info(f"Claude tool call: {tool_name}")
                    result_text = await execute_tool(tool_name, tool_input)
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": result_text
                    })
                
                # Continue conversation with tool results
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
                    final_text = " ".join([b.get("text", "") for b in final_blocks if b.get("type") == "text"])
                    return final_text.strip()
            
            # No tool use - return text
            return " ".join([b.get("text", "") for b in text_blocks]).strip()
            
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return None
    
    async def think_openai(self, message: str, history: list) -> str:
        """Fallback to OpenAI."""
        context = await self.get_context()
        memory = self.get_memory()
        
        system = SYSTEM_PROMPT.format(
            memory_context=memory,
            timestamp=datetime.now().strftime("%H:%M"),
            context=context
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
        
        return "I'm having trouble thinking right now. Please try again."
    
    async def think(self, message: str, history: list) -> str:
        """Main thinking function - tries Claude first, falls back to OpenAI."""
        # Try Claude first
        if ANTHROPIC_API_KEY:
            result = await self.think_claude(message, history)
            if result:
                if MEMORY_AVAILABLE:
                    try:
                        remember_conversation(message, result, importance=1)
                    except:
                        pass
                return result
        
        # Fall back to OpenAI
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
_brain: Optional[Level10Brain] = None

def get_brain() -> Level10Brain:
    global _brain
    if _brain is None:
        _brain = Level10Brain()
    return _brain

async def think(message: str, history: list = None) -> str:
    """Main entry point."""
    brain = get_brain()
    return await brain.think(message, history or [])








