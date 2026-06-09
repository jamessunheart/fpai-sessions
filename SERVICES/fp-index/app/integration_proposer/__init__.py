"""Integration Proposer — Step 4 of the self-assembly loop.

Reads the gap registry, picks highest-leverage gaps, generates concrete
integration proposals (code scaffold + test plan + rollout plan + risks),
runs each through the conscience gate (regenerative vs extractive scoring),
and writes them to proposals.jsonl for human review.

Never auto-deploys. Proposals require explicit approval via API.
"""

from .proposer import (
    PROPOSER_VERSION,
    rank_candidate_gaps,
    generate_proposal,
    propose_from_top_gap,
)
from .conscience import score_regenerative_alignment, CONSCIENCE_VERSION
from .registry import (
    PROPOSALS_PATH,
    append_proposal,
    read_proposals,
    pending_proposals,
    update_proposal_status,
)

__all__ = [
    "PROPOSER_VERSION", "CONSCIENCE_VERSION", "PROPOSALS_PATH",
    "rank_candidate_gaps", "generate_proposal", "propose_from_top_gap",
    "score_regenerative_alignment",
    "append_proposal", "read_proposals", "pending_proposals",
    "update_proposal_status",
]
