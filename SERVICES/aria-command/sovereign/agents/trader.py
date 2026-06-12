#!/usr/bin/env python3
"""
ARIA ASCENSION - TRADER AGENT
=============================

Specializes in market analysis and trading:
- Signal interpretation
- Position management
- Market condition analysis
- Trade suggestions
"""

import os
import re
import json
import httpx
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from .base import BaseAgent, AgentCapability, AgentResponse

logger = logging.getLogger("aria.agents.trader")

# Configuration
WHALETRACK_URL = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8600")
WHALETRACK_LIVE_URL = os.getenv("WHALETRACK_LIVE_URL", "http://198.54.123.234:8601")


class TraderAgent(BaseAgent):
    """
    Trader Agent - Expert in market analysis and trading.
    """
    
    name = "trader"
    description = "Expert in market analysis, trading signals, and position management"
    capabilities = [
        AgentCapability.TRADING,
        AgentCapability.MARKET_ANALYSIS,
        AgentCapability.REASONING
    ]
    priority = 20  # High priority for trading queries
    
    # Trading-related patterns
    TRADING_PATTERNS = [
        r'\b(sol|btc|eth|xrp|bitcoin|ethereum|solana)\b',
        r'\b(trade|trading|signal|signals|position|positions)\b',
        r'\b(long|short|buy|sell|entry|exit)\b',
        r'\b(market|price|profit|loss|pnl|leverage)\b',
        r'\b(bullish|bearish|trend|momentum|bias)\b',
    ]
    
    def __init__(self):
        super().__init__()
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def can_handle(self, query: str, context: Dict = None) -> float:
        """Determine if this is a trading-related query."""
        query_lower = query.lower()
        
        # Count pattern matches
        matches = 0
        for pattern in self.TRADING_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                matches += 1
        
        # Direct trading commands
        if query_lower.startswith(("/signal", "/trade", "/position")):
            return 0.95
        
        # Strong match
        if matches >= 2:
            return 0.85
        elif matches == 1:
            return 0.6
        
        return 0.1
    
    async def process(self, query: str, context: Dict = None) -> AgentResponse:
        """Process a trading-related query."""
        query_lower = query.lower()
        
        try:
            # Determine what's being asked
            if "signal" in query_lower or "signals" in query_lower:
                return await self._get_signals(query)
            
            elif "position" in query_lower or "positions" in query_lower:
                return await self._get_positions()
            
            elif any(sym in query_lower for sym in ["sol", "btc", "eth", "xrp"]):
                # Extract symbol
                for sym in ["sol", "btc", "eth", "xrp"]:
                    if sym in query_lower:
                        return await self._get_signal_for_symbol(sym.upper())
            
            elif "market" in query_lower:
                return await self._get_market_overview()
            
            else:
                # General trading query
                return await self._general_trading_response(query)
        
        except Exception as e:
            logger.error(f"Trader agent error: {e}")
            return self._create_response(
                success=False,
                content=f"Error processing trading query: {str(e)}",
                confidence=0.3
            )
    
    async def _get_signals(self, query: str) -> AgentResponse:
        """Get current trading signals from liquidity-clarity endpoint."""
        try:
            response = await self.http_client.get(
                f"{WHALETRACK_URL}/api/liquidity-clarity"
            )
            
            if response.status_code == 200:
                data = response.json()
                symbols = data.get("symbols", {})
                
                if not symbols:
                    return self._create_response(
                        success=True,
                        content="📊 No signals available at the moment",
                        confidence=0.7
                    )
                
                # Format signals nicely
                lines = ["📊 **Current Trading Signals**\n"]
                
                for symbol_pair, signal in symbols.items():
                    symbol = symbol_pair.replace("/USDT", "")
                    bias = signal.get("bias", "neutral")
                    strength = signal.get("bias_strength", 0)
                    clarity = signal.get("clarity_score", 0)
                    price = signal.get("price", 0)
                    action = signal.get("recommended_action", "WAIT")
                    
                    emoji = "🟢" if bias == "bullish" else "🔴" if bias == "bearish" else "⚪"
                    lines.append(f"{emoji} **{symbol}**: ${price:,.2f}")
                    lines.append(f"   {bias.upper()} ({strength:.1f}%) → {action}")
                    lines.append(f"   Clarity: {clarity:.0f}%\n")
                
                return self._create_response(
                    success=True,
                    content="\n".join(lines),
                    confidence=0.9,
                    data={"symbols": symbols}
                )
            else:
                return self._create_response(
                    success=False,
                    content="Unable to fetch signals from WhaleTrack",
                    confidence=0.5
                )
        
        except Exception as e:
            return self._create_response(
                success=False,
                content=f"Signal fetch error: {str(e)}",
                confidence=0.3
            )
    
    async def _get_signal_for_symbol(self, symbol: str) -> AgentResponse:
        """Get signal for a specific symbol."""
        try:
            response = await self.http_client.get(
                f"{WHALETRACK_URL}/api/liquidity-clarity"
            )
            
            if response.status_code == 200:
                data = response.json()
                symbols = data.get("symbols", {})
                
                # Find the symbol (check both formats)
                symbol_key = f"{symbol}/USDT"
                if symbol_key in symbols:
                    asset = symbols[symbol_key]
                    clarity = asset.get("clarity_score", 0)
                    bias = asset.get("bias", "neutral")
                    strength = asset.get("bias_strength", 0)
                    price = asset.get("price", 0)
                    action = asset.get("recommended_action", "WAIT")
                    target = asset.get("primary_target")
                    stop = asset.get("stop_loss", 0)
                    rr = asset.get("risk_reward", 0)
                    
                    emoji = "🟢" if bias == "bullish" else "🔴" if bias == "bearish" else "⚪"
                    
                    content = f"""{emoji} **{symbol}/USDT Signal**

**Price:** ${price:,.2f}
**Bias:** {bias.upper()} ({strength:.1f}% strength)
**Clarity Score:** {clarity:.0f}%
**Recommended:** {action}"""
                    
                    if target and action != "WAIT":
                        content += f"""
**Target:** ${target:,.2f}
**Stop Loss:** ${stop:,.4f}
**Risk/Reward:** {rr:.2f}"""
                    
                    content += "\n\n*Data from WhaleTrack Magnet*"
                    
                    return self._create_response(
                        success=True,
                        content=content.strip(),
                        confidence=0.9,
                        data={"symbol": symbol, "bias": bias, "clarity": clarity, "action": action}
                    )
                
                return self._create_response(
                    success=False,
                    content=f"No data found for {symbol}. Available: {', '.join(symbols.keys())}",
                    confidence=0.5
                )
        
        except Exception as e:
            return self._create_response(
                success=False,
                content=f"Error fetching {symbol} data: {str(e)}",
                confidence=0.3
            )
    
    async def _get_positions(self) -> AgentResponse:
        """Get current trading positions."""
        try:
            response = await self.http_client.get(
                f"{WHALETRACK_LIVE_URL}/api/live/positions"
            )
            
            if response.status_code == 200:
                data = response.json()
                positions = data.get("positions", [])
                
                if not positions:
                    return self._create_response(
                        success=True,
                        content="📭 No active positions",
                        confidence=0.9
                    )
                
                lines = ["📈 **Active Positions**\n"]
                for pos in positions:
                    symbol = pos.get("symbol", "Unknown")
                    side = pos.get("side", "?")
                    size = pos.get("size", 0)
                    pnl = pos.get("unrealized_pnl", 0)
                    emoji = "🟢" if pnl >= 0 else "🔴"
                    
                    lines.append(f"{emoji} **{symbol}** {side}")
                    lines.append(f"   Size: {size}, P&L: ${pnl:,.2f}")
                
                return self._create_response(
                    success=True,
                    content="\n".join(lines),
                    confidence=0.9,
                    data={"positions": positions}
                )
        
        except Exception as e:
            return self._create_response(
                success=False,
                content=f"Error fetching positions: {str(e)}",
                confidence=0.3
            )
    
    async def _get_market_overview(self) -> AgentResponse:
        """Get overall market overview."""
        try:
            response = await self.http_client.get(
                f"{WHALETRACK_URL}/api/liquidity-clarity"
            )
            
            if response.status_code == 200:
                data = response.json()
                symbols = data.get("symbols", {})
                
                lines = ["🌐 **Market Overview**\n"]
                
                for symbol_pair, asset in symbols.items():
                    symbol = symbol_pair.replace("/USDT", "")
                    price = asset.get("price", 0)
                    bias = asset.get("bias", "neutral")
                    clarity = asset.get("clarity_score", 0)
                    action = asset.get("recommended_action", "WAIT")
                    
                    emoji = "🟢" if bias == "bullish" else "🔴" if bias == "bearish" else "⚪"
                    lines.append(f"{emoji} **{symbol}**: ${price:,.2f}")
                    lines.append(f"   {bias.upper()} → {action} ({clarity:.0f}% clarity)")
                
                return self._create_response(
                    success=True,
                    content="\n".join(lines),
                    confidence=0.85,
                    data={"symbols": symbols}
                )
        
        except Exception as e:
            return self._create_response(
                success=False,
                content=f"Market overview error: {str(e)}",
                confidence=0.3
            )
    
    async def _general_trading_response(self, query: str) -> AgentResponse:
        """Handle general trading queries."""
        # Get market data for context
        market_response = await self._get_market_overview()
        
        if market_response.success:
            content = f"""
I can help with trading! Here's the current market:

{market_response.content}

**What I can do:**
- `/signal SOL` - Get signal for a specific asset
- `/signals` - Get all current signals
- `/positions` - View active positions

What would you like to know?
"""
            return self._create_response(
                success=True,
                content=content.strip(),
                confidence=0.7,
                reasoning="Providing trading overview and options"
            )
        else:
            return self._create_response(
                success=False,
                content="Unable to fetch market data right now. Please try again.",
                confidence=0.4
            )

