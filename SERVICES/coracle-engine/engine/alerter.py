"""
Coracle Prediction Engine - Multi-Channel Alerter
==================================================
Sends real-time trade alerts when the Sacred Gate passes.

Channels:
- Telegram messages (primary)
- Phone calls via Twilio (for high-conviction setups)
- Voice messages via Telegram
"""
import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from typing import Optional, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

import os as _os

TWILIO_ACCOUNT_SID = _os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = _os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE = _os.environ.get("TWILIO_PHONE", "")
JAMES_PHONE = _os.environ.get("JAMES_PHONE", "")


@dataclass
class AlertConfig:
    """Configuration for the alerter."""
    telegram_bot_token: str
    telegram_chat_id: str
    cooldown_minutes: int = 15  # Minimum time between alerts for same asset
    enabled: bool = True
    phone_calls_enabled: bool = True  # Enable phone calls for high-conviction
    phone_number: str = JAMES_PHONE
    min_confluence_for_call: float = 0.60  # Only call for 60%+ confluence


@dataclass
class AlertState:
    """Tracks alert state to prevent spam."""
    last_alert_time: dict = field(default_factory=dict)  # asset -> datetime
    sent_contract_ids: Set[str] = field(default_factory=set)


class CoracleAlerter:
    """Sends multi-channel alerts for valid Coracle contracts."""
    
    def __init__(self, config: AlertConfig):
        self.config = config
        self.state = AlertState()
        self.base_url = f"https://api.telegram.org/bot{config.telegram_bot_token}"
        self.twilio_client = None
        self._init_twilio()
    
    def _init_twilio(self):
        """Initialize Twilio client for phone calls."""
        try:
            from twilio.rest import Client
            self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            logger.info("📞 Twilio phone call client initialized")
        except ImportError:
            logger.warning("Twilio library not installed - phone calls disabled")
        except Exception as e:
            logger.error(f"Failed to init Twilio: {e}")
    
    def _can_alert(self, asset: str, contract_id: str) -> bool:
        """Check if we should send an alert (cooldown + dedup)."""
        if not self.config.enabled:
            return False
        
        # Already sent this contract
        if contract_id in self.state.sent_contract_ids:
            return False
        
        # Check cooldown
        last_alert = self.state.last_alert_time.get(asset)
        if last_alert:
            cooldown = timedelta(minutes=self.config.cooldown_minutes)
            if datetime.utcnow() - last_alert < cooldown:
                logger.debug(f"Cooldown active for {asset}")
                return False
        
        return True
    
    def _format_contract_alert(self, contract: dict, signals: dict) -> str:
        """Format a contract into a beautiful Telegram message."""
        direction = contract.get("direction", "UNKNOWN")
        symbol = contract.get("symbol", "???")
        entry = contract.get("entry_price", 0)
        stop_loss = contract.get("stop_loss", 0)
        take_profits = contract.get("take_profits", [])
        confluence = contract.get("confluence_score", 0)
        grade = contract.get("grade", "?")
        rr_ratio = contract.get("rr_ratio", 0)
        
        # Direction emoji
        dir_emoji = "🟢 LONG" if direction == "LONG" else "🔴 SHORT"
        
        # Grade emoji
        grade_emojis = {"A": "🏆", "B": "✨", "C": "👍", "D": "⚠️"}
        grade_emoji = grade_emojis.get(grade, "❓")
        
        # Build message
        msg = f"""
🔮 **CORACLE TRADE SIGNAL**
{'='*30}

{dir_emoji} **{symbol}**

📊 **Contract Details**
├ Entry: **${entry:,.2f}**
├ Stop Loss: **${stop_loss:,.2f}**
├ Risk: **{abs((stop_loss - entry) / entry * 100):.2f}%**
└ R:R Ratio: **{rr_ratio:.1f}:1**

🎯 **Take Profit Targets**"""
        
        for i, tp in enumerate(take_profits, 1):
            tp_price = tp.get("price", 0)
            tp_size = tp.get("position_size", 0) * 100
            tp_prob = tp.get("probability", 0) * 100
            msg += f"\n├ TP{i}: **${tp_price:,.2f}** ({tp_size:.0f}% @ {tp_prob:.0f}% prob)"
        
        msg += f"""

📈 **Signal Confluence**
├ Score: **{confluence*100:.0f}%**
└ Grade: {grade_emoji} **{grade}**

🐋 **Key Signals**"""
        
        # Add key signal info
        key_signals = ["bai", "cvd", "wadi", "fgi", "ls_ratio"]
        for sig_name in key_signals:
            sig = signals.get(sig_name)
            if sig:
                signal_val = sig.get("signal", "N/A")
                strength = sig.get("strength", 0)
                msg += f"\n├ {sig.get('name', sig_name)}: {signal_val} ({strength:.0f}%)"
        
        msg += f"""

⏰ Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

⚠️ _This is not financial advice. Trade at your own risk._
"""
        return msg
    
    async def send_alert(self, contract: dict, signals: dict) -> bool:
        """Send a multi-channel alert for a contract."""
        contract_id = contract.get("contract_id", "unknown")
        symbol = contract.get("symbol", "???")
        
        if not self._can_alert(symbol, contract_id):
            return False
        
        message = self._format_contract_alert(contract, signals)
        confluence = contract.get("confluence_score", 0)
        
        # 1. Always send Telegram message
        telegram_sent = await self._send_telegram_message(message)
        
        # 2. For high-conviction setups, also make a phone call
        if (self.config.phone_calls_enabled and 
            confluence >= self.config.min_confluence_for_call):
            await self._make_phone_call(contract, signals)
        
        if telegram_sent:
            self.state.sent_contract_ids.add(contract_id)
            self.state.last_alert_time[symbol] = datetime.utcnow()
            logger.info(f"✅ Alert sent for {symbol} contract {contract_id}")
            
        return telegram_sent
    
    async def _send_telegram_message(self, message: str) -> bool:
        """Send a Telegram text message."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": self.config.telegram_chat_id,
                        "text": message,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False
    
    async def _make_phone_call(self, contract: dict, signals: dict) -> bool:
        """Make a phone call to alert about a high-conviction trade setup.
        
        Designed to leave a detailed voicemail if not answered, with all
        information needed to execute the trade manually.
        """
        if not self.twilio_client:
            logger.warning("Twilio not available - skipping phone call")
            return False
        
        try:
            symbol = contract.get("symbol", "unknown")
            direction = contract.get("direction", "LONG")
            entry = contract.get("entry_price", 0)
            confluence = contract.get("confluence_score", 0)
            grade = contract.get("grade", "B")
            stop_loss = contract.get("stop_loss", 0)
            take_profits = contract.get("take_profits", [])
            rr_ratio = contract.get("rr_ratio", 0)
            
            # Calculate risk percentage
            risk_pct = abs((stop_loss - entry) / entry * 100) if entry > 0 else 0
            
            # Format entry price for speech (handle decimals for small coins)
            if entry < 10:
                entry_speech = f"{entry:.4f}"
            elif entry < 100:
                entry_speech = f"{entry:.2f}"
            else:
                entry_speech = f"{entry:,.0f}"
            
            # Format stop loss for speech
            if stop_loss < 10:
                sl_speech = f"{stop_loss:.4f}"
            elif stop_loss < 100:
                sl_speech = f"{stop_loss:.2f}"
            else:
                sl_speech = f"{stop_loss:,.0f}"
            
            # Build take profit speech
            tp_speech = ""
            for i, tp in enumerate(take_profits[:3], 1):
                tp_price = tp.get("price", 0)
                tp_size = tp.get("position_size", 0) * 100
                if tp_price < 10:
                    tp_price_speech = f"{tp_price:.4f}"
                elif tp_price < 100:
                    tp_price_speech = f"{tp_price:.2f}"
                else:
                    tp_price_speech = f"{tp_price:,.0f}"
                tp_speech += f"Take profit {i}: {tp_price_speech} dollars, close {tp_size:.0f}% of position. "
            
            # Get key signal summary
            bai_signal = signals.get("bai", {}).get("signal", "unknown")
            cvd_signal = signals.get("cvd", {}).get("signal", "unknown")
            fgi_value = signals.get("fgi", {}).get("value", 50)
            
            # Build comprehensive TwiML for voicemail
            twiml = f"""
            <Response>
                <Say voice="alice">
                    Coracle Trading Alert. This is an automated message with a high probability trade setup.
                </Say>
                <Pause length="1"/>
                
                <Say voice="alice">
                    Asset: {symbol}.
                    Direction: {direction}.
                    Confluence score: {confluence*100:.0f} percent.
                    Grade: {grade}.
                </Say>
                <Pause length="1"/>
                
                <Say voice="alice">
                    Entry price: {entry_speech} dollars.
                </Say>
                <Pause length="0.5"/>
                
                <Say voice="alice">
                    Stop loss: {sl_speech} dollars.
                    Risk: {risk_pct:.1f} percent.
                    Risk to reward ratio: {rr_ratio:.1f} to 1.
                </Say>
                <Pause length="1"/>
                
                <Say voice="alice">
                    {tp_speech}
                </Say>
                <Pause length="1"/>
                
                <Say voice="alice">
                    Key signals: Orderbook imbalance is {bai_signal}. 
                    Volume delta is {cvd_signal}. 
                    Fear and greed index is {fgi_value}.
                </Say>
                <Pause length="1"/>
                
                <Say voice="alice">
                    Repeating: {symbol} {direction} at {entry_speech}. 
                    Stop at {sl_speech}. 
                    {confluence*100:.0f} percent confluence.
                </Say>
                <Pause length="1"/>
                
                <Say voice="alice">
                    Full details are in your Telegram. This message will not repeat. Act accordingly.
                </Say>
            </Response>
            """
            
            # Make the call (will go to voicemail if not answered)
            call = self.twilio_client.calls.create(
                twiml=twiml,
                to=self.config.phone_number,
                from_=TWILIO_PHONE,
                # Machine detection settings for voicemail
                machine_detection="Enable",
                machine_detection_timeout=5
            )
            
            logger.info(f"📞 Phone call initiated: {call.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Phone call failed: {e}")
            return False
    
    async def call_now(self, message: str) -> bool:
        """Make an immediate phone call with a custom message."""
        if not self.twilio_client:
            return False
        
        try:
            twiml = f"""
            <Response>
                <Say voice="alice">
                    {message}
                </Say>
            </Response>
            """
            
            call = self.twilio_client.calls.create(
                twiml=twiml,
                to=self.config.phone_number,
                from_=TWILIO_PHONE,
                machine_detection="Enable",
                machine_detection_timeout=5
            )
            
            logger.info(f"📞 Custom call initiated: {call.sid}")
            return True
        except Exception as e:
            logger.error(f"Custom call failed: {e}")
            return False
    
    async def call_with_trade_details(
        self, 
        symbol: str, 
        direction: str, 
        entry: float, 
        stop_loss: float, 
        take_profit: float,
        confluence: float = 0.70
    ) -> bool:
        """
        Make a phone call with specific trade details.
        Useful for testing or manual alerts.
        """
        if not self.twilio_client:
            return False
        
        try:
            risk_pct = abs((stop_loss - entry) / entry * 100) if entry > 0 else 0
            reward_pct = abs((take_profit - entry) / entry * 100) if entry > 0 else 0
            rr_ratio = reward_pct / risk_pct if risk_pct > 0 else 0
            
            # Format prices
            def fmt(p):
                if p < 10: return f"{p:.4f}"
                elif p < 100: return f"{p:.2f}"
                else: return f"{p:,.0f}"
            
            twiml = f"""
            <Response>
                <Say voice="alice">
                    Coracle Trading Alert.
                </Say>
                <Pause length="1"/>
                <Say voice="alice">
                    {symbol} {direction} setup detected.
                    Confluence: {confluence*100:.0f} percent.
                </Say>
                <Pause length="1"/>
                <Say voice="alice">
                    Entry: {fmt(entry)} dollars.
                    Stop loss: {fmt(stop_loss)} dollars. Risk: {risk_pct:.1f} percent.
                    Take profit: {fmt(take_profit)} dollars. Reward: {reward_pct:.1f} percent.
                    Risk reward ratio: {rr_ratio:.1f} to 1.
                </Say>
                <Pause length="1"/>
                <Say voice="alice">
                    Repeating: {symbol} {direction} at {fmt(entry)}. Stop at {fmt(stop_loss)}. Target {fmt(take_profit)}.
                </Say>
                <Pause length="1"/>
                <Say voice="alice">
                    Check Telegram for full analysis. Good luck.
                </Say>
            </Response>
            """
            
            call = self.twilio_client.calls.create(
                twiml=twiml,
                to=self.config.phone_number,
                from_=TWILIO_PHONE,
                machine_detection="Enable",
                machine_detection_timeout=5
            )
            
            logger.info(f"📞 Trade detail call initiated: {call.sid}")
            return True
        except Exception as e:
            logger.error(f"Trade call failed: {e}")
            return False
    
    async def send_startup_message(self) -> bool:
        """Send a startup confirmation message."""
        msg = """
🔮 **CORACLE ALERTER ONLINE**

I'm now monitoring for high-probability trading setups.

**Tracked Assets:** BTC, ETH, SOL, XRP
**Alert Cooldown:** 15 minutes per asset

When the Sacred Three-Key Gate passes, you'll receive:
• Entry price
• Stop loss
• Take profit targets
• Confluence score
• Signal breakdown

_Stay sharp. Trade smart._
"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.base_url}/sendMessage",
                    json={
                        "chat_id": self.config.telegram_chat_id,
                        "text": msg,
                        "parse_mode": "Markdown"
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending startup message: {e}")
            return False


# Singleton instance (configured at runtime)
_alerter: Optional[CoracleAlerter] = None


def get_alerter() -> Optional[CoracleAlerter]:
    """Get the configured alerter instance."""
    return _alerter


def configure_alerter(bot_token: str, chat_id: str, enabled: bool = True) -> CoracleAlerter:
    """Configure and return the alerter instance."""
    global _alerter
    config = AlertConfig(
        telegram_bot_token=bot_token,
        telegram_chat_id=chat_id,
        enabled=enabled
    )
    _alerter = CoracleAlerter(config)
    return _alerter

