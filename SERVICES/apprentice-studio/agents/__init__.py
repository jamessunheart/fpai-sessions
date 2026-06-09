"""Apprentice Studio agents — eight AI roles holding the program down."""

from .base import StudioAgent, StudioRole, ProposalArtifact, AgentReport
from .studio_director import StudioDirectorAgent
from .recruiter import RecruiterAgent
from .curriculum import CurriculumAgent
from .builder_mentor import BuilderMentorAgent
from .comms import CommsAgent
from .funding import FundingAgent
from .operations import OperationsAgent
from .aria_coach import AriaCoachAgent

__all__ = [
    "StudioAgent",
    "StudioRole",
    "ProposalArtifact",
    "AgentReport",
    "StudioDirectorAgent",
    "RecruiterAgent",
    "CurriculumAgent",
    "BuilderMentorAgent",
    "CommsAgent",
    "FundingAgent",
    "OperationsAgent",
    "AriaCoachAgent",
]
