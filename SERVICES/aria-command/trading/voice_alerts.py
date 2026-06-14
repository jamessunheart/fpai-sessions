#!/usr/bin/env python3
"""
🔊 TRADING VOICE ALERTS
========================

Voice-based trading alerts via Aria's voice system:
- High-confidence signal announcements
- Trade execution notifications
- Position alerts (approaching target/stop)
- Daily summaries
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger("aria.trading.voice_alerts")

# Steward phone for urgent calls
STEWARD_PHONE = os.getenv("STEWARD_PHONE", "+19252397291")
STEWARD_CHAT_ID = int(os.getenv("STEWARD_CHAT_ID", "8145877081"))


class TradingVoiceAlerts:
    """
    Voice-based trading alerts using Aria's voice system.
    """
    
    def __init__(self):
        self._last_signal_voice_alert: Dict[str, datetime] = {}
        self._alert_cooldown_minutes = 30
    
    async def _send_voice_message(self, text: str, voice: str = "shimmer"):
        """Send a voice message via Telegram."""
        try:
            from telegram.utils import send_voice_message
            await send_voice_message(STEWARD_CHAT_ID, text, voice=voice)
            logger.info(f"🔊 Sent voice alert: {text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to send voice message: {e}")
            # Fallback to text
            try:
                from telegram.utils import send_message
                await send_message(STEWARD_CHAT_ID, f"🔊 {text}")
            except:
                pass
    
    async def _call_phone(self, message: str):
        """Make a phone call for urgent alerts."""
        try:
            from voice.caller import make_call
            await make_call(STEWARD_PHONE, message)
            logger.info(f"📞 Made phone call: {message[:50]}...")
        except Exception as e:
            logger.error(f"Failed to make call: {e}")
    
    async def announce_high_confidence_signal(
        self,
        symbol: str,
        action: str,
        confidence: float,
        price: float,
        target: float,
        risk_reward: float
    ):
        """
        Announce a high-confidence trading signal via voice.
        """
        # Check cooldown
        key = f"{symbol}_{action}"
        if key in self._last_signal_voice_alert:
            elapsed = (datetime.now() - self._last_signal_voice_alert[key]).total_seconds() / 60
            if elapsed < self._alert_cooldown_minutes:
                return
        
        self._last_signal_voice_alert[key] = datetime.now()
        
        direction = "long" if action == "LONG" else "short"
        gain_potential = abs(target - price) / price * 100
        
        message = (
            f"James, I've detected a high confidence trading signal. "
            f"{symbol} is showing a {direction} setup with {confidence:.0f}% confidence. "
            f"Current price is ${price:,.0f}. "
            f"Target is ${target:,.0f}, that's about {gain_potential:.1f}% potential gain "
            f"with a {risk_reward:.1f} to 1 risk reward ratio. "
            f"Would you like me to take this trade?"
        )
        
        # Use shimmer voice for trading (calm, professional)
        await self._send_voice_message(message, voice="shimmer")
    
    async def announce_trade_executed(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        entry_price: float,
        leverage: int,
        strategy: str = "Signal Shark"
    ):
        """Announce that a trade was executed."""
        message = (
            f"Trade executed. I just opened a {side} position on {symbol} "
            f"at ${entry_price:,.0f}. Position size is ${size_usd:,.0f} "
            f"with {leverage}x leverage using the {strategy} strategy."
        )
        
        await self._send_voice_message(message, voice="shimmer")
    
    async def announce_trade_closed(
        self,
        symbol: str,
        side: str,
        pnl: float,
        pnl_percent: float,
        reason: str = "target"
    ):
        """Announce that a trade was closed."""
        result = "profit" if pnl > 0 else "loss"
        amount = abs(pnl)
        
        if reason == "target":
            reason_text = "The position hit target"
        elif reason == "stop":
            reason_text = "The stop loss was triggered"
        else:
            reason_text = f"The trade was closed {reason}"
        
        message = (
            f"Position closed. {reason_text}. "
            f"The {symbol} {side} trade made a {result} of ${amount:,.2f}, "
            f"that's {abs(pnl_percent):.1f}%."
        )
        
        await self._send_voice_message(message, voice="shimmer")
    
    async def alert_approaching_target(
        self,
        symbol: str,
        current_price: float,
        target_price: float,
        pnl: float,
        distance_percent: float
    ):
        """Alert when position is approaching target."""
        message = (
            f"Heads up, your {symbol} position is approaching target. "
            f"Current price is ${current_price:,.0f}, just {distance_percent:.1f}% away from target at ${target_price:,.0f}. "
            f"You're up ${pnl:,.0f} so far."
        )
        
        await self._send_voice_message(message, voice="shimmer")
    
    async def alert_approaching_stop(
        self,
        symbol: str,
        current_price: float,
        stop_price: float,
        pnl: float,
        distance_percent: float
    ):
        """Alert when position is approaching stop loss."""
        message = (
            f"Warning! Your {symbol} position is approaching stop loss. "
            f"Current price is ${current_price:,.0f}, only {distance_percent:.1f}% from stop at ${stop_price:,.0f}. "
            f"Current loss is ${abs(pnl):,.0f}. Should I close it now or hold?"
        )
        
        # Use onyx voice for warnings (urgent)
        await self._send_voice_message(message, voice="onyx")
    
    async def emergency_alert(self, message: str):
        """Send emergency alert - voice message + phone call."""
        await self._send_voice_message(
            f"Emergency trading alert! {message}",
            voice="onyx"
        )
        
        # For true emergencies, also call
        await self._call_phone(message)
    
    async def daily_summary(
        self,
        total_pnl: float,
        trades_today: int,
        win_rate: float,
        best_trade: Optional[Dict] = None,
        worst_trade: Optional[Dict] = None
    ):
        """Deliver daily trading summary via voice."""
        result = "profit" if total_pnl > 0 else "loss" if total_pnl < 0 else "flat"
        
        if total_pnl == 0 and trades_today == 0:
            message = "No trading activity today. Markets are on standby."
        else:
            message = (
                f"Here's your trading summary for today. "
                f"You made {trades_today} trades with a total {result} of ${abs(total_pnl):,.0f}. "
                f"Win rate was {win_rate:.0f}%. "
            )
            
            if best_trade:
                message += f"Best trade was {best_trade.get('symbol', 'unknown')} with ${best_trade.get('pnl', 0):,.0f} profit. "
            
            if total_pnl > 0:
                message += "Great work today!"
            elif total_pnl < 0:
                message += "We'll get them tomorrow."
        
        # Use fable voice for summaries (storytelling)
        await self._send_voice_message(message, voice="fable")


# Singleton
_voice_alerts: Optional[TradingVoiceAlerts] = None


def get_voice_alerts() -> TradingVoiceAlerts:
    """Get or create global voice alerts instance."""
    global _voice_alerts
    if _voice_alerts is None:
        _voice_alerts = TradingVoiceAlerts()
    return _voice_alerts









