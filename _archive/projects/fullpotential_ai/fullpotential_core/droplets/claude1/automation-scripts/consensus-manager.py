#!/usr/bin/env python3
"""
Consensus Manager - Multi-Session Decision Making
Ensures all active sessions reach consensus before major actions
"""

import json
import datetime
from pathlib import Path
from typing import Dict, List, Optional

class ConsensusManager:
    """Manage consensus voting across all sessions"""

    def __init__(self):
        self.base_path = Path("/Users/jamessunheart/Development/docs/coordination")
        self.consensus_path = self.base_path / "consciousness"
        self.consensus_path.mkdir(exist_ok=True)

        self.proposals_file = self.consensus_path / "proposals.json"
        self.votes_file = self.consensus_path / "votes.json"
        self.consensus_log_file = self.consensus_path / "consensus_log.jsonl"

    def propose_action(
        self,
        session_id: str,
        action_type: str,
        description: str,
        details: Dict,
        requires_unanimous: bool = False,
        expires_in_hours: int = 24
    ) -> str:
        """Propose an action that requires consensus"""

        proposals = self._load_proposals()

        proposal_id = f"proposal-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

        proposal = {
            "proposal_id": proposal_id,
            "proposer": session_id,
            "action_type": action_type,
            "description": description,
            "details": details,
            "requires_unanimous": requires_unanimous,
            "created_at": datetime.datetime.now().isoformat(),
            "expires_at": (datetime.datetime.now() + datetime.timedelta(hours=expires_in_hours)).isoformat(),
            "status": "pending",
            "votes": {},
            "consensus_reached": False
        }

        proposals[proposal_id] = proposal
        self._save_proposals(proposals)

        print(f"📋 Proposal created: {proposal_id}")
        print(f"   Action: {action_type}")
        print(f"   Description: {description}")
        print(f"   Requires: {'Unanimous' if requires_unanimous else 'Majority'} consensus")

        return proposal_id

    def vote(self, session_id: str, proposal_id: str, vote: str, reasoning: str = "") -> Dict:
        """Cast a vote on a proposal (approve/reject/abstain)"""

        if vote not in ["approve", "reject", "abstain"]:
            raise ValueError("Vote must be 'approve', 'reject', or 'abstain'")

        proposals = self._load_proposals()

        if proposal_id not in proposals:
            return {"error": "Proposal not found"}

        proposal = proposals[proposal_id]

        # Check if expired
        if datetime.datetime.fromisoformat(proposal["expires_at"]) < datetime.datetime.now():
            proposal["status"] = "expired"
            self._save_proposals(proposals)
            return {"error": "Proposal has expired"}

        # Record vote
        proposal["votes"][session_id] = {
            "vote": vote,
            "reasoning": reasoning,
            "timestamp": datetime.datetime.now().isoformat()
        }

        # Check for consensus
        consensus_result = self._check_consensus(proposal)

        if consensus_result["reached"]:
            proposal["consensus_reached"] = True
            proposal["status"] = "approved" if consensus_result["approved"] else "rejected"
            proposal["consensus_type"] = consensus_result["type"]
            proposal["final_tally"] = consensus_result["tally"]

            # Log consensus
            self._log_consensus(proposal)

        proposals[proposal_id] = proposal
        self._save_proposals(proposals)

        print(f"🗳️  Vote recorded: {session_id} → {vote}")
        if consensus_result["reached"]:
            print(f"✅ Consensus reached: {proposal['status'].upper()}")

        return {
            "vote_recorded": True,
            "consensus_reached": consensus_result["reached"],
            "consensus_result": proposal.get("status"),
            "current_tally": consensus_result["tally"]
        }

    def get_pending_proposals(self, session_id: Optional[str] = None) -> List[Dict]:
        """Get all pending proposals (optionally filter for a session)"""

        proposals = self._load_proposals()
        pending = []

        for pid, proposal in proposals.items():
            if proposal["status"] == "pending":
                # Check if not expired
                if datetime.datetime.fromisoformat(proposal["expires_at"]) > datetime.datetime.now():
                    # Check if session hasn't voted yet
                    if session_id is None or session_id not in proposal["votes"]:
                        pending.append(proposal)

        return sorted(pending, key=lambda x: x["created_at"], reverse=True)

    def get_proposal_status(self, proposal_id: str) -> Dict:
        """Get current status of a proposal"""

        proposals = self._load_proposals()

        if proposal_id not in proposals:
            return {"error": "Proposal not found"}

        proposal = proposals[proposal_id]

        tally = self._count_votes(proposal)

        return {
            "proposal_id": proposal_id,
            "status": proposal["status"],
            "action_type": proposal["action_type"],
            "description": proposal["description"],
            "created_at": proposal["created_at"],
            "expires_at": proposal["expires_at"],
            "requires_unanimous": proposal["requires_unanimous"],
            "votes": proposal["votes"],
            "tally": tally,
            "consensus_reached": proposal["consensus_reached"]
        }

    def _check_consensus(self, proposal: Dict) -> Dict:
        """Check if consensus has been reached"""

        votes = proposal["votes"]
        requires_unanimous = proposal["requires_unanimous"]

        if not votes:
            return {"reached": False, "tally": {}}

        tally = self._count_votes(proposal)

        total_votes = tally["approve"] + tally["reject"] + tally["abstain"]

        # Unanimous required
        if requires_unanimous:
            if tally["reject"] > 0:
                return {
                    "reached": True,
                    "approved": False,
                    "type": "unanimous_rejected",
                    "tally": tally
                }
            elif tally["approve"] >= self._get_active_session_count():
                return {
                    "reached": True,
                    "approved": True,
                    "type": "unanimous_approved",
                    "tally": tally
                }

        # Majority required
        else:
            # At least 2 votes needed
            if total_votes >= 2:
                if tally["approve"] > tally["reject"]:
                    return {
                        "reached": True,
                        "approved": True,
                        "type": "majority_approved",
                        "tally": tally
                    }
                elif tally["reject"] > tally["approve"]:
                    return {
                        "reached": True,
                        "approved": False,
                        "type": "majority_rejected",
                        "tally": tally
                    }

        return {"reached": False, "tally": tally}

    def _count_votes(self, proposal: Dict) -> Dict:
        """Count votes for a proposal"""

        tally = {"approve": 0, "reject": 0, "abstain": 0}

        for session_id, vote_data in proposal["votes"].items():
            vote = vote_data["vote"]
            if vote in tally:
                tally[vote] += 1

        return tally

    def _get_active_session_count(self) -> int:
        """Get count of active sessions"""

        sessions_file = self.consensus_path / "active_sessions.json"

        if sessions_file.exists():
            sessions = json.loads(sessions_file.read_text())
            return len(sessions)

        return 1  # At least current session

    def _log_consensus(self, proposal: Dict):
        """Log consensus decision"""

        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "proposal_id": proposal["proposal_id"],
            "action_type": proposal["action_type"],
            "description": proposal["description"],
            "status": proposal["status"],
            "consensus_type": proposal.get("consensus_type"),
            "final_tally": proposal.get("final_tally"),
            "votes": proposal["votes"]
        }

        if self.consensus_log_file.exists():
            with open(self.consensus_log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        else:
            self.consensus_log_file.write_text(json.dumps(log_entry) + '\n')

    def _load_proposals(self) -> Dict:
        if self.proposals_file.exists():
            return json.loads(self.proposals_file.read_text())
        return {}

    def _save_proposals(self, proposals: Dict):
        self.proposals_file.write_text(json.dumps(proposals, indent=2))

    def get_consensus_history(self, hours: int = 168) -> List[Dict]:
        """Get consensus decisions from last N hours"""

        if not self.consensus_log_file.exists():
            return []

        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        history = []

        with open(self.consensus_log_file) as f:
            for line in f:
                entry = json.loads(line)
                timestamp = datetime.datetime.fromisoformat(entry["timestamp"])
                if timestamp > cutoff:
                    history.append(entry)

        return sorted(history, key=lambda x: x["timestamp"], reverse=True)


def main():
    """CLI for consensus management"""
    import sys

    cm = ConsensusManager()

    if len(sys.argv) < 2:
        print("""
🗳️  Consensus Manager - Multi-Session Decision Making

Commands:
  propose <session> <type> <description>     - Create proposal
  vote <session> <proposal-id> <vote>        - Vote on proposal (approve/reject/abstain)
  pending [session]                          - Show pending proposals
  status <proposal-id>                       - Get proposal status
  history                                    - Show consensus history

Examples:
  ./consensus-manager.py propose session-1 dns_change "Add wildcard DNS record"
  ./consensus-manager.py vote session-1 proposal-20251115-134530 approve
  ./consensus-manager.py pending session-1
  ./consensus-manager.py status proposal-20251115-134530
        """)
        return

    command = sys.argv[1]

    if command == "propose" and len(sys.argv) >= 5:
        session_id = sys.argv[2]
        action_type = sys.argv[3]
        description = " ".join(sys.argv[4:])

        proposal_id = cm.propose_action(
            session_id=session_id,
            action_type=action_type,
            description=description,
            details={},
            requires_unanimous=action_type in ["dns_change", "credential_update", "system_shutdown"]
        )

        print(f"\n✅ Proposal ID: {proposal_id}")
        print("\nOther sessions can vote with:")
        print(f"  ./consensus-manager.py vote <session-id> {proposal_id} approve")

    elif command == "vote" and len(sys.argv) >= 5:
        session_id = sys.argv[2]
        proposal_id = sys.argv[3]
        vote = sys.argv[4]
        reasoning = " ".join(sys.argv[5:]) if len(sys.argv) > 5 else ""

        result = cm.vote(session_id, proposal_id, vote, reasoning)
        print(json.dumps(result, indent=2))

    elif command == "pending":
        session_id = sys.argv[2] if len(sys.argv) > 2 else None
        proposals = cm.get_pending_proposals(session_id)

        print(f"\n📋 Pending Proposals: {len(proposals)}\n")

        for p in proposals:
            print(f"ID: {p['proposal_id']}")
            print(f"Type: {p['action_type']}")
            print(f"Description: {p['description']}")
            print(f"Proposer: {p['proposer']}")
            print(f"Requires: {'Unanimous' if p['requires_unanimous'] else 'Majority'}")

            tally = cm._count_votes(p)
            print(f"Current votes: ✅{tally['approve']} ❌{tally['reject']} ⊘{tally['abstain']}")
            print(f"Expires: {p['expires_at']}")
            print()

    elif command == "status" and len(sys.argv) >= 3:
        proposal_id = sys.argv[2]
        status = cm.get_proposal_status(proposal_id)
        print(json.dumps(status, indent=2))

    elif command == "history":
        history = cm.get_consensus_history()
        print(f"\n📜 Consensus History: {len(history)} decisions\n")

        for entry in history[:10]:
            print(f"[{entry['timestamp']}] {entry['action_type']}")
            print(f"  {entry['description']}")
            print(f"  Status: {entry['status'].upper()} ({entry.get('consensus_type', 'N/A')})")
            print()

    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    main()
