"""
ARIA CIRCUIT BREAKER
====================

Prevents cascading failures by stopping calls to broken services.

Based on the classic circuit breaker pattern:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is broken, fail fast without calling
- HALF-OPEN: Testing if service recovered

When a service fails repeatedly (5x in 60 seconds), the circuit opens:
- Stops all calls to that service immediately
- Returns fallback response instead
- Automatically tries again after cooldown period
- If recovery succeeds, circuit closes again

This prevents one broken service from bringing down everything.
"""

import os
import asyncio
import logging
from typing import Dict, Optional, Any, Callable, Awaitable, TypeVar
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import functools

logger = logging.getLogger("aria.consciousness.circuit")

# Configuration
FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_FAILURE_THRESHOLD", "5"))  # Failures to trigger open
FAILURE_WINDOW = int(os.getenv("CIRCUIT_FAILURE_WINDOW", "60"))  # Seconds to count failures
COOLDOWN_SECONDS = int(os.getenv("CIRCUIT_COOLDOWN", "60"))  # Time before retry
HALF_OPEN_REQUESTS = int(os.getenv("CIRCUIT_HALF_OPEN_REQUESTS", "3"))  # Successes needed to close

T = TypeVar('T')


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    rejected_count: int = 0  # Calls rejected while open
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    state_changes: int = 0


@dataclass
class CircuitBreaker:
    """
    Circuit breaker for a single service.
    
    Tracks failures and opens the circuit when a threshold is exceeded.
    """
    name: str
    failure_threshold: int = FAILURE_THRESHOLD
    failure_window: int = FAILURE_WINDOW
    cooldown_seconds: int = COOLDOWN_SECONDS
    half_open_requests: int = HALF_OPEN_REQUESTS
    
    # State
    state: CircuitState = field(default=CircuitState.CLOSED)
    failures: list = field(default_factory=list)
    half_open_successes: int = 0
    last_state_change: datetime = field(default_factory=datetime.now)
    stats: CircuitStats = field(default_factory=CircuitStats)
    
    # Fallback function
    fallback: Optional[Callable] = None
    
    def __post_init__(self):
        logger.info(f"⚡ Circuit breaker created: {self.name}")
    
    def _cleanup_old_failures(self):
        """Remove failures outside the window."""
        cutoff = datetime.now() - timedelta(seconds=self.failure_window)
        self.failures = [f for f in self.failures if f > cutoff]
    
    def record_failure(self, error: Exception = None):
        """Record a failure and check if circuit should open."""
        now = datetime.now()
        self.failures.append(now)
        self._cleanup_old_failures()
        
        self.stats.failure_count += 1
        self.stats.last_failure = now
        
        logger.warning(f"⚡ {self.name}: Failure recorded ({len(self.failures)}/{self.failure_threshold})")
        
        # Check if we should open the circuit
        if self.state == CircuitState.CLOSED:
            if len(self.failures) >= self.failure_threshold:
                self._open_circuit()
        
        elif self.state == CircuitState.HALF_OPEN:
            # Failure during half-open: go back to open
            self._open_circuit()
    
    def record_success(self):
        """Record a success."""
        now = datetime.now()
        self.stats.success_count += 1
        self.stats.last_success = now
        
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_successes += 1
            logger.info(f"⚡ {self.name}: Half-open success ({self.half_open_successes}/{self.half_open_requests})")
            
            if self.half_open_successes >= self.half_open_requests:
                self._close_circuit()
    
    def _open_circuit(self):
        """Open the circuit (stop all calls)."""
        if self.state != CircuitState.OPEN:
            logger.warning(f"🔴 {self.name}: Circuit OPENED (too many failures)")
            self.state = CircuitState.OPEN
            self.last_state_change = datetime.now()
            self.stats.state_changes += 1
    
    def _close_circuit(self):
        """Close the circuit (resume normal operation)."""
        logger.info(f"🟢 {self.name}: Circuit CLOSED (service recovered)")
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.now()
        self.half_open_successes = 0
        self.failures = []
        self.stats.state_changes += 1
    
    def _check_half_open(self):
        """Check if we should try half-open state."""
        if self.state == CircuitState.OPEN:
            elapsed = (datetime.now() - self.last_state_change).total_seconds()
            if elapsed >= self.cooldown_seconds:
                logger.info(f"🟡 {self.name}: Circuit HALF-OPEN (testing recovery)")
                self.state = CircuitState.HALF_OPEN
                self.half_open_successes = 0
                self.last_state_change = datetime.now()
                self.stats.state_changes += 1
    
    def should_allow_request(self) -> bool:
        """
        Check if a request should be allowed through.
        
        Returns True if the request should proceed.
        Returns False if it should be rejected (circuit is open).
        """
        self._check_half_open()
        
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.HALF_OPEN:
            return True  # Allow test requests
        
        # Circuit is open - reject
        self.stats.rejected_count += 1
        logger.debug(f"⚡ {self.name}: Request rejected (circuit open)")
        return False
    
    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """
        Execute a function through the circuit breaker.
        
        If circuit is open, returns fallback instead.
        """
        self.stats.total_calls += 1
        
        if not self.should_allow_request():
            if self.fallback:
                return await self.fallback(*args, **kwargs) if asyncio.iscoroutinefunction(self.fallback) else self.fallback(*args, **kwargs)
            raise CircuitOpenError(f"Circuit {self.name} is open")
        
        try:
            result = await func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_failure(e)
            raise
    
    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        self._check_half_open()  # Update state if needed
        
        return {
            "name": self.name,
            "state": self.state.value,
            "failures_in_window": len(self.failures),
            "failure_threshold": self.failure_threshold,
            "seconds_until_retry": max(0, self.cooldown_seconds - (datetime.now() - self.last_state_change).total_seconds()) if self.state == CircuitState.OPEN else 0,
            "half_open_successes": self.half_open_successes,
            "stats": {
                "total_calls": self.stats.total_calls,
                "success_count": self.stats.success_count,
                "failure_count": self.stats.failure_count,
                "rejected_count": self.stats.rejected_count,
                "state_changes": self.stats.state_changes
            }
        }


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""
    pass


# ============================================================================
# CIRCUIT MANAGER
# ============================================================================

class CircuitManager:
    """
    Manages circuit breakers for multiple services.
    """
    
    def __init__(self):
        self.circuits: Dict[str, CircuitBreaker] = {}
        self._create_default_circuits()
    
    def _create_default_circuits(self):
        """Create circuit breakers for known services."""
        default_services = [
            ("claude_api", "Claude API calls"),
            ("openai_api", "OpenAI API calls"),
            ("gemini_api", "Gemini API calls"),
            ("telegram", "Telegram API calls"),
            ("mem0", "Mem0 memory service"),
            ("whaletrack", "WhaleTrack trading API"),
            ("consciousness_optimizer", "Consciousness optimizer service"),
        ]
        
        for service_id, description in default_services:
            self.circuits[service_id] = CircuitBreaker(name=service_id)
    
    def get_circuit(self, name: str) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.circuits:
            self.circuits[name] = CircuitBreaker(name=name)
        return self.circuits[name]
    
    def record_failure(self, name: str, error: Exception = None):
        """Record a failure for a service."""
        circuit = self.get_circuit(name)
        circuit.record_failure(error)
    
    def record_success(self, name: str):
        """Record a success for a service."""
        circuit = self.get_circuit(name)
        circuit.record_success()
    
    def should_allow(self, name: str) -> bool:
        """Check if requests should be allowed for a service."""
        circuit = self.get_circuit(name)
        return circuit.should_allow_request()
    
    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all circuit breakers."""
        return {
            name: circuit.get_status()
            for name, circuit in self.circuits.items()
        }
    
    def get_open_circuits(self) -> Dict[str, Any]:
        """Get only the open circuit breakers."""
        return {
            name: circuit.get_status()
            for name, circuit in self.circuits.items()
            if circuit.state != CircuitState.CLOSED
        }
    
    def reset_circuit(self, name: str):
        """Manually reset a circuit to closed state."""
        if name in self.circuits:
            circuit = self.circuits[name]
            circuit.state = CircuitState.CLOSED
            circuit.failures = []
            circuit.half_open_successes = 0
            circuit.last_state_change = datetime.now()
            logger.info(f"⚡ {name}: Circuit manually reset to CLOSED")


# ============================================================================
# DECORATOR
# ============================================================================

def circuit_protected(circuit_name: str, fallback: Callable = None):
    """
    Decorator to protect a function with a circuit breaker.
    
    Usage:
        @circuit_protected("claude_api")
        async def call_claude(message):
            return await claude.messages.create(...)
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            manager = get_circuit_manager()
            circuit = manager.get_circuit(circuit_name)
            
            if fallback:
                circuit.fallback = fallback
            
            return await circuit.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# SINGLETON
# ============================================================================

_circuit_manager: Optional[CircuitManager] = None


def get_circuit_manager() -> CircuitManager:
    """Get or create circuit manager."""
    global _circuit_manager
    if _circuit_manager is None:
        _circuit_manager = CircuitManager()
    return _circuit_manager









