#!/usr/bin/env python3
"""
Session Coordinator - Sessions must agree on unique IDs, roles, and goals
All sessions vote to approve each new session's identity
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

class SessionCoordinator:
    """Coordinate session registration with multi-session approval"""

    def __init__(self):
        self.base_path = Path("/Users/jamessunheart/Development/docs/coordination/consciousness")
        self.base_path.mkdir(exist_ok=True)

        self.sessions_file = self.base_path / "coordinated_sessions.json"
        self.pending_file = self.base_path / "pending_registrations.json"
        self.votes_file = self.base_path / "registration_votes.json"

    def propose_session(self, proposed_id: int, role: str, goal: str, proposer_name: str = "") -> dict:
        """
        Propose a new session registration
        Must be approved by all existing sessions
        """

        sessions = self._load_sessions()
        pending = self._load_pending()

        # Check if ID already taken
        if str(proposed_id) in sessions:
            return {
                "error": "Session ID already taken",
                "taken_by": sessions[str(proposed_id)]
            }

        # Check if ID already pending
        for reg_id, reg_data in pending.items():
            if reg_data["proposed_id"] == proposed_id:
                return {
                    "error": "Session ID already pending approval",
                    "pending_registration": reg_id
                }

        # Create registration proposal
        registration_id = f"reg-{int(time.time())}"

        registration = {
            "registration_id": registration_id,
            "proposed_id": proposed_id,
            "role": role,
            "goal": goal,
            "proposer_name": proposer_name or f"session-{proposed_id}",
            "proposed_at": time.time(),
            "status": "pending",
            "votes": {},
            "approved_by": []
        }

        # Get existing sessions that must approve
        existing_sessions = list(sessions.keys())

        if not existing_sessions:
            # First session - auto-approve
            registration["status"] = "approved"
            registration["approved_at"] = time.time()
            self._register_session(proposed_id, role, goal, proposer_name)

            return {
                "registration_id": registration_id,
                "status": "approved",
                "message": "First session - automatically approved",
                "session_id": proposed_id
            }

        registration["requires_approval_from"] = existing_sessions

        pending[registration_id] = registration
        self._save_pending(pending)

        print(f"📋 Registration Proposal Created: {registration_id}")
        print(f"   Proposed ID: #{proposed_id}")
        print(f"   Role: {role}")
        print(f"   Goal: {goal}")
        print(f"   Requires approval from {len(existing_sessions)} existing sessions:")
        for sess_id in existing_sessions:
            sess = sessions[sess_id]
            print(f"   • Session #{sess_id} ({sess['role']})")

        return {
            "registration_id": registration_id,
            "status": "pending",
            "proposed_id": proposed_id,
            "requires_approval_from": existing_sessions,
            "vote_command": f"./session-coordinator.py vote <your-session-id> {registration_id} approve"
        }

    def vote_on_registration(self, voter_session_id: int, registration_id: str, vote: str, reason: str = "") -> dict:
        """
        Vote to approve/reject a session registration
        voter_session_id must be an existing registered session
        """

        sessions = self._load_sessions()
        pending = self._load_pending()

        # Verify voter is registered
        if str(voter_session_id) not in sessions:
            return {
                "error": "Voter session not registered",
                "voter_id": voter_session_id
            }

        # Verify registration exists
        if registration_id not in pending:
            return {
                "error": "Registration not found",
                "registration_id": registration_id
            }

        registration = pending[registration_id]

        # Check if already voted
        if str(voter_session_id) in registration["votes"]:
            return {
                "error": "Already voted",
                "previous_vote": registration["votes"][str(voter_session_id)]
            }

        # Record vote
        registration["votes"][str(voter_session_id)] = {
            "vote": vote,
            "reason": reason,
            "timestamp": time.time()
        }

        # Check for consensus
        required_sessions = set(registration["requires_approval_from"])
        votes_received = set(registration["votes"].keys())

        approvals = sum(1 for v in registration["votes"].values() if v["vote"] == "approve")
        rejections = sum(1 for v in registration["votes"].values() if v["vote"] == "reject")

        consensus_reached = False

        # Unanimous approval required
        if votes_received == required_sessions:
            if approvals == len(required_sessions):
                # APPROVED
                registration["status"] = "approved"
                registration["approved_at"] = time.time()

                # Register the session
                self._register_session(
                    registration["proposed_id"],
                    registration["role"],
                    registration["goal"],
                    registration["proposer_name"]
                )

                consensus_reached = True
                result_status = "APPROVED"

            else:
                # REJECTED
                registration["status"] = "rejected"
                registration["rejected_at"] = time.time()
                consensus_reached = True
                result_status = "REJECTED"

        pending[registration_id] = registration
        self._save_pending(pending)

        result = {
            "vote_recorded": True,
            "voter_id": voter_session_id,
            "vote": vote,
            "votes_received": len(registration["votes"]),
            "votes_required": len(required_sessions),
            "approvals": approvals,
            "rejections": rejections
        }

        if consensus_reached:
            result["consensus_reached"] = True
            result["status"] = result_status
            result["registration_id"] = registration_id

            if result_status == "APPROVED":
                result["session_id"] = registration["proposed_id"]
                print(f"\n✅ CONSENSUS REACHED: Session #{registration['proposed_id']} APPROVED")
                print(f"   Role: {registration['role']}")
                print(f"   Goal: {registration['goal']}")

        return result

    def get_active_sessions(self) -> Dict:
        """Get all active registered sessions"""
        sessions = self._load_sessions()
        return {
            int(k): v for k, v in sessions.items()
        }

    def get_pending_registrations(self) -> List[Dict]:
        """Get all pending registrations"""
        pending = self._load_pending()
        return [
            {**v, "registration_id": k}
            for k, v in pending.items()
            if v["status"] == "pending"
        ]

    def _register_session(self, session_id: int, role: str, goal: str, name: str):
        """Actually register a session after approval"""
        sessions = self._load_sessions()

        sessions[str(session_id)] = {
            "session_id": session_id,
            "role": role,
            "goal": goal,
            "name": name,
            "registered_at": time.time(),
            "status": "active"
        }

        self._save_sessions(sessions)

        print(f"✅ Session #{session_id} registered")

    def _load_sessions(self) -> Dict:
        if self.sessions_file.exists():
            return json.loads(self.sessions_file.read_text())
        return {}

    def _save_sessions(self, sessions: Dict):
        self.sessions_file.write_text(json.dumps(sessions, indent=2))

    def _load_pending(self) -> Dict:
        if self.pending_file.exists():
            return json.loads(self.pending_file.read_text())
        return {}

    def _save_pending(self, pending: Dict):
        self.pending_file.write_text(json.dumps(pending, indent=2))


def main():
    import sys

    sc = SessionCoordinator()

    if len(sys.argv) < 2:
        print("""
🤝 Session Coordinator - Multi-Session Agreement Required

All sessions must agree on unique IDs, roles, and goals

Commands:
  propose <id> <role> <goal> [name]       - Propose new session
  vote <voter-id> <reg-id> <approve|reject> [reason]  - Vote on registration
  sessions                                 - List active sessions
  pending                                  - List pending registrations

Example Flow:
  # Session proposes itself
  ./session-coordinator.py propose 1 "Mission Control" "Coordinate all sessions"

  # Other sessions vote
  ./session-coordinator.py vote 1 reg-1234567890 approve "Good role and goal"
  ./session-coordinator.py vote 2 reg-1234567890 approve "Approved"

  # Once all vote → Session registered!

Roles Examples:
  - Mission Control
  - Security Reviewer
  - Deployment Manager
  - Knowledge Curator
  - Consensus Validator

Goal Examples:
  - Coordinate all sessions toward highest priority
  - Review and approve critical changes
  - Deploy and monitor services
  - Maintain unified knowledge base
  - Validate multi-session consensus
        """)
        return

    cmd = sys.argv[1]

    if cmd == "propose" and len(sys.argv) >= 5:
        proposed_id = int(sys.argv[2])
        role = sys.argv[3]
        goal = sys.argv[4]
        name = sys.argv[5] if len(sys.argv) > 5 else ""

        result = sc.propose_session(proposed_id, role, goal, name)
        print(json.dumps(result, indent=2))

    elif cmd == "vote" and len(sys.argv) >= 5:
        voter_id = int(sys.argv[2])
        reg_id = sys.argv[3]
        vote = sys.argv[4]
        reason = " ".join(sys.argv[5:]) if len(sys.argv) > 5 else ""

        result = sc.vote_on_registration(voter_id, reg_id, vote, reason)
        print(json.dumps(result, indent=2))

    elif cmd == "sessions":
        sessions = sc.get_active_sessions()

        print(f"\n🔗 Active Sessions: {len(sessions)}\n")

        for sess_id, sess in sorted(sessions.items()):
            print(f"Session #{sess_id}")
            print(f"  Role: {sess['role']}")
            print(f"  Goal: {sess['goal']}")
            print(f"  Name: {sess['name']}")
            print()

    elif cmd == "pending":
        pending = sc.get_pending_registrations()

        print(f"\n📋 Pending Registrations: {len(pending)}\n")

        for reg in pending:
            print(f"Registration: {reg['registration_id']}")
            print(f"  Proposed ID: #{reg['proposed_id']}")
            print(f"  Role: {reg['role']}")
            print(f"  Goal: {reg['goal']}")
            print(f"  Votes: {len(reg['votes'])}/{len(reg['requires_approval_from'])}")
            print()

    else:
        print(f"❌ Unknown command: {cmd}")


if __name__ == "__main__":
    main()
