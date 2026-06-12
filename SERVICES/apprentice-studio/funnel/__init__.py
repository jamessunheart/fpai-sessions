"""
Apprentice Studio Funnel — end-to-end recruiting pipeline.

Single source of truth for every candidate's state from inbound/outbound to
hire. Drives all comms drafts (which go to outbox/ for human review before
sending). Exposes a CLI so the human's interface is one command.
"""

from .pipeline import Funnel, get_funnel
from .stages import Stage, Decision, Candidate

__all__ = ["Funnel", "get_funnel", "Stage", "Decision", "Candidate"]
