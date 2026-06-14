"""
Aria Trading Commands Module
=============================

Natural language processing for trading and money management commands.
Integrates with WhaleTrack trading system for account management and auto-trading.
"""

import re
import httpx
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime

logger = logging.getLogger("aria.trading_commands")

# Trading API base URL
TRADING_API_BASE = "http://127.0.0.1:8600"


class TradingCommands:
    """Process trading-related natural language commands."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def close(self):
        await self.client.aclose()
    
    def extract_amount(self, text: str) -> Optional[float]:
        """Extract dollar amount from text."""
        # Patterns: $1000, $1,000, 1000 dollars, 1000 USD
        patterns = [
            r'\$([\d,]+\.?\d*)',
            r'([\d,]+\.?\d*)\s*(?:dollars?|USD|usd)',
            r'([\d,]+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.replace(',', ''))
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def extract_strategy(self, text: str) -> Optional[str]:
        """Extract strategy name from text."""
        text_lower = text.lower()
        
        strategy_map = {
            "signal shark": "signal-shark",
            "signal shark max": "signal-shark-max",
            "momentum rider": "momentum-rider",
            "steady growth": "steady-growth",
            "safe haven": "safe-haven",
        }
        
        for name, strategy_id in strategy_map.items():
            if name in text_lower:
                return strategy_id
        
        return None
    
    async def process_trading_command(self, 
                                     message: str, 
                                     user_id: str,
                                     api_key: Optional[str] = None) -> str:
        """
        Process trading-related commands and return response.
        
        Supported commands:
        - Money management: deposit, withdraw, move to idle, allocate
        - Auto-trading: enable, disable, set mode, status
        - Queries: balance, account summary, performance, trades
        """
        msg_lower = message.lower().strip()
        
        # Headers for authenticated requests
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        
        # ========== MONEY MANAGEMENT ==========
        
        # Deposit
        if "deposit" in msg_lower:
            amount = self.extract_amount(message)
            if not amount:
                return "❌ Please specify an amount to deposit. Example: 'Deposit $1000 to trading'"
            
            try:
                resp = await self.client.post(
                    f"{TRADING_API_BASE}/api/account/deposit",
                    json={"amount": amount},
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    # Note: Funds now go to idle_balance first (Aria's holding area)
                    # User needs to allocate to strategies or move to trading
                    return f"✅ Deposited ${amount:,.2f} to your account.\n" \
                           f"💰 Funds are now in your idle balance (available for allocation).\n" \
                           f"Idle Balance: ${data.get('idle_balance', data.get('new_trading_balance', 0)):,.2f}\n" \
                           f"Total Balance: ${data['total_balance']:,.2f}\n\n" \
                           f"💡 Next steps:\n" \
                           f"  • Say 'Allocate $X to [Strategy]' to invest in a strategy\n" \
                           f"  • Say 'Move $X into top performing strategy' for auto-allocation"
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Deposit failed: {error}"
            except Exception as e:
                logger.error(f"Deposit error: {e}")
                return f"❌ Error processing deposit: {str(e)}"
        
        # Withdraw
        if "withdraw" in msg_lower:
            amount = self.extract_amount(message)
            if not amount:
                return "❌ Please specify an amount to withdraw. Example: 'Withdraw $500 from trading'"
            
            try:
                resp = await self.client.post(
                    f"{TRADING_API_BASE}/api/account/withdraw",
                    json={"amount": amount},
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    return f"✅ Withdrew ${amount:,.2f} from your account.\n" \
                           f"New total balance: ${data['new_total_balance']:,.2f}"
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Withdrawal failed: {error}"
            except Exception as e:
                logger.error(f"Withdraw error: {e}")
                return f"❌ Error processing withdrawal: {str(e)}"
        
        # Move to idle
        if ("move" in msg_lower or "transfer" in msg_lower) and "idle" in msg_lower:
            amount = self.extract_amount(message)
            if not amount:
                return "❌ Please specify an amount. Example: 'Move $2000 to idle'"
            
            try:
                resp = await self.client.post(
                    f"{TRADING_API_BASE}/api/account/move-to-idle",
                    json={"amount": amount},
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    return f"✅ Moved ${amount:,.2f} to idle balance.\n" \
                           f"Idle balance: ${data['idle_balance']:,.2f}\n" \
                           f"Trading balance: ${data['trading_balance']:,.2f}"
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Failed to move funds: {error}"
            except Exception as e:
                logger.error(f"Move to idle error: {e}")
                return f"❌ Error moving funds: {str(e)}"
        
        # Allocate to strategy
        if "allocate" in msg_lower or ("assign" in msg_lower and "strategy" in msg_lower):
            amount = self.extract_amount(message)
            strategy = self.extract_strategy(message) or "signal-shark"
            
            if not amount:
                return "❌ Please specify an amount. Example: 'Allocate $5000 to Signal Shark'"
            
            try:
                resp = await self.client.post(
                    f"{TRADING_API_BASE}/api/account/allocate",
                    json={"strategy": strategy, "amount": amount},
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    return f"✅ Allocated ${amount:,.2f} to {data['strategy']}.\n" \
                           f"Idle balance: ${data['idle_balance']:,.2f}\n" \
                           f"Trading balance: ${data['trading_balance']:,.2f}"
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Allocation failed: {error}"
            except Exception as e:
                logger.error(f"Allocate error: {e}")
                return f"❌ Error allocating funds: {str(e)}"
        
        # ========== AUTO-TRADING CONTROL ==========
        
        # Enable auto-trading
        if ("enable" in msg_lower or "start" in msg_lower) and ("auto" in msg_lower or "trading" in msg_lower):
            strategy = self.extract_strategy(message) or "signal-shark"
            amount = self.extract_amount(message)
            
            if not amount:
                return "❌ Please specify capital allocation. Example: 'Enable Signal Shark auto-trading with $10000'"
            
            # Detect mode
            mode = "automatic"
            if "approval" in msg_lower or "confirm" in msg_lower:
                mode = "approval"
            
            try:
                resp = await self.client.post(
                    f"{TRADING_API_BASE}/api/auto-trade/enable",
                    json={
                        "strategy": strategy,
                        "mode": mode,
                        "capital_allocation": amount
                    },
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    return f"✅ Auto-trading enabled for {data['strategy_display']}!\n" \
                           f"Mode: {data['mode']}\n" \
                           f"Capital allocated: ${data['allocated_capital']:,.2f}\n" \
                           f"Status: {data['auto_trader_status']}"
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Failed to enable auto-trading: {error}"
            except Exception as e:
                logger.error(f"Enable auto-trading error: {e}")
                return f"❌ Error enabling auto-trading: {str(e)}"
        
        # Disable auto-trading
        if ("disable" in msg_lower or "stop" in msg_lower) and ("auto" in msg_lower or "trading" in msg_lower):
            try:
                resp = await self.client.post(
                    f"{TRADING_API_BASE}/api/auto-trade/disable",
                    headers=headers
                )
                
                if resp.status_code == 200:
                    return "✅ Auto-trading disabled."
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Failed to disable auto-trading: {error}"
            except Exception as e:
                logger.error(f"Disable auto-trading error: {e}")
                return f"❌ Error disabling auto-trading: {str(e)}"
        
        # ========== QUERIES ==========
        
        # Balance query
        if "balance" in msg_lower or ("account" in msg_lower and "summary" in msg_lower):
            try:
                resp = await self.client.get(
                    f"{TRADING_API_BASE}/api/account/balance",
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    response = "💰 **Account Balance**\n\n"
                    response += f"Total Balance: ${data['total_balance']:,.2f}\n"
                    response += f"Trading Balance: ${data['trading_balance']:,.2f}\n"
                    response += f"Idle Balance: ${data['idle_balance']:,.2f}\n"
                    
                    if data.get('allocated_to_strategies'):
                        response += "\n**Allocated to Strategies:**\n"
                        for strategy, amount in data['allocated_to_strategies'].items():
                            response += f"  • {strategy}: ${amount:,.2f}\n"
                    
                    return response
                else:
                    return "❌ Failed to fetch balance"
            except Exception as e:
                logger.error(f"Balance query error: {e}")
                return f"❌ Error fetching balance: {str(e)}"
        
        # Auto-trading status
        if ("auto" in msg_lower or "trading" in msg_lower) and "status" in msg_lower:
            try:
                resp = await self.client.get(
                    f"{TRADING_API_BASE}/api/auto-trade/status",
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    if not data.get('enabled'):
                        return "⏸️ Auto-trading is currently disabled."
                    
                    response = f"🤖 **Auto-Trading Status**\n\n"
                    response += f"Strategy: {data.get('strategy_display', data.get('strategy'))}\n"
                    response += f"Mode: {data.get('mode')}\n"
                    response += f"Capital: ${data.get('capital_allocation', 0):,.2f}\n"
                    response += f"Open Positions: {data.get('open_positions', 0)}\n"
                    response += f"Total P&L: ${data.get('total_pnl', 0):,.2f}\n"
                    response += f"Trades Opened: {data.get('trades_opened', 0)}\n"
                    response += f"Wins: {data.get('wins', 0)} | Losses: {data.get('losses', 0)}\n"
                    
                    if data.get('pending_trades', 0) > 0:
                        response += f"\n⏳ {data['pending_trades']} pending trade(s) awaiting approval"
                    
                    return response
                else:
                    return "❌ Failed to fetch auto-trading status"
            except Exception as e:
                logger.error(f"Auto-trading status error: {e}")
                return f"❌ Error fetching status: {str(e)}"
        
        # Pending trades
        if "pending" in msg_lower and "trade" in msg_lower:
            try:
                resp = await self.client.get(
                    f"{TRADING_API_BASE}/api/auto-trade/pending",
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    pending = data.get('pending_trades', [])
                    
                    if not pending:
                        return "✅ No pending trades."
                    
                    response = f"⏳ **Pending Trades ({len(pending)})**\n\n"
                    for trade in pending:
                        response += f"**{trade['symbol']} {trade['direction'].upper()}**\n"
                        response += f"  Size: ${trade['size_usd']:,.0f} @ {trade['leverage']}x\n"
                        response += f"  Entry: ${trade['entry_price']:,.2f}\n"
                        response += f"  Target: ${trade['target_price']:,.2f}\n"
                        response += f"  Stop: ${trade['stop_loss']:,.2f}\n"
                        response += f"  Confidence: {trade['confidence']:.1f}%\n"
                        response += f"  Expires: {trade['expires_at']}\n\n"
                    
                    return response
                else:
                    return "❌ Failed to fetch pending trades"
            except Exception as e:
                logger.error(f"Pending trades error: {e}")
                return f"❌ Error fetching pending trades: {str(e)}"
        
        # Strategy diagnostics - target entry prices
        if ("target" in msg_lower or "entry" in msg_lower or "waiting" in msg_lower) and "strategy" in msg_lower:
            strategy = self.extract_strategy(message) or "signal-shark-max"
            
            try:
                resp = await self.client.get(
                    f"{TRADING_API_BASE}/api/strategies/{strategy}/diagnostics",
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    strategy_info = data.get('strategy', {})
                    target_entries = data.get('target_entries', {})
                    current_signal = data.get('current_signal', {})
                    
                    response = f"🎯 **{strategy_info.get('display_name', strategy)} Target Entry Prices**\n\n"
                    
                    if target_entries:
                        current_price = target_entries.get('current_price', 0)
                        waiting_for = target_entries.get('waiting_for', 'FLAT')
                        bias_confidence = target_entries.get('bias_confidence', 0)
                        
                        response += f"Current Price: ${current_price:,.2f}\n"
                        response += f"Waiting For: **{waiting_for}** ({bias_confidence:.1f}% confidence)\n\n"
                        
                        long_target = target_entries.get('long_target')
                        short_target = target_entries.get('short_target')
                        
                        if long_target:
                            is_active = "✅ ACTIVE" if long_target.get('is_active') else ""
                            prob = long_target.get('probability', 0)
                            prob_emoji = "🔥" if prob >= 75 else "✅" if prob >= 60 else "⚠️" if prob >= 40 else "❄️"
                            response += f"🟢 **Long Target:**\n"
                            response += f"   Price: ${long_target.get('price', 0):,.2f} {is_active}\n"
                            response += f"   Probability: {prob:.1f}% {prob_emoji}\n"
                            response += f"   Distance: {long_target.get('distance_pct', 0):.2f}%\n"
                            response += f"   Score: {long_target.get('score', 0):.1f}\n"
                            response += f"   Liquidity: ${long_target.get('liquidity_usd', 0):,.0f}\n"
                            response += f"   Confidence: {long_target.get('confidence', 0):.1f}%\n\n"
                        
                        if short_target:
                            is_active = "✅ ACTIVE" if short_target.get('is_active') else ""
                            prob = short_target.get('probability', 0)
                            prob_emoji = "🔥" if prob >= 75 else "✅" if prob >= 60 else "⚠️" if prob >= 40 else "❄️"
                            response += f"🔴 **Short Target:**\n"
                            response += f"   Price: ${short_target.get('price', 0):,.2f} {is_active}\n"
                            response += f"   Probability: {prob:.1f}% {prob_emoji}\n"
                            response += f"   Distance: {short_target.get('distance_pct', 0):.2f}%\n"
                            response += f"   Score: {short_target.get('score', 0):.1f}\n"
                            response += f"   Liquidity: ${short_target.get('liquidity_usd', 0):,.0f}\n"
                            response += f"   Confidence: {short_target.get('confidence', 0):.1f}%\n\n"
                    else:
                        response += "⚠️ No target entry prices available (checking market data...)\n\n"
                    
                    # Add signal status if available
                    if current_signal and not current_signal.get('error'):
                        response += "📊 **Current Signal Status:**\n"
                        response += f"   Combined Confidence: {current_signal.get('combined_confidence', 0):.1f}% (required: {strategy_info.get('min_confidence', 0)}%)\n"
                        response += f"   Probability: {current_signal.get('probability', 0):.1f}% (required: {strategy_info.get('min_probability', 0)}%)\n"
                        action = current_signal.get('recommendation_action', 'UNKNOWN')
                        if action.startswith('ENTER'):
                            response += f"   ✅ Ready to trade: {action}\n"
                        else:
                            response += f"   ⏸️ Not ready: {action}\n"
                    
                    return response
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Failed to fetch diagnostics: {error}"
            except Exception as e:
                logger.error(f"Strategy diagnostics error: {e}")
                return f"❌ Error fetching strategy diagnostics: {str(e)}"
        
        # Available strategies
        if "strategies" in msg_lower or ("what" in msg_lower and "strategy" in msg_lower) or ("list" in msg_lower and "strategy" in msg_lower):
            try:
                resp = await self.client.get(
                    f"{TRADING_API_BASE}/api/strategies",
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    top_strategy = data.get('top_performing')
                    recommended = data.get('recommended', [])
                    
                    response = "📊 **Available Trading Strategies**\n\n"
                    
                    if top_strategy:
                        response += f"🏆 **Top Performer:** {top_strategy['display_name']}\n"
                        response += f"   Win Rate: {top_strategy['win_rate']:.1f}%\n"
                        response += f"   Total P&L: ${top_strategy['total_pnl']:,.2f}\n\n"
                    
                    response += "**All Recommended Strategies:**\n"
                    for strat in recommended:
                        response += f"  • **{strat['display_name']}** ({strat['name']})\n"
                        response += f"    Win Rate: {strat['win_rate']:.1f}%\n"
                        response += f"    Total P&L: ${strat['total_pnl']:,.2f}\n"
                        response += f"    Trades: {strat['total_trades']}\n"
                        response += f"    Leverage: {strat['leverage']}x\n\n"
                    
                    return response
                else:
                    return "❌ Failed to fetch strategies"
            except Exception as e:
                logger.error(f"Strategies query error: {e}")
                return f"❌ Error fetching strategies: {str(e)}"
        
        # Allocate to top performing strategy
        if ("top" in msg_lower or "best" in msg_lower or "highest" in msg_lower) and \
           ("performing" in msg_lower or "strategy" in msg_lower) and \
           ("allocate" in msg_lower or "move" in msg_lower or "put" in msg_lower or "invest" in msg_lower):
            
            amount = self.extract_amount(message)
            if not amount:
                return "❌ Please specify an amount. Example: 'Move $5000 into top performing strategy'"
            
            try:
                # Get strategies to find top performer
                resp = await self.client.get(
                    f"{TRADING_API_BASE}/api/strategies",
                    headers=headers
                )
                
                if resp.status_code != 200:
                    return "❌ Failed to fetch strategies"
                
                data = resp.json()
                top_strategy = data.get('top_performing')
                
                if not top_strategy:
                    return "❌ No top performing strategy found"
                
                strategy_name = top_strategy['name']
                strategy_display = top_strategy['display_name']
                
                # Allocate to top performing strategy
                resp = await self.client.post(
                    f"{TRADING_API_BASE}/api/account/allocate",
                    json={"strategy": strategy_name, "amount": amount},
                    headers=headers
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    return f"✅ Allocated ${amount:,.2f} to **{strategy_display}** (Top Performer)!\n" \
                           f"Win Rate: {top_strategy['win_rate']:.1f}%\n" \
                           f"Total P&L: ${top_strategy['total_pnl']:,.2f}\n" \
                           f"Idle Balance: ${data['idle_balance']:,.2f}\n" \
                           f"Trading Balance: ${data['trading_balance']:,.2f}"
                else:
                    error = resp.json().get("detail", "Unknown error")
                    return f"❌ Allocation failed: {error}"
            except Exception as e:
                logger.error(f"Top strategy allocation error: {e}")
                return f"❌ Error allocating to top strategy: {str(e)}"
        
        # No match found
        return None


# Singleton instance
_trading_commands: Optional[TradingCommands] = None


def get_trading_commands() -> TradingCommands:
    """Get singleton trading commands instance."""
    global _trading_commands
    if _trading_commands is None:
        _trading_commands = TradingCommands()
    return _trading_commands



