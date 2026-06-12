# Continuity Intelligence System
from .engine import CIS, get_cis, parse_state_input, parse_outcome_input
from .handler import handle_cis_message, proactive_check
from .threads import (
    get_thread_manager, extract_threads, process_message_threads,
    get_active_threads, get_thread_context, Thread
)
from .sensors import sense_all, AggregatedState
from .learning import (
    run_learning_cycle, get_timing_preference, get_action_weight,
    get_learning_engine, LearningReport
)
from .decisions import decide, get_decision_engine, Decision

__all__ = [
    # Core
    'CIS', 'get_cis', 'parse_state_input', 'parse_outcome_input', 
    'handle_cis_message', 'proactive_check',
    # Threads
    'get_thread_manager', 'extract_threads', 'process_message_threads',
    'get_active_threads', 'get_thread_context', 'Thread',
    # Sensors
    'sense_all', 'AggregatedState',
    # Learning
    'run_learning_cycle', 'get_timing_preference', 'get_action_weight',
    'get_learning_engine', 'LearningReport',
    # Decisions
    'decide', 'get_decision_engine', 'Decision'
]

