"""
Token Exchange API

FastAPI endpoints for:
- Token management (list, info, buy, sell)
- AI Wallet management (create, status, mode switching)
- Portfolio optimization (suggestions, rebalancing)
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime
import structlog

from ..tokenization.models import (
    AIWallet,
    StrategyToken,
    TokenHolding,
    TokenTransaction,
    WalletMode,
    RiskTolerance,
    TransactionType,
)
from ..tokenization.ai_optimizer import AIWalletOptimizer

logger = structlog.get_logger()

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/api/tokens", tags=["tokens"])
wallet_router = APIRouter(prefix="/api/wallet", tags=["wallet"])


# ============================================================================
# PYDANTIC MODELS (API Schemas)
# ============================================================================

class TokenListResponse(BaseModel):
    """Response for listing available tokens"""
    tokens: List[Dict]
    total: int


class TokenInfoResponse(BaseModel):
    """Detailed information about a strategy token"""
    id: int
    token_symbol: str
    strategy_name: str
    strategy_description: str
    current_nav: float
    total_aum: float
    status: str
    sharpe_ratio: Optional[float]
    max_drawdown: Optional[float]
    total_return_pct: Optional[float]
    last_30d_return_pct: Optional[float]
    last_7d_return_pct: Optional[float]
    holders_count: int
    circulating_supply: int
    total_supply: int


class TokenBuyRequest(BaseModel):
    """Request to buy strategy tokens"""
    wallet_address: str
    token_symbol: str
    quantity: float = Field(gt=0, description="Number of tokens to purchase")
    max_price: Optional[float] = None  # Max price willing to pay (slippage protection)


class TokenSellRequest(BaseModel):
    """Request to sell strategy tokens"""
    wallet_address: str
    token_symbol: str
    quantity: float = Field(gt=0, description="Number of tokens to sell")
    min_price: Optional[float] = None  # Min price willing to accept


class TransactionResponse(BaseModel):
    """Response after successful transaction"""
    transaction_id: int
    transaction_type: str
    token_symbol: str
    quantity: float
    price_per_token: float
    total_value: float
    platform_fee: float
    executed_at: datetime
    new_wallet_balance: float


class WalletCreateRequest(BaseModel):
    """Request to create new AI wallet"""
    user_id: str
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    initial_capital: float = Field(gt=0, description="Starting capital in USD")
    mode: str = Field(default="hybrid", pattern="^(full_ai|hybrid|manual)$")
    risk_tolerance: str = Field(default="moderate", pattern="^(conservative|moderate|aggressive)$")


class WalletStatusResponse(BaseModel):
    """Wallet status and holdings"""
    wallet_address: str
    user_name: Optional[str]
    mode: str
    ai_optimizer_active: bool
    total_capital: float
    cash_balance: float
    invested_balance: float
    total_return_pct: float
    sharpe_ratio: Optional[float]
    holdings: List[Dict]
    num_holdings: int
    risk_tolerance: str
    church_verified: bool
    attestation_signed: bool


class WalletModeSwitchRequest(BaseModel):
    """Request to switch wallet mode"""
    wallet_address: str
    new_mode: str = Field(pattern="^(full_ai|hybrid|manual)$")


class OptimizationSuggestionResponse(BaseModel):
    """AI optimizer's suggested allocation"""
    target_allocations: Dict[str, float]  # token_symbol -> percentage
    expected_return: float
    expected_sharpe: float
    expected_volatility: float
    reasoning: str
    changes_summary: str
    buy_orders: List[Dict]
    sell_orders: List[Dict]


class RebalanceRequest(BaseModel):
    """Request to execute rebalancing"""
    wallet_address: str
    approve: bool = True  # For hybrid mode, user must approve


# ============================================================================
# TOKEN ENDPOINTS
# ============================================================================

@router.get("/list", response_model=TokenListResponse)
async def list_tokens(status: str = "active"):
    """
    List all available strategy tokens.

    Query params:
    - status: Filter by token status (active, proving, all)
    """

    try:
        if status == "all":
            tokens = StrategyToken.list_active()  # TODO: Add list_all method
        else:
            tokens = StrategyToken.list_active()

        return TokenListResponse(
            tokens=[t.to_dict() for t in tokens],
            total=len(tokens)
        )

    except Exception as e:
        logger.error("list_tokens_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tokens: {str(e)}"
        )


@router.get("/{symbol}/info", response_model=TokenInfoResponse)
async def get_token_info(symbol: str):
    """
    Get detailed information about a specific token.

    Path params:
    - symbol: Token symbol (e.g., STRAT-AAVE-MOMENTUM-001)
    """

    try:
        token = StrategyToken.load_by_symbol(symbol)

        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Token {symbol} not found"
            )

        # Count holders (simplified - could cache this)
        import sqlite3
        conn = sqlite3.connect("treasury_arena.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT wallet_id) FROM token_holdings WHERE token_id = ?", (token.id,))
        holders_count = cursor.fetchone()[0]
        conn.close()

        return TokenInfoResponse(
            id=token.id,
            token_symbol=token.token_symbol,
            strategy_name=token.strategy_name,
            strategy_description=token.strategy_description,
            current_nav=token.current_nav,
            total_aum=token.total_aum,
            status=token.status.value,
            sharpe_ratio=token.sharpe_ratio,
            max_drawdown=token.max_drawdown,
            total_return_pct=token.total_return_pct,
            last_30d_return_pct=token.last_30d_return_pct,
            last_7d_return_pct=token.last_7d_return_pct,
            holders_count=holders_count,
            circulating_supply=token.circulating_supply,
            total_supply=token.total_supply
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_token_info_failed", symbol=symbol, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get token info: {str(e)}"
        )


@router.post("/buy", response_model=TransactionResponse)
async def buy_tokens(request: TokenBuyRequest):
    """
    Purchase strategy tokens.

    Body params:
    - wallet_address: User's wallet address
    - token_symbol: Token to purchase
    - quantity: Number of tokens
    - max_price: Optional max price per token (slippage protection)
    """

    try:
        # Load wallet
        wallet = AIWallet.load_by_address(request.wallet_address)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {request.wallet_address} not found"
            )

        # Load token
        token = StrategyToken.load_by_symbol(request.token_symbol)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Token {request.token_symbol} not found"
            )

        # Check token is active
        if token.status.value != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Token {request.token_symbol} is not active (status: {token.status.value})"
            )

        # Check slippage protection
        if request.max_price and token.current_nav > request.max_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Current price {token.current_nav} exceeds max price {request.max_price}"
            )

        # Check minimum purchase
        if request.quantity < token.min_purchase:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quantity {request.quantity} below minimum {token.min_purchase}"
            )

        # Calculate total cost
        total_cost = request.quantity * token.current_nav
        platform_fee = total_cost * 0.01  # 1% fee
        total_with_fees = total_cost + platform_fee

        # Check wallet has sufficient funds
        if wallet.cash_balance < total_with_fees:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient funds. Need {total_with_fees}, have {wallet.cash_balance}"
            )

        # Execute purchase
        optimizer = AIWalletOptimizer()
        import sqlite3
        conn = sqlite3.connect("treasury_arena.db")
        optimizer._execute_buy(wallet, token, request.quantity, "user", conn)
        conn.commit()
        conn.close()

        # Reload wallet to get updated balance
        wallet = AIWallet.load_by_address(request.wallet_address)

        # Get transaction record (most recent)
        transactions = TokenTransaction.get_wallet_transactions(wallet.id, limit=1)
        tx = transactions[0] if transactions else None

        return TransactionResponse(
            transaction_id=tx.id if tx else 0,
            transaction_type="buy",
            token_symbol=request.token_symbol,
            quantity=request.quantity,
            price_per_token=token.current_nav,
            total_value=total_cost,
            platform_fee=platform_fee,
            executed_at=datetime.now(),
            new_wallet_balance=wallet.cash_balance
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("buy_tokens_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to buy tokens: {str(e)}"
        )


@router.post("/sell", response_model=TransactionResponse)
async def sell_tokens(request: TokenSellRequest):
    """
    Sell strategy tokens.

    Body params:
    - wallet_address: User's wallet address
    - token_symbol: Token to sell
    - quantity: Number of tokens
    - min_price: Optional min price per token
    """

    try:
        # Load wallet
        wallet = AIWallet.load_by_address(request.wallet_address)
        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {request.wallet_address} not found"
            )

        # Load token
        token = StrategyToken.load_by_symbol(request.token_symbol)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Token {request.token_symbol} not found"
            )

        # Check slippage protection
        if request.min_price and token.current_nav < request.min_price:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Current price {token.current_nav} below min price {request.min_price}"
            )

        # Check wallet owns this token
        holdings = TokenHolding.get_wallet_holdings(wallet.id)
        holding = next((h for h in holdings if h.token_id == token.id), None)

        if not holding:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Wallet does not own {request.token_symbol}"
            )

        if holding.quantity < request.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient tokens. Have {holding.quantity}, trying to sell {request.quantity}"
            )

        # Calculate proceeds
        total_proceeds = request.quantity * token.current_nav
        platform_fee = total_proceeds * 0.01  # 1% fee
        net_proceeds = total_proceeds - platform_fee

        # Execute sale
        optimizer = AIWalletOptimizer()
        import sqlite3
        conn = sqlite3.connect("treasury_arena.db")
        optimizer._execute_sell(wallet, token, request.quantity, "user", conn)
        conn.commit()
        conn.close()

        # Reload wallet to get updated balance
        wallet = AIWallet.load_by_address(request.wallet_address)

        # Get transaction record (most recent)
        transactions = TokenTransaction.get_wallet_transactions(wallet.id, limit=1)
        tx = transactions[0] if transactions else None

        return TransactionResponse(
            transaction_id=tx.id if tx else 0,
            transaction_type="sell",
            token_symbol=request.token_symbol,
            quantity=request.quantity,
            price_per_token=token.current_nav,
            total_value=total_proceeds,
            platform_fee=platform_fee,
            executed_at=datetime.now(),
            new_wallet_balance=wallet.cash_balance
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("sell_tokens_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sell tokens: {str(e)}"
        )


# ============================================================================
# WALLET ENDPOINTS
# ============================================================================

@wallet_router.post("/create", response_model=WalletStatusResponse)
async def create_wallet(request: WalletCreateRequest):
    """
    Create a new AI wallet.

    Body params:
    - user_id: Church/trust identifier
    - initial_capital: Starting capital in USD
    - mode: Wallet mode (full_ai, hybrid, manual)
    - risk_tolerance: Risk preference (conservative, moderate, aggressive)
    """

    try:
        # Create wallet
        wallet = AIWallet(
            user_id=request.user_id,
            user_email=request.user_email,
            user_name=request.user_name,
            mode=WalletMode(request.mode),
            risk_tolerance=RiskTolerance(request.risk_tolerance),
            total_capital=request.initial_capital,
            cash_balance=request.initial_capital,
            initial_capital=request.initial_capital,
            all_time_high=request.initial_capital
        )

        wallet.save()

        logger.info("wallet_created", wallet_id=wallet.id, user_id=request.user_id)

        return WalletStatusResponse(
            wallet_address=wallet.wallet_address,
            user_name=wallet.user_name,
            mode=wallet.mode.value,
            ai_optimizer_active=wallet.ai_optimizer_active,
            total_capital=wallet.total_capital,
            cash_balance=wallet.cash_balance,
            invested_balance=wallet.invested_balance,
            total_return_pct=wallet.total_return_pct,
            sharpe_ratio=wallet.sharpe_ratio,
            holdings=[],
            num_holdings=0,
            risk_tolerance=wallet.risk_tolerance.value,
            church_verified=wallet.church_verified,
            attestation_signed=wallet.attestation_signed
        )

    except Exception as e:
        logger.error("create_wallet_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create wallet: {str(e)}"
        )


@wallet_router.get("/{wallet_address}/status", response_model=WalletStatusResponse)
async def get_wallet_status(wallet_address: str):
    """
    Get wallet status and current holdings.

    Path params:
    - wallet_address: Wallet UUID
    """

    try:
        wallet = AIWallet.load_by_address(wallet_address)

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_address} not found"
            )

        # Get holdings
        holdings = TokenHolding.get_wallet_holdings(wallet.id)

        holdings_data = []
        for holding in holdings:
            token = StrategyToken.load(holding.token_id)
            if token:
                # Update holding value with current NAV
                holding.update_value(token.current_nav)
                holding.save()

                holdings_data.append({
                    "token_symbol": token.token_symbol,
                    "strategy_name": token.strategy_name,
                    "quantity": holding.quantity,
                    "avg_cost_basis": holding.avg_cost_basis,
                    "current_value": holding.current_value,
                    "unrealized_pnl": holding.unrealized_pnl,
                    "unrealized_pnl_pct": holding.unrealized_pnl_pct,
                })

        # Update wallet totals
        wallet.invested_balance = sum(h.current_value for h in holdings)
        wallet.total_capital = wallet.cash_balance + wallet.invested_balance
        wallet.total_return_pct = ((wallet.total_capital - wallet.initial_capital) / wallet.initial_capital * 100)
        wallet.save()

        return WalletStatusResponse(
            wallet_address=wallet.wallet_address,
            user_name=wallet.user_name,
            mode=wallet.mode.value,
            ai_optimizer_active=wallet.ai_optimizer_active,
            total_capital=wallet.total_capital,
            cash_balance=wallet.cash_balance,
            invested_balance=wallet.invested_balance,
            total_return_pct=wallet.total_return_pct,
            sharpe_ratio=wallet.sharpe_ratio,
            holdings=holdings_data,
            num_holdings=len(holdings_data),
            risk_tolerance=wallet.risk_tolerance.value,
            church_verified=wallet.church_verified,
            attestation_signed=wallet.attestation_signed
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_wallet_status_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get wallet status: {str(e)}"
        )


@wallet_router.post("/mode", response_model=WalletStatusResponse)
async def switch_wallet_mode(request: WalletModeSwitchRequest):
    """
    Switch wallet management mode.

    Body params:
    - wallet_address: Wallet UUID
    - new_mode: New mode (full_ai, hybrid, manual)
    """

    try:
        wallet = AIWallet.load_by_address(request.wallet_address)

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {request.wallet_address} not found"
            )

        old_mode = wallet.mode.value
        wallet.mode = WalletMode(request.new_mode)
        wallet.ai_optimizer_active = (request.new_mode != "manual")
        wallet.save()

        logger.info("wallet_mode_switched", wallet_id=wallet.id, old_mode=old_mode, new_mode=request.new_mode)

        # Return updated status
        return await get_wallet_status(request.wallet_address)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("switch_wallet_mode_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch wallet mode: {str(e)}"
        )


@wallet_router.get("/{wallet_address}/suggested", response_model=OptimizationSuggestionResponse)
async def get_optimization_suggestion(wallet_address: str):
    """
    Get AI optimizer's suggested allocation.

    Path params:
    - wallet_address: Wallet UUID
    """

    try:
        wallet = AIWallet.load_by_address(wallet_address)

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {wallet_address} not found"
            )

        # Run optimization
        optimizer = AIWalletOptimizer()
        recommendation = optimizer.optimize_wallet(wallet)

        # Convert allocations from token_id to token_symbol
        allocations_by_symbol = {}
        for token_id, pct in recommendation.target_allocations.items():
            token = StrategyToken.load(token_id)
            if token:
                allocations_by_symbol[token.token_symbol] = pct

        # Convert orders to dicts
        buy_orders_data = []
        for token_id, qty in recommendation.buy_orders:
            token = StrategyToken.load(token_id)
            if token:
                buy_orders_data.append({
                    "token_symbol": token.token_symbol,
                    "quantity": qty,
                    "estimated_cost": qty * token.current_nav
                })

        sell_orders_data = []
        for token_id, qty in recommendation.sell_orders:
            token = StrategyToken.load(token_id)
            if token:
                sell_orders_data.append({
                    "token_symbol": token.token_symbol,
                    "quantity": qty,
                    "estimated_proceeds": qty * token.current_nav
                })

        return OptimizationSuggestionResponse(
            target_allocations=allocations_by_symbol,
            expected_return=recommendation.expected_return,
            expected_sharpe=recommendation.expected_sharpe,
            expected_volatility=recommendation.expected_volatility,
            reasoning=recommendation.reasoning,
            changes_summary=recommendation.changes_summary,
            buy_orders=buy_orders_data,
            sell_orders=sell_orders_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_optimization_suggestion_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimization suggestion: {str(e)}"
        )


@wallet_router.post("/rebalance", response_model=WalletStatusResponse)
async def execute_rebalance(request: RebalanceRequest):
    """
    Execute portfolio rebalancing.

    Body params:
    - wallet_address: Wallet UUID
    - approve: User approval (required for hybrid mode)
    """

    try:
        wallet = AIWallet.load_by_address(request.wallet_address)

        if not wallet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Wallet {request.wallet_address} not found"
            )

        # Check mode
        if wallet.mode == WalletMode.MANUAL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot auto-rebalance in manual mode"
            )

        if wallet.mode == WalletMode.HYBRID and not request.approve:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User approval required for hybrid mode rebalancing"
            )

        # Get optimization recommendation
        optimizer = AIWalletOptimizer()
        recommendation = optimizer.optimize_wallet(wallet)

        # Execute rebalance
        success = optimizer.execute_rebalance(
            wallet=wallet,
            recommendation=recommendation,
            triggered_by="user" if wallet.mode == WalletMode.HYBRID else "ai_optimizer"
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Rebalancing failed"
            )

        logger.info("rebalance_executed", wallet_id=wallet.id, mode=wallet.mode.value)

        # Return updated wallet status
        return await get_wallet_status(request.wallet_address)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("execute_rebalance_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute rebalance: {str(e)}"
        )
