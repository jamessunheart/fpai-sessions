"""
WhiteRock Blessings Engine - State Machine Tests
Critical tests for blessing request state transitions.
"""

import pytest
from app.state_machine import (
    validate_transition, create_transition_log_entry,
    get_allowed_transitions, is_terminal_state,
    sanitize_state_history_for_member, VALID_TRANSITIONS
)


class TestStateTransitionValidation:
    """Tests for state transition validation."""
    
    def test_valid_draft_to_pending(self):
        """Test valid transition from draft to pending."""
        is_valid, error = validate_transition("draft", "pending")
        assert is_valid == True
        assert error is None
    
    def test_valid_pending_to_committee_review(self):
        """Test valid transition from pending to committee_review."""
        is_valid, error = validate_transition("pending", "committee_review")
        assert is_valid == True
    
    def test_valid_committee_review_to_approved(self):
        """Test valid approval with compliance flag and amount."""
        is_valid, error = validate_transition(
            "committee_review", "approved",
            compliance_flag=True,
            amount_approved_cents=10000
        )
        assert is_valid == True
    
    def test_invalid_approval_without_compliance_flag(self):
        """Test approval fails without compliance flag."""
        is_valid, error = validate_transition(
            "committee_review", "approved",
            compliance_flag=False,
            amount_approved_cents=10000
        )
        assert is_valid == False
        assert "compliance flag" in error.lower()
    
    def test_invalid_approval_without_amount(self):
        """Test approval fails without approved amount."""
        is_valid, error = validate_transition(
            "committee_review", "approved",
            compliance_flag=True,
            amount_approved_cents=None
        )
        assert is_valid == False
        assert "amount" in error.lower()
    
    def test_invalid_denial_without_reason(self):
        """Test denial fails without reason."""
        is_valid, error = validate_transition(
            "committee_review", "denied",
            denial_reason=None
        )
        assert is_valid == False
        assert "reason" in error.lower()
    
    def test_valid_denial_with_reason(self):
        """Test valid denial with reason."""
        is_valid, error = validate_transition(
            "committee_review", "denied",
            denial_reason="Insufficient documentation"
        )
        assert is_valid == True
    
    def test_cannot_skip_committee_review(self):
        """Test cannot transition from pending directly to approved."""
        is_valid, error = validate_transition("pending", "approved")
        assert is_valid == False
        assert "invalid transition" in error.lower()
    
    def test_cannot_skip_disbursement(self):
        """Test cannot transition from approved directly to closed."""
        is_valid, error = validate_transition("approved", "closed")
        assert is_valid == False
    
    def test_info_requested_returns_to_review(self):
        """Test info_requested can go back to committee_review."""
        is_valid, error = validate_transition("info_requested", "committee_review")
        assert is_valid == True
    
    def test_closed_is_terminal(self):
        """Test closed state has no valid transitions."""
        is_valid, error = validate_transition("closed", "pending")
        assert is_valid == False
    
    def test_unknown_state(self):
        """Test unknown current state returns error."""
        is_valid, error = validate_transition("unknown_state", "pending")
        assert is_valid == False
        assert "unknown" in error.lower()


class TestStateHelpers:
    """Tests for state machine helper functions."""
    
    def test_get_allowed_transitions(self):
        """Test getting allowed transitions from a state."""
        allowed = get_allowed_transitions("committee_review")
        assert "info_requested" in allowed
        assert "approved" in allowed
        assert "denied" in allowed
        assert "pending" not in allowed
    
    def test_is_terminal_state(self):
        """Test terminal state detection."""
        assert is_terminal_state("closed") == True
        assert is_terminal_state("pending") == False
        assert is_terminal_state("approved") == False
    
    def test_create_transition_log_entry(self):
        """Test transition log entry creation."""
        entry = create_transition_log_entry(
            from_state="pending",
            to_state="committee_review",
            actor_id=123,
            notes="Test notes"
        )
        
        assert entry["from"] == "pending"
        assert entry["to"] == "committee_review"
        assert entry["actor_id"] == 123
        assert entry["notes"] == "Test notes"
        assert "timestamp" in entry
    
    def test_sanitize_state_history_removes_notes(self):
        """Test internal notes are removed for member viewing."""
        history = [
            {"from": "draft", "to": "pending", "actor_id": 1, "notes": None},
            {"from": "pending", "to": "committee_review", "actor_id": 2, "notes": "Internal: check docs"},
        ]
        
        sanitized = sanitize_state_history_for_member(history)
        
        assert len(sanitized) == 2
        for entry in sanitized:
            assert "notes" not in entry


class TestAllValidTransitions:
    """Ensure all transitions in VALID_TRANSITIONS map work."""
    
    @pytest.mark.parametrize("from_state,to_states", VALID_TRANSITIONS.items())
    def test_all_defined_transitions_are_valid(self, from_state, to_states):
        """Test that all defined transitions validate successfully."""
        for to_state in to_states:
            # Provide required fields for special transitions
            kwargs = {}
            if to_state == "approved":
                kwargs = {"compliance_flag": True, "amount_approved_cents": 1000}
            elif to_state == "denied":
                kwargs = {"denial_reason": "Test reason"}
            
            is_valid, error = validate_transition(from_state, to_state, **kwargs)
            assert is_valid == True, f"{from_state} -> {to_state}: {error}"



