#!/usr/bin/env python3
"""
ARIA ULTRA POWER - AUTOPILOT LOOP
==================================

Main autopilot control loop:
- Continuous market monitoring
- Signal generation and execution
- Mode-based autonomy
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import httpx

logger = logging.getLogger("aria.autopilot.loop")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
SUNHEART_CHAT_ID = os.getenv("SUNHEART_CHAT_ID", "")


class AutopilotMode(Enum):
    """Autopilot operating modes."""
    OFF = "off"           # No automated trading
    MONITOR = "monitor"   # Generate signals, no execution
    GUIDED = "guided"     # Ask approval for each trade
    AUTO = "auto"         # Full autonomy within risk limits


@dataclass
class AutopilotState:
    """Current autopilot state."""
    mode: AutopilotMode
    running: bool
    last_check: float
    signals_generated: int
    trades_executed: int
    trades_approved: int
    trades_rejected: int
    total_pnl: float
    started_at: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode.value,
            "running": self.running,
            "last_check": self.last_check,
            "signals_generated": self.signals_generated,
            "trades_executed": self.trades_executed,
            "trades_approved": self.trades_approved,
            "trades_rejected": self.trades_rejected,
            "total_pnl": self.total_pnl,
            "uptime_hours": (time.time() - self.started_at) / 3600 if self.started_at else 0,
        }


class AutopilotLoop:
    """
    Main autopilot control loop.
    
    Features:
    - Configurable autonomy modes
    - Continuous signal monitoring
    - Risk-aware execution
    - Telegram notifications
    """
    
    def __init__(self):
        self.http = httpx.AsyncClient(timeout=30.0)
        self._mode = AutopilotMode.OFF
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = 60  # seconds
        
        self._state = AutopilotState(
            mode=AutopilotMode.OFF,
            running=False,
            last_check=0,
            signals_generated=0,
            trades_executed=0,
            trades_approved=0,
            trades_rejected=0,
            total_pnl=0,
        )
        
        logger.info("AutopilotLoop initialized")
    
    @property
    def mode(self) -> AutopilotMode:
        return self._mode
    
    @mode.setter
    def mode(self, value: AutopilotMode):
        old_mode = self._mode
        self._mode = value
        self._state.mode = value
        logger.info(f"Autopilot mode changed: {old_mode.value} -> {value.value}")
    
    async def start(self, mode: AutopilotMode = AutopilotMode.MONITOR):
        """Start the autopilot loop."""
        if self._running:
            logger.warning("Autopilot already running")
            return
        
        self._mode = mode
        self._running = True
        self._state.mode = mode
        self._state.running = True
        self._state.started_at = time.time()
        
        self._task = asyncio.create_task(self._run_loop())
        
        await self._notify(f"🤖 **Autopilot Started**\nMode: {mode.value}")
        logger.info(f"Autopilot started in {mode.value} mode")
    
    async def stop(self):
        """Stop the autopilot loop."""
        if not self._running:
            return
        
        self._running = False
        self._state.running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await self._notify("🛑 **Autopilot Stopped**")
        logger.info("Autopilot stopped")
    
    async def _run_loop(self):
        """Main autopilot loop."""
        while self._running:
            try:
                await self._check_cycle()
            except Exception as e:
                logger.error(f"Autopilot cycle error: {e}")
            
            await asyncio.sleep(self._check_interval)
    
    async def _check_cycle(self):
        """Run a single check cycle."""
        from .strategy import get_strategy_executor
        from .risk import get_risk_engine
        
        self._state.last_check = time.time()
        
        # Skip if mode is OFF
        if self._mode == AutopilotMode.OFF:
            return
        
        # Check risk first
        risk_engine = get_risk_engine()
        risk = await risk_engine.assess_risk()
        
        if not risk.can_trade and self._mode != AutopilotMode.MONITOR:
            await self._notify(
                f"⚠️ **Risk Alert**\n"
                f"Level: {risk.overall_level.value}\n"
                f"Violations: {', '.join(risk.violations) if risk.violations else 'None'}"
            )
            return
        
        # Generate signals
        executor = get_strategy_executor()
        signals = await executor.generate_signals()
        
        if not signals:
            return
        
        self._state.signals_generated += len(signals)
        
        # Process signals based on mode
        for signal in signals:
            if self._mode == AutopilotMode.MONITOR:
                # Just notify
                await self._notify(
                    f"📊 **Signal Generated**\n{executor.format_signal(signal)}"
                )
            
            elif self._mode == AutopilotMode.GUIDED:
                # Ask for approval
                tier = executor.get_execution_tier(signal)
                if tier == "auto":
                    # High confidence, still notify
                    result = await executor.execute_signal(signal, approved=True)
                    if result["success"]:
                        self._state.trades_executed += 1
                        await self._notify(
                            f"✅ **Trade Executed (Auto)**\n{executor.format_signal(signal)}"
                        )
                else:
                    # Request approval
                    await self._request_approval(signal)
            
            elif self._mode == AutopilotMode.AUTO:
                # Full autonomy
                result = await executor.execute_signal(signal, approved=True)
                if result["success"]:
                    self._state.trades_executed += 1
                    await self._notify(
                        f"✅ **Trade Executed**\n{executor.format_signal(signal)}"
                    )
                else:
                    await self._notify(
                        f"❌ **Trade Failed**\n{result.get('reason', 'Unknown error')}"
                    )
    
    async def _request_approval(self, signal):
        """Request user approval for a trade."""
        from .strategy import get_strategy_executor
        
        executor = get_strategy_executor()
        pending_idx = len(executor.get_pending_signals())
        
        # Add to pending
        executor._pending_signals.append(signal)
        
        message = (
            f"🔔 **Trade Approval Needed**\n\n"
            f"{executor.format_signal(signal)}\n\n"
            f"Reply:\n"
            f"• `/approve {pending_idx}` to execute\n"
            f"• `/reject {pending_idx}` to skip"
        )
        
        await self._notify(message)
    
    async def _notify(self, message: str):
        """Send notification via Telegram."""
        if not SUNHEART_CHAT_ID:
            logger.warning("No SUNHEART_CHAT_ID set for notifications")
            return
        
        try:
            await self.http.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": SUNHEART_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown"
                }
            )
        except Exception as e:
            logger.error(f"Notification error: {e}")
    
    def get_state(self) -> AutopilotState:
        """Get current autopilot state."""
        return self._state
    
    def set_check_interval(self, seconds: int):
        """Set check interval in seconds."""
        self._check_interval = max(10, seconds)  # Minimum 10 seconds
    
    def format_status(self) -> str:
        """Format status for display."""
        state = self._state
        
        mode_emoji = {
            AutopilotMode.OFF: "⏹️",
            AutopilotMode.MONITOR: "👁️",
            AutopilotMode.GUIDED: "🎯",
            AutopilotMode.AUTO: "🤖",
        }
        
        emoji = mode_emoji.get(state.mode, "❓")
        running_str = "Running" if state.running else "Stopped"
        
        lines = [
            f"{emoji} **Autopilot Status**",
            "",
            f"Mode: {state.mode.value}",
            f"Status: {running_str}",
            f"Check Interval: {self._check_interval}s",
        ]
        
        if state.started_at:
            uptime = (time.time() - state.started_at) / 3600
            lines.append(f"Uptime: {uptime:.1f} hours")
        
        lines.append("")
        lines.append("**Statistics:**")
        lines.append(f"• Signals generated: {state.signals_generated}")
        lines.append(f"• Trades executed: {state.trades_executed}")
        lines.append(f"• Trades approved: {state.trades_approved}")
        lines.append(f"• Trades rejected: {state.trades_rejected}")
        
        return "\n".join(lines)


# Singleton instance
_autopilot: Optional[AutopilotLoop] = None


def get_autopilot() -> AutopilotLoop:
    """Get global AutopilotLoop instance."""
    global _autopilot
    if _autopilot is None:
        _autopilot = AutopilotLoop()
    return _autopilot


