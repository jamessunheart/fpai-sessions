#!/usr/bin/env python3
"""
Sequential Consensus Manager
Requires coordinated sequential voting from all sessions with proof
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

class SequentialConsensus:
    """Consensus with sequential proof that sessions coordinated"""

    def __init__(self):
        self.base_path = Path("/Users/jamessunheart/Development/docs/coordination")
        self.consensus_path = self.base_path / "consciousness"
        self.proposals_file = self.consensus_path / "sequential_proposals.json"
        self.session_registry = self.consensus_path / "session_registry.json"

    def create_proposal(self, session_id: str, action: str, description: str) -> dict:
        """Create proposal with sequence number"""

        proposals = self._load_proposals()

        # Get proposal sequence
        proposal_seq = self._get_next_proposal_sequence(proposals)
        proposal_id = f"prop-{proposal_seq:04d}"

        # Get expected vote sequences (one per active session)
        active_sessions = self._get_active_sessions()
        expected_votes = {s["session_id"]: s["sequence_number"] for s in active_sessions}

        proposal = {
            "proposal_id": proposal_id,
            "sequence_number": proposal_seq,
            "proposer": session_id,
            "action": action,
            "description": description,
            "created_at": time.time(),
            "status": "pending",
            "expected_vote_sequences": expected_votes,
            "votes": {},
            "vote_sequence_chain": []  # Track vote order
        }

        proposals[proposal_id] = proposal
        self._save_proposals(proposals)

        print(f"📋 Proposal {proposal_id} created (sequence #{proposal_seq})")
        print(f"   Expected votes from {len(expected_votes)} sessions:")
        for sess_id, seq in expected_votes.items():
            print(f"   • {sess_id} (session #{seq})")

        return proposal

    def vote(self, session_id: str, proposal_id: str, vote: str, vote_nonce: int) -> dict:
        """
        Vote with sequential proof

        vote_nonce: Must be session_sequence + proposal_sequence
        This proves the session knows both numbers and coordinated
        """

        proposals = self._load_proposals()

        if proposal_id not in proposals:
            return {"error": "Proposal not found"}

        proposal = proposals[proposal_id]

        # Verify session is expected to vote
        if session_id not in proposal["expected_vote_sequences"]:
            return {"error": "Session not authorized to vote"}

        # Verify vote nonce (proves coordination)
        expected_nonce = proposal["expected_vote_sequences"][session_id] + proposal["sequence_number"]

        if vote_nonce != expected_nonce:
            return {
                "error": "Invalid vote nonce",
                "expected": expected_nonce,
                "received": vote_nonce,
                "reason": f"Must be session_seq ({proposal['expected_vote_sequences'][session_id]}) + proposal_seq ({proposal['sequence_number']})"
            }

        # Record vote with proof
        vote_data = {
            "vote": vote,
            "timestamp": time.time(),
            "vote_nonce": vote_nonce,
            "verified": True
        }

        proposal["votes"][session_id] = vote_data
        proposal["vote_sequence_chain"].append({
            "session_id": session_id,
            "vote": vote,
            "nonce": vote_nonce,
            "timestamp": vote_data["timestamp"]
        })

        # Check for consensus
        if len(proposal["votes"]) == len(proposal["expected_vote_sequences"]):
            # All sessions voted
            approvals = sum(1 for v in proposal["votes"].values() if v["vote"] == "approve")
            total = len(proposal["votes"])

            if approvals == total:
                proposal["status"] = "approved"
                proposal["consensus_reached_at"] = time.time()
            elif approvals > total / 2:
                proposal["status"] = "majority_approved"
                proposal["consensus_reached_at"] = time.time()
            else:
                proposal["status"] = "rejected"
                proposal["consensus_reached_at"] = time.time()

        proposals[proposal_id] = proposal
        self._save_proposals(proposals)

        result = {
            "vote_recorded": True,
            "session_id": session_id,
            "vote": vote,
            "nonce_verified": True,
            "votes_count": len(proposal["votes"]),
            "expected_count": len(proposal["expected_vote_sequences"]),
            "status": proposal["status"]
        }

        if proposal["status"] != "pending":
            result["consensus_reached"] = True
            result["final_status"] = proposal["status"]

        return result

    def verify_consensus(self, proposal_id: str) -> dict:
        """Verify consensus was reached with proper sequential proof"""

        proposals = self._load_proposals()

        if proposal_id not in proposals:
            return {"error": "Proposal not found"}

        proposal = proposals[proposal_id]

        # Verify all vote nonces
        valid_votes = []
        for session_id, vote_data in proposal["votes"].items():
            expected_nonce = proposal["expected_vote_sequences"][session_id] + proposal["sequence_number"]

            if vote_data["vote_nonce"] == expected_nonce:
                valid_votes.append({
                    "session_id": session_id,
                    "vote": vote_data["vote"],
                    "nonce": vote_data["vote_nonce"],
                    "valid": True
                })
            else:
                valid_votes.append({
                    "session_id": session_id,
                    "vote": vote_data["vote"],
                    "nonce": vote_data["vote_nonce"],
                    "valid": False,
                    "expected": expected_nonce
                })

        all_valid = all(v["valid"] for v in valid_votes)

        return {
            "proposal_id": proposal_id,
            "status": proposal["status"],
            "votes": valid_votes,
            "all_nonces_valid": all_valid,
            "consensus_proven": all_valid and proposal["status"] in ["approved", "majority_approved", "rejected"],
            "vote_chain": proposal["vote_sequence_chain"]
        }

    def _get_next_proposal_sequence(self, proposals: dict) -> int:
        if not proposals:
            return 1
        max_seq = max((p.get("sequence_number", 0) for p in proposals.values()), default=0)
        return max_seq + 1

    def _get_active_sessions(self) -> list:
        if self.session_registry.exists():
            registry = json.loads(self.session_registry.read_text())
            return [s for s in registry.values() if s.get("status") == "active"]
        return []

    def _load_proposals(self) -> dict:
        if self.proposals_file.exists():
            return json.loads(self.proposals_file.read_text())
        return {}

    def _save_proposals(self, proposals: dict):
        self.proposals_file.write_text(json.dumps(proposals, indent=2))


def main():
    import sys

    sc = SequentialConsensus()

    if len(sys.argv) < 2:
        print("""
🔢 Sequential Consensus - Provable Multi-Session Voting

Commands:
  propose <session-id> <action> <description>
  vote <session-id> <proposal-id> <approve|reject> <nonce>
  verify <proposal-id>
  status <proposal-id>

Nonce Calculation:
  vote_nonce = your_session_sequence + proposal_sequence

Example:
  # Session #1 voting on Proposal #3:
  # nonce = 1 + 3 = 4
  ./sequential-consensus.py vote session-0001-abc123 prop-0003 approve 4
        """)
        return

    cmd = sys.argv[1]

    if cmd == "propose" and len(sys.argv) >= 5:
        session_id = sys.argv[2]
        action = sys.argv[3]
        description = " ".join(sys.argv[4:])

        proposal = sc.create_proposal(session_id, action, description)
        print(f"\n✅ Vote using:")
        print(f"   ./sequential-consensus.py vote <session-id> {proposal['proposal_id']} approve <nonce>")

    elif cmd == "vote" and len(sys.argv) >= 6:
        session_id = sys.argv[2]
        proposal_id = sys.argv[3]
        vote = sys.argv[4]
        nonce = int(sys.argv[5])

        result = sc.vote(session_id, proposal_id, vote, nonce)
        print(json.dumps(result, indent=2))

    elif cmd == "verify" and len(sys.argv) >= 3:
        proposal_id = sys.argv[2]
        verification = sc.verify_consensus(proposal_id)
        print(json.dumps(verification, indent=2))

    elif cmd == "status" and len(sys.argv) >= 3:
        proposal_id = sys.argv[2]
        proposals = sc._load_proposals()
        if proposal_id in proposals:
            print(json.dumps(proposals[proposal_id], indent=2))
        else:
            print({"error": "Proposal not found"})


if __name__ == "__main__":
    main()
