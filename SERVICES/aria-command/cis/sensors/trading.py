#!/usr/bin/env python3
"""
Trading Signal Sensor
=====================
Senses state from trading patterns without explicit input.

Signals:
- Unusual hours trading = stress
- Rapid trades = overwhelm
- Big losses = strain
- Long flat periods = calm or stuck
- Win streaks = flow state
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger("cis.sensors.trading")

@dataclass
class TradingSignal:
    state: str  # calm, busy, overloaded, stuck
    intensity: int  # 1-5
    confidence: str  # low, medium, high
    signals: Dict  # what triggered the inference
    source: str = "trading"


class TradingSensor:
    """Senses state from Hyperliquid trading patterns."""
    
    def __init__(self):
        self.creds_path = "/opt/fpai/hyperliquid_credentials.json"
        self._load_credentials()
    
    def _load_credentials(self):
        try:
            with open(self.creds_path) as f:
                creds = json.load(f)
                self.account = creds.get("main_account")
        except Exception as e:
            logger.warning(f"Could not load trading credentials: {e}")
            self.account = None
    
    def _get_account_state(self) -> Optional[Dict]:
        """Get current account state from Hyperliquid."""
        if not self.account:
            return None
        
        try:
            import requests
            r = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "clearinghouseState", "user": self.account},
                timeout=10
            )
            return r.json()
        except Exception as e:
            logger.error(f"Failed to get account state: {e}")
            return None
    
    def _get_recent_fills(self, hours: int = 24) -> List[Dict]:
        """Get recent trade fills."""
        if not self.account:
            return []
        
        try:
            import requests
            r = requests.post(
                "https://api.hyperliquid.xyz/info",
                json={"type": "userFills", "user": self.account},
                timeout=10
            )
            fills = r.json()
            if not isinstance(fills, list):
                return []
            
            # Filter to recent hours
            cutoff = datetime.now() - timedelta(hours=hours)
            recent = []
            for f in fills:
                try:
                    # Hyperliquid uses millisecond timestamps
                    fill_time = datetime.fromtimestamp(f.get("time", 0) / 1000)
                    if fill_time > cutoff:
                        recent.append(f)
                except:
                    continue
            
            return recent
        except Exception as e:
            logger.error(f"Failed to get fills: {e}")
            return []
    
    def sense(self) -> Optional[TradingSignal]:
        """Sense current state from trading patterns."""
        signals = {}
        
        # Get account state
        account = self._get_account_state()
        if not account:
            return None
        
        margin = account.get("marginSummary", {})
        positions = [p for p in account.get("assetPositions", []) 
                    if float(p.get("position", {}).get("szi", 0)) != 0]
        
        # Get recent fills
        fills_24h = self._get_recent_fills(24)
        fills_2h = self._get_recent_fills(2)
        
        # === Signal: Trading frequency ===
        signals["trades_2h"] = len(fills_2h)
        signals["trades_24h"] = len(fills_24h)
        
        # === Signal: PnL ===
        total_pnl = sum(float(f.get("closedPnl", 0)) for f in fills_24h)
        signals["pnl_24h"] = total_pnl
        
        # === Signal: Position count ===
        signals["open_positions"] = len(positions)
        
        # === Signal: Time of day trading ===
        now = datetime.now()
        hour = now.hour
        is_late_night = hour >= 23 or hour < 6
        signals["late_night_trading"] = is_late_night and len(fills_2h) > 0
        
        # === Signal: Loss streak ===
        recent_outcomes = [float(f.get("closedPnl", 0)) for f in fills_24h[:10]]
        loss_streak = 0
        for pnl in recent_outcomes:
            if pnl < 0:
                loss_streak += 1
            else:
                break
        signals["loss_streak"] = loss_streak
        
        # === Inference ===
        state = "calm"
        intensity = 2
        confidence = "low"
        
        # High trading frequency = busy or overloaded
        if len(fills_2h) >= 5:
            state = "overloaded"
            intensity = 4
            confidence = "medium"
        elif len(fills_2h) >= 2:
            state = "busy"
            intensity = 3
            confidence = "medium"
        
        # Loss streak = strain
        if loss_streak >= 3:
            state = "overloaded"
            intensity = max(intensity, 4)
            confidence = "high"
        elif loss_streak >= 2:
            intensity = max(intensity, 3)
        
        # Late night trading = elevated concern
        if is_late_night and len(fills_2h) > 0:
            intensity = min(5, intensity + 1)
            confidence = "medium" if confidence == "low" else confidence
        
        # No activity = calm (or could be stuck, need other signals)
        if len(fills_24h) == 0 and len(positions) == 0:
            state = "calm"
            intensity = 1
            confidence = "low"  # Could be away, not necessarily calm
        
        # Good PnL = positive state
        if total_pnl > 50:
            state = "calm" if state != "overloaded" else state
            intensity = max(1, intensity - 1)
        
        return TradingSignal(
            state=state,
            intensity=intensity,
            confidence=confidence,
            signals=signals
        )


# Singleton
_sensor: Optional[TradingSensor] = None

def get_trading_sensor() -> TradingSensor:
    global _sensor
    if _sensor is None:
        _sensor = TradingSensor()
    return _sensor

def sense_trading() -> Optional[TradingSignal]:
    """Convenience function to sense trading state."""
    return get_trading_sensor().sense()








