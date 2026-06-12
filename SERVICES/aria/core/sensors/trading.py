"""
TRADING SENSOR
==============

Monitors WhaleTrack Magnet for trading signals and opportunities.

Watches:
- Market regime (trending/ranging/volatile)
- Signal strength and direction
- Current positions and P&L
- Cross-asset correlations
- Position risk (stop loss proximity)
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
import httpx

from ..proactive import Signal, Priority, ActionType

logger = logging.getLogger("aria.sensors.trading")

# WhaleTrack endpoints
WHALETRACK_MAGNET_URL = os.getenv("WHALETRACK_MAGNET_URL", "http://198.54.123.234:8601")
WHALETRACK_LIVE_URL = os.getenv("WHALETRACK_LIVE_URL", "http://198.54.123.234:8600")

# Thresholds
STRONG_SIGNAL_THRESHOLD = 80  # Confidence above this = urgent
MODERATE_SIGNAL_THRESHOLD = 60
POSITION_RISK_THRESHOLD = 0.9  # 90% to stop loss = urgent


class TradingSensor:
    """
    Sensor for trading signals and opportunities.
    
    Connects to WhaleTrack Magnet and monitors:
    - Signal strength for trade opportunities
    - Position risk for open trades
    - Market regime changes
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=15.0)
        self.last_regime = None
        self.last_signal = {}
        logger.info("TradingSensor initialized")
    
    async def close(self):
        """Close HTTP client."""
        await self.http.aclose()
    
    async def sense(self) -> List[Signal]:
        """
        Sense trading signals and generate alerts.
        
        Returns list of signals detected.
        """
        signals = []
        
        # 1. Check for strong trading signals
        signal_data = await self._get_magnet_signal()
        if signal_data:
            signal = self._process_signal(signal_data)
            if signal:
                signals.append(signal)
        
        # 2. Check market regime
        regime_signal = await self._check_regime()
        if regime_signal:
            signals.append(regime_signal)
        
        # 3. Check position risk
        position_signals = await self._check_positions()
        signals.extend(position_signals)
        
        return signals
    
    async def _get_magnet_signal(self) -> Optional[Dict]:
        """Get current signal from WhaleTrack Magnet."""
        try:
            r = await self.http.get(f"{WHALETRACK_MAGNET_URL}/api/signal/current")
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warning(f"Magnet signal error: {e}")
        return None
    
    def _process_signal(self, data: Dict) -> Optional[Signal]:
        """Process a magnet signal into an alert if strong enough."""
        confidence = data.get("confidence", 0)
        direction = data.get("direction", "NEUTRAL")
        symbol = data.get("symbol", "SOL")
        
        # Skip neutral or weak signals
        if direction == "NEUTRAL" or confidence < MODERATE_SIGNAL_THRESHOLD:
            return None
        
        # Check if this is a new signal
        signal_key = f"{symbol}_{direction}"
        if signal_key == self.last_signal.get("key"):
            last_conf = self.last_signal.get("confidence", 0)
            # Only alert if confidence increased significantly
            if confidence - last_conf < 10:
                return None
        
        self.last_signal = {"key": signal_key, "confidence": confidence}
        
        # Determine priority
        if confidence >= STRONG_SIGNAL_THRESHOLD:
            priority = Priority.URGENT
            action_type = ActionType.PROPOSE
        else:
            priority = Priority.MEDIUM
            action_type = ActionType.NOTIFY
        
        # Build signal
        entry = data.get("entry", data.get("current_price", 0))
        target = data.get("target", 0)
        stop = data.get("stop_loss", 0)
        
        return Signal(
            source="trading",
            signal_type="strong_signal",
            priority=priority,
            title=f"🎯 {direction} Signal on {symbol} ({confidence}%)",
            description=self._format_signal_description(data),
            data={
                "symbol": symbol,
                "direction": direction,
                "confidence": confidence,
                "entry": entry,
                "target": target,
                "stop_loss": stop,
                "risk_reward": abs(target - entry) / abs(entry - stop) if stop and entry != stop else 0
            },
            action_type=action_type,
            suggested_action=f"Execute {direction} on {symbol} at {entry}"
        )
    
    def _format_signal_description(self, data: Dict) -> str:
        """Format signal into readable description."""
        direction = data.get("direction", "NEUTRAL")
        symbol = data.get("symbol", "SOL")
        confidence = data.get("confidence", 0)
        entry = data.get("entry", data.get("current_price", 0))
        target = data.get("target", 0)
        stop = data.get("stop_loss", 0)
        
        lines = [
            f"**{symbol}/USDT {direction}**",
            f"Confidence: {confidence}%",
            "",
            f"📍 Entry: ${entry:,.2f}" if entry else "",
            f"🎯 Target: ${target:,.2f}" if target else "",
            f"🛑 Stop: ${stop:,.2f}" if stop else "",
        ]
        
        if target and entry and stop and entry != stop:
            rr = abs(target - entry) / abs(entry - stop)
            lines.append(f"📊 Risk/Reward: {rr:.1f}:1")
        
        reasons = data.get("reasons", [])
        if reasons:
            lines.append("")
            lines.append("Why:")
            for r in reasons[:3]:
                lines.append(f"• {r}")
        
        return "\n".join(filter(None, lines))
    
    async def _check_regime(self) -> Optional[Signal]:
        """Check for market regime changes."""
        try:
            r = await self.http.get(f"{WHALETRACK_MAGNET_URL}/api/regime")
            if r.status_code == 200:
                data = r.json()
                regime = data.get("regime", "unknown")
                
                if regime != self.last_regime and self.last_regime is not None:
                    self.last_regime = regime
                    
                    regime_emoji = {
                        "trending": "📈",
                        "ranging": "↔️",
                        "volatile": "🌊",
                        "breakout": "🚀"
                    }.get(regime, "❓")
                    
                    return Signal(
                        source="trading",
                        signal_type="regime_change",
                        priority=Priority.MEDIUM,
                        title=f"{regime_emoji} Market Regime Changed to {regime.upper()}",
                        description=f"Market conditions have shifted to {regime}. Adjusting strategies accordingly.",
                        data={"old_regime": self.last_regime, "new_regime": regime},
                        action_type=ActionType.NOTIFY
                    )
                
                self.last_regime = regime
                
        except Exception as e:
            logger.warning(f"Regime check error: {e}")
        
        return None
    
    async def _check_positions(self) -> List[Signal]:
        """Check open positions for risk."""
        signals = []
        
        try:
            r = await self.http.get(f"{WHALETRACK_LIVE_URL}/api/live/positions")
            if r.status_code != 200:
                return signals
            
            positions = r.json().get("positions", [])
            
            for pos in positions:
                symbol = pos.get("symbol", "")
                entry = pos.get("entry_price", 0)
                current = pos.get("current_price", 0)
                stop = pos.get("stop_loss", 0)
                side = pos.get("side", "LONG")
                pnl_pct = pos.get("pnl_percent", 0)
                
                if not all([entry, current, stop]):
                    continue
                
                # Calculate distance to stop
                if side == "LONG":
                    dist_to_stop = (current - stop) / (entry - stop) if entry != stop else 1
                else:
                    dist_to_stop = (stop - current) / (stop - entry) if entry != stop else 1
                
                # Check if position is at risk
                if dist_to_stop < (1 - POSITION_RISK_THRESHOLD):
                    signals.append(Signal(
                        source="trading",
                        signal_type="position_risk",
                        priority=Priority.URGENT,
                        title=f"⚠️ {symbol} Position Near Stop Loss!",
                        description=f"Your {side} position is {dist_to_stop*100:.0f}% to stop loss.\n"
                                   f"Current P&L: {pnl_pct:+.1f}%",
                        data={
                            "symbol": symbol,
                            "side": side,
                            "entry": entry,
                            "current": current,
                            "stop": stop,
                            "pnl_percent": pnl_pct,
                            "distance_to_stop": dist_to_stop
                        },
                        action_type=ActionType.NOTIFY
                    ))
                
                # Check for significant P&L (positive or negative)
                if abs(pnl_pct) > 10:
                    direction = "profit" if pnl_pct > 0 else "loss"
                    emoji = "💰" if pnl_pct > 0 else "📉"
                    
                    signals.append(Signal(
                        source="trading",
                        signal_type="significant_pnl",
                        priority=Priority.MEDIUM if pnl_pct > 0 else Priority.HIGH,
                        title=f"{emoji} {symbol} at {pnl_pct:+.1f}% {direction}",
                        description=f"Your {side} on {symbol} is showing significant {direction}.",
                        data={
                            "symbol": symbol,
                            "side": side,
                            "pnl_percent": pnl_pct
                        },
                        action_type=ActionType.NOTIFY
                    ))
        
        except Exception as e:
            logger.warning(f"Position check error: {e}")
        
        return signals
    
    async def get_status(self) -> Dict:
        """Get sensor status."""
        return {
            "name": "trading",
            "last_regime": self.last_regime,
            "last_signal": self.last_signal,
            "magnet_url": WHALETRACK_MAGNET_URL,
            "live_url": WHALETRACK_LIVE_URL
        }


