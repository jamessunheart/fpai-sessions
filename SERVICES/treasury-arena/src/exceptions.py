"""
Custom Exceptions for Treasury Arena

Provides specific exception types for different failure modes in the arena.
"""


class ArenaError(Exception):
    """Base exception for all arena errors"""
    pass


class AllocationError(ArenaError):
    """Raised when capital allocation fails validation"""

    def __init__(self, message: str, attempted: float = 0, available: float = 0):
        super().__init__(message)
        self.attempted = attempted
        self.available = available
        self.overflow = attempted - available


class CapitalConservationError(ArenaError):
    """Raised when capital conservation is violated"""

    def __init__(self, message: str, expected: float = 0, actual: float = 0):
        super().__init__(message)
        self.expected = expected
        self.actual = actual
        self.discrepancy = actual - expected


class ValidationError(ArenaError):
    """Raised when validation checks fail"""

    def __init__(self, message: str, field: str = None, value: Any = None):
        super().__init__(message)
        self.field = field
        self.value = value


class AgentError(ArenaError):
    """Raised when agent operations fail"""

    def __init__(self, message: str, agent_id: str = None):
        super().__init__(message)
        self.agent_id = agent_id


class EvolutionError(ArenaError):
    """Raised when evolution cycle fails"""

    def __init__(self, message: str, cycle_step: str = None):
        super().__init__(message)
        self.cycle_step = cycle_step


class EventSourcingError(ArenaError):
    """Raised when event sourcing operations fail"""

    def __init__(self, message: str, event_id: str = None, event_type: str = None):
        super().__init__(message)
        self.event_id = event_id
        self.event_type = event_type


class GraduationError(ArenaError):
    """Raised when agent graduation fails"""

    def __init__(self, message: str, agent_id: str = None, from_level: str = None, to_level: str = None):
        super().__init__(message)
        self.agent_id = agent_id
        self.from_level = from_level
        self.to_level = to_level


from typing import Any  # Add typing import for Any
