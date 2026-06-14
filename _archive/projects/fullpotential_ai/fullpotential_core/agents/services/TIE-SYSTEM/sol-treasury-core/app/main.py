"""
sol-treasury-core - Python API Service
Wraps Solana smart contract with REST API and event monitoring
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import List, Optional

from app.models import (
    DepositRequest, DepositResponse,
    WithdrawRequest, WithdrawResponse,
    TreasuryBalance, TreasuryControl,
    TransactionHistory, TreasuryTransaction
)
from app.solana_client import SolanaClient
from app.database import get_db, init_db, AsyncSession
from app import crud

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting sol-treasury-core...")
    await init_db()
    logger.info("✅ Database initialized")

    # Initialize Solana client
    global solana_client
    solana_client = SolanaClient()
    await solana_client.connect()
    logger.info("✅ Solana client connected")

    # Start event monitor
    # asyncio.create_task(solana_client.monitor_events())
    # logger.info("✅ Event monitor started")

    yield

    # Shutdown
    logger.info("👋 Shutting down...")
    await solana_client.disconnect()


app = FastAPI(
    title="sol-treasury-core",
    description="TIE System Treasury - SOL custody and capital flow management",
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

# Global Solana client
solana_client: Optional[SolanaClient] = None


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")


manager = ConnectionManager()


# ============================================================================
# API Endpoints
# ============================================================================

@app.post("/treasury/deposit", response_model=DepositResponse, status_code=202)
async def deposit_sol(
    request: DepositRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate SOL deposit to treasury.
    User must sign transaction with their wallet.
    """
    try:
        # Validate amount
        if request.amount_sol <= 0:
            raise HTTPException(status_code=400, detail="Amount must be greater than zero")

        # Prepare deposit transaction
        tx_signature = await solana_client.prepare_deposit(
            wallet_address=request.wallet_address,
            amount_sol=request.amount_sol
        )

        # Calculate TIE contract value (2x deposited)
        tie_contract_value = request.amount_sol * 2

        # Record in database
        transaction = await crud.create_transaction(
            db=db,
            transaction_id=tx_signature,
            wallet_address=request.wallet_address,
            type="deposit",
            amount_sol=request.amount_sol,
            tie_contract_value=tie_contract_value,
            status="pending"
        )

        # Broadcast to WebSocket
        await manager.broadcast({
            "type": "deposit",
            "data": {
                "wallet": request.wallet_address,
                "amount": request.amount_sol,
                "tie_value": tie_contract_value,
                "tx": tx_signature
            }
        })

        return DepositResponse(
            transaction_id=tx_signature,
            tie_contract_value=tie_contract_value,
            status="pending"
        )

    except Exception as e:
        logger.error(f"Deposit error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/treasury/withdraw", response_model=WithdrawResponse, status_code=202)
async def withdraw_sol(
    request: WithdrawRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process approved withdrawal (requires redemption-algorithm authorization).
    """
    try:
        # Verify authorization signature
        # TODO: Verify request.authorization is valid from redemption-algorithm

        # Execute withdrawal on Solana
        tx_signature = await solana_client.withdraw(
            recipient=request.wallet_address,
            amount_sol=request.amount_sol
        )

        # Record in database
        transaction = await crud.create_transaction(
            db=db,
            transaction_id=tx_signature,
            wallet_address=request.wallet_address,
            type="withdrawal",
            amount_sol=request.amount_sol,
            status="processing"
        )

        # Broadcast
        await manager.broadcast({
            "type": "withdrawal",
            "data": {
                "wallet": request.wallet_address,
                "amount": request.amount_sol,
                "tx": tx_signature
            }
        })

        return WithdrawResponse(
            transaction_id=tx_signature,
            status="processing"
        )

    except Exception as e:
        logger.error(f"Withdrawal error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/treasury/balance", response_model=TreasuryBalance)
async def get_balance():
    """Get current treasury balance and stats"""
    try:
        stats = await solana_client.get_treasury_stats()

        return TreasuryBalance(
            total_deposited=stats["total_deposited"],
            current_balance=stats["current_balance"],
            treasury_ratio=stats["treasury_ratio"]
        )

    except Exception as e:
        logger.error(f"Balance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/treasury/control", response_model=TreasuryControl)
async def get_control():
    """
    Get holder control percentage.
    TODO: This requires integration with voting-weight-tracker service
    """
    # Mock for now - will integrate with voting-weight-tracker
    holder_control_pct = 75.0

    if holder_control_pct > 66:
        status = "green"
    elif holder_control_pct > 60:
        status = "yellow_low"
    elif holder_control_pct > 51:
        status = "yellow_high"
    elif holder_control_pct > 45:
        status = "orange"
    else:
        status = "red"

    return TreasuryControl(
        holder_control_pct=holder_control_pct,
        status=status,
        threshold=51.0
    )


@app.get("/treasury/history", response_model=TransactionHistory)
async def get_history(
    wallet_address: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get deposit/withdrawal history"""
    try:
        transactions = await crud.get_transactions(
            db=db,
            wallet_address=wallet_address,
            limit=limit,
            offset=offset
        )

        total = await crud.count_transactions(db=db, wallet_address=wallet_address)

        return TransactionHistory(
            transactions=transactions,
            total=total
        )

    except Exception as e:
        logger.error(f"History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/treasury/emergency/pause")
async def emergency_pause():
    """
    Pause all deposits/withdrawals (emergency only).
    Requires multi-sig authorization in production.
    """
    try:
        # TODO: Verify multi-sig authorization

        await solana_client.pause_treasury()

        await manager.broadcast({
            "type": "emergency",
            "data": {"paused": True}
        })

        return {
            "paused": True,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Pause error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "sol-treasury-core",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "solana_connected": solana_client is not None and solana_client.is_connected()
    }


# ============================================================================
# WebSocket
# ============================================================================

@app.websocket("/ws/treasury")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time treasury updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Could handle commands here
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8920)
