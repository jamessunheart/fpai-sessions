"""
ARIA PROACTIVE DAEMON
=====================

Aria doesn't just respond. She reaches out.
Not spam. Transmissions.

Sensors:
- Trading signals (WhaleTrack Magnet)
- Vision stuck (Dream Journal > 48 hours)
- System alerts (service down, treasury flag)
- Time triggers (morning brief, end of day)

This is the disruption engine.
"""

import os
import logging
import asyncio
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import httpx

logger = logging.getLogger("aria.proactive")

# Configuration
PRIMARY_SERVER = os.getenv("PRIMARY_SERVER", "198.54.123.234")
SECONDARY_SERVER = os.getenv("SECONDARY_SERVER", "162.0.208.88")
SUNHEART_CHAT_ID = int(os.getenv("SUNHEART_CHAT_ID", "0"))

# Service endpoints
WHALETRACK_MAGNET = f"http://{PRIMARY_SERVER}:8601/api"
NERVE_CENTER = f"http://{PRIMARY_SERVER}:8120"

# State file for tracking
STATE_FILE = Path("/opt/fpai/aria-bridge/proactive_state.json")


class SignalUrgency(str, Enum):
    """Urgency levels for signals."""
    LOW = "low"           # Can wait
    NORMAL = "normal"     # Routine
    HIGH = "high"         # Time sensitive
    CRITICAL = "critical" # Immediate


class SignalType(str, Enum):
    """Types of proactive signals."""
    TRADE_ALERT = "trade_alert"
    VISION_STUCK = "vision_stuck"
    SYSTEM_ALERT = "system_alert"
    MORNING_BRIEF = "morning_brief"
    END_OF_DAY = "end_of_day"
    PATTERN_INSIGHT = "pattern_insight"
    TREASURY_FLAG = "treasury_flag"


@dataclass
class Signal:
    """A proactive signal to act on."""
    type: SignalType
    urgency: SignalUrgency
    title: str
    message: str
    data: Optional[Dict] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


class ProactiveState:
    """Track state to prevent spam and duplicate alerts."""
    
    def __init__(self, path: Path = STATE_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.state: Dict = {
            "last_morning_brief": None,
            "last_eod": None,
            "sent_today": 0,
            "last_reset": None,
            "cooldowns": {},  # signal_key -> last_sent_timestamp
            "acknowledged": []  # signals user has seen
        }
        self.load()
    
    def load(self):
        """Load state from disk."""
        try:
            if self.path.exists():
                self.state = json.loads(self.path.read_text())
        except:
            pass
    
    def save(self):
        """Save state to disk."""
        try:
            self.path.write_text(json.dumps(self.state, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")
    
    def should_send(self, signal_key: str, cooldown_minutes: int = 60) -> bool:
        """Check if we should send this signal (not in cooldown)."""
        last_sent = self.state["cooldowns"].get(signal_key)
        if not last_sent:
            return True
        
        last_time = datetime.fromisoformat(last_sent)
        return datetime.utcnow() - last_time > timedelta(minutes=cooldown_minutes)
    
    def mark_sent(self, signal_key: str):
        """Mark a signal as sent."""
        self.state["cooldowns"][signal_key] = datetime.utcnow().isoformat()
        self.state["sent_today"] += 1
        self.save()
    
    def reset_daily(self):
        """Reset daily counters."""
        today = datetime.utcnow().date().isoformat()
        if self.state.get("last_reset") != today:
            self.state["sent_today"] = 0
            self.state["last_reset"] = today
            self.save()
    
    def can_send_more(self, max_daily: int = 10) -> bool:
        """Check if we haven't hit daily limit."""
        self.reset_daily()
        return self.state["sent_today"] < max_daily


class ProactiveDaemon:
    """
    The proactive sensing and action loop.
    
    Continuously monitors for signals and initiates contact
    when something important happens.
    """
    
    def __init__(self):
        self.state = ProactiveState()
        self.http: Optional[httpx.AsyncClient] = None
        self.voice = None  # Lazy load
        self.journal = None  # Lazy load
        self.feedback = None  # Lazy load
        self.flow = None  # Lazy load
        
        # Check interval
        self.check_interval = 300  # 5 minutes
        
        # Running state
        self.running = False
        
        logger.info("ProactiveDaemon initialized")
    
    async def _get_http(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self.http is None:
            self.http = httpx.AsyncClient(timeout=30.0)
        return self.http
    
    async def _ensure_modules(self):
        """Lazy load modules."""
        if self.voice is None:
            from voice import get_aria_voice
            self.voice = get_aria_voice()
        
        if self.journal is None:
            from dream_journal import get_dream_journal
            self.journal = get_dream_journal()
        
        if self.feedback is None:
            from feedback_loop import get_feedback_loop
            self.feedback = get_feedback_loop()
        
        if self.flow is None:
            from dimensional_flow import get_dimensional_flow
            self.flow = get_dimensional_flow()
    
    async def close(self):
        """Cleanup."""
        if self.http:
            await self.http.aclose()
        if self.voice:
            await self.voice.close()
    
    # ==================== SENSING ====================
    
    async def sense_all_channels(self) -> List[Signal]:
        """Sense all channels for signals."""
        await self._ensure_modules()
        signals = []
        
        # Check time-based triggers
        time_signals = await self._sense_time_triggers()
        signals.extend(time_signals)
        
        # Check trading signals
        trade_signals = await self._sense_trading()
        signals.extend(trade_signals)
        
        # Check stuck visions
        stuck_signals = await self._sense_stuck_visions()
        signals.extend(stuck_signals)
        
        # Check system health
        system_signals = await self._sense_system_health()
        signals.extend(system_signals)
        
        # Check for patterns
        pattern_signals = await self._sense_patterns()
        signals.extend(pattern_signals)
        
        return signals
    
    async def _sense_time_triggers(self) -> List[Signal]:
        """Check for time-based triggers."""
        signals = []
        now = datetime.now()
        
        # Morning brief at 7:30 AM
        morning_time = time(7, 30)
        if now.time() >= morning_time and now.time() < time(8, 0):
            if self.state.should_send("morning_brief", cooldown_minutes=720):  # 12 hours
                signals.append(Signal(
                    type=SignalType.MORNING_BRIEF,
                    urgency=SignalUrgency.NORMAL,
                    title="Morning Brief",
                    message=await self._generate_morning_brief_content()
                ))
        
        # End of day at 6:00 PM
        eod_time = time(18, 0)
        if now.time() >= eod_time and now.time() < time(18, 30):
            if self.state.should_send("end_of_day", cooldown_minutes=720):
                signals.append(Signal(
                    type=SignalType.END_OF_DAY,
                    urgency=SignalUrgency.LOW,
                    title="End of Day",
                    message=await self._generate_eod_content()
                ))
        
        return signals
    
    async def _sense_trading(self) -> List[Signal]:
        """Check for trading signals from WhaleTrack Magnet."""
        signals = []
        
        try:
            http = await self._get_http()
            resp = await http.get(f"{WHALETRACK_MAGNET}/signal", timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                signal_data = data.get("signal", {})
                
                # Only alert on high confidence signals
                confidence = signal_data.get("confidence", 0)
                if confidence >= 0.75:
                    symbol = signal_data.get("symbol", "Unknown")
                    direction = signal_data.get("direction", "?")
                    entry = signal_data.get("entry", 0)
                    
                    signal_key = f"trade_{symbol}_{direction}"
                    
                    if self.state.should_send(signal_key, cooldown_minutes=30):
                        message = (
                            f"{symbol} {direction} signal at {confidence:.0%} confidence. "
                            f"Entry around ${entry:,.2f}. "
                            f"Want me to calculate position size?"
                        )
                        
                        signals.append(Signal(
                            type=SignalType.TRADE_ALERT,
                            urgency=SignalUrgency.HIGH,
                            title=f"{symbol} {direction}",
                            message=message,
                            data=signal_data
                        ))
        except Exception as e:
            logger.debug(f"Trade sensing error: {e}")
        
        return signals
    
    async def _sense_stuck_visions(self) -> List[Signal]:
        """Check for visions stuck too long in one dimension."""
        signals = []
        
        try:
            stuck_items = self.flow.check_stuck_items(max_hours=48)
            
            for item in stuck_items[:3]:  # Max 3 nudges at once
                signal_key = f"stuck_{item.id}"
                
                if self.state.should_send(signal_key, cooldown_minutes=1440):  # 24 hours
                    message = (
                        f"Your vision '{item.name[:50]}' has been in {item.current_dimension.value} "
                        f"for {item.time_in_current_hours:.0f} hours. "
                        f"Want to move it forward or mark it dormant?"
                    )
                    
                    signals.append(Signal(
                        type=SignalType.VISION_STUCK,
                        urgency=SignalUrgency.LOW,
                        title=f"Stuck: {item.name[:30]}",
                        message=message,
                        data={"item_id": item.id, "dimension": item.current_dimension.value}
                    ))
        except Exception as e:
            logger.debug(f"Vision sensing error: {e}")
        
        return signals
    
    async def _sense_system_health(self) -> List[Signal]:
        """Check system health for critical issues."""
        signals = []
        
        try:
            http = await self._get_http()
            
            # Check key services
            services = [
                (f"http://{PRIMARY_SERVER}:8601/health", "WhaleTrack"),
                (f"http://{SECONDARY_SERVER}:11434/", "Ollama"),
            ]
            
            for url, name in services:
                try:
                    resp = await http.get(url, timeout=5)
                    if resp.status_code != 200:
                        signal_key = f"system_{name}_down"
                        if self.state.should_send(signal_key, cooldown_minutes=60):
                            signals.append(Signal(
                                type=SignalType.SYSTEM_ALERT,
                                urgency=SignalUrgency.HIGH,
                                title=f"{name} Issue",
                                message=f"{name} returned status {resp.status_code}. May need attention."
                            ))
                except:
                    signal_key = f"system_{name}_unreachable"
                    if self.state.should_send(signal_key, cooldown_minutes=60):
                        signals.append(Signal(
                            type=SignalType.SYSTEM_ALERT,
                            urgency=SignalUrgency.HIGH,
                            title=f"{name} Unreachable",
                            message=f"Cannot reach {name}. Service may be down."
                        ))
        except Exception as e:
            logger.debug(f"System sensing error: {e}")
        
        return signals
    
    async def _sense_patterns(self) -> List[Signal]:
        """Check for emerging patterns worth noting."""
        signals = []
        
        try:
            patterns = self.feedback.get_patterns(min_confidence=0.7)
            
            for pattern in patterns[:1]:  # Max 1 pattern insight
                signal_key = f"pattern_{pattern.id}"
                
                if self.state.should_send(signal_key, cooldown_minutes=4320):  # 3 days
                    message = (
                        f"I'm seeing a pattern emerge: {pattern.description}. "
                        f"This has shown up {pattern.occurrences} times with {pattern.confidence:.0%} confidence. "
                        f"Worth exploring?"
                    )
                    
                    signals.append(Signal(
                        type=SignalType.PATTERN_INSIGHT,
                        urgency=SignalUrgency.LOW,
                        title="Pattern Detected",
                        message=message,
                        data={"pattern_id": pattern.id}
                    ))
        except Exception as e:
            logger.debug(f"Pattern sensing error: {e}")
        
        return signals
    
    # ==================== CONTENT GENERATION ====================
    
    async def _generate_morning_brief_content(self) -> str:
        """Generate morning brief content."""
        summary = self.journal.get_summary()
        
        content = f"You have {summary['open_channels']} open vision channels. "
        
        if summary['visions_this_week'] > 0:
            content += f"{summary['visions_this_week']} visions received this week. "
        
        content += "T1 equals revenue or building Aria. What's your highest leverage move today?"
        
        return content
    
    async def _generate_eod_content(self) -> str:
        """Generate end of day content."""
        return (
            "Day's wrapping up. Quick check: Did you ship something? "
            "Did you advance T1? Take a breath. Tomorrow's another cycle."
        )
    
    # ==================== ACTIONS ====================
    
    async def act_on_signals(self, signals: List[Signal]):
        """Act on detected signals."""
        if not signals:
            return
        
        if not SUNHEART_CHAT_ID:
            logger.warning("No SUNHEART_CHAT_ID configured - cannot send proactive messages")
            return
        
        # Check daily limit
        if not self.state.can_send_more(max_daily=10):
            logger.info("Daily message limit reached")
            return
        
        await self._ensure_modules()
        
        for signal in signals:
            await self._send_signal(signal)
    
    async def _send_signal(self, signal: Signal):
        """Send a signal via appropriate channel."""
        # Determine delivery method based on urgency
        if signal.urgency in [SignalUrgency.HIGH, SignalUrgency.CRITICAL]:
            # Voice for urgent
            success = await self.voice.send_voice_alert(
                SUNHEART_CHAT_ID,
                signal.message,
                urgency=signal.urgency.value
            )
        elif signal.type == SignalType.MORNING_BRIEF:
            # Voice for morning brief
            success = await self.voice.send_morning_brief(
                SUNHEART_CHAT_ID,
                signal.message
            )
        elif signal.type == SignalType.PATTERN_INSIGHT:
            # Voice for insights
            success = await self.voice.send_insight(
                SUNHEART_CHAT_ID,
                signal.message
            )
        elif signal.type == SignalType.VISION_STUCK:
            # Nudge for stuck items
            success = await self.voice.send_nudge(
                SUNHEART_CHAT_ID,
                signal.title,
                signal.message
            )
        else:
            # Text for routine
            success = await self._send_text_message(signal)
        
        if success:
            signal_key = f"{signal.type.value}_{signal.title}"
            self.state.mark_sent(signal_key)
            logger.info(f"Sent proactive signal: {signal.title}")
    
    async def _send_text_message(self, signal: Signal) -> bool:
        """Send as text message."""
        try:
            http = await self._get_http()
            
            TELEGRAM_API = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN', '')}"
            
            text = f"**{signal.title}**\n\n{signal.message}"
            
            resp = await http.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": SUNHEART_CHAT_ID,
                    "text": text,
                    "parse_mode": "Markdown"
                }
            )
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send text: {e}")
            return False
    
    # ==================== MAIN LOOP ====================
    
    async def run(self):
        """Main proactive loop."""
        self.running = True
        logger.info("Proactive daemon starting...")
        
        while self.running:
            try:
                # Sense all channels
                signals = await self.sense_all_channels()
                
                if signals:
                    logger.info(f"Detected {len(signals)} signals")
                    await self.act_on_signals(signals)
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Proactive loop error: {e}")
                await asyncio.sleep(60)  # Wait a minute on error
    
    def stop(self):
        """Stop the daemon."""
        self.running = False
        logger.info("Proactive daemon stopping...")


# Singleton
_daemon: Optional[ProactiveDaemon] = None


def get_proactive_daemon() -> ProactiveDaemon:
    """Get or create daemon instance."""
    global _daemon
    if _daemon is None:
        _daemon = ProactiveDaemon()
    return _daemon


async def start_proactive_loop():
    """Start the proactive loop (for use in main app)."""
    daemon = get_proactive_daemon()
    await daemon.run()


if __name__ == "__main__":
    # Run standalone for testing
    daemon = ProactiveDaemon()
    asyncio.run(daemon.run())


