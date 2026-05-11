"""Work coordination - prevent duplicate work claims"""
import logging
from typing import Dict, Optional
from datetime import datetime
from .models import WorkClaim, WorkClaimStatus

logger = logging.getLogger(__name__)


class WorkCoordinator:
    """Manages work claims to prevent conflicts"""

    def __init__(self):
        # work_id -> WorkClaim
        self.active_claims: Dict[str, WorkClaim] = {}

    def claim_work(self, work_id: str, session_id: str, description: str) -> tuple[bool, str]:
        """
        Attempt to claim work atomically
        Returns: (success: bool, message: str)
        """
        # Check if already claimed
        if work_id in self.active_claims:
            existing_claim = self.active_claims[work_id]

            if existing_claim.status == WorkClaimStatus.CLAIMED:
                return False, f"Work already claimed by {existing_claim.claimed_by}"

            elif existing_claim.status == WorkClaimStatus.COMPLETED:
                return False, f"Work already completed by {existing_claim.claimed_by}"

        # Claim is available
        claim = WorkClaim(
            work_id=work_id,
            claimed_by=session_id,
            claimed_at=datetime.utcnow(),
            description=description,
            status=WorkClaimStatus.CLAIMED
        )

        self.active_claims[work_id] = claim

        logger.info(f"Work claimed: {work_id} by {session_id}")

        return True, f"Work claimed successfully"

    def release_work(self, work_id: str, session_id: str) -> tuple[bool, str]:
        """
        Release a work claim
        Returns: (success: bool, message: str)
        """
        if work_id not in self.active_claims:
            return False, "Work not found"

        claim = self.active_claims[work_id]

        # Only the owner can release
        if claim.claimed_by != session_id:
            return False, f"Work claimed by {claim.claimed_by}, not {session_id}"

        claim.status = WorkClaimStatus.RELEASED

        # Remove from active claims
        del self.active_claims[work_id]

        logger.info(f"Work released: {work_id} by {session_id}")

        return True, "Work released"

    def complete_work(self, work_id: str, session_id: str) -> tuple[bool, str]:
        """
        Mark work as completed
        Returns: (success: bool, message: str)
        """
        if work_id not in self.active_claims:
            return False, "Work not found"

        claim = self.active_claims[work_id]

        # Only the owner can complete
        if claim.claimed_by != session_id:
            return False, f"Work claimed by {claim.claimed_by}, not {session_id}"

        claim.status = WorkClaimStatus.COMPLETED
        claim.completed_at = datetime.utcnow()

        logger.info(f"Work completed: {work_id} by {session_id}")

        return True, "Work completed"

    def release_session_work(self, session_id: str):
        """Release all work claimed by a session (e.g., on disconnect)"""
        released = []

        for work_id, claim in list(self.active_claims.items()):
            if claim.claimed_by == session_id and claim.status == WorkClaimStatus.CLAIMED:
                claim.status = WorkClaimStatus.RELEASED
                del self.active_claims[work_id]
                released.append(work_id)

        if released:
            logger.info(f"Auto-released work for {session_id}: {released}")

        return released

    def get_claimed_work(self) -> list[WorkClaim]:
        """Get all currently claimed work"""
        return [
            claim for claim in self.active_claims.values()
            if claim.status == WorkClaimStatus.CLAIMED
        ]

    def get_session_work(self, session_id: str) -> list[WorkClaim]:
        """Get work claimed by a specific session"""
        return [
            claim for claim in self.active_claims.values()
            if claim.claimed_by == session_id
        ]

    def is_claimed(self, work_id: str) -> bool:
        """Check if work is currently claimed"""
        return work_id in self.active_claims and \
            self.active_claims[work_id].status == WorkClaimStatus.CLAIMED
