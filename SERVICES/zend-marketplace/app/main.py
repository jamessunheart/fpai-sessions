"""
ZEND Marketplace - P2P UC/USDT Exchange
=======================================

Service: zend-marketplace
Port: 8584

Provides:
- P2P order book for UC ↔ USDT exchange
- Order matching engine
- Trade settlement tracking
- Liquidity provider management

Non-custodial for USDT: Money moves directly between parties via TON.
UC escrow: Seller's UC is escrowed during trade, released to buyer on confirmation.
"""

import json
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiosqlite
import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    CreateOrderRequest,
    OrderResponse,
    MatchResult,
    ConfirmPaymentRequest,
    TradeResponse,
    RegisterLPRequest,
    LPStatusResponse,
    MarketStats,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# -----------------------------------------------------------------------------
# Credits Gateway Client
# -----------------------------------------------------------------------------


class CreditsClient:
    """Credits Gateway client with shared HTTP connection.
    
    MEMORY FIX: Uses shared httpx.AsyncClient to prevent connection leaks.
    """
    _shared_client: Optional[httpx.AsyncClient] = None
    
    def __init__(self, base_url: str, api_key: Optional[str]):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Get or create shared HTTP client."""
        if cls._shared_client is None or cls._shared_client.is_closed:
            cls._shared_client = httpx.AsyncClient(
                timeout=10.0,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return cls._shared_client
    
    @classmethod
    async def close_client(cls):
        """Close shared client on shutdown."""
        if cls._shared_client and not cls._shared_client.is_closed:
            await cls._shared_client.aclose()
            cls._shared_client = None

    async def transfer_uc(
        self,
        from_account: str,
        to_account: str,
        amount_uc: float,
        reason: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {
            "from_account": from_account,
            "to_account": to_account,
            "amount": round(float(amount_uc), 8),
            "credit_type": "uc",
            "reason": reason,
            "metadata": metadata or {},
        }
        client = await self.get_client()
        r = await client.post(
            f"{self.base_url}/api/transfer",
            headers=self._headers(),
            json=payload,
        )
        if r.status_code == 200:
            return r.json()
        raise HTTPException(status_code=502, detail=f"Credits Gateway error: {r.text}")

    async def get_balance(self, account_id: str) -> Dict[str, Any]:
        client = await self.get_client()
        r = await client.get(
            f"{self.base_url}/api/balance/{account_id}",
            headers=self._headers(),
        )
        if r.status_code == 200:
            return r.json()
        return {"balances": {}}


credits = CreditsClient(settings.credits_gateway_url, settings.credits_api_key)


# -----------------------------------------------------------------------------
# TON Client (for verification)
# -----------------------------------------------------------------------------


class TonClient:
    """TON service client with shared HTTP connection.
    
    MEMORY FIX: Uses shared httpx.AsyncClient to prevent connection leaks.
    """
    _shared_client: Optional[httpx.AsyncClient] = None
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
    
    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Get or create shared HTTP client."""
        if cls._shared_client is None or cls._shared_client.is_closed:
            cls._shared_client = httpx.AsyncClient(
                timeout=10.0,
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
            )
        return cls._shared_client
    
    @classmethod
    async def close_client(cls):
        """Close shared client on shutdown."""
        if cls._shared_client and not cls._shared_client.is_closed:
            await cls._shared_client.aclose()
            cls._shared_client = None

    async def verify_transaction(self, tx_hash: str, expected_amount: float, expected_to: str) -> Dict[str, Any]:
        try:
            client = await self.get_client()
            r = await client.get(
                f"{self.base_url}/api/ton/verify/{tx_hash}",
                params={"expected_amount": expected_amount, "expected_to": expected_to}
            )
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            return {"verified": False, "error": str(e)}
        return {"verified": False, "error": "Unknown error"}


ton = TonClient(settings.zend_ton_url)


# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------


async def init_db():
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.executescript(
            """
            -- Market orders
            CREATE TABLE IF NOT EXISTS market_orders (
                order_id TEXT PRIMARY KEY,
                order_type TEXT NOT NULL,
                member_id TEXT NOT NULL,
                entity_id TEXT,
                amount_uc REAL NOT NULL,
                rate REAL DEFAULT 1.0,
                accepted_rails_json TEXT NOT NULL,
                ton_wallet_address TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                matched_with TEXT,
                matched_at TEXT
            );

            -- Trade settlements
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                sell_order_id TEXT NOT NULL,
                buy_order_id TEXT NOT NULL,
                amount_uc REAL NOT NULL,
                amount_usdt REAL NOT NULL,
                rail TEXT NOT NULL,
                seller_member_id TEXT NOT NULL,
                buyer_member_id TEXT NOT NULL,
                seller_ton_address TEXT,
                buyer_ton_address TEXT,
                ton_tx_hash TEXT,
                seller_confirmed BOOLEAN DEFAULT FALSE,
                buyer_confirmed BOOLEAN DEFAULT FALSE,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                settled_at TEXT
            );

            -- Liquidity providers
            CREATE TABLE IF NOT EXISTS liquidity_providers (
                entity_id TEXT PRIMARY KEY,
                max_buy_uc REAL NOT NULL,
                daily_limit_uc REAL NOT NULL,
                daily_used_uc REAL DEFAULT 0,
                auto_buy_enabled BOOLEAN DEFAULT TRUE,
                min_amount_uc REAL DEFAULT 10,
                max_amount_uc REAL DEFAULT 500,
                ton_wallet_address TEXT NOT NULL,
                last_reset_date TEXT NOT NULL
            );

            -- Create indexes
            CREATE INDEX IF NOT EXISTS idx_orders_status ON market_orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_type ON market_orders(order_type, status);
            CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);
            """
        )
        await conn.commit()


# -----------------------------------------------------------------------------
# Order Functions
# -----------------------------------------------------------------------------


async def create_order(
    order_id: str,
    order_type: str,
    member_id: str,
    entity_id: Optional[str],
    amount_uc: float,
    accepted_rails: List[str],
    ton_wallet_address: Optional[str],
    expires_at: str,
) -> None:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """
            INSERT INTO market_orders (order_id, order_type, member_id, entity_id, amount_uc, rate, accepted_rails_json, ton_wallet_address, status, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (order_id, order_type, member_id, entity_id, amount_uc, settings.default_rate, json.dumps(accepted_rails), ton_wallet_address, "open", _utc_now_iso(), expires_at),
        )
        await conn.commit()


async def get_order(order_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM market_orders WHERE order_id = ?", (order_id,))
        row = await cur.fetchone()
        if row:
            d = dict(row)
            d["accepted_rails"] = json.loads(d.get("accepted_rails_json", "[]"))
            return d
        return None


async def get_open_orders(order_type: Optional[str] = None) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        if order_type:
            cur = await conn.execute(
                "SELECT * FROM market_orders WHERE status = 'open' AND order_type = ? ORDER BY created_at",
                (order_type,)
            )
        else:
            cur = await conn.execute("SELECT * FROM market_orders WHERE status = 'open' ORDER BY created_at")
        rows = await cur.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["accepted_rails"] = json.loads(d.get("accepted_rails_json", "[]"))
            result.append(d)
        return result


async def update_order_status(order_id: str, status: str, matched_with: Optional[str] = None) -> None:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        if matched_with:
            await conn.execute(
                "UPDATE market_orders SET status = ?, matched_with = ?, matched_at = ? WHERE order_id = ?",
                (status, matched_with, _utc_now_iso(), order_id),
            )
        else:
            await conn.execute(
                "UPDATE market_orders SET status = ? WHERE order_id = ?",
                (status, order_id),
            )
        await conn.commit()


async def cancel_order(order_id: str) -> None:
    await update_order_status(order_id, "cancelled")


# -----------------------------------------------------------------------------
# Trade Functions
# -----------------------------------------------------------------------------


async def create_trade(
    trade_id: str,
    sell_order_id: str,
    buy_order_id: str,
    amount_uc: float,
    amount_usdt: float,
    rail: str,
    seller_member_id: str,
    buyer_member_id: str,
    seller_ton_address: Optional[str],
    buyer_ton_address: Optional[str],
) -> None:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """
            INSERT INTO trades (trade_id, sell_order_id, buy_order_id, amount_uc, amount_usdt, rail, seller_member_id, buyer_member_id, seller_ton_address, buyer_ton_address, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (trade_id, sell_order_id, buy_order_id, amount_uc, amount_usdt, rail, seller_member_id, buyer_member_id, seller_ton_address, buyer_ton_address, "pending_payment", _utc_now_iso()),
        )
        await conn.commit()


async def get_trade(trade_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def update_trade(trade_id: str, **updates) -> None:
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [trade_id]
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(f"UPDATE trades SET {set_clause} WHERE trade_id = ?", values)
        await conn.commit()


# -----------------------------------------------------------------------------
# Liquidity Provider Functions
# -----------------------------------------------------------------------------


async def get_lp(entity_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT * FROM liquidity_providers WHERE entity_id = ?", (entity_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def upsert_lp(
    entity_id: str,
    max_buy_uc: float,
    daily_limit_uc: float,
    auto_buy_enabled: bool,
    min_amount_uc: float,
    max_amount_uc: float,
    ton_wallet_address: str,
) -> None:
    today = datetime.now(timezone.utc).date().isoformat()
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            """
            INSERT INTO liquidity_providers (entity_id, max_buy_uc, daily_limit_uc, daily_used_uc, auto_buy_enabled, min_amount_uc, max_amount_uc, ton_wallet_address, last_reset_date)
            VALUES (?, ?, ?, 0, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                max_buy_uc = excluded.max_buy_uc,
                daily_limit_uc = excluded.daily_limit_uc,
                auto_buy_enabled = excluded.auto_buy_enabled,
                min_amount_uc = excluded.min_amount_uc,
                max_amount_uc = excluded.max_amount_uc,
                ton_wallet_address = excluded.ton_wallet_address
            """,
            (entity_id, max_buy_uc, daily_limit_uc, auto_buy_enabled, min_amount_uc, max_amount_uc, ton_wallet_address, today),
        )
        await conn.commit()


async def get_active_lps() -> List[Dict[str, Any]]:
    today = datetime.now(timezone.utc).date().isoformat()
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        # Reset daily limits if needed
        await conn.execute(
            "UPDATE liquidity_providers SET daily_used_uc = 0, last_reset_date = ? WHERE last_reset_date != ?",
            (today, today),
        )
        await conn.commit()

        cur = await conn.execute(
            "SELECT * FROM liquidity_providers WHERE auto_buy_enabled = TRUE AND daily_used_uc < daily_limit_uc"
        )
        rows = await cur.fetchall()
        return [dict(row) for row in rows]


async def update_lp_usage(entity_id: str, amount_uc: float) -> None:
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute(
            "UPDATE liquidity_providers SET daily_used_uc = daily_used_uc + ? WHERE entity_id = ?",
            (amount_uc, entity_id),
        )
        await conn.commit()


# -----------------------------------------------------------------------------
# Matching Engine
# -----------------------------------------------------------------------------


async def find_match(order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find a matching counter-order."""
    counter_type = "buy_uc" if order["order_type"] == "sell_uc" else "sell_uc"

    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute(
            """
            SELECT * FROM market_orders
            WHERE status = 'open' AND order_type = ? AND amount_uc >= ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (counter_type, order["amount_uc"]),
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def find_lp_match(sell_order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Find a liquidity provider willing to buy."""
    lps = await get_active_lps()

    for lp in lps:
        remaining = lp["daily_limit_uc"] - lp["daily_used_uc"]
        if (
            sell_order["amount_uc"] >= lp["min_amount_uc"]
            and sell_order["amount_uc"] <= lp["max_amount_uc"]
            and sell_order["amount_uc"] <= remaining
        ):
            return lp

    return None


async def execute_match(sell_order: Dict[str, Any], buy_order: Dict[str, Any]) -> str:
    """Execute a match between sell and buy orders."""
    trade_id = f"trade_{secrets.token_urlsafe(12)}"
    amount_uc = min(sell_order["amount_uc"], buy_order["amount_uc"])
    amount_usdt = amount_uc * settings.default_rate

    # Determine rail
    sell_rails = json.loads(sell_order.get("accepted_rails_json", '["ton_usdt"]'))
    buy_rails = json.loads(buy_order.get("accepted_rails_json", '["ton_usdt"]')) if buy_order.get("accepted_rails_json") else ["ton_usdt"]
    common_rails = set(sell_rails) & set(buy_rails)
    rail = "ton_usdt" if "ton_usdt" in common_rails else list(common_rails)[0] if common_rails else "ton_usdt"

    # Escrow UC from seller
    try:
        await credits.transfer_uc(
            from_account=sell_order["entity_id"] or sell_order["member_id"],
            to_account=settings.marketplace_escrow_account,
            amount_uc=amount_uc,
            reason=f"marketplace_escrow:{trade_id}",
            metadata={"trade_id": trade_id, "source": "zend-marketplace"},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to escrow UC: {e}")

    # Create trade record
    await create_trade(
        trade_id=trade_id,
        sell_order_id=sell_order["order_id"],
        buy_order_id=buy_order["order_id"],
        amount_uc=amount_uc,
        amount_usdt=amount_usdt,
        rail=rail,
        seller_member_id=sell_order["member_id"],
        buyer_member_id=buy_order["member_id"],
        seller_ton_address=sell_order.get("ton_wallet_address"),
        buyer_ton_address=buy_order.get("ton_wallet_address"),
    )

    # Update order statuses
    await update_order_status(sell_order["order_id"], "matched", buy_order["order_id"])
    await update_order_status(buy_order["order_id"], "matched", sell_order["order_id"])

    return trade_id


async def execute_lp_match(sell_order: Dict[str, Any], lp: Dict[str, Any]) -> str:
    """Execute a match with a liquidity provider."""
    trade_id = f"trade_{secrets.token_urlsafe(12)}"
    amount_uc = sell_order["amount_uc"]
    amount_usdt = amount_uc * settings.default_rate

    # Escrow UC from seller
    try:
        await credits.transfer_uc(
            from_account=sell_order["entity_id"] or sell_order["member_id"],
            to_account=settings.marketplace_escrow_account,
            amount_uc=amount_uc,
            reason=f"marketplace_escrow:{trade_id}",
            metadata={"trade_id": trade_id, "source": "zend-marketplace", "lp_match": True},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to escrow UC: {e}")

    # Create synthetic buy order for LP
    buy_order_id = f"lp_order_{secrets.token_urlsafe(8)}"

    # Create trade record
    await create_trade(
        trade_id=trade_id,
        sell_order_id=sell_order["order_id"],
        buy_order_id=buy_order_id,
        amount_uc=amount_uc,
        amount_usdt=amount_usdt,
        rail="ton_usdt",
        seller_member_id=sell_order["member_id"],
        buyer_member_id=lp["entity_id"],
        seller_ton_address=sell_order.get("ton_wallet_address"),
        buyer_ton_address=lp["ton_wallet_address"],
    )

    # Update LP usage
    await update_lp_usage(lp["entity_id"], amount_uc)

    # Update sell order status
    await update_order_status(sell_order["order_id"], "matched", buy_order_id)

    return trade_id


# -----------------------------------------------------------------------------
# FastAPI App
# -----------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    # MEMORY FIX: Close shared HTTP clients on shutdown
    await CreditsClient.close_client()
    await TonClient.close_client()


app = FastAPI(
    title="ZEND Marketplace",
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
        "rate": settings.default_rate,
        "min_trade_uc": settings.min_trade_uc,
        "max_trade_uc": settings.max_trade_uc,
        "timestamp": _utc_now_iso()
    }


@app.post("/api/marketplace/orders", response_model=OrderResponse)
async def create_market_order(req: CreateOrderRequest, background_tasks: BackgroundTasks):
    """
    Create a sell or buy order.
    
    - sell_uc: User wants to sell UC for USDT
    - buy_uc: User wants to buy UC with USDT
    """
    if req.order_type not in ("sell_uc", "buy_uc"):
        raise HTTPException(status_code=400, detail="order_type must be 'sell_uc' or 'buy_uc'")

    if req.amount_uc < settings.min_trade_uc:
        raise HTTPException(status_code=400, detail=f"Minimum trade is {settings.min_trade_uc} UC")

    if req.amount_uc > settings.max_trade_uc:
        raise HTTPException(status_code=400, detail=f"Maximum trade is {settings.max_trade_uc} UC")

    order_id = f"order_{secrets.token_urlsafe(12)}"
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=settings.order_expiry_hours)).isoformat()

    await create_order(
        order_id=order_id,
        order_type=req.order_type,
        member_id=req.member_id,
        entity_id=req.entity_id,
        amount_uc=req.amount_uc,
        accepted_rails=req.accepted_rails,
        ton_wallet_address=req.ton_wallet_address,
        expires_at=expires_at,
    )

    # Try to auto-match
    order = await get_order(order_id)
    if order and req.order_type == "sell_uc":
        # Check for LP match first (instant liquidity)
        lp = await find_lp_match(order)
        if lp:
            trade_id = await execute_lp_match(order, lp)
            order = await get_order(order_id)  # Refresh

    return OrderResponse(
        order_id=order_id,
        order_type=req.order_type,
        member_id=req.member_id,
        entity_id=req.entity_id,
        amount_uc=req.amount_uc,
        rate=settings.default_rate,
        accepted_rails=req.accepted_rails,
        ton_wallet_address=req.ton_wallet_address,
        status=order["status"] if order else "open",
        created_at=order["created_at"] if order else _utc_now_iso(),
        expires_at=expires_at,
        matched_with=order.get("matched_with") if order else None,
        matched_at=order.get("matched_at") if order else None,
    )


@app.get("/api/marketplace/orders/{order_id}", response_model=OrderResponse)
async def get_order_details(order_id: str):
    """Get order details."""
    order = await get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return OrderResponse(
        order_id=order["order_id"],
        order_type=order["order_type"],
        member_id=order["member_id"],
        entity_id=order.get("entity_id"),
        amount_uc=order["amount_uc"],
        rate=order["rate"],
        accepted_rails=order["accepted_rails"],
        ton_wallet_address=order.get("ton_wallet_address"),
        status=order["status"],
        created_at=order["created_at"],
        expires_at=order["expires_at"],
        matched_with=order.get("matched_with"),
        matched_at=order.get("matched_at"),
    )


@app.delete("/api/marketplace/orders/{order_id}")
async def cancel_market_order(order_id: str):
    """Cancel an open order."""
    order = await get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["status"] != "open":
        raise HTTPException(status_code=400, detail=f"Cannot cancel order with status '{order['status']}'")

    await cancel_order(order_id)
    return {"success": True, "order_id": order_id, "message": "Order cancelled"}


@app.get("/api/marketplace/orders/open")
async def list_open_orders(order_type: Optional[str] = None):
    """List open orders."""
    orders = await get_open_orders(order_type)
    return {"orders": orders, "count": len(orders)}


@app.post("/api/marketplace/match", response_model=MatchResult)
async def trigger_match(order_id: str):
    """Manually trigger matching for an order."""
    order = await get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order["status"] != "open":
        return MatchResult(
            matched=False,
            message=f"Order not open (status: {order['status']})"
        )

    # Try regular match
    counter_order = await find_match(order)
    if counter_order:
        trade_id = await execute_match(
            sell_order=order if order["order_type"] == "sell_uc" else counter_order,
            buy_order=counter_order if order["order_type"] == "sell_uc" else order,
        )
        trade = await get_trade(trade_id)
        return MatchResult(
            matched=True,
            trade_id=trade_id,
            sell_order_id=trade["sell_order_id"],
            buy_order_id=trade["buy_order_id"],
            amount_uc=trade["amount_uc"],
            amount_usdt=trade["amount_usdt"],
            seller_member_id=trade["seller_member_id"],
            buyer_member_id=trade["buyer_member_id"],
            seller_ton_address=trade.get("seller_ton_address"),
            buyer_ton_address=trade.get("buyer_ton_address"),
            next_step="Buyer sends USDT to seller's TON wallet",
            message="Orders matched! Awaiting payment."
        )

    # Try LP match for sell orders
    if order["order_type"] == "sell_uc":
        lp = await find_lp_match(order)
        if lp:
            trade_id = await execute_lp_match(order, lp)
            trade = await get_trade(trade_id)
            return MatchResult(
                matched=True,
                trade_id=trade_id,
                sell_order_id=trade["sell_order_id"],
                buy_order_id=trade["buy_order_id"],
                amount_uc=trade["amount_uc"],
                amount_usdt=trade["amount_usdt"],
                seller_member_id=trade["seller_member_id"],
                buyer_member_id=trade["buyer_member_id"],
                seller_ton_address=trade.get("seller_ton_address"),
                buyer_ton_address=trade.get("buyer_ton_address"),
                next_step="LP will send USDT to your TON wallet",
                message="Matched with liquidity provider!"
            )

    return MatchResult(
        matched=False,
        message="No matching orders found. Your order remains open."
    )


@app.post("/api/marketplace/confirm")
async def confirm_payment(req: ConfirmPaymentRequest):
    """
    Confirm payment received.
    
    Called by seller after receiving USDT from buyer.
    If tx_hash provided, will verify on-chain.
    """
    trade = await get_trade(req.trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if trade["status"] == "completed":
        return {"success": True, "trade_id": req.trade_id, "message": "Trade already completed"}

    # Verify confirmer is seller
    if req.confirmer_member_id != trade["seller_member_id"]:
        raise HTTPException(status_code=403, detail="Only seller can confirm payment receipt")

    # Optionally verify on-chain
    if req.tx_hash:
        verification = await ton.verify_transaction(
            tx_hash=req.tx_hash,
            expected_amount=trade["amount_usdt"],
            expected_to=trade["seller_ton_address"],
        )
        if not verification.get("verified"):
            raise HTTPException(status_code=400, detail=f"Transaction verification failed: {verification.get('error')}")

        await update_trade(req.trade_id, ton_tx_hash=req.tx_hash)

    # Mark seller confirmed
    await update_trade(req.trade_id, seller_confirmed=True)

    # Release UC from escrow to buyer
    try:
        await credits.transfer_uc(
            from_account=settings.marketplace_escrow_account,
            to_account=trade["buyer_member_id"],
            amount_uc=trade["amount_uc"],
            reason=f"marketplace_release:{req.trade_id}",
            metadata={"trade_id": req.trade_id, "source": "zend-marketplace"},
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to release UC: {e}")

    # Complete trade
    await update_trade(req.trade_id, status="completed", settled_at=_utc_now_iso())

    return {
        "success": True,
        "trade_id": req.trade_id,
        "message": "Payment confirmed. UC released to buyer.",
        "amount_uc": trade["amount_uc"],
        "buyer_member_id": trade["buyer_member_id"],
    }


@app.get("/api/marketplace/trades/{trade_id}", response_model=TradeResponse)
async def get_trade_details(trade_id: str):
    """Get trade details."""
    trade = await get_trade(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    return TradeResponse(**trade)


# -----------------------------------------------------------------------------
# Liquidity Provider Endpoints
# -----------------------------------------------------------------------------


@app.post("/api/marketplace/liquidity/register", response_model=LPStatusResponse)
async def register_liquidity_provider(req: RegisterLPRequest):
    """Register an entity as a liquidity provider."""
    await upsert_lp(
        entity_id=req.entity_id,
        max_buy_uc=req.max_buy_uc,
        daily_limit_uc=req.daily_limit_uc,
        auto_buy_enabled=req.auto_buy_enabled,
        min_amount_uc=req.min_amount_uc,
        max_amount_uc=req.max_amount_uc,
        ton_wallet_address=req.ton_wallet_address,
    )

    lp = await get_lp(req.entity_id)
    return LPStatusResponse(
        entity_id=req.entity_id,
        max_buy_uc=lp["max_buy_uc"],
        daily_limit_uc=lp["daily_limit_uc"],
        daily_used_uc=lp["daily_used_uc"],
        daily_remaining_uc=lp["daily_limit_uc"] - lp["daily_used_uc"],
        auto_buy_enabled=lp["auto_buy_enabled"],
        min_amount_uc=lp["min_amount_uc"],
        max_amount_uc=lp["max_amount_uc"],
        ton_wallet_address=lp["ton_wallet_address"],
        is_active=True,
        last_reset_date=lp["last_reset_date"],
    )


@app.get("/api/marketplace/liquidity/{entity_id}", response_model=LPStatusResponse)
async def get_lp_status(entity_id: str):
    """Get liquidity provider status."""
    lp = await get_lp(entity_id)
    if not lp:
        raise HTTPException(status_code=404, detail="Liquidity provider not found")

    return LPStatusResponse(
        entity_id=entity_id,
        max_buy_uc=lp["max_buy_uc"],
        daily_limit_uc=lp["daily_limit_uc"],
        daily_used_uc=lp["daily_used_uc"],
        daily_remaining_uc=lp["daily_limit_uc"] - lp["daily_used_uc"],
        auto_buy_enabled=lp["auto_buy_enabled"],
        min_amount_uc=lp["min_amount_uc"],
        max_amount_uc=lp["max_amount_uc"],
        ton_wallet_address=lp["ton_wallet_address"],
        is_active=lp["auto_buy_enabled"] and lp["daily_used_uc"] < lp["daily_limit_uc"],
        last_reset_date=lp["last_reset_date"],
    )


@app.put("/api/marketplace/liquidity/{entity_id}")
async def update_lp_settings(entity_id: str, auto_buy_enabled: Optional[bool] = None, max_amount_uc: Optional[float] = None):
    """Update liquidity provider settings."""
    lp = await get_lp(entity_id)
    if not lp:
        raise HTTPException(status_code=404, detail="Liquidity provider not found")

    updates = {}
    if auto_buy_enabled is not None:
        updates["auto_buy_enabled"] = auto_buy_enabled
    if max_amount_uc is not None:
        updates["max_amount_uc"] = max_amount_uc

    if updates:
        async with aiosqlite.connect(str(settings.db_path)) as conn:
            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [entity_id]
            await conn.execute(f"UPDATE liquidity_providers SET {set_clause} WHERE entity_id = ?", values)
            await conn.commit()

    return {"success": True, "entity_id": entity_id, "updated": list(updates.keys())}


@app.get("/api/marketplace/stats", response_model=MarketStats)
async def get_marketplace_stats():
    """Get marketplace statistics."""
    async with aiosqlite.connect(str(settings.db_path)) as conn:
        conn.row_factory = aiosqlite.Row
        # Open orders
        cur = await conn.execute("SELECT COUNT(*) as c FROM market_orders WHERE status = 'open' AND order_type = 'sell_uc'")
        sell_count = (await cur.fetchone())["c"]

        cur = await conn.execute("SELECT COUNT(*) as c FROM market_orders WHERE status = 'open' AND order_type = 'buy_uc'")
        buy_count = (await cur.fetchone())["c"]

        # 24h stats
        yesterday = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        cur = await conn.execute(
            "SELECT COUNT(*) as c, COALESCE(SUM(amount_uc), 0) as vol FROM trades WHERE created_at >= ?",
            (yesterday,)
        )
        row = await cur.fetchone()
        trades_24h = row["c"]
        volume_24h = row["vol"]

        # Active LPs
        cur = await conn.execute(
            "SELECT COUNT(*) as c, COALESCE(SUM(daily_limit_uc - daily_used_uc), 0) as avail FROM liquidity_providers WHERE auto_buy_enabled = TRUE"
        )
        row = await cur.fetchone()
        lp_count = row["c"]
        lp_liquidity = row["avail"]

    return MarketStats(
        open_sell_orders=sell_count,
        open_buy_orders=buy_count,
        total_volume_24h_uc=volume_24h,
        total_trades_24h=trades_24h,
        active_liquidity_providers=lp_count,
        instant_liquidity_available_uc=lp_liquidity,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.service_port)

