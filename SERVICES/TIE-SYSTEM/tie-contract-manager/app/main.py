"""
tie-contract-manager - TIE NFT Contract Issuance & Management
Mints NFTs representing 2x value of deposited SOL
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Optional
import httpx

from app.models import (
    MintContractRequest, MintContractResponse,
    RedeemContractRequest, RedeemContractResponse,
    UserContracts, TIEContract, ContractStatus
)
from app.database import get_db, init_db, AsyncSession
from app import crud
from app.nft_client import NFTClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global NFT client
nft_client: Optional[NFTClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    logger.info("🚀 Starting tie-contract-manager...")
    await init_db()
    logger.info("✅ Database initialized")

    global nft_client
    nft_client = NFTClient()
    await nft_client.connect()
    logger.info("✅ NFT client connected")

    yield

    logger.info("👋 Shutting down...")
    await nft_client.disconnect()


app = FastAPI(
    title="tie-contract-manager",
    description="TIE NFT Contract Issuance & Management",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/contracts/mint", response_model=MintContractResponse, status_code=201)
async def mint_contract(
    request: MintContractRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Mint new TIE contract NFT.
    Called by sol-treasury-core when deposit is confirmed.
    """
    try:
        # Calculate contract value (2x deposited)
        contract_value = request.sol_deposited * 2

        # Generate contract ID
        contract_id = await crud.generate_contract_id(db)

        # Mint NFT on Solana
        nft_mint = await nft_client.mint_tie_contract(
            owner=request.wallet,
            sol_deposited=request.sol_deposited,
            contract_value=contract_value,
            contract_id=contract_id,
            deposit_tx=request.deposit_tx
        )

        # Create database record
        contract = await crud.create_contract(
            db=db,
            contract_id=contract_id,
            nft_mint=nft_mint,
            owner=request.wallet,
            sol_deposited=request.sol_deposited,
            contract_value=contract_value,
            deposit_tx=request.deposit_tx,
            status=ContractStatus.HELD,
            voting_weight=2
        )

        # Notify voting-weight-tracker
        await notify_voting_tracker_add(
            wallet=request.wallet,
            votes=2,
            contract_id=contract_id
        )

        logger.info(f"Minted TIE contract {contract_id} for {request.wallet}")

        return MintContractResponse(
            contract_id=contract_id,
            nft_mint=nft_mint,
            contract_value=contract_value,
            voting_weight=2
        )

    except Exception as e:
        logger.error(f"Mint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contracts/{wallet}", response_model=UserContracts)
async def get_user_contracts(
    wallet: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all contracts for a wallet address"""
    try:
        contracts = await crud.get_user_contracts(db, wallet)

        held = [c for c in contracts if c.status == ContractStatus.HELD]
        redeemed = [c for c in contracts if c.status == ContractStatus.REDEEMED]

        total_voting_power = sum(c.voting_weight for c in contracts)

        return UserContracts(
            wallet=wallet,
            held_contracts=held,
            redeemed_contracts=redeemed,
            total_held=len(held),
            total_redeemed=len(redeemed),
            total_voting_power=total_voting_power
        )

    except Exception as e:
        logger.error(f"Get contracts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contracts/nft/{mint_address}", response_model=TIEContract)
async def get_contract_by_mint(
    mint_address: str,
    db: AsyncSession = Depends(get_db)
):
    """Get contract details by NFT mint address"""
    try:
        contract = await crud.get_contract_by_mint(db, mint_address)

        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        return contract

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get contract error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/contracts/redeem", response_model=RedeemContractResponse)
async def redeem_contract(
    request: RedeemContractRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Mark contract as redeemed.
    Called by redemption-algorithm after approval.
    """
    try:
        # Verify authorization from redemption-algorithm
        # TODO: Verify request.authorization signature

        # Get contract
        contract = await crud.get_contract_by_mint(db, request.nft_mint)

        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found")

        if contract.status == ContractStatus.REDEEMED:
            raise HTTPException(status_code=400, detail="Contract already redeemed")

        if contract.owner != request.redeemer:
            raise HTTPException(status_code=403, detail="Not contract owner")

        # Update contract status
        old_weight = contract.voting_weight
        new_weight = 1  # Redeemed contracts get 1 vote

        await crud.update_contract_status(
            db=db,
            contract_id=contract.contract_id,
            status=ContractStatus.REDEEMED,
            voting_weight=new_weight
        )

        # Update NFT metadata on-chain
        await nft_client.update_contract_metadata(
            nft_mint=request.nft_mint,
            status=ContractStatus.REDEEMED,
            voting_weight=new_weight
        )

        # Notify voting-weight-tracker
        await notify_voting_tracker_update(
            wallet=request.redeemer,
            contract_id=contract.contract_id,
            old_weight=old_weight,
            new_weight=new_weight
        )

        logger.info(f"Redeemed contract {contract.contract_id} for {request.redeemer}")

        return RedeemContractResponse(
            redeemed=True,
            voting_weight_updated=new_weight
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Redeem error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "ok",
        "service": "tie-contract-manager",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "nft_client_connected": nft_client is not None and nft_client.is_connected()
    }


# Helper functions for service integration

async def notify_voting_tracker_add(wallet: str, votes: int, contract_id: str):
    """Notify voting-weight-tracker of new contract"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8922/voting/add",
                json={
                    "wallet": wallet,
                    "votes": votes,
                    "contract_id": contract_id
                },
                timeout=5.0
            )
            response.raise_for_status()
            logger.info(f"Notified voting tracker: +{votes} votes for {wallet}")

    except Exception as e:
        logger.error(f"Failed to notify voting tracker: {e}")
        # Don't fail minting if voting tracker is down


async def notify_voting_tracker_update(
    wallet: str,
    contract_id: str,
    old_weight: int,
    new_weight: int
):
    """Notify voting-weight-tracker of contract redemption"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8922/voting/update",
                json={
                    "wallet": wallet,
                    "contract_id": contract_id,
                    "old_weight": old_weight,
                    "new_weight": new_weight
                },
                timeout=5.0
            )
            response.raise_for_status()
            logger.info(f"Notified voting tracker: {wallet} {old_weight}→{new_weight} votes")

    except Exception as e:
        logger.error(f"Failed to notify voting tracker: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8921)
