#!/usr/bin/env python3
"""
📱 TRADING NOTIFICATIONS - Telegram + SMS/Voice
Real-time alerts for the Aggressive Sweep Trader
"""

import os
import requests
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger("Notifications")

# Telegram Config
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8541321124:AAEpkRWpt4jNzVFgAmsJArsHN-QcKGNcoG0")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "1759822075")

# Twilio Config (for SMS/Voice)
TWILIO_SID = os.getenv("TWILIO_SID", "")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN", "")
TWILIO_FROM = os.getenv("TWILIO_FROM", "")  # Your Twilio phone number
TWILIO_TO = os.getenv("TWILIO_TO", "")      # Your personal phone number


class TelegramNotifier:
    """Send notifications via Telegram"""
    
    def __init__(self, token: str = TELEGRAM_BOT_TOKEN, chat_id: str = TELEGRAM_CHAT_ID):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send a message to Telegram"""
        try:
            r = requests.post(
                f"{self.base_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": parse_mode
                },
                timeout=10
            )
            if r.status_code == 200:
                logger.info("Telegram sent: %s", message[:50])
                return True
            else:
                logger.error("Telegram error: %s", r.text)
                return False
        except Exception as e:
            logger.error("Telegram failed: %s", e)
            return False


class TwilioNotifier:
    """Send SMS and Voice calls via Twilio"""
    
    def __init__(self):
        self.sid = TWILIO_SID
        self.token = TWILIO_TOKEN
        self.from_number = TWILIO_FROM
        self.to_number = TWILIO_TO
        self.enabled = bool(self.sid and self.token and self.from_number and self.to_number)
    
    def send_sms(self, message: str) -> bool:
        """Send SMS message"""
        if not self.enabled:
            logger.warning("Twilio not configured")
            return False
        
        try:
            r = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json",
                auth=(self.sid, self.token),
                data={
                    "From": self.from_number,
                    "To": self.to_number,
                    "Body": message
                },
                timeout=10
            )
            if r.status_code in [200, 201]:
                logger.info("SMS sent: %s", message[:50])
                return True
            else:
                logger.error("SMS error: %s", r.text)
                return False
        except Exception as e:
            logger.error("SMS failed: %s", e)
            return False
    
    def make_call(self, message: str) -> bool:
        """Make a voice call with TTS message"""
        if not self.enabled:
            logger.warning("Twilio not configured")
            return False
        
        try:
            twiml = f'<Response><Say voice="alice">{message}</Say></Response>'
            r = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Calls.json",
                auth=(self.sid, self.token),
                data={
                    "From": self.from_number,
                    "To": self.to_number,
                    "Twiml": twiml
                },
                timeout=10
            )
            if r.status_code in [200, 201]:
                logger.info("Call initiated: %s", message[:50])
                return True
            else:
                logger.error("Call error: %s", r.text)
                return False
        except Exception as e:
            logger.error("Call failed: %s", e)
            return False


class TradingNotifications:
    """Unified notification system for trading alerts"""
    
    def __init__(self):
        self.telegram = TelegramNotifier()
        self.twilio = TwilioNotifier()
    
    def balance_update(self, equity: float, pnl: float, positions: list):
        """Send balance update"""
        now = datetime.now().strftime("%H:%M")
        sign = "+" if pnl > 0 else ""
        emoji = "📈" if pnl > 0 else "📉" if pnl < 0 else "➖"
        
        msg = f"""
{emoji} <b>BALANCE UPDATE</b> ({now})

💰 <b>Equity:</b> ${equity:,.2f}
{sign}${pnl:.2f} unrealized

"""
        if positions:
            msg += "<b>Positions:</b>\n"
            for p in positions:
                psign = "+" if p["pnl"] > 0 else ""
                msg += f"• {p['coin']} {p['dir']}: {psign}${p['pnl']:.2f}\n"
        else:
            msg += "No open positions"
        
        self.telegram.send(msg)
    
    def new_trade_signal(self, signal: dict):
        """Alert when a new trade signal is detected"""
        msg = f"""
🚨 <b>SWEEP DETECTED!</b>

<b>{signal['sym']}</b> {signal['type']}
Direction: <b>{signal['dir']}</b>

Entry: ${signal['entry']:,.2f}
Stop: ${signal['stop']:,.2f}
Target: ${signal['target']:,.2f}

R/R: {signal['rr']:.1f}:1
Confidence: {signal['conf']:.0f}%
Leverage: {signal['leverage']}x

<b>Potential:</b>
✅ Win: +{signal['potential_gain']:.0f}% of account
❌ Loss: -{signal['potential_loss']:.0f}% of account
"""
        self.telegram.send(msg)
        
        # SMS for new signals
        if self.twilio.enabled:
            sms = f"SWEEP: {signal['sym']} {signal['dir']} @ ${signal['entry']:,.0f} | RR {signal['rr']:.1f} | {signal['conf']:.0f}% conf"
            self.twilio.send_sms(sms)
    
    def trade_executed(self, symbol: str, direction: str, entry: float, size: float, leverage: int):
        """Alert when a trade is executed"""
        msg = f"""
🔥 <b>TRADE EXECUTED!</b>

<b>{symbol} {direction}</b> @ ${entry:,.2f}
Size: ${size:,.2f} ({leverage}x leverage)

Good luck! 🎯
"""
        self.telegram.send(msg)
        
        # Call for executed trades
        if self.twilio.enabled:
            call_msg = f"Trade executed. {symbol} {direction} at {entry:.0f} dollars."
            self.twilio.make_call(call_msg)
    
    def trade_closed(self, symbol: str, direction: str, entry: float, exit_price: float, pnl: float, pnl_pct: float, reason: str):
        """Alert when a trade is closed"""
        emoji = "✅" if pnl > 0 else "❌"
        sign = "+" if pnl > 0 else ""
        
        msg = f"""
{emoji} <b>TRADE CLOSED!</b>

<b>{symbol} {direction}</b>
Entry: ${entry:,.2f}
Exit: ${exit_price:,.2f}

<b>P/L: {sign}${pnl:.2f} ({sign}{pnl_pct:.1f}%)</b>
Reason: {reason}
"""
        self.telegram.send(msg)
        
        # SMS for closed trades
        if self.twilio.enabled:
            sms = f"{symbol} CLOSED: {sign}${pnl:.2f} ({sign}{pnl_pct:.1f}%) - {reason}"
            self.twilio.send_sms(sms)
    
    def hourly_summary(self, equity: float, start_equity: float, positions: list, trades_today: int):
        """Hourly summary update"""
        change = equity - start_equity
        change_pct = (change / start_equity) * 100 if start_equity > 0 else 0
        sign = "+" if change > 0 else ""
        emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
        
        msg = f"""
{emoji} <b>HOURLY UPDATE</b>

💰 Equity: ${equity:,.2f}
📊 Today: {sign}${change:.2f} ({sign}{change_pct:.1f}%)
📈 Trades: {trades_today}

"""
        if positions:
            msg += "<b>Open:</b>\n"
            for p in positions:
                psign = "+" if p["pnl"] > 0 else ""
                msg += f"• {p['coin']} {p['dir']}: {psign}${p['pnl']:.2f}\n"
        else:
            msg += "🎯 Hunting for sweeps..."
        
        self.telegram.send(msg)
    
    def daily_report(self, equity: float, start_equity: float, trades: int, wins: int, total_pnl: float):
        """End of day report"""
        change = equity - start_equity
        change_pct = (change / start_equity) * 100 if start_equity > 0 else 0
        win_rate = (wins / trades * 100) if trades > 0 else 0
        sign = "+" if change > 0 else ""
        
        msg = f"""
📊 <b>DAILY REPORT</b>

💰 <b>Equity:</b> ${equity:,.2f}
📈 <b>Day P/L:</b> {sign}${change:.2f} ({sign}{change_pct:.1f}%)

<b>Stats:</b>
• Trades: {trades}
• Wins: {wins} ({win_rate:.0f}%)
• Total P/L: {sign}${total_pnl:.2f}

Good night! 🌙
"""
        self.telegram.send(msg)
        
        # SMS daily summary
        if self.twilio.enabled:
            sms = f"Daily: ${equity:.0f} ({sign}{change_pct:.1f}%) | {trades} trades, {win_rate:.0f}% WR"
            self.twilio.send_sms(sms)
    
    def alert(self, message: str, urgent: bool = False):
        """Generic alert message"""
        self.telegram.send(f"⚠️ {message}")
        
        if urgent and self.twilio.enabled:
            self.twilio.send_sms(message)


# Test function
def test_notifications():
    notif = TradingNotifications()
    notif.telegram.send("🧪 <b>Test notification!</b>\n\nAggressive Sweep Trader is connected.")
    print("Test notification sent!")


if __name__ == "__main__":
    test_notifications()
