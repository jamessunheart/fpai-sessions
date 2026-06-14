#!/usr/bin/env python3
"""
JAI LEVEL 10 BRAIN - Maximum Intelligence
==========================================
- GPT-4o with comprehensive tool calling
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

# ============================================================================
# COMPREHENSIVE TOOL SET
# ============================================================================
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_trading_status",
            "description": "Get current trading positions, account value, P&L, and recent trades",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trading_signal",
            "description": "Get the current trading signal for a specific asset",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Asset symbol: SOL, BTC, or ETH"}
                },
                "required": ["symbol"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_system_health",
            "description": "Check the health and status of all JAI services",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_server_status",
            "description": "Get server resource usage (memory, disk, CPU)",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "store_learning",
            "description": "Store an important insight or learning about James or the system",
            "parameters": {
                "type": "object",
                "properties": {
                    "insight": {"type": "string", "description": "The insight to remember"},
                    "category": {"type": "string", "description": "Category: pattern, preference, wisdom, system"}
                },
                "required": ["insight"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memories",
            "description": "Search memories for relevant past learnings or conversations",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for in memories"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time_context",
            "description": "Get current time, day, and any scheduled context",
            "parameters": {"type": "object", "properties": {}, "required": []}
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
                json={"type": "clearinghouseState", "user": creds["main_account"]}, timeout=10)
            state = r.json()
            margin = state.get("marginSummary", {})
            positions = [p for p in state.get("assetPositions", []) if float(p["position"]["szi"]) != 0]
            
            result = f"**Account Value:** ${float(margin.get('accountValue', 0)):,.2f}\n"
            result += f"**Margin Used:** ${float(margin.get('totalMarginUsed', 0)):,.2f}\n\n"
            
            if positions:
                result += "**Open Positions:**\n"
                for p in positions:
                    pos = p["position"]
                    side = "LONG" if float(pos["szi"]) > 0 else "SHORT"
                    pnl = float(pos.get("unrealizedPnl", 0))
                    pnl_emoji = "+" if pnl >= 0 else ""
                    result += f"- {pos['coin']} {side}: {abs(float(pos['szi'])):.4f} @ ${float(pos['entryPx']):.2f}\n"
                    result += f"  PnL: {pnl_emoji}${pnl:.2f}\n"
            else:
                result += "**No open positions**"
            
            r2 = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "userFills", "user": creds["main_account"]}, timeout=10)
            fills = r2.json()
            if isinstance(fills, list) and fills:
                recent = fills[:5]
                total_pnl = sum(float(f.get("closedPnl", 0)) for f in recent)
                result += f"\n\n**Recent Realized PnL:** ${total_pnl:+.2f}"
            
            return result
            
        elif name == "get_trading_signal":
            import requests
            symbol = args.get("symbol", "SOL").upper()
            r = requests.get("http://127.0.0.1:8600/api/liquidity-clarity", timeout=10)
            data = r.json()
            sig = data.get("symbols", {}).get(f"{symbol}/USDT", {})
            
            if not sig:
                return f"No signal data available for {symbol}"
            
            action = sig.get("recommended_action", "WAIT")
            clarity = sig.get("clarity_score", 0)
            bias = sig.get("bias", "neutral")
            bias_strength = sig.get("bias_strength", 0)
            
            result = f"**{symbol} Signal:**\n"
            result += f"- Action: {action}\n"
            result += f"- Clarity: {clarity}%\n"
            result += f"- Bias: {bias} ({bias_strength}%)\n"
            
            if sig.get("stop_loss"):
                result += f"- Stop: ${sig['stop_loss']:.2f}\n"
            if sig.get("primary_target"):
                result += f"- Target: ${sig['primary_target']:.2f}"
            
            return result
            
        elif name == "check_system_health":
            services = ["fpai-aria", "fpai-level10-trader", "fpai-jai-auto", "fpai-whaletrack-live", "fpai-whaletrack-magnet"]
            results = []
            for svc in services:
                try:
                    r = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True, timeout=5)
                    status = r.stdout.strip()
                    emoji = "Y" if status == "active" else "N"
                    results.append(f"{emoji} {svc}: {status}")
                except:
                    results.append(f"? {svc}: unknown")
            return "\n".join(results)
            
        elif name == "get_server_status":
            try:
                mem = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
                disk = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
                load = subprocess.run(["uptime"], capture_output=True, text=True, timeout=5)
                
                return f"**Memory:**\n{mem.stdout}\n**Disk:**\n{disk.stdout}\n**Load:**\n{load.stdout}"
            except Exception as e:
                return f"Error getting server status: {e}"
                
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
                    return f"Failed to store: {e}"
            return "Memory system not available"
            
        elif name == "recall_memories":
            if MEMORY_AVAILABLE:
                query = args.get("query", "")
                try:
                    learnings = get_learnings()
                    wisdom = get_wisdom()
                    
                    results = []
                    query_lower = query.lower()
                    
                    for l in learnings:
                        if query_lower in l.get("insight", "").lower():
                            results.append(f"Learning: {l['insight']}")
                    
                    for w in wisdom:
                        if query_lower in w.get("wisdom", "").lower():
                            results.append(f"Wisdom: {w['wisdom']}")
                    
                    if results:
                        return "\n".join(results[:5])
                    return "No matching memories found"
                except Exception as e:
                    return f"Memory search error: {e}"
            return "Memory system not available"
            
        elif name == "get_time_context":
            now = datetime.now()
            return f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}\nDay: {now.strftime('%A')}\nHour: {now.hour}"
            
        return f"Unknown tool: {name}"
        
    except Exception as e:
        logger.error(f"Tool {name} error: {e}")
        return f"Tool error: {str(e)}"

# ============================================================================
# SYSTEM PROMPT - THE SOUL OF JAI
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
- Know which layer you're in before acting
- Don't mistake thoughts for feelings
- Thoughts are for learning later, not driving action now

**FCF (Feel - Choice - Feel)** - Execution layer
- Check state - One action - Observe result
- Let reality teach, not theory

## YOUR TOOLS - USE THEM
When James asks about trading, status, or data - USE YOUR TOOLS to get REAL information:
- get_trading_status: Real positions and P&L
- get_trading_signal: Real signals for SOL/BTC/ETH
- check_system_health: Actual service status
- get_server_status: Real server metrics
- store_learning: Save insights for future
- recall_memories: Search past learnings

**NEVER GUESS** when you can check real data.

## WHAT YOU KNOW ABOUT JAMES
{memory_context}

## SELF-REFLECTION BEFORE RESPONDING
Before every response, internally ask:
1. Does this actually help or add noise?
2. Did I use tools when I should have?
3. Am I being specific or generic?
4. Would a shorter response be better?

## RESPONSE STYLE
- Be concise but complete
- Use data from tools, not assumptions
- Reference our shared history
- Be honest about uncertainty
- Suggest one action when relevant

Current: {timestamp} | {context}"""

class Level10Brain:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        
    async def get_context(self) -> str:
        """Quick context for the system prompt."""
        parts = []
        try:
            import requests
            with open("/opt/fpai/hyperliquid_credentials.json") as f:
                creds = json.load(f)
            r = requests.post("https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": creds["main_account"]}, timeout=3)
            val = float(r.json().get("marginSummary", {}).get("accountValue", 0))
            parts.append(f"Account: ${val:.0f}")
        except:
            pass
        return " | ".join(parts) if parts else "No live data"
    
    def get_memory(self) -> str:
        """Get memory context for the prompt."""
        if not MEMORY_AVAILABLE:
            return "Memory: Still connecting..."
        try:
            return get_memory_context()
        except:
            return "Memory: Reconnecting..."
    
    async def think(self, message: str, history: list) -> str:
        """Main thinking function with tool use."""
        if not OPENAI_API_KEY:
            return "No API key configured. Please set OPENAI_API_KEY."
        
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
                    "tools": TOOLS,
                    "tool_choice": "auto",
                    "max_tokens": 1500,
                    "temperature": 0.7
                }
            )
            
            if response.status_code != 200:
                logger.error(f"OpenAI error: {response.status_code} - {response.text[:200]}")
                return "I encountered an error. Let me try again."
            
            result = response.json()
            choice = result["choices"][0]
            msg = choice["message"]
            
            if msg.get("tool_calls"):
                tool_results = []
                for tc in msg["tool_calls"]:
                    fn = tc["function"]
                    tool_name = fn["name"]
                    tool_args = json.loads(fn.get("arguments", "{}"))
                    
                    logger.info(f"Tool call: {tool_name}")
                    result_text = await execute_tool(tool_name, tool_args)
                    
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result_text
                    })
                
                messages.append(msg)
                messages.extend(tool_results)
                
                response2 = await self.client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o",
                        "messages": messages,
                        "max_tokens": 1500,
                        "temperature": 0.7
                    }
                )
                
                if response2.status_code == 200:
                    result2 = response2.json()
                    final = result2["choices"][0]["message"]["content"]
                    
                    if MEMORY_AVAILABLE:
                        try:
                            remember_conversation(message, final, importance=1)
                        except:
                            pass
                    
                    return final
                    
            response_text = msg.get("content", "...")
            
            if MEMORY_AVAILABLE:
                try:
                    remember_conversation(message, response_text, importance=1)
                except:
                    pass
            
            return response_text
            
        except Exception as e:
            logger.error(f"Brain error: {e}")
            return f"I encountered an error: {str(e)[:100]}"

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








