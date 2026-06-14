"""
Event System for Treasury Arena

All state changes in the arena are captured as events for audit trail and event sourcing.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class Event:
    """Base event class"""
    event_id: str
    event_type: str
    agent_id: Optional[str]
    timestamp: datetime
    data: Dict[str, Any]
    caused_by: Optional[str] = None  # Previous event_id that triggered this

    def to_dict(self) -> Dict:
        """Convert event to dictionary for storage"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'agent_id': self.agent_id,
            'timestamp': self.timestamp.isoformat(),
            'data': json.dumps(self.data),
            'caused_by': self.caused_by
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Event':
        """Create event from dictionary"""
        return cls(
            event_id=data['event_id'],
            event_type=data['event_type'],
            agent_id=data.get('agent_id'),
            timestamp=datetime.fromisoformat(data['timestamp']),
            data=json.loads(data['data']) if isinstance(data['data'], str) else data['data'],
            caused_by=data.get('caused_by')
        )


class AgentSpawned(Event):
    """Event: New agent created"""

    @classmethod
    def create(cls, agent_id: str, strategy: str, virtual_capital: float, params: Dict) -> 'AgentSpawned':
        return cls(
            event_id=str(uuid.uuid4()),
            event_type='AgentSpawned',
            agent_id=agent_id,
            timestamp=datetime.now(),
            data={
                'strategy': strategy,
                'virtual_capital': virtual_capital,
                'params': params
            }
        )


class AgentKilled(Event):
    """Event: Agent terminated"""

    @classmethod
    def create(cls, agent_id: str, reason: str, final_capital: float, fitness: float) -> 'AgentKilled':
        return cls(
            event_id=str(uuid.uuid4()),
            event_type='AgentKilled',
            agent_id=agent_id,
            timestamp=datetime.now(),
            data={
                'reason': reason,
                'final_capital': final_capital,
                'fitness': fitness
            }
        )


class CapitalAllocated(Event):
    """Event: Capital allocated to agent"""

    @classmethod
    def create(
        cls,
        agent_id: str,
        amount: float,
        tier: str,
        total_allocated: float,
        arena_capital: float
    ) -> 'CapitalAllocated':
        return cls(
            event_id=str(uuid.uuid4()),
            event_type='CapitalAllocated',
            agent_id=agent_id,
            timestamp=datetime.now(),
            data={
                'amount': amount,
                'tier': tier,
                'total_allocated': total_allocated,
                'arena_capital': arena_capital,
                'utilization': total_allocated / arena_capital if arena_capital > 0 else 0
            }
        )


class AgentGraduated(Event):
    """Event: Agent graduated to next level"""

    @classmethod
    def create(
        cls,
        agent_id: str,
        from_level: str,
        to_level: str,
        capital_allocated: float,
        fitness: float
    ) -> 'AgentGraduated':
        return cls(
            event_id=str(uuid.uuid4()),
            event_type='AgentGraduated',
            agent_id=agent_id,
            timestamp=datetime.now(),
            data={
                'from_level': from_level,
                'to_level': to_level,
                'capital_allocated': capital_allocated,
                'fitness': fitness
            }
        )


class AgentMutated(Event):
    """Event: Agent mutated from parent"""

    @classmethod
    def create(
        cls,
        agent_id: str,
        parent_id: str,
        mutated_params: Dict,
        caused_by: str
    ) -> 'AgentMutated':
        return cls(
            event_id=str(uuid.uuid4()),
            event_type='AgentMutated',
            agent_id=agent_id,
            timestamp=datetime.now(),
            data={
                'parent_id': parent_id,
                'mutated_params': mutated_params
            },
            caused_by=caused_by
        )


class EvolutionCycleComplete(Event):
    """Event: Evolution cycle completed"""

    @classmethod
    def create(
        cls,
        agents_killed: int,
        agents_spawned: int,
        agents_mutated: int,
        total_active: int,
        total_proving: int,
        total_simulating: int
    ) -> 'EvolutionCycleComplete':
        return cls(
            event_id=str(uuid.uuid4()),
            event_type='EvolutionCycleComplete',
            agent_id=None,  # System event
            timestamp=datetime.now(),
            data={
                'agents_killed': agents_killed,
                'agents_spawned': agents_spawned,
                'agents_mutated': agents_mutated,
                'total_active': total_active,
                'total_proving': total_proving,
                'total_simulating': total_simulating
            }
        )


class CapitalConservationCheck(Event):
    """Event: Capital conservation verified"""

    @classmethod
    def create(
        cls,
        total_capital: float,
        allocated_capital: float,
        conserved: bool,
        discrepancy: float = 0.0
    ) -> 'CapitalConservationCheck':
        return cls(
            event_id=str(uuid.uuid4()),
            event_type='CapitalConservationCheck',
            agent_id=None,  # System event
            timestamp=datetime.now(),
            data={
                'total_capital': total_capital,
                'allocated_capital': allocated_capital,
                'conserved': conserved,
                'discrepancy': discrepancy
            }
        )


class AllocationError(Event):
    """Event: Capital allocation failed validation"""

    @classmethod
    def create(
        cls,
        attempted_allocation: float,
        available_capital: float,
        overflow_amount: float,
        error_message: str
    ) -> 'AllocationError':
        return cls(
            event_id=str(uuid.uuid4()),
            event_type='AllocationError',
            agent_id=None,  # System event
            timestamp=datetime.now(),
            data={
                'attempted_allocation': attempted_allocation,
                'available_capital': available_capital,
                'overflow_amount': overflow_amount,
                'error_message': error_message
            }
        )


# Event type registry
EVENT_TYPES = {
    'AgentSpawned': AgentSpawned,
    'AgentKilled': AgentKilled,
    'CapitalAllocated': CapitalAllocated,
    'AgentGraduated': AgentGraduated,
    'AgentMutated': AgentMutated,
    'EvolutionCycleComplete': EvolutionCycleComplete,
    'CapitalConservationCheck': CapitalConservationCheck,
    'AllocationError': AllocationError
}


def deserialize_event(event_dict: Dict) -> Event:
    """Deserialize event from dictionary"""
    event_type = event_dict.get('event_type')

    if event_type in EVENT_TYPES:
        return EVENT_TYPES[event_type].from_dict(event_dict)
    else:
        # Return base Event for unknown types
        return Event.from_dict(event_dict)
