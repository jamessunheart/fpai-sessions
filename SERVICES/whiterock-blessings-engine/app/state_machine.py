"""
WhiteRock Blessings Engine - Blessing State Machine
Formal state transitions with validation and logging.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from app.schemas import BlessingStatusEnum

# Valid state transitions map
VALID_TRANSITIONS: Dict[str, List[str]] = {
    "draft": ["pending"],
    "pending": ["committee_review"],
    "committee_review": ["info_requested", "approved", "denied"],
    "info_requested": ["committee_review"],
    "approved": ["disbursed"],
    "disbursed": ["closed"],
    "denied": ["closed"],
    "closed": []  # Terminal state
}

# States requiring compliance flag for transition
REQUIRES_COMPLIANCE_FLAG = ["approved"]

# States that are terminal
TERMINAL_STATES = ["closed"]

# States that allow member viewing
MEMBER_VISIBLE_STATES = [
    "draft", "pending", "committee_review", "info_requested",
    "approved", "denied", "disbursed", "closed"
]


class StateTransitionError(Exception):
    """Error raised when state transition is invalid."""
    def __init__(self, current_state: str, new_state: str, reason: str):
        self.current_state = current_state
        self.new_state = new_state
        self.reason = reason
        super().__init__(f"Cannot transition from '{current_state}' to '{new_state}': {reason}")


def validate_transition(
    current_state: str,
    new_state: str,
    compliance_flag: Optional[bool] = None,
    amount_approved_cents: Optional[int] = None,
    denial_reason: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate if a state transition is allowed.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if current state exists
    if current_state not in VALID_TRANSITIONS:
        return False, f"Unknown current state: {current_state}"
    
    # Check if new state is valid from current state
    allowed_states = VALID_TRANSITIONS[current_state]
    if new_state not in allowed_states:
        return False, f"Invalid transition: '{current_state}' → '{new_state}'. Allowed: {allowed_states}"
    
    # Check compliance flag requirement for approval
    if new_state in REQUIRES_COMPLIANCE_FLAG:
        if not compliance_flag:
            return False, "Compliance flag must be set to true for approval"
        if amount_approved_cents is None or amount_approved_cents <= 0:
            return False, "Approved amount required for approval"
    
    # Check denial reason requirement
    if new_state == "denied":
        if not denial_reason:
            return False, "Denial reason required"
    
    return True, None


def create_transition_log_entry(
    from_state: str,
    to_state: str,
    actor_id: int,
    notes: Optional[str] = None
) -> dict:
    """Create a state transition log entry."""
    return {
        "from": from_state,
        "to": to_state,
        "timestamp": datetime.utcnow().isoformat(),
        "actor_id": actor_id,
        "notes": notes
    }


def get_allowed_transitions(current_state: str) -> List[str]:
    """Get list of allowed transitions from current state."""
    return VALID_TRANSITIONS.get(current_state, [])


def is_terminal_state(state: str) -> bool:
    """Check if a state is terminal (no further transitions)."""
    return state in TERMINAL_STATES


def can_member_view(state: str) -> bool:
    """Check if a member can view a request in this state."""
    return state in MEMBER_VISIBLE_STATES


def sanitize_state_history_for_member(state_history: List[dict]) -> List[dict]:
    """
    Remove internal notes from state history for member viewing.
    Committee notes should not be visible to members.
    """
    return [
        {k: v for k, v in entry.items() if k != "notes"}
        for entry in state_history
    ]


def get_state_display_name(state: str) -> str:
    """Get human-readable state name."""
    display_names = {
        "draft": "Draft",
        "pending": "Pending Review",
        "committee_review": "Under Committee Review",
        "info_requested": "Additional Information Requested",
        "approved": "Approved",
        "denied": "Denied",
        "disbursed": "Disbursed",
        "closed": "Closed"
    }
    return display_names.get(state, state.title())


def get_member_notification_message(new_state: str, denial_reason: Optional[str] = None) -> str:
    """Get notification message for member when state changes."""
    messages = {
        "pending": "Your blessing request has been submitted and is pending review.",
        "committee_review": "Your request is now being reviewed by the Distribution Committee.",
        "info_requested": "The Committee has requested additional information for your blessing request.",
        "approved": "Your blessing request has been approved! Disbursement will be processed soon.",
        "denied": f"Your blessing request was not approved at this time. {denial_reason or ''}",
        "disbursed": "Your blessing has been disbursed. Thank you for being part of WhiteRock community.",
        "closed": "Your blessing request has been closed."
    }
    return messages.get(new_state, f"Your request status has been updated to: {get_state_display_name(new_state)}")



