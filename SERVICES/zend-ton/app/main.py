"""
ZEND TON Integration Service v1.0
=================================

Service: zend-ton
Port: 8583

Provides:
- TON wallet connection management
- USDT balance queries
- Transfer deep link generation
- On-chain transaction verification

Non-custodial: We never hold funds. Users sign transactions in their own wallet.
"""

import json
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiosqlite
from fastapi import BackgroundTasks, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    TonBalanceResponse,
    TonConnectRequest,
    TonConnectResponse,
    TonTransferRequest,
    TonTransferResponse,
    TonTxVerification,
    TonTxVerifyRequest,
    TonWalletInfo,
    SaveConnectionRequest,
    WebhookPayload,
)
from app.ton_client import get_ton_client


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------


async def init_db():
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.executescript(
            """
            -- TON wallet connections
            CREATE TABLE IF NOT EXISTS ton_connections (
                member_id TEXT PRIMARY KEY,
                ton_address TEXT NOT NULL,
                connected_at TEXT NOT NULL,
                last_verified TEXT
            );

            -- Pending transfers (for tracking)
            CREATE TABLE IF NOT EXISTS pending_transfers (
                transfer_id TEXT PRIMARY KEY,
                from_member_id TEXT NOT NULL,
                to_address TEXT NOT NULL,
                amount_usdt REAL NOT NULL,
                comment TEXT,
                purpose TEXT,
                deep_link TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                settled_tx_hash TEXT,
                settled_at TEXT
            );

            -- TON transaction log
            CREATE TABLE IF NOT EXISTS ton_transactions (
                tx_hash TEXT PRIMARY KEY,
                direction TEXT NOT NULL,
                member_id TEXT NOT NULL,
                amount_usdt REAL NOT NULL,
                from_address TEXT,
                to_address TEXT,
                purpose TEXT,
                related_order_id TEXT,
                confirmed_at TEXT NOT NULL
            );

            -- TON Connect sessions
            CREATE TABLE IF NOT EXISTS ton_connect_sessions (
                session_id TEXT PRIMARY KEY,
                member_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                connected_address TEXT
            );
            """
        )
        await conn.commit()


async def get_connection(member_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT * FROM ton_connections WHERE member_id = ?",
            (member_id,)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def save_connection(member_id: str, ton_address: str):
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            """
            INSERT INTO ton_connections (member_id, ton_address, connected_at, last_verified)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(member_id) DO UPDATE SET
                ton_address = excluded.ton_address,
                last_verified = excluded.last_verified
            """,
            (member_id, ton_address, _utc_now_iso(), _utc_now_iso())
        )
        await conn.commit()


async def save_pending_transfer(
    transfer_id: str,
    from_member_id: str,
    to_address: str,
    amount_usdt: float,
    comment: str,
    purpose: str,
    deep_link: str,
    expires_at: str
):
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            """
            INSERT INTO pending_transfers
            (transfer_id, from_member_id, to_address, amount_usdt, comment, purpose, deep_link, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (transfer_id, from_member_id, to_address, amount_usdt, comment, purpose, deep_link, "pending", _utc_now_iso(), expires_at)
        )
        await conn.commit()


async def record_transaction(
    tx_hash: str,
    direction: str,
    member_id: str,
    amount_usdt: float,
    from_address: str,
    to_address: str,
    purpose: str,
    related_order_id: Optional[str] = None
):
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO ton_transactions
            (tx_hash, direction, member_id, amount_usdt, from_address, to_address, purpose, related_order_id, confirmed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tx_hash, direction, member_id, amount_usdt, from_address, to_address, purpose, related_order_id, _utc_now_iso())
        )
        await conn.commit()


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="ZEND TON Integration",
    version=settings.service_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.service_version,
        "network": settings.ton_network,
        "usdt_contract": settings.usdt_jetton_master,
        "timestamp": _utc_now_iso()
    }


@app.get("/api/ton/wallet/{member_id}", response_model=TonBalanceResponse)
async def get_wallet(member_id: str):
    """
    Get member's connected TON wallet and balances.
    """
    conn = await get_connection(member_id)

    if not conn:
        return TonBalanceResponse(
            member_id=member_id,
            connected=False,
            timestamp=_utc_now_iso()
        )

    ton_address = conn["ton_address"]
    ton_client = get_ton_client()

    # Fetch balances
    balances = await ton_client.get_all_balances(ton_address)

    return TonBalanceResponse(
        member_id=member_id,
        ton_address=ton_address,
        connected=True,
        balances=balances,
        usdt_balance=balances.get("USDT", 0.0),
        ton_balance=balances.get("TON", 0.0),
        usdt_yield_apy=2.86,  # Current USDT staking APY on TON
        timestamp=_utc_now_iso()
    )


@app.post("/api/ton/connect", response_model=TonConnectResponse)
async def initiate_connect(req: TonConnectRequest):
    """
    Initiate TON Connect flow for wallet connection.

    Returns a connect URL that user opens in their TON wallet.
    """
    session_id = f"tcs_{secrets.token_urlsafe(16)}"
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()

    # Store session
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """
            INSERT INTO ton_connect_sessions (session_id, member_id, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, req.member_id, "pending", _utc_now_iso(), expires_at)
        )
        await conn.commit()

    # Generate TON Connect URL
    # In production, this would use the TON Connect SDK to generate proper manifest-based connection
    connect_url = f"ton://connect?manifest={settings.ton_connect_manifest_url}&session={session_id}"

    return TonConnectResponse(
        member_id=req.member_id,
        connect_url=connect_url,
        session_id=session_id,
        expires_at=expires_at
    )


@app.post("/api/ton/connection/save")
async def save_wallet_connection(req: SaveConnectionRequest):
    """
    Save a wallet connection after successful TON Connect.

    Called by frontend/bot after user confirms connection in wallet.
    """
    await save_connection(req.member_id, req.ton_address)

    return {
        "success": True,
        "member_id": req.member_id,
        "ton_address": req.ton_address,
        "message": "Wallet connected successfully"
    }


@app.post("/api/ton/transfer", response_model=TonTransferResponse)
async def create_transfer(req: TonTransferRequest, background_tasks: BackgroundTasks):
    """
    Generate a USDT transfer deep link.

    User opens this link in their TON wallet to sign and send the transaction.
    We do NOT custody funds - user signs directly in their wallet.
    """
    # Verify sender has connected wallet
    conn = await get_connection(req.from_member_id)
    if not conn:
        raise HTTPException(
            status_code=400,
            detail="No TON wallet connected. Please connect wallet first."
        )

    # Generate transfer
    ton_client = get_ton_client()
    deep_link, qr_data = ton_client.generate_transfer_deep_link(
        to_address=req.to_address,
        amount_usdt=req.amount_usdt,
        comment=req.comment
    )

    transfer_id = f"tt_{secrets.token_urlsafe(12)}"
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # Save pending transfer for tracking
    background_tasks.add_task(
        save_pending_transfer,
        transfer_id=transfer_id,
        from_member_id=req.from_member_id,
        to_address=req.to_address,
        amount_usdt=req.amount_usdt,
        comment=req.comment,
        purpose=req.purpose,
        deep_link=deep_link,
        expires_at=expires_at
    )

    return TonTransferResponse(
        transfer_id=transfer_id,
        from_member_id=req.from_member_id,
        to_address=req.to_address,
        amount_usdt=req.amount_usdt,
        comment=req.comment,
        deep_link=deep_link,
        qr_data=qr_data,
        expires_at=expires_at,
        status="pending"
    )


@app.get("/api/ton/verify/{tx_hash}", response_model=TonTxVerification)
async def verify_transaction(
    tx_hash: str,
    expected_amount: Optional[float] = None,
    expected_to: Optional[str] = None
):
    """
    Verify a TON transaction on-chain.

    Used by marketplace to confirm P2P settlements.
    """
    ton_client = get_ton_client()
    result = await ton_client.verify_transaction(
        tx_hash=tx_hash,
        expected_amount=expected_amount,
        expected_to=expected_to
    )

    return TonTxVerification(
        tx_hash=tx_hash,
        verified=result.get("verified", False),
        amount_usdt=result.get("amount_usdt", 0.0),
        from_address=result.get("from_address", ""),
        to_address=result.get("to_address", ""),
        comment=result.get("comment"),
        confirmed_at=result.get("confirmed_at"),
        block_height=result.get("block_height"),
        error=result.get("error")
    )


@app.post("/api/ton/verify")
async def verify_transaction_post(req: TonTxVerifyRequest):
    """POST version of transaction verification."""
    return await verify_transaction(
        tx_hash=req.tx_hash,
        expected_amount=req.expected_amount,
        expected_to=req.expected_to
    )


@app.post("/api/ton/webhook")
async def handle_webhook(payload: WebhookPayload, background_tasks: BackgroundTasks):
    """
    Handle TON blockchain webhooks.

    Called by indexer service when transactions are detected.
    """
    # Find member by address
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            "SELECT member_id FROM ton_connections WHERE ton_address = ?",
            (payload.to_address if payload.direction == "in" else payload.from_address,)
        )
        row = await cur.fetchone()
        member_id = row["member_id"] if row else "unknown"

    # Record transaction
    background_tasks.add_task(
        record_transaction,
        tx_hash=payload.tx_hash,
        direction=payload.direction,
        member_id=member_id,
        amount_usdt=payload.amount if payload.asset == "USDT" else 0.0,
        from_address=payload.from_address,
        to_address=payload.to_address,
        purpose="webhook_detected"
    )

    return {"status": "received", "tx_hash": payload.tx_hash}


@app.get("/api/ton/transactions/{member_id}")
async def get_member_transactions(member_id: str, limit: int = 20):
    """
    Get transaction history for a member.
    """
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """
            SELECT * FROM ton_transactions
            WHERE member_id = ?
            ORDER BY confirmed_at DESC
            LIMIT ?
            """,
            (member_id, limit)
        )
        rows = await cur.fetchall()
        return {
            "member_id": member_id,
            "transactions": [dict(row) for row in rows],
            "count": len(rows)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)

