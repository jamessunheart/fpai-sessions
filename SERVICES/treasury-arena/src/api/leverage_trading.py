"""
Treasury Arena - Leveraged Trading API

Endpoints for users to:
- Create leverage accounts
- Open/close leveraged positions
- Request withdrawals
- View platform stats
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.insert(0, '/Users/jamessunheart/Development/SERVICES/treasury-arena')

from src.leverage_engine import LeverageEngine, LeverageTier

router = APIRouter(prefix="/api/leverage", tags=["leverage"])

# Database path
DB_PATH = "treasury_arena_production.db"


# Request/Response Models
class CreateAccountRequest(BaseModel):
    wallet_id: int
    user_id: str
    deposit_amount: float
    leverage_tier: int = 3  # Default 3x


class OpenPositionRequest(BaseModel):
    account_id: int
    token_symbol: str
    quantity: float
    entry_price: float
    leverage_multiplier: float


class ClosePositionRequest(BaseModel):
    trade_id: int
    exit_price: float


class WithdrawalRequest(BaseModel):
    account_id: int
    amount: float


# Endpoints

@router.post("/account/create")
async def create_leverage_account(req: CreateAccountRequest):
    """
    Create a new leverage trading account

    Example:
    ```
    POST /api/leverage/account/create
    {
        "wallet_id": 1,
        "user_id": "user-123",
        "deposit_amount": 1000,
        "leverage_tier": 3
    }
    ```

    Returns account details with trading power
    """
    engine = LeverageEngine(DB_PATH)

    # Map tier number to enum
    tier_map = {2: LeverageTier.CONSERVATIVE, 3: LeverageTier.MODERATE, 5: LeverageTier.AGGRESSIVE}
    tier = tier_map.get(req.leverage_tier, LeverageTier.MODERATE)

    account = engine.create_account(
        wallet_id=req.wallet_id,
        user_id=req.user_id,
        deposit_amount=req.deposit_amount,
        leverage_tier=tier
    )

    return {
        "success": True,
        "account_id": account.id,
        "deposited": account.deposited_capital,
        "leverage": account.leverage_tier.value,
        "trading_power": account.trading_power,
        "message": f"Account created with {account.leverage_tier.value}x leverage. You have ${account.trading_power:,.2f} trading power!"
    }


@router.post("/position/open")
async def open_position(req: OpenPositionRequest):
    """
    Open a leveraged trading position

    Example:
    ```
    POST /api/leverage/position/open
    {
        "account_id": 1,
        "token_symbol": "STRAT-SOL-ECOSYSTEM-001",
        "quantity": 100,
        "entry_price": 1.20,
        "leverage_multiplier": 3
    }
    ```

    Opens position and returns fees charged
    """
    engine = LeverageEngine(DB_PATH)

    success, message, fees = engine.open_leveraged_position(
        account_id=req.account_id,
        token_symbol=req.token_symbol,
        quantity=req.quantity,
        entry_price=req.entry_price,
        leverage_multiplier=req.leverage_multiplier
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message,
        "fees_charged": fees,
        "position_value": req.quantity * req.entry_price,
        "leveraged_exposure": req.quantity * req.entry_price * req.leverage_multiplier
    }


@router.post("/position/close")
async def close_position(req: ClosePositionRequest):
    """
    Close a leveraged position

    Example:
    ```
    POST /api/leverage/position/close
    {
        "trade_id": 1,
        "exit_price": 1.50
    }
    ```

    Closes position and returns P&L
    """
    engine = LeverageEngine(DB_PATH)

    success, message, pnl = engine.close_position(
        trade_id=req.trade_id,
        exit_price=req.exit_price
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message,
        "pnl": pnl,
        "pnl_formatted": f"${pnl:+,.2f}"
    }


@router.post("/withdrawal/request")
async def request_withdrawal(req: WithdrawalRequest):
    """
    Request a withdrawal (subject to monthly limits)

    Example:
    ```
    POST /api/leverage/withdrawal/request
    {
        "account_id": 1,
        "amount": 500
    }
    ```

    Withdrawals are limited to 20% of profits per month
    """
    engine = LeverageEngine(DB_PATH)

    success, message = engine.request_withdrawal(
        account_id=req.account_id,
        amount=req.amount
    )

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "message": message
    }


@router.get("/stats/platform")
async def get_platform_stats():
    """
    Get platform-wide statistics

    Returns:
    - Total accounts
    - Total capital deposited
    - Total trading power (with leverage)
    - Total fees collected
    - Active positions
    """
    engine = LeverageEngine(DB_PATH)
    stats = engine.get_platform_stats()

    return {
        "success": True,
        "stats": {
            "total_accounts": stats["total_accounts"],
            "total_deposited": f"${stats['total_deposited']:,.2f}",
            "total_trading_power": f"${stats['total_trading_power']:,.2f}",
            "leverage_multiplier": f"{stats['leverage_multiplier']:.1f}x",
            "total_fees_collected": f"${stats['total_fees_collected']:,.2f}",
            "fees_breakdown": stats["fees_by_type"],
            "active_positions": stats["active_positions"]
        }
    }


@router.get("/account/{account_id}")
async def get_account_details(account_id: int):
    """Get detailed account information"""
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            user_id, deposited_capital, leverage_tier, trading_power,
            current_balance, total_profit, total_loss, total_withdrawn,
            is_liquidated
        FROM leverage_accounts
        WHERE id = ?
    """, (account_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Account not found")

    deposited = row[1]
    balance = row[4]
    profit = row[5]
    loss = row[6]

    net_pnl = profit - loss
    roi_pct = (net_pnl / deposited * 100) if deposited > 0 else 0

    return {
        "success": True,
        "account": {
            "user_id": row[0],
            "deposited": f"${deposited:,.2f}",
            "leverage": f"{row[2]}x",
            "trading_power": f"${row[3]:,.2f}",
            "current_balance": f"${balance:,.2f}",
            "total_profit": f"${profit:,.2f}",
            "total_loss": f"${loss:,.2f}",
            "net_pnl": f"${net_pnl:+,.2f}",
            "roi": f"{roi_pct:+.1f}%",
            "total_withdrawn": f"${row[7]:,.2f}",
            "is_liquidated": bool(row[8])
        }
    }


@router.get("/health")
async def health_check():
    """Health check for leverage trading system"""
    return {
        "status": "healthy",
        "service": "leverage-trading",
        "version": "1.0.0"
    }
