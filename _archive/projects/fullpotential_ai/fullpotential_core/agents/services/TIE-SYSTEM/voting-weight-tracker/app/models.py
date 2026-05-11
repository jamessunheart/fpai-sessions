"""
Pydantic models for API request/response validation
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# Request Models

class AddVotesRequest(BaseModel):
    """Request to add voting weight to a wallet (called on contract mint)"""
    wallet: str = Field(..., description="Solana wallet address")
    votes: int = Field(..., description="Number of votes to add (typically 2 for new contracts)")
    contract_id: str = Field(..., description="TIE contract ID")
    event_type: str = Field(default="contract_minted", description="Event type")


class UpdateVotesRequest(BaseModel):
    """Request to update voting weight (called on contract redemption)"""
    wallet: str = Field(..., description="Solana wallet address")
    contract_id: str = Field(..., description="TIE contract ID being redeemed")
    old_votes: int = Field(..., description="Previous vote count (typically 2)")
    new_votes: int = Field(..., description="New vote count (typically 1)")
    event_type: str = Field(default="contract_redeemed", description="Event type")


# Response Models

class AddVotesResponse(BaseModel):
    """Response after adding votes"""
    wallet: str
    total_votes: int
    holder_votes: int
    seller_votes: int


class UpdateVotesResponse(BaseModel):
    """Response after updating votes"""
    wallet: str
    total_votes: int
    holder_votes: int
    seller_votes: int
    vote_delta: int  # Change in voting power (typically -1)


class WalletVotingPower(BaseModel):
    """Voting power details for a specific wallet"""
    wallet: str
    total_votes: int
    holder_votes: int
    seller_votes: int
    held_contracts: int
    redeemed_contracts: int


class GovernanceStatus(BaseModel):
    """System-wide governance status"""
    total_votes: int
    holder_votes: int
    seller_votes: int
    holder_control_percentage: float
    is_stable: bool  # True if holder_control_percentage > 51%
    critical_threshold: float = 51.0
    margin_above_critical: float  # How far above 51% we are
    total_wallets: int
    holder_wallets: int  # Wallets with held contracts (2 votes)
    seller_wallets: int  # Wallets with only redeemed contracts (1 vote)


class TopVoter(BaseModel):
    """Individual voter in leaderboard"""
    wallet: str
    total_votes: int
    holder_votes: int
    seller_votes: int
    vote_percentage: float  # Percentage of total voting power


class LeaderboardResponse(BaseModel):
    """Top voters by total voting power"""
    top_voters: List[TopVoter]


class VotingEventResponse(BaseModel):
    """Individual voting event in history"""
    timestamp: datetime
    wallet: str
    contract_id: str
    event_type: str  # "contract_minted" or "contract_redeemed"
    vote_change: int  # +2 for mint, -1 for redeem
    new_total: int  # Total votes after this event


class VotingHistoryResponse(BaseModel):
    """Voting event history"""
    events: List[VotingEventResponse]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str  # "healthy" or "unhealthy"
    database: str  # "connected" or "error"
    cache: str  # "connected" or "disconnected"
    holder_control: float
    governance_stable: bool
