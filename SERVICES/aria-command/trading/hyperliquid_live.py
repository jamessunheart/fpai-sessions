#!/usr/bin/env python3
"""
🔴 HYPERLIQUID LIVE CONNECTION
==============================

Direct connection to Hyperliquid for live trading.
Uses stored credentials to fetch positions and execute trades.
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("aria.trading.hyperliquid")

# Credentials file
CREDENTIALS_FILE = Path("/opt/fpai/hyperliquid_credentials.json")
BACKUP_CREDENTIALS = Path("/opt/fpai/services/whaletrack-live/data/.credentials.json")


def _load_credentials() -> Optional[Dict]:
    """Load Hyperliquid credentials."""
    for path in [CREDENTIALS_FILE, BACKUP_CREDENTIALS]:
        if path.exists():
            try:
                with open(path) as f:
                    creds = json.load(f)
                    if creds.get("api_secret") and creds.get("main_account"):
                        return creds
            except Exception as e:
                logger.error(f"Failed to load credentials from {path}: {e}")
    return None


class HyperliquidLive:
    """
    Live Hyperliquid connection for trading.
    """
    
    def __init__(self):
        self._creds = _load_credentials()
        self._info = None
        self._exchange = None
        self._account = None
        
        if self._creds:
            self._connect()
    
    def _connect(self):
        """Initialize Hyperliquid connection."""
        try:
            from hyperliquid.info import Info
            from hyperliquid.exchange import Exchange
            from hyperliquid.utils import constants
            from eth_account import Account
            
            self._info = Info(constants.MAINNET_API_URL, skip_ws=True)
            
            if self._creds.get("api_secret"):
                self._account = Account.from_key(self._creds["api_secret"])
                self._exchange = Exchange(self._account, constants.MAINNET_API_URL)
                logger.info(f"✅ Hyperliquid connected: {self._account.address[:10]}...")
            
        except Exception as e:
            logger.error(f"Failed to connect to Hyperliquid: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._info is not None and self._creds is not None
    
    @property
    def main_account(self) -> Optional[str]:
        """Get main account address."""
        return self._creds.get("main_account") if self._creds else None
    
    def get_account_state(self) -> Dict[str, Any]:
        """Get current account state."""
        if not self.is_connected:
            return {"error": "Not connected"}
        
        try:
            state = self._info.user_state(self.main_account)
            
            margin = state.get("marginSummary", {})
            
            return {
                "connected": True,
                "account_value": float(margin.get("accountValue", 0)),
                "withdrawable": float(state.get("withdrawable", 0)),
                "total_margin": float(margin.get("totalMarginUsed", 0)),
                "total_pnl": float(margin.get("totalRawUsd", 0)) - float(margin.get("accountValue", 0)),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e), "connected": False}
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions."""
        if not self.is_connected:
            return []
        
        try:
            state = self._info.user_state(self.main_account)
            positions = state.get("assetPositions", [])
            
            result = []
            for pos in positions:
                p = pos.get("position", {})
                size = float(p.get("szi", 0))
                
                if size == 0:
                    continue
                
                coin = p.get("coin", "???")
                entry = float(p.get("entryPx", 0))
                mark = float(p.get("markPx", 0)) if p.get("markPx") else entry
                upnl = float(p.get("unrealizedPnl", 0))
                leverage = float(p.get("leverage", {}).get("value", 1))
                liq = float(p.get("liquidationPx", 0)) if p.get("liquidationPx") else 0
                
                # Calculate PnL percent
                position_value = abs(size) * entry
                pnl_pct = (upnl / position_value * 100) if position_value > 0 else 0
                
                result.append({
                    "symbol": coin,
                    "side": "long" if size > 0 else "short",
                    "size": abs(size),
                    "size_usd": abs(size) * mark,
                    "entry_price": entry,
                    "mark_price": mark,
                    "unrealized_pnl": upnl,
                    "pnl_percent": pnl_pct,
                    "leverage": leverage,
                    "liquidation_price": liq
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def get_balance(self) -> float:
        """Get account balance."""
        state = self.get_account_state()
        return state.get("account_value", 0)
    
    async def place_order(
        self,
        symbol: str,
        side: str,  # "buy" or "sell"
        size: float,
        price: Optional[float] = None,  # None for market order
        reduce_only: bool = False
    ) -> Dict:
        """
        Place an order on Hyperliquid.
        
        Args:
            symbol: Trading pair (e.g., "SOL", "BTC")
            side: "buy" or "sell"
            size: Position size in units
            price: Limit price (None for market)
            reduce_only: Only reduce position
        
        Returns:
            Order result
        """
        if not self._exchange:
            return {"success": False, "error": "Exchange not connected"}
        
        try:
            is_buy = side.lower() == "buy"
            
            if price is None:
                # Market order
                result = self._exchange.market_open(
                    coin=symbol,
                    is_buy=is_buy,
                    sz=size,
                    reduce_only=reduce_only
                )
            else:
                # Limit order
                result = self._exchange.order(
                    coin=symbol,
                    is_buy=is_buy,
                    sz=size,
                    limit_px=price,
                    reduce_only=reduce_only
                )
            
            if result.get("status") == "ok":
                return {
                    "success": True,
                    "order_id": result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting", {}).get("oid"),
                    "filled": result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("filled"),
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "error": result.get("response", str(result))
                }
                
        except Exception as e:
            logger.error(f"Order failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def close_position(self, symbol: str) -> Dict:
        """Close a position."""
        positions = self.get_positions()
        pos = next((p for p in positions if p["symbol"].upper() == symbol.upper()), None)
        
        if not pos:
            return {"success": False, "error": f"No position in {symbol}"}
        
        # Close by opening opposite
        side = "sell" if pos["side"] == "long" else "buy"
        
        return await self.place_order(
            symbol=symbol,
            side=side,
            size=pos["size"],
            reduce_only=True
        )
    
    async def close_all_positions(self) -> Dict:
        """Close all positions (emergency stop)."""
        positions = self.get_positions()
        
        if not positions:
            return {"success": True, "message": "No positions to close"}
        
        results = []
        for pos in positions:
            result = await self.close_position(pos["symbol"])
            results.append({
                "symbol": pos["symbol"],
                "result": result
            })
        
        return {
            "success": all(r["result"].get("success") for r in results),
            "closed": len([r for r in results if r["result"].get("success")]),
            "results": results
        }
    
    def format_status(self) -> str:
        """Format current status for Aria."""
        if not self.is_connected:
            return "🔴 **Hyperliquid Not Connected**"
        
        state = self.get_account_state()
        positions = self.get_positions()
        
        if state.get("error"):
            return f"🔴 **Error:** {state.get('error')}"
        
        lines = ["🟢 **HYPERLIQUID LIVE**\n"]
        lines.append(f"💰 Account Value: **${state.get('account_value', 0):,.2f}**")
        lines.append(f"💵 Withdrawable: **${state.get('withdrawable', 0):,.2f}**")
        
        if positions:
            lines.append(f"\n**Open Positions ({len(positions)}):**")
            total_upnl = 0
            for pos in positions:
                emoji = "📈" if pos["unrealized_pnl"] >= 0 else "📉"
                side_emoji = "🟢" if pos["side"] == "long" else "🔴"
                lines.append(
                    f"{side_emoji} **{pos['symbol']}** {pos['side'].upper()} "
                    f"{pos['size']:.4f} @ ${pos['entry_price']:,.2f}"
                )
                lines.append(
                    f"   {emoji} uPnL: **${pos['unrealized_pnl']:+,.2f}** ({pos['pnl_percent']:+.2f}%)"
                )
                total_upnl += pos["unrealized_pnl"]
            
            lines.append(f"\n**Total uPnL: ${total_upnl:+,.2f}**")
        else:
            lines.append("\n📊 No open positions (flat)")
        
        return "\n".join(lines)


# Singleton
_hyperliquid: Optional[HyperliquidLive] = None


def get_hyperliquid() -> HyperliquidLive:
    """Get or create global Hyperliquid connection."""
    global _hyperliquid
    if _hyperliquid is None:
        _hyperliquid = HyperliquidLive()
    return _hyperliquid


async def get_live_status() -> str:
    """Get formatted live status."""
    hl = get_hyperliquid()
    return hl.format_status()


async def get_live_positions() -> List[Dict]:
    """Get live positions."""
    hl = get_hyperliquid()
    return hl.get_positions()


async def get_live_balance() -> float:
    """Get live balance."""
    hl = get_hyperliquid()
    return hl.get_balance()









