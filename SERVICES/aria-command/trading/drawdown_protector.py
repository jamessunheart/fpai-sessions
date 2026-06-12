#!/usr/bin/env python3
"""
🛡️ DRAWDOWN PROTECTION SYSTEM
==============================

Protects account during drawdowns:
- Tiered position size reduction
- Trading pause on severe drawdown
- Recovery tracking
- Automatic resume when recovered

Prevents catastrophic losses during losing streaks.
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass
from pathlib import Path
import json

logger = logging.getLogger("aria.trading.drawdown")

DATA_DIR = Path(os.getenv("ARIA_DATA_DIR", "/opt/fpai/aria-command/data"))
STEWARD_CHAT_ID = int(os.getenv("STEWARD_CHAT_ID", "1759822075"))


@dataclass
class DrawdownConfig:
    """Drawdown protection configuration."""
    # Level 1: Caution
    level_1_pct: float = 5.0           # At 5% drawdown
    level_1_reduction: float = 0.5     # Reduce size by 50%
    
    # Level 2: Warning  
    level_2_pct: float = 10.0          # At 10% drawdown
    level_2_reduction: float = 0.25    # Only 25% size
    
    # Level 3: Critical
    level_3_pct: float = 15.0          # At 15% drawdown
    level_3_action: str = "pause"      # Stop trading
    
    # Recovery
    recovery_threshold: float = 0.5    # Resume after 50% recovery
    
    # Consecutive loss protection
    consecutive_loss_pause: int = 5    # Pause after 5 consecutive losses


class DrawdownProtector:
    """
    Protects account during drawdowns.
    
    Features:
    - Tracks peak equity and current drawdown
    - Reduces position sizes based on drawdown level
    - Pauses trading on severe drawdown
    - Resumes when recovered
    """
    
    def __init__(self, config: Optional[DrawdownConfig] = None):
        self._config = config or DrawdownConfig()
        self._peak_equity: float = 0.0
        self._current_equity: float = 0.0
        self._trading_paused: bool = False
        self._pause_reason: Optional[str] = None
        self._pause_started: Optional[datetime] = None
        self._consecutive_losses: int = 0
        self._recovery_target: float = 0.0
        
        # Load state
        self._load_state()
    
    def _state_file(self) -> Path:
        """Get state file path."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DATA_DIR / "drawdown_state.json"
    
    def _load_state(self):
        """Load persisted state."""
        try:
            path = self._state_file()
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                
                self._peak_equity = data.get("peak_equity", 0)
                self._trading_paused = data.get("trading_paused", False)
                self._pause_reason = data.get("pause_reason")
                self._consecutive_losses = data.get("consecutive_losses", 0)
                self._recovery_target = data.get("recovery_target", 0)
                
                logger.info(f"🛡️ Loaded drawdown state: peak=${self._peak_equity:,.2f}")
        except Exception as e:
            logger.warning(f"Failed to load drawdown state: {e}")
    
    def _save_state(self):
        """Save state to file."""
        try:
            data = {
                "peak_equity": self._peak_equity,
                "trading_paused": self._trading_paused,
                "pause_reason": self._pause_reason,
                "consecutive_losses": self._consecutive_losses,
                "recovery_target": self._recovery_target,
                "updated_at": datetime.now().isoformat()
            }
            
            with open(self._state_file(), "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save drawdown state: {e}")
    
    def update_equity(self, new_equity: float):
        """
        Update equity tracking.
        
        Called after each trade or periodically.
        """
        self._current_equity = new_equity
        
        if new_equity > self._peak_equity:
            self._peak_equity = new_equity
            self._save_state()
            logger.debug(f"📈 New peak equity: ${self._peak_equity:,.2f}")
        
        # Check if we've recovered from pause
        if self._trading_paused and self._recovery_target > 0:
            if new_equity >= self._recovery_target:
                self._resume_trading("Equity recovered")
    
    @property
    def current_drawdown_pct(self) -> float:
        """Calculate current drawdown percentage."""
        if self._peak_equity == 0:
            return 0.0
        return (self._peak_equity - self._current_equity) / self._peak_equity * 100
    
    @property
    def drawdown_level(self) -> int:
        """Get current drawdown level (0-3)."""
        dd = self.current_drawdown_pct
        
        if dd >= self._config.level_3_pct:
            return 3
        elif dd >= self._config.level_2_pct:
            return 2
        elif dd >= self._config.level_1_pct:
            return 1
        else:
            return 0
    
    def get_size_multiplier(self) -> float:
        """
        Get position size multiplier based on drawdown.
        
        Returns 0 if trading should be paused.
        """
        if self._trading_paused:
            return 0.0
        
        level = self.drawdown_level
        
        if level == 3:
            return 0.0  # Stop trading
        elif level == 2:
            return self._config.level_2_reduction
        elif level == 1:
            return self._config.level_1_reduction
        else:
            return 1.0
    
    def should_pause_trading(self) -> bool:
        """Check if trading should be paused."""
        if self._trading_paused:
            return True
        
        # Check drawdown level
        if self.drawdown_level >= 3:
            self._pause_trading("Maximum drawdown reached")
            return True
        
        # Check consecutive losses
        if self._consecutive_losses >= self._config.consecutive_loss_pause:
            self._pause_trading(f"{self._consecutive_losses} consecutive losses")
            return True
        
        return False
    
    def _pause_trading(self, reason: str):
        """Pause trading."""
        if self._trading_paused:
            return
        
        self._trading_paused = True
        self._pause_reason = reason
        self._pause_started = datetime.now()
        
        # Set recovery target
        recovery_amount = (self._peak_equity - self._current_equity) * self._config.recovery_threshold
        self._recovery_target = self._current_equity + recovery_amount
        
        self._save_state()
        
        logger.warning(f"⛔ Trading PAUSED: {reason}")
        
        # Notify steward
        self._notify_pause(reason)
    
    def _resume_trading(self, reason: str):
        """Resume trading after pause."""
        if not self._trading_paused:
            return
        
        self._trading_paused = False
        self._pause_reason = None
        self._consecutive_losses = 0
        
        self._save_state()
        
        logger.info(f"✅ Trading RESUMED: {reason}")
        
        # Notify steward
        self._notify_resume(reason)
    
    def record_trade_result(self, is_win: bool, pnl: float, new_equity: float):
        """
        Record a trade result for consecutive loss tracking.
        """
        if is_win:
            self._consecutive_losses = 0
        else:
            self._consecutive_losses += 1
        
        self.update_equity(new_equity)
        self._save_state()
        
        # Check if we should pause
        self.should_pause_trading()
    
    def force_resume(self, reason: str = "Manual override"):
        """Force resume trading (manual override)."""
        self._resume_trading(reason)
        self._consecutive_losses = 0
        self._recovery_target = 0
        self._save_state()
    
    def get_status(self) -> Dict:
        """Get current drawdown protection status."""
        return {
            "peak_equity": self._peak_equity,
            "current_equity": self._current_equity,
            "drawdown_pct": round(self.current_drawdown_pct, 2),
            "drawdown_level": self.drawdown_level,
            "size_multiplier": self.get_size_multiplier(),
            "trading_paused": self._trading_paused,
            "pause_reason": self._pause_reason,
            "consecutive_losses": self._consecutive_losses,
            "recovery_target": self._recovery_target,
            "config": {
                "level_1_pct": self._config.level_1_pct,
                "level_2_pct": self._config.level_2_pct,
                "level_3_pct": self._config.level_3_pct,
                "consecutive_loss_pause": self._config.consecutive_loss_pause
            }
        }
    
    async def _notify_pause(self, reason: str):
        """Notify steward of trading pause."""
        try:
            from telegram.bot import send_message
            
            message = f"""⛔ **TRADING PAUSED**

**Reason:** {reason}

**Status:**
• Peak Equity: ${self._peak_equity:,.2f}
• Current Equity: ${self._current_equity:,.2f}
• Drawdown: {self.current_drawdown_pct:.1f}%
• Consecutive Losses: {self._consecutive_losses}

**Recovery Target:** ${self._recovery_target:,.2f}

_Trading will auto-resume when equity recovers to target_
_Or use manual override to force resume_"""
            
            await send_message(STEWARD_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Failed to notify: {e}")
    
    async def _notify_resume(self, reason: str):
        """Notify steward of trading resume."""
        try:
            from telegram.bot import send_message
            
            message = f"""✅ **TRADING RESUMED**

**Reason:** {reason}

**Status:**
• Current Equity: ${self._current_equity:,.2f}
• Drawdown: {self.current_drawdown_pct:.1f}%

_Position sizing back to normal_"""
            
            await send_message(STEWARD_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Failed to notify: {e}")


# Singleton
_drawdown_protector: Optional[DrawdownProtector] = None


def get_drawdown_protector(config: Optional[DrawdownConfig] = None) -> DrawdownProtector:
    """Get or create global drawdown protector."""
    global _drawdown_protector
    if _drawdown_protector is None:
        _drawdown_protector = DrawdownProtector(config)
    return _drawdown_protector









