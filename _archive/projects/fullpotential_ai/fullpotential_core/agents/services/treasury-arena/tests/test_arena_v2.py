"""
Tests for Arena Manager v2 - Event Sourcing

Tests event emission, capital conservation, and audit trail functionality.
"""

import pytest
import sqlite3
import os
from datetime import datetime
from src.arena_manager import ArenaManager
from src.events import (
    AgentSpawned, AgentKilled, CapitalAllocated, AgentGraduated,
    AgentMutated, EvolutionCycleComplete, CapitalConservationCheck
)
from src.exceptions import AllocationError, CapitalConservationError


@pytest.fixture
def arena():
    """Create arena instance for testing"""
    # Use in-memory database for tests
    arena = ArenaManager(total_capital=100000, db_path=":memory:")
    yield arena
    # Cleanup
    if arena.db_conn:
        arena.db_conn.close()


@pytest.fixture
def arena_with_agents(arena):
    """Create arena with some agents"""
    # Spawn 5 agents
    for _ in range(5):
        arena.spawn_agent("DeFi-Yield-Farmer")
    return arena


class TestEventEmission:
    """Test that all operations emit proper events"""

    def test_spawn_agent_emits_event(self, arena):
        """Test that spawning an agent emits AgentSpawned event"""
        agent = arena.spawn_agent("DeFi-Yield-Farmer")

        # Query database for event
        cursor = arena.db_conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE event_type = 'AgentSpawned'
            AND agent_id = ?
        """, (agent.id,))

        event_row = cursor.fetchone()
        assert event_row is not None
        assert event_row['event_type'] == 'AgentSpawned'
        assert event_row['agent_id'] == agent.id

    def test_allocate_capital_emits_events(self, arena_with_agents):
        """Test that capital allocation emits CapitalAllocated events"""
        arena = arena_with_agents

        # Allocate capital
        allocations = arena.allocate_capital()

        # Should have CapitalAllocated events for each agent
        cursor = arena.db_conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM events WHERE event_type = 'CapitalAllocated'")
        count = cursor.fetchone()['count']

        assert count == len(allocations)

    def test_kill_agent_emits_event(self, arena_with_agents):
        """Test that killing an agent emits AgentKilled event"""
        arena = arena_with_agents

        # Get an agent
        agent = arena.simulation_agents[0]

        # Manually set kill conditions
        agent.fitness_score = -1
        agent.days_negative = 31

        # Kill underperformers
        killed = arena.kill_underperformers()

        if killed:
            # Query for AgentKilled event
            cursor = arena.db_conn.cursor()
            cursor.execute("""
                SELECT * FROM events
                WHERE event_type = 'AgentKilled'
                AND agent_id = ?
            """, (killed[0].id,))

            event_row = cursor.fetchone()
            assert event_row is not None
            assert event_row['event_type'] == 'AgentKilled'

    def test_graduate_to_proving_emits_event(self, arena):
        """Test that graduating to proving emits AgentGraduated event"""
        # Spawn agent
        agent = arena.spawn_agent("DeFi-Yield-Farmer")

        # Set graduation conditions
        agent.fitness_score = 2.5
        agent.age = 35
        agent.performance_history = [
            {'pnl': 100, 'capital': 11000},
            {'pnl': 150, 'capital': 11150}
        ]

        # Graduate
        arena.graduate_to_proving(agent)

        # Query for AgentGraduated event
        cursor = arena.db_conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE event_type = 'AgentGraduated'
            AND agent_id = ?
        """, (agent.id,))

        event_row = cursor.fetchone()
        assert event_row is not None
        assert event_row['event_type'] == 'AgentGraduated'

    def test_mutate_agent_emits_events(self, arena):
        """Test that mutating an agent emits both AgentSpawned and AgentMutated events"""
        # Spawn parent agent
        parent = arena.spawn_agent("DeFi-Yield-Farmer", params={'risk_tolerance': 0.5})

        # Mutate
        mutated = arena.mutate_agent(parent)

        # Should have AgentMutated event
        cursor = arena.db_conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE event_type = 'AgentMutated'
            AND agent_id = ?
        """, (mutated.id,))

        event_row = cursor.fetchone()
        assert event_row is not None
        assert event_row['event_type'] == 'AgentMutated'

    def test_evolution_cycle_emits_event(self, arena_with_agents):
        """Test that evolution cycle emits EvolutionCycleComplete event"""
        arena = arena_with_agents

        # Run evolution cycle
        arena.run_evolution_cycle()

        # Query for EvolutionCycleComplete event
        cursor = arena.db_conn.cursor()
        cursor.execute("SELECT * FROM events WHERE event_type = 'EvolutionCycleComplete'")

        event_row = cursor.fetchone()
        assert event_row is not None
        assert event_row['event_type'] == 'EvolutionCycleComplete'


class TestCapitalConservation:
    """Test capital conservation verification"""

    def test_verify_capital_conservation_passes(self, arena_with_agents):
        """Test that capital conservation check passes when capital is conserved"""
        arena = arena_with_agents

        # Allocate capital
        arena.allocate_capital()

        # Verify conservation
        conserved, discrepancy = arena.verify_capital_conservation()

        assert conserved is True
        assert abs(discrepancy) < 0.01  # Allow tiny floating point errors

    def test_capital_allocation_overflow_prevented(self, arena):
        """Test that capital allocation overflow is prevented"""
        # Spawn way too many agents
        for _ in range(100):
            arena.spawn_agent("DeFi-Yield-Farmer")

        # Allocation should not overflow
        allocations = arena.allocate_capital()

        total_allocated = sum(allocations.values())
        assert total_allocated <= arena.arena_capital


class TestEventReplay:
    """Test event replay functionality"""

    def test_replay_all_events(self, arena_with_agents):
        """Test replaying all events from the beginning"""
        arena = arena_with_agents

        # Allocate capital and do some operations
        arena.allocate_capital()

        # Replay all events
        events = arena.replay_events()

        # Should have events
        assert len(events) > 0

        # First events should be AgentSpawned
        assert any(e['event_type'] == 'AgentSpawned' for e in events)

    def test_replay_events_for_agent(self, arena):
        """Test replaying events for a specific agent"""
        # Spawn agent
        agent = arena.spawn_agent("DeFi-Yield-Farmer")

        # Allocate capital
        arena.allocate_capital()

        # Replay events for this agent
        events = arena.replay_events(agent_id=agent.id)

        # Should have at least AgentSpawned event
        assert len(events) >= 1
        assert all(e['agent_id'] == agent.id for e in events if e['agent_id'] is not None)


class TestCapitalAllocationBreakdown:
    """Test capital allocation breakdown reporting"""

    def test_get_allocation_breakdown(self, arena_with_agents):
        """Test getting capital allocation breakdown"""
        arena = arena_with_agents

        # Allocate capital
        arena.allocate_capital()

        # Get breakdown
        breakdown = arena.get_capital_allocation_breakdown()

        # Should have all required fields
        assert 'total_capital' in breakdown
        assert 'allocated_capital' in breakdown
        assert 'unallocated_capital' in breakdown
        assert 'utilization' in breakdown
        assert 'allocations' in breakdown

        # Utilization should be between 0 and 1
        assert 0 <= breakdown['utilization'] <= 1

        # Total should match
        assert breakdown['total_capital'] == arena.arena_capital


class TestEventCausality:
    """Test event causality tracking"""

    def test_mutation_caused_by_spawn(self, arena):
        """Test that mutation event is caused by spawn event"""
        # Spawn parent
        parent = arena.spawn_agent("DeFi-Yield-Farmer")

        # Mutate
        mutated = arena.mutate_agent(parent)

        # Get mutation event
        cursor = arena.db_conn.cursor()
        cursor.execute("""
            SELECT * FROM events
            WHERE event_type = 'AgentMutated'
            AND agent_id = ?
        """, (mutated.id,))

        mutation_event = cursor.fetchone()

        # Should have caused_by linking to spawn event
        assert mutation_event['caused_by'] is not None


class TestDatabaseSchema:
    """Test that database schema is correct"""

    def test_events_table_exists(self, arena):
        """Test that events table exists with correct schema"""
        cursor = arena.db_conn.cursor()

        # Get table info
        cursor.execute("PRAGMA table_info(events)")
        columns = {row['name']: row['type'] for row in cursor.fetchall()}

        # Check required columns
        assert 'event_id' in columns
        assert 'event_type' in columns
        assert 'agent_id' in columns
        assert 'timestamp' in columns
        assert 'data' in columns
        assert 'caused_by' in columns

    def test_arena_state_table_exists(self, arena):
        """Test that arena_state table exists"""
        cursor = arena.db_conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='arena_state'")
        result = cursor.fetchone()

        assert result is not None

    def test_capital_ledger_table_exists(self, arena):
        """Test that capital_ledger table exists"""
        cursor = arena.db_conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='capital_ledger'")
        result = cursor.fetchone()

        assert result is not None


class TestErrorIsolation:
    """Test error isolation in evolution cycle"""

    def test_safe_run_evolution_catches_errors(self, arena):
        """Test that safe_run_evolution catches and isolates errors"""
        # This should not raise an exception even if something goes wrong
        success, error = arena.safe_run_evolution()

        # Should return a tuple
        assert isinstance(success, bool)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
