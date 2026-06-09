#!/usr/bin/env python3
"""
🔥 ARIA LIVE TRADING BRIDGE
============================

Connects Aria to the WhaleTrack auto-trading system.
Enables:
- Setting Hyperliquid credentials
- Starting/stopping auto-trading
- Monitoring positions and PnL
- Emergency stop
"""

import os
import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import httpx

logger = logging.getLogger("aria.trading.live_bridge")

# WhaleTrack API base - PORT 8601 is the actual trading service
WHALETRACK_URL = os.getenv("WHALETRACK_URL", "http://198.54.123.234:8601")

# Default user for James (steward)
STEWARD_USER_ID = "steward_james"

# Flag to track if WhaleTrack is using the new or old API
_api_version = None  # Will be detected on first call


class LiveTradingBridge:
    """
    Bridge between Aria and the WhaleTrack auto-trading system.
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._auth_token: Optional[str] = None
    
    async def close(self):
        await self.http.aclose()
    
    def _headers(self) -> Dict[str, str]:
        """Get auth headers."""
        headers = {"Content-Type": "application/json"}
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers
    
    async def login_steward(self) -> bool:
        """Login as steward to get auth token."""
        try:
            response = await self.http.post(
                f"{WHALETRACK_URL}/api/auth/login",
                json={
                    "email": "steward@fullpotential.ai",
                    "password": os.getenv("STEWARD_PASSWORD", "steward_temp_2024")
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self._auth_token = data.get("token") or data.get("access_token")
                logger.info("✅ Logged in as steward")
                return True
            else:
                logger.error(f"Login failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    # ========================================================================
    # CREDENTIALS MANAGEMENT
    # ========================================================================
    
    async def set_hyperliquid_credentials(
        self,
        api_secret: str,
        main_account: str
    ) -> Dict[str, Any]:
        """
        Set Hyperliquid API credentials for live trading.
        
        Args:
            api_secret: Private key for signing trades
            main_account: Main Hyperliquid wallet address
        
        Returns:
            Connection status
        """
        try:
            response = await self.http.post(
                f"{WHALETRACK_URL}/api/live/credentials",
                headers=self._headers(),
                json={
                    "api_secret": api_secret,
                    "main_account": main_account
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "connected": data.get("connected", False),
                    "balance": data.get("balance", 0),
                    "message": "Hyperliquid credentials set successfully"
                }
            else:
                error = response.json().get("detail", response.text)
                return {
                    "success": False,
                    "message": f"Failed to set credentials: {error}"
                }
        except Exception as e:
            logger.error(f"Set credentials error: {e}")
            return {"success": False, "message": str(e)}
    
    async def get_live_status(self) -> Dict[str, Any]:
        """Get current live trading status from WhaleTrack."""
        try:
            # Use the health endpoint which includes trading status
            response = await self.http.get(f"{WHALETRACK_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                # Parse health response for trading info
                adapter_info = data.get("adapter", {})
                return {
                    "connected": data.get("adapter_connected", False),
                    "mode": data.get("mode", "paper"),
                    "trading_enabled": data.get("trading_enabled", False),
                    "balance": adapter_info.get("balance", 0),
                    "authenticated": adapter_info.get("authenticated", False),
                    "btc_price": adapter_info.get("btc_price", 0),
                    "service": data.get("service", "unknown"),
                    "timestamp": data.get("timestamp")
                }
            else:
                return {
                    "connected": False,
                    "mode": "unknown",
                    "error": f"Health check failed: {response.status_code}"
                }
        except Exception as e:
            logger.error(f"Get status error: {e}")
            return {"connected": False, "error": str(e)}
    
    # ========================================================================
    # AUTO-TRADING CONTROL
    # ========================================================================
    
    async def enable_auto_trading(
        self,
        strategy: str = "signal-shark",
        capital: float = 1000.0,
        mode: str = "automatic"
    ) -> Dict[str, Any]:
        """
        Enable auto-trading with specified strategy.
        
        Args:
            strategy: Strategy name (signal-shark, signal-shark-max, etc.)
            capital: Capital allocation in USD
            mode: 'automatic' or 'approval'
        
        Returns:
            Status of auto-trading activation
        """
        try:
            # Enable via WhaleTrack API
            response = await self.http.post(
                f"{WHALETRACK_URL}/api/auto-trade/users/{STEWARD_USER_ID}/enable",
                headers=self._headers(),
                json={
                    "strategy_name": strategy,
                    "mode": mode,
                    "capital_allocation": capital
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "strategy": strategy,
                    "capital": capital,
                    "mode": mode,
                    "message": f"Auto-trading enabled with {strategy}",
                    "details": data
                }
            else:
                error = response.json().get("detail", response.text)
                return {
                    "success": False,
                    "message": f"Failed to enable auto-trading: {error}"
                }
        except Exception as e:
            logger.error(f"Enable auto-trading error: {e}")
            return {"success": False, "message": str(e)}
    
    async def disable_auto_trading(self) -> Dict[str, Any]:
        """Stop auto-trading."""
        try:
            response = await self.http.post(
                f"{WHALETRACK_URL}/api/auto-trade/users/{STEWARD_USER_ID}/disable",
                headers=self._headers()
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "Auto-trading disabled"
                }
            else:
                return {
                    "success": False,
                    "message": response.json().get("detail", response.text)
                }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    async def get_auto_trading_status(self) -> Dict[str, Any]:
        """Get current auto-trading status."""
        try:
            response = await self.http.get(
                f"{WHALETRACK_URL}/api/auto-trade/users/{STEWARD_USER_ID}/status",
                headers=self._headers()
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {
                    "running": False,
                    "message": "Auto-trading not configured"
                }
            else:
                return {"error": response.text}
        except Exception as e:
            return {"error": str(e)}
    
    # ========================================================================
    # POSITION MONITORING
    # ========================================================================
    
    async def get_positions(self) -> List[Dict]:
        """Get all open positions from WhaleTrack."""
        try:
            # Use the correct endpoint for WhaleTrack Live
            response = await self.http.get(
                f"{WHALETRACK_URL}/api/positions",
                headers=self._headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                # Handle both list and dict responses
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return data.get("positions", [])
                return []
            else:
                logger.debug(f"Positions endpoint returned {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Get positions error: {e}")
            return []
    
    async def get_live_pnl(self) -> Dict[str, Any]:
        """Get real-time PnL summary."""
        try:
            # Get positions
            positions = await self.get_positions()
            
            # Get live status for balance
            status = await self.get_live_status()
            
            total_pnl = sum(float(p.get("pnl", 0)) for p in positions)
            total_pnl_pct = sum(float(p.get("pnl_percent", 0)) for p in positions)
            
            return {
                "positions": len(positions),
                "total_pnl": total_pnl,
                "total_pnl_percent": total_pnl_pct,
                "balance": status.get("balance", 0),
                "equity": status.get("equity", 0),
                "connected": status.get("connected", False)
            }
        except Exception as e:
            return {"error": str(e)}
    
    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Close a specific position on WhaleTrack."""
        try:
            # Use the correct endpoint: POST /api/close/{symbol}
            response = await self.http.post(
                f"{WHALETRACK_URL}/api/close/{symbol.upper()}",
                headers=self._headers()
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": f"Closed {symbol} position",
                    "details": response.json()
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "message": f"No open position for {symbol}"
                }
            else:
                return {
                    "success": False,
                    "message": response.json().get("detail", response.text)
                }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    async def emergency_stop(self) -> Dict[str, Any]:
        """Emergency: Close all positions and stop trading."""
        try:
            # Use the correct endpoint: POST /api/emergency-stop
            response = await self.http.post(
                f"{WHALETRACK_URL}/api/emergency-stop",
                headers=self._headers()
            )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "details": response.json(),
                    "message": "🛑 EMERGENCY STOP COMPLETE"
                }
            else:
                # Try close-all as fallback
                close_response = await self.http.post(
                    f"{WHALETRACK_URL}/api/close-all",
                    headers=self._headers()
                )
                
                return {
                    "success": close_response.status_code == 200,
                    "details": close_response.json() if close_response.status_code == 200 else {},
                    "message": "🛑 EMERGENCY STOP ATTEMPTED"
                }
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    # ========================================================================
    # SIGNAL MONITORING
    # ========================================================================
    
    async def get_current_signals(self) -> Dict[str, Any]:
        """
        Get current trading signals.
        
        Note: WhaleTrack Live service doesn't have a signals endpoint.
        Signals come from the internal auto-trader or external analysis.
        This returns stats as a proxy for market activity.
        """
        try:
            # Get stats as a proxy for signal activity
            response = await self.http.get(
                f"{WHALETRACK_URL}/api/stats",
                headers=self._headers()
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "source": "whaletrack-stats",
                    "stats": data,
                    "note": "Full signals require internal auto-trader"
                }
            else:
                logger.debug(f"Stats endpoint returned {response.status_code}")
                return {"note": "Signals endpoint not available on this service"}
        except Exception as e:
            return {"error": str(e)}
    
    async def check_for_opportunities(self) -> List[Dict]:
        """Check for current trading opportunities."""
        signals = await self.get_current_signals()
        
        opportunities = []
        for symbol, data in signals.items():
            if isinstance(data, dict):
                action = data.get("recommended_action", "WAIT")
                if action in ["LONG", "SHORT"]:
                    opportunities.append({
                        "symbol": symbol,
                        "action": action,
                        "price": data.get("price"),
                        "target": data.get("primary_target"),
                        "stop": data.get("stop_loss"),
                        "confidence": data.get("clarity_score"),
                        "rr": data.get("risk_reward")
                    })
        
        return opportunities
    
    # ========================================================================
    # PERFORMANCE ANALYTICS
    # ========================================================================
    
    async def get_performance(self) -> Dict[str, Any]:
        """Get trading performance metrics."""
        try:
            # Use stats endpoint for performance data
            response = await self.http.get(
                f"{WHALETRACK_URL}/api/stats",
                headers=self._headers()
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.debug(f"Stats endpoint returned {response.status_code}")
                return {"error": "Performance data not available"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_trade_history(self, limit: int = 10) -> List[Dict]:
        """Get recent trade history."""
        try:
            # Use history endpoint
            response = await self.http.get(
                f"{WHALETRACK_URL}/api/history",
                headers=self._headers(),
                params={"limit": limit}
            )
            
            if response.status_code == 200:
                data = response.json()
                # Handle both list and dict responses
                if isinstance(data, list):
                    return data[:limit]
                elif isinstance(data, dict):
                    return data.get("trades", data.get("history", []))[:limit]
                return []
            else:
                return []
        except Exception as e:
            logger.error(f"Get history error: {e}")
            return []


# ============================================================================
# SINGLETON
# ============================================================================

_bridge: Optional[LiveTradingBridge] = None


def get_live_trading_bridge() -> LiveTradingBridge:
    """Get or create global live trading bridge."""
    global _bridge
    if _bridge is None:
        _bridge = LiveTradingBridge()
    return _bridge


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def get_trading_status() -> Dict[str, Any]:
    """Get complete trading status for Aria."""
    bridge = get_live_trading_bridge()
    
    live_status = await bridge.get_live_status()
    auto_status = await bridge.get_auto_trading_status()
    positions = await bridge.get_positions()
    signals = await bridge.get_current_signals()
    
    # Find actionable signals
    opportunities = []
    for symbol, data in signals.items():
        if isinstance(data, dict) and data.get("recommended_action") in ["LONG", "SHORT"]:
            opportunities.append({
                "symbol": symbol.replace("/USDT", ""),
                "action": data.get("recommended_action"),
                "confidence": data.get("clarity_score"),
                "target": data.get("primary_target"),
                "rr": data.get("risk_reward")
            })
    
    return {
        "live_connected": live_status.get("connected", False),
        "balance": live_status.get("balance", 0),
        "mode": live_status.get("mode", "paper"),
        "auto_trading": {
            "running": auto_status.get("running", False),
            "strategy": auto_status.get("strategy_name"),
            "mode": auto_status.get("mode")
        },
        "positions": positions,
        "opportunities": opportunities,
        "timestamp": datetime.now().isoformat()
    }


async def enable_signal_shark(capital: float = 1000.0, mode: str = "automatic") -> Dict[str, Any]:
    """Quick way to enable Signal Shark auto-trading."""
    bridge = get_live_trading_bridge()
    return await bridge.enable_auto_trading("signal-shark", capital, mode)


async def stop_trading() -> Dict[str, Any]:
    """Quick way to stop all trading."""
    bridge = get_live_trading_bridge()
    return await bridge.emergency_stop()

