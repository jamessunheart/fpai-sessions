"""
voting-weight-tracker - TIE Voting Weight Tracking & 2:1 Governance Enforcement
Port 8922
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .database import init_db, get_db
from .models import (
    AddVotesRequest,
    AddVotesResponse,
    UpdateVotesRequest,
    UpdateVotesResponse,
    WalletVotingPower,
    GovernanceStatus,
    TopVoter,
    LeaderboardResponse,
    VotingHistoryResponse,
    VotingEventResponse,
    HealthResponse
)
from . import crud
from .cache import cache_client

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown"""
    logger.info("🚀 Starting voting-weight-tracker (Port 8922)")

    # Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # Connect Redis
    await cache_client.connect()
    logger.info("✅ Redis cache connected")

    yield

    # Cleanup
    await cache_client.disconnect()
    logger.info("👋 Shutdown complete")


app = FastAPI(
    title="voting-weight-tracker",
    description="TIE Voting Weight Tracking & 2:1 Governance Enforcement",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/voting/add", response_model=AddVotesResponse, status_code=201)
async def add_votes(
    request: AddVotesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Add voting weight to wallet (called by tie-contract-manager on mint).

    When a TIE contract is minted, the holder receives 2 votes.
    """
    try:
        logger.info(f"Adding {request.votes} votes to {request.wallet} (contract: {request.contract_id})")

        # Add votes to wallet
        voting_power = await crud.add_votes(
            db=db,
            wallet=request.wallet,
            votes=request.votes,
            contract_id=request.contract_id,
            event_type=request.event_type
        )

        # Recalculate governance metrics
        governance = await crud.get_governance_status(db)

        # Update cache
        await cache_client.set_governance_status(governance)

        # Check stability
        if governance.holder_control_percentage < 55.0:
            logger.warning(f"⚠️  Holder control at {governance.holder_control_percentage}% (below 55%)")

        return AddVotesResponse(
            wallet=voting_power.wallet,
            total_votes=voting_power.total_votes,
            holder_votes=voting_power.holder_votes,
            seller_votes=voting_power.seller_votes
        )

    except Exception as e:
        logger.error(f"Failed to add votes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voting/update", response_model=UpdateVotesResponse)
async def update_votes(
    request: UpdateVotesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update voting weight when contract is redeemed.

    When a TIE contract is redeemed, voting weight transitions from 2 (holder) to 1 (seller).
    """
    try:
        logger.info(f"Updating votes for {request.wallet}: {request.old_votes}→{request.new_votes} (contract: {request.contract_id})")

        # Update votes
        voting_power = await crud.update_votes(
            db=db,
            wallet=request.wallet,
            contract_id=request.contract_id,
            old_votes=request.old_votes,
            new_votes=request.new_votes,
            event_type=request.event_type
        )

        # Recalculate governance metrics
        governance = await crud.get_governance_status(db)

        # Update cache
        await cache_client.set_governance_status(governance)

        # Check stability and alert if needed
        if governance.holder_control_percentage < 52.0:
            logger.error(f"🚨 URGENT: Holder control at {governance.holder_control_percentage}% (below 52%)")
            # TODO: Alert governance-guardian
        elif governance.holder_control_percentage < 55.0:
            logger.warning(f"⚠️  Holder control at {governance.holder_control_percentage}% (below 55%)")

        vote_delta = request.new_votes - request.old_votes

        return UpdateVotesResponse(
            wallet=voting_power.wallet,
            total_votes=voting_power.total_votes,
            holder_votes=voting_power.holder_votes,
            seller_votes=voting_power.seller_votes,
            vote_delta=vote_delta
        )

    except Exception as e:
        logger.error(f"Failed to update votes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voting/wallet/{wallet}", response_model=WalletVotingPower)
async def get_wallet_voting_power(
    wallet: str,
    db: AsyncSession = Depends(get_db)
):
    """Get voting power for a specific wallet."""
    try:
        voting_power = await crud.get_wallet_voting_power(db, wallet)

        if not voting_power:
            return WalletVotingPower(
                wallet=wallet,
                total_votes=0,
                holder_votes=0,
                seller_votes=0,
                held_contracts=0,
                redeemed_contracts=0
            )

        return voting_power

    except Exception as e:
        logger.error(f"Failed to get wallet voting power: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voting/governance", response_model=GovernanceStatus)
async def get_governance_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Get current system governance status.

    Called by governance-guardian to monitor holder control percentage.
    """
    try:
        # Try cache first
        cached = await cache_client.get_governance_status()
        if cached:
            return cached

        # Calculate from database
        governance = await crud.get_governance_status(db)

        # Update cache
        await cache_client.set_governance_status(governance)

        return governance

    except Exception as e:
        logger.error(f"Failed to get governance status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voting/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get top voters by total voting power."""
    try:
        top_voters = await crud.get_top_voters(db, limit)

        # Calculate total votes for percentages
        governance = await crud.get_governance_status(db)
        total_votes = governance.total_votes if governance.total_votes > 0 else 1

        voters_with_percentage = [
            TopVoter(
                wallet=v.wallet,
                total_votes=v.total_votes,
                holder_votes=v.holder_votes,
                seller_votes=v.seller_votes,
                vote_percentage=round((v.total_votes / total_votes) * 100, 2)
            )
            for v in top_voters
        ]

        return LeaderboardResponse(top_voters=voters_with_percentage)

    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/voting/history", response_model=VotingHistoryResponse)
async def get_voting_history(
    wallet: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get voting event history (optionally filtered by wallet)."""
    try:
        events = await crud.get_voting_history(db, wallet, limit)

        event_responses = [
            VotingEventResponse(
                timestamp=e.timestamp,
                wallet=e.wallet,
                contract_id=e.contract_id,
                event_type=e.event_type,
                vote_change=e.vote_change,
                new_total=e.new_total_votes
            )
            for e in events
        ]

        return VotingHistoryResponse(events=event_responses)

    except Exception as e:
        logger.error(f"Failed to get voting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Check database
        governance = await crud.get_governance_status(db)

        # Check Redis
        cache_connected = await cache_client.is_connected()

        return HealthResponse(
            status="healthy",
            database="connected",
            cache="connected" if cache_connected else "disconnected",
            holder_control=governance.holder_control_percentage,
            governance_stable=governance.is_stable
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            database="error",
            cache="error",
            holder_control=0.0,
            governance_stable=False
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "voting-weight-tracker",
        "version": "1.0.0",
        "port": 8922,
        "status": "operational",
        "purpose": "TIE Voting Weight Tracking & 2:1 Governance Enforcement"
    }
