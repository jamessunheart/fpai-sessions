#!/usr/bin/env python3
"""
🛡️ RESILIENT EXCHANGE CLIENT
==============================

Self-healing exchange connection with automatic recovery.

Features:
- Automatic reconnection with exponential backoff
- Health monitoring with latency tracking
- Graceful degradation under failures
- Multi-level alert escalation
"""

import asyncio
import logging
import time
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Any, Callable, Dict, List, TypeVar
from functools import wraps

logger = logging.getLogger("aria.trading.resilient")

T = TypeVar('T')


class ConnectionState(Enum):
    """Exchange connection states."""
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    DEGRADED = "degraded"         # Working but with issues
    DISCONNECTED = "disconnected"
    FAILED = "failed"             # Gave up


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 5
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt (0-indexed)."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


@dataclass
class HealthStatus:
    """Current health status of exchange connection."""
    state: ConnectionState = ConnectionState.DISCONNECTED
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    latency_ms: float = 0.0
    latency_history: List[float] = field(default_factory=list)
    error_count_1h: int = 0
    
    @property
    def error_rate_1h(self) -> float:
        """Calculate error rate in last hour."""
        # Simplified: just return error count as rate
        return float(self.error_count_1h)
    
    @property
    def avg_latency_ms(self) -> float:
        """Average latency over recent calls."""
        if not self.latency_history:
            return 0.0
        # Keep last 20 measurements
        recent = self.latency_history[-20:]
        return sum(recent) / len(recent)
    
    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return (
            self.state == ConnectionState.CONNECTED and
            self.consecutive_failures == 0 and
            self.avg_latency_ms < 5000  # < 5 second latency
        )
    
    def record_success(self, latency_ms: float):
        """Record a successful operation."""
        self.last_success = datetime.now()
        self.consecutive_failures = 0
        self.consecutive_successes += 1
        self.latency_ms = latency_ms
        self.latency_history.append(latency_ms)
        if len(self.latency_history) > 100:
            self.latency_history = self.latency_history[-100:]
        
        if self.state != ConnectionState.CONNECTED:
            self.state = ConnectionState.CONNECTED
    
    def record_failure(self, error: str):
        """Record a failed operation."""
        self.last_failure = datetime.now()
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.error_count_1h += 1
        
        if self.consecutive_failures >= 5:
            self.state = ConnectionState.FAILED
        elif self.consecutive_failures >= 3:
            self.state = ConnectionState.DEGRADED
        else:
            self.state = ConnectionState.RECONNECTING
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "state": self.state.value,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "latency_ms": round(self.latency_ms, 2),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "error_rate_1h": self.error_rate_1h,
            "is_healthy": self.is_healthy
        }


class ResilientExchangeClient:
    """
    Self-healing exchange connection with automatic recovery.
    
    Wraps the HyperliquidLive client with:
    - Automatic reconnection on failures
    - Health monitoring
    - Graceful degradation
    - Alert escalation
    """
    
    def __init__(self):
        from .hyperliquid_live import get_hyperliquid
        
        self._hl = get_hyperliquid()
        self._health = HealthStatus()
        self._retry_config = RetryConfig()
        self._alert_levels: Dict[int, datetime] = {}  # Level -> last alert time
        self._running = False
        self._health_task: Optional[asyncio.Task] = None
        
        # Alert cooldowns (seconds)
        self._alert_cooldowns = {
            1: 60,       # Level 1: every minute
            2: 300,      # Level 2: every 5 minutes
            3: 600,      # Level 3: every 10 minutes
            4: 0         # Level 4: always (emergency)
        }
        
        # Update initial state based on connection
        if self._hl.is_connected:
            self._health.state = ConnectionState.CONNECTED
    
    @property
    def health(self) -> HealthStatus:
        """Get current health status."""
        return self._health
    
    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._hl.is_connected
    
    @property
    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return self._health.is_healthy
    
    async def start_health_monitoring(self):
        """Start background health monitoring."""
        if self._running:
            return
        
        self._running = True
        self._health_task = asyncio.create_task(self._health_check_loop())
        logger.info("🏥 Started exchange health monitoring")
    
    async def stop_health_monitoring(self):
        """Stop health monitoring."""
        self._running = False
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        logger.info("🏥 Stopped exchange health monitoring")
    
    async def _health_check_loop(self):
        """Continuous health monitoring loop."""
        while self._running:
            try:
                await self._perform_health_check()
            except Exception as e:
                logger.error(f"Health check error: {e}")
            
            # Check every 10 seconds
            await asyncio.sleep(10)
    
    async def _perform_health_check(self):
        """Perform a single health check."""
        start_time = time.time()
        
        try:
            # Simple ping: get account state
            state = self._hl.get_account_state()
            
            latency_ms = (time.time() - start_time) * 1000
            
            if state.get("error"):
                self._health.record_failure(state["error"])
                await self._handle_failure(Exception(state["error"]), "health_check")
            else:
                self._health.record_success(latency_ms)
                
                # Clear error count periodically
                if self._health.consecutive_successes > 10:
                    self._health.error_count_1h = max(0, self._health.error_count_1h - 1)
        
        except Exception as e:
            self._health.record_failure(str(e))
            await self._handle_failure(e, "health_check")
    
    async def execute_with_retry(
        self,
        operation: Callable[..., T],
        *args,
        critical: bool = False,
        operation_name: str = "operation",
        **kwargs
    ) -> T:
        """
        Execute operation with automatic retry.
        
        Args:
            operation: The function to execute
            *args: Arguments for the function
            critical: If True, use more aggressive retry and alert immediately
            operation_name: Name for logging
            **kwargs: Keyword arguments for the function
            
        Returns:
            Result of the operation
        """
        max_attempts = self._retry_config.max_attempts
        if critical:
            max_attempts = max_attempts * 2  # Double attempts for critical
        
        last_error = None
        
        for attempt in range(max_attempts):
            start_time = time.time()
            
            try:
                # Execute the operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                latency_ms = (time.time() - start_time) * 1000
                self._health.record_success(latency_ms)
                
                return result
            
            except Exception as e:
                last_error = e
                latency_ms = (time.time() - start_time) * 1000
                self._health.record_failure(str(e))
                
                logger.warning(
                    f"⚠️ {operation_name} attempt {attempt + 1}/{max_attempts} failed: {e}"
                )
                
                if critical and attempt == 0:
                    # Immediate alert for critical operations
                    await self._escalate_alert(
                        2,
                        f"⚠️ Critical operation '{operation_name}' failed: {e}"
                    )
                
                if attempt < max_attempts - 1:
                    delay = self._retry_config.get_delay(attempt)
                    if critical:
                        delay = delay / 2  # Faster retry for critical
                    
                    logger.info(f"⏳ Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    
                    # Try to recover connection
                    await self._recover_connection()
        
        # All attempts failed
        await self._handle_failure(last_error, operation_name, critical=critical)
        raise last_error
    
    async def _handle_failure(
        self,
        error: Exception,
        operation: str,
        critical: bool = False
    ):
        """Handle connection failure."""
        logger.error(f"❌ {operation} failed: {error}")
        
        # Determine alert level
        if critical:
            level = 3
        elif self._health.consecutive_failures >= 5:
            level = 3
        elif self._health.consecutive_failures >= 3:
            level = 2
        else:
            level = 1
        
        await self._escalate_alert(
            level,
            f"Exchange {operation} failed ({self._health.consecutive_failures} consecutive): {error}"
        )
        
        # If too many failures, trigger emergency
        if self._health.consecutive_failures >= 10:
            await self._trigger_emergency_mode()
    
    async def _recover_connection(self):
        """Attempt to recover the connection."""
        logger.info("🔄 Attempting connection recovery...")
        
        self._health.state = ConnectionState.RECONNECTING
        
        try:
            # Force reconnect
            self._hl._connect()
            
            if self._hl.is_connected:
                # Verify with a test call
                state = self._hl.get_account_state()
                
                if not state.get("error"):
                    self._health.state = ConnectionState.CONNECTED
                    logger.info("✅ Connection recovered!")
                    return True
        
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
        
        self._health.state = ConnectionState.DEGRADED
        return False
    
    async def _escalate_alert(self, level: int, message: str):
        """Escalate alert based on severity level."""
        # Check cooldown
        cooldown = self._alert_cooldowns.get(level, 60)
        last_alert = self._alert_levels.get(level)
        
        if last_alert and cooldown > 0:
            elapsed = (datetime.now() - last_alert).total_seconds()
            if elapsed < cooldown:
                return  # Still in cooldown
        
        self._alert_levels[level] = datetime.now()
        
        # Send alerts based on level
        try:
            if level >= 1:
                # Telegram notification
                await self._send_telegram_alert(message, level)
            
            if level >= 3:
                # SMS for critical
                await self._send_sms_alert(message)
            
            if level >= 4:
                # Emergency stop
                await self._trigger_emergency_mode()
        
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    async def _send_telegram_alert(self, message: str, level: int):
        """Send Telegram alert."""
        try:
            from telegram.bot import get_bot
            
            prefix = {
                1: "ℹ️",
                2: "⚠️",
                3: "🚨",
                4: "🆘"
            }.get(level, "❗")
            
            bot = await get_bot()
            steward_id = 1087024913  # James's Telegram ID
            
            await bot.send_message(
                chat_id=steward_id,
                text=f"{prefix} **EXCHANGE ALERT (Level {level})**\n\n{message}"
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
    
    async def _send_sms_alert(self, message: str):
        """Send SMS alert for critical issues."""
        logger.critical(f"📱 SMS ALERT: {message}")
        # SMS integration would go here
    
    async def _trigger_emergency_mode(self):
        """Trigger emergency mode - close all positions."""
        logger.critical("🆘 EMERGENCY MODE TRIGGERED")
        
        await self._escalate_alert(
            4,
            "🆘 EMERGENCY: Exchange connection critically failed. "
            "Consider closing positions manually."
        )
        
        # Try to close all positions
        try:
            result = await self._hl.close_all_positions()
            if result.get("success"):
                logger.info("✅ Emergency: All positions closed")
            else:
                logger.error(f"❌ Emergency close failed: {result}")
        except Exception as e:
            logger.error(f"❌ Emergency close exception: {e}")
    
    # ==================
    # Wrapped Operations
    # ==================
    
    def get_account_state(self) -> Dict:
        """Get account state (synchronous wrapper)."""
        return self._hl.get_account_state()
    
    def get_positions(self) -> List[Dict]:
        """Get positions (synchronous wrapper)."""
        return self._hl.get_positions()
    
    def get_balance(self) -> float:
        """Get balance (synchronous wrapper)."""
        return self._hl.get_balance()
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        size: float,
        price: Optional[float] = None,
        reduce_only: bool = False
    ) -> Dict:
        """Place order with retry logic."""
        return await self.execute_with_retry(
            self._hl.place_order,
            symbol=symbol,
            side=side,
            size=size,
            price=price,
            reduce_only=reduce_only,
            critical=True,
            operation_name=f"place_order({symbol} {side} {size})"
        )
    
    async def close_position(self, symbol: str) -> Dict:
        """Close position with retry logic."""
        return await self.execute_with_retry(
            self._hl.close_position,
            symbol,
            critical=True,
            operation_name=f"close_position({symbol})"
        )
    
    async def close_all_positions(self) -> Dict:
        """Close all positions with retry logic."""
        return await self.execute_with_retry(
            self._hl.close_all_positions,
            critical=True,
            operation_name="close_all_positions"
        )


# Singleton
_resilient_client: Optional[ResilientExchangeClient] = None


def get_resilient_client() -> ResilientExchangeClient:
    """Get or create global resilient client."""
    global _resilient_client
    if _resilient_client is None:
        _resilient_client = ResilientExchangeClient()
    return _resilient_client


async def start_exchange_monitoring():
    """Start exchange health monitoring."""
    client = get_resilient_client()
    await client.start_health_monitoring()


async def stop_exchange_monitoring():
    """Stop exchange health monitoring."""
    client = get_resilient_client()
    await client.stop_health_monitoring()


def get_exchange_health() -> Dict:
    """Get current exchange health status."""
    client = get_resilient_client()
    return client.health.to_dict()









