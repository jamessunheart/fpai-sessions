"""
Multi-User Trading Manager
Manages trading operations across multiple PMA members.
"""

import os
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

from .vault import get_vault, ExchangeCredentials
from .hyperliquid_live import HyperliquidClient
from .true_level10_strategy import TRUE_LEVEL_10, TRUE_LEVEL_10_CONFIG
from membership.pma_verifier import (
    get_verifier, 
    MembershipTier, 
    MemberProfile,
    check_trading_eligibility
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TradingStatus(Enum):
    """Trading status for a user."""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


class AccountType(Enum):
    """Account type for trading."""
    INDIVIDUAL = "individual"
    TRUST = "trust"
    LLC = "llc"
    CHURCH = "church"


# Daily limits per entity type (from ZEND_REGENERATIVE_SPEC.md)
ENTITY_LIMITS = {
    AccountType.INDIVIDUAL: {
        "daily_trade_limit_uc": 1000,
        "max_position_size_pct": 0.25,  # 25% of balance per position
        "can_provide_liquidity": False
    },
    AccountType.TRUST: {
        "daily_trade_limit_uc": 50000,
        "max_position_size_pct": 0.40,  # 40% per position
        "can_provide_liquidity": True
    },
    AccountType.LLC: {
        "daily_trade_limit_uc": 25000,
        "max_position_size_pct": 0.35,
        "can_provide_liquidity": True
    },
    AccountType.CHURCH: {
        "daily_trade_limit_uc": 100000,
        "max_position_size_pct": 0.50,
        "can_provide_liquidity": True
    }
}


@dataclass
class UserTradingState:
    """Trading state for an individual user."""
    user_id: str
    tier: MembershipTier
    status: TradingStatus
    exchange: str
    balance: float
    open_positions: List[Dict[str, Any]]
    daily_pnl: float
    total_pnl: float
    trades_today: int
    last_trade_time: Optional[datetime]
    last_check_time: Optional[datetime]
    error_message: Optional[str] = None


@dataclass
class EntityTradingAccount:
    """
    Trading account for an entity (Trust, LLC, Church).
    Supports multiple authorized users.
    """
    entity_id: str
    entity_name: str
    account_type: AccountType
    status: TradingStatus
    
    # Authorized users (can execute trades for this entity)
    authorized_users: List[str]
    primary_admin: str
    
    # Financial state
    balance: float
    open_positions: List[Dict[str, Any]]
    daily_pnl: float
    total_pnl: float
    daily_volume: float
    trades_today: int
    
    # Limits (from ENTITY_LIMITS)
    daily_limit_uc: float
    max_position_size_pct: float
    
    # Metadata
    created_at: datetime
    last_trade_time: Optional[datetime] = None
    last_check_time: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def can_trade(self, user_id: str) -> bool:
        """Check if user is authorized to trade for this entity."""
        return user_id in self.authorized_users or user_id == self.primary_admin
    
    def within_daily_limit(self, amount: float) -> bool:
        """Check if trade is within daily limit."""
        return (self.daily_volume + amount) <= self.daily_limit_uc
    
    def get_max_position_size(self) -> float:
        """Get maximum position size for this entity."""
        return self.balance * self.max_position_size_pct


class MultiUserTradingManager:
    """
    Manages trading operations for multiple PMA members.
    Handles both Tier 1 (connected accounts) and Tier 2 (pooled fund).
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.vault = get_vault()
        self.verifier = get_verifier()
        self.user_states: Dict[str, UserTradingState] = {}
        self.user_clients: Dict[str, HyperliquidClient] = {}
        
        # Entity accounts (Trusts, LLCs, Churches)
        self.entity_accounts: Dict[str, EntityTradingAccount] = {}
        self.entity_clients: Dict[str, HyperliquidClient] = {}
        
        self.running = False
        self._lock = asyncio.Lock()
        self._initialized = True
        logger.info("Multi-User Trading Manager initialized (with entity support)")
    
    async def start(self):
        """Start the multi-user trading manager."""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting Multi-User Trading Manager")
        
        # Load all active traders
        await self._load_active_traders()
        
        # Start monitoring loop
        asyncio.create_task(self._monitoring_loop())
    
    async def stop(self):
        """Stop the multi-user trading manager."""
        self.running = False
        logger.info("Stopping Multi-User Trading Manager")
    
    async def _load_active_traders(self):
        """Load all active traders from membership database."""
        traders = self.verifier.get_all_active_traders()
        
        for member in traders:
            if member.trading_tier == MembershipTier.STEWARD:
                await self._initialize_steward(member)
            elif member.trading_tier == MembershipTier.TRUSTEE:
                # Trustees use pooled fund, handled separately
                pass
        
        logger.info(f"Loaded {len(traders)} active traders")
    
    async def _initialize_steward(self, member: MemberProfile) -> bool:
        """Initialize a Tier 1 Steward's trading."""
        try:
            # Get their API credentials
            creds = self.vault.get_credentials(member.user_id, "hyperliquid")
            
            if not creds:
                logger.warning(f"No credentials found for user {member.user_id}")
                return False
            
            # Create Hyperliquid client
            client = HyperliquidClient()
            client.set_credentials(creds.api_key, creds.api_secret, creds.wallet_address)
            
            if not client.connected:
                logger.error(f"Failed to connect for user {member.user_id}")
                self.user_states[member.user_id] = UserTradingState(
                    user_id=member.user_id,
                    tier=MembershipTier.STEWARD,
                    status=TradingStatus.ERROR,
                    exchange="hyperliquid",
                    balance=0,
                    open_positions=[],
                    daily_pnl=0,
                    total_pnl=0,
                    trades_today=0,
                    last_trade_time=None,
                    last_check_time=datetime.now(),
                    error_message="Failed to connect to exchange"
                )
                return False
            
            # Store client
            self.user_clients[member.user_id] = client
            
            # Get initial state
            account_state = await client.get_account_state()
            balance = float(account_state.get("marginSummary", {}).get("accountValue", 0))
            positions = account_state.get("positions", [])
            
            self.user_states[member.user_id] = UserTradingState(
                user_id=member.user_id,
                tier=MembershipTier.STEWARD,
                status=TradingStatus.ACTIVE,
                exchange="hyperliquid",
                balance=balance,
                open_positions=positions,
                daily_pnl=0,
                total_pnl=0,
                trades_today=0,
                last_trade_time=member.last_trade_date,
                last_check_time=datetime.now()
            )
            
            logger.info(f"Initialized trading for user {member.user_id}: ${balance:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing user {member.user_id}: {e}")
            return False
    
    async def add_trader(self, user_id: str) -> Dict[str, Any]:
        """Add a new trader to the system."""
        async with self._lock:
            # Verify membership
            member = self.verifier.get_member_by_id(user_id)
            if not member:
                return {"success": False, "error": "Member not found"}
            
            if not member.is_eligible_for_trading():
                eligibility = self.verifier.check_eligibility(member.telegram_id)
                return {"success": False, "error": eligibility.get("message")}
            
            if member.trading_tier == MembershipTier.STEWARD:
                success = await self._initialize_steward(member)
                if success:
                    return {"success": True, "message": "Trading enabled"}
                return {"success": False, "error": "Failed to initialize trading"}
            
            elif member.trading_tier == MembershipTier.TRUSTEE:
                # Add to pooled fund tracking
                self.user_states[user_id] = UserTradingState(
                    user_id=user_id,
                    tier=MembershipTier.TRUSTEE,
                    status=TradingStatus.ACTIVE,
                    exchange="pooled",
                    balance=0,  # Will be calculated from pool share
                    open_positions=[],
                    daily_pnl=0,
                    total_pnl=0,
                    trades_today=0,
                    last_trade_time=None,
                    last_check_time=datetime.now()
                )
                return {"success": True, "message": "Added to Fellowship Pool"}
            
            return {"success": False, "error": "Unknown tier"}
    
    async def remove_trader(self, user_id: str) -> Dict[str, Any]:
        """Remove a trader from the system."""
        async with self._lock:
            if user_id not in self.user_states:
                return {"success": False, "error": "Trader not found"}
            
            state = self.user_states[user_id]
            
            # Check for open positions
            if state.open_positions:
                return {
                    "success": False, 
                    "error": "Close all positions first",
                    "positions": len(state.open_positions)
                }
            
            # Remove from tracking
            del self.user_states[user_id]
            if user_id in self.user_clients:
                del self.user_clients[user_id]
            
            # Disable in membership
            self.verifier.disable_trading(user_id)
            
            return {"success": True, "message": "Trading disabled"}
    
    async def pause_trading(self, user_id: str) -> bool:
        """Pause trading for a user."""
        if user_id in self.user_states:
            self.user_states[user_id].status = TradingStatus.PAUSED
            logger.info(f"Paused trading for user {user_id}")
            return True
        return False
    
    async def resume_trading(self, user_id: str) -> bool:
        """Resume trading for a user."""
        if user_id in self.user_states:
            self.user_states[user_id].status = TradingStatus.ACTIVE
            logger.info(f"Resumed trading for user {user_id}")
            return True
        return False
    
    async def get_user_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get trading status for a user."""
        if user_id not in self.user_states:
            return None
        
        state = self.user_states[user_id]
        
        return {
            "user_id": state.user_id,
            "tier": state.tier.value,
            "status": state.status.value,
            "exchange": state.exchange,
            "balance": state.balance,
            "open_positions": len(state.open_positions),
            "daily_pnl": state.daily_pnl,
            "total_pnl": state.total_pnl,
            "trades_today": state.trades_today,
            "last_trade": state.last_trade_time.isoformat() if state.last_trade_time else None,
            "last_check": state.last_check_time.isoformat() if state.last_check_time else None,
            "error": state.error_message
        }
    
    async def get_all_status(self) -> List[Dict[str, Any]]:
        """Get trading status for all users."""
        return [
            await self.get_user_status(user_id)
            for user_id in self.user_states
        ]
    
    async def _monitoring_loop(self):
        """Main monitoring and trading loop."""
        while self.running:
            try:
                for user_id, state in list(self.user_states.items()):
                    if state.status != TradingStatus.ACTIVE:
                        continue
                    
                    if state.tier == MembershipTier.STEWARD:
                        await self._process_steward(user_id, state)
                    
                    # Small delay between users
                    await asyncio.sleep(1)
                
                # Wait before next cycle
                await asyncio.sleep(TRUE_LEVEL_10_CONFIG.check_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _process_steward(self, user_id: str, state: UserTradingState):
        """Process trading for a Tier 1 Steward."""
        try:
            client = self.user_clients.get(user_id)
            if not client:
                return
            
            # Update account state
            account_state = await client.get_account_state()
            state.balance = float(account_state.get("marginSummary", {}).get("accountValue", 0))
            state.open_positions = [
                p for p in account_state.get("positions", [])
                if float(p.get("szi", 0)) != 0
            ]
            state.last_check_time = datetime.now()
            
            # Process each symbol
            for symbol in TRUE_LEVEL_10_CONFIG.symbols:
                await self._evaluate_symbol_for_user(user_id, client, symbol, state)
            
        except Exception as e:
            logger.error(f"Error processing user {user_id}: {e}")
            state.error_message = str(e)
    
    async def _evaluate_symbol_for_user(
        self,
        user_id: str,
        client: HyperliquidClient,
        symbol: str,
        state: UserTradingState
    ):
        """Evaluate trading signal for a symbol for a specific user."""
        try:
            # Get market data
            klines = await client.get_klines(symbol, "1h", limit=50)
            if not klines or len(klines) < 20:
                return
            
            closes = [float(k['close']) for k in klines]
            
            # Calculate indicators
            current_price = closes[-1]
            ma20 = sum(closes[-20:]) / 20
            ma7 = sum(closes[-7:]) / 7
            
            # RSI calculation
            gains, losses = [], []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                gains.append(max(0, change))
                losses.append(max(0, -change))
            
            avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else 0
            avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else 0
            rsi = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss != 0 else 50
            
            indicators = {
                "rsi": rsi,
                "price": current_price,
                "ma20": ma20,
                "slope": ma7 - ma20
            }
            
            # Get signal from strategy
            signal = TRUE_LEVEL_10(indicators)
            
            # Check current position
            current_position = None
            for pos in state.open_positions:
                if pos.get("coin") == symbol:
                    current_position = pos
                    break
            
            if current_position:
                # Manage existing position
                await self._manage_position_for_user(
                    user_id, client, symbol, current_position, current_price, state
                )
            elif signal in ("LONG", "SHORT"):
                # Consider new trade
                await self._open_trade_for_user(
                    user_id, client, symbol, signal, current_price, state
                )
                
        except Exception as e:
            logger.error(f"Error evaluating {symbol} for user {user_id}: {e}")
    
    async def _open_trade_for_user(
        self,
        user_id: str,
        client: HyperliquidClient,
        symbol: str,
        signal: str,
        price: float,
        state: UserTradingState
    ):
        """Open a new trade for a user."""
        try:
            # Calculate position size (80% of available margin)
            account = await client.get_account_state()
            available = float(account.get("marginSummary", {}).get("availableMargin", 0))
            
            trade_size_usd = available * 0.80
            size = (trade_size_usd / price) * TRUE_LEVEL_10_CONFIG.leverage
            
            if size * price < 10:  # Minimum $10
                return
            
            side = "buy" if signal == "LONG" else "sell"
            
            result = await client.place_order(symbol, side, size)
            
            if result.get("success"):
                state.trades_today += 1
                state.last_trade_time = datetime.now()
                self.verifier.record_trade(user_id)
                
                logger.info(f"User {user_id}: Opened {signal} {symbol} @ ${price:.2f}")
                
        except Exception as e:
            logger.error(f"Error opening trade for user {user_id}: {e}")
    
    async def _manage_position_for_user(
        self,
        user_id: str,
        client: HyperliquidClient,
        symbol: str,
        position: Dict[str, Any],
        current_price: float,
        state: UserTradingState
    ):
        """Manage an existing position for a user."""
        try:
            entry_price = float(position.get("entryPx", 0))
            size = abs(float(position.get("szi", 0)))
            is_long = float(position.get("szi", 0)) > 0
            
            # Calculate PnL
            if is_long:
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
            
            pnl_pct_leveraged = pnl_pct * TRUE_LEVEL_10_CONFIG.leverage
            
            # Check stop loss
            if pnl_pct_leveraged <= -TRUE_LEVEL_10_CONFIG.stop_loss_pct:
                await self._close_position_for_user(
                    user_id, client, symbol, size, is_long, "STOP", state
                )
                return
            
            # Check take profit
            if pnl_pct_leveraged >= TRUE_LEVEL_10_CONFIG.take_profit_pct:
                await self._close_position_for_user(
                    user_id, client, symbol, size, is_long, "TARGET", state
                )
                return
            
        except Exception as e:
            logger.error(f"Error managing position for user {user_id}: {e}")
    
    async def _close_position_for_user(
        self,
        user_id: str,
        client: HyperliquidClient,
        symbol: str,
        size: float,
        is_long: bool,
        reason: str,
        state: UserTradingState
    ):
        """Close a position for a user."""
        try:
            side = "sell" if is_long else "buy"
            result = await client.place_order(symbol, side, size, reduce_only=True)
            
            if result.get("success"):
                logger.info(f"User {user_id}: Closed {symbol} ({reason})")
                state.trades_today += 1
                state.last_trade_time = datetime.now()
                self.verifier.record_trade(user_id)
                
        except Exception as e:
            logger.error(f"Error closing position for user {user_id}: {e}")
    
    async def emergency_stop_all(self) -> Dict[str, Any]:
        """Emergency stop all trading for all users and entities."""
        results = {}
        
        # Stop individual users
        for user_id in list(self.user_states.keys()):
            try:
                state = self.user_states[user_id]
                state.status = TradingStatus.PAUSED
                
                if state.tier == MembershipTier.STEWARD:
                    client = self.user_clients.get(user_id)
                    if client and state.open_positions:
                        # Close all positions
                        for pos in state.open_positions:
                            symbol = pos.get("coin")
                            size = abs(float(pos.get("szi", 0)))
                            is_long = float(pos.get("szi", 0)) > 0
                            await self._close_position_for_user(
                                user_id, client, symbol, size, is_long, "EMERGENCY", state
                            )
                
                results[user_id] = {"success": True}
                
            except Exception as e:
                results[user_id] = {"success": False, "error": str(e)}
        
        # Stop entity accounts
        for entity_id in list(self.entity_accounts.keys()):
            try:
                entity = self.entity_accounts[entity_id]
                entity.status = TradingStatus.PAUSED
                
                client = self.entity_clients.get(entity_id)
                if client and entity.open_positions:
                    for pos in entity.open_positions:
                        symbol = pos.get("coin")
                        size = abs(float(pos.get("szi", 0)))
                        is_long = float(pos.get("szi", 0)) > 0
                        side = "sell" if is_long else "buy"
                        await client.place_order(symbol, side, size, reduce_only=True)
                
                results[f"entity:{entity_id}"] = {"success": True}
                
            except Exception as e:
                results[f"entity:{entity_id}"] = {"success": False, "error": str(e)}
        
        logger.warning("EMERGENCY STOP executed for all users and entities")
        return results
    
    # =========================================================================
    # ENTITY ACCOUNT MANAGEMENT
    # =========================================================================
    
    async def create_entity_account(
        self,
        entity_id: str,
        entity_name: str,
        account_type: AccountType,
        primary_admin: str,
        authorized_users: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new entity trading account.
        
        Args:
            entity_id: Unique identifier for the entity
            entity_name: Display name (e.g., "Sunheart Private Trust")
            account_type: Type of entity (TRUST, LLC, CHURCH)
            primary_admin: User ID of primary administrator
            authorized_users: List of user IDs who can trade for this entity
        """
        async with self._lock:
            if entity_id in self.entity_accounts:
                return {"success": False, "error": "Entity account already exists"}
            
            # Get limits for this entity type
            limits = ENTITY_LIMITS.get(account_type, ENTITY_LIMITS[AccountType.INDIVIDUAL])
            
            # Create entity account
            entity = EntityTradingAccount(
                entity_id=entity_id,
                entity_name=entity_name,
                account_type=account_type,
                status=TradingStatus.DISABLED,  # Needs credentials
                authorized_users=authorized_users or [],
                primary_admin=primary_admin,
                balance=0,
                open_positions=[],
                daily_pnl=0,
                total_pnl=0,
                daily_volume=0,
                trades_today=0,
                daily_limit_uc=limits["daily_trade_limit_uc"],
                max_position_size_pct=limits["max_position_size_pct"],
                created_at=datetime.now()
            )
            
            self.entity_accounts[entity_id] = entity
            
            logger.info(f"Created entity account: {entity_name} ({account_type.value})")
            
            return {
                "success": True,
                "entity_id": entity_id,
                "account_type": account_type.value,
                "message": "Entity account created. Add API credentials to enable trading."
            }
    
    async def connect_entity_exchange(
        self,
        entity_id: str,
        user_id: str,  # Admin making the request
        api_key: str,
        api_secret: str,
        wallet_address: str = None
    ) -> Dict[str, Any]:
        """
        Connect an entity's exchange account.
        
        Args:
            entity_id: Entity to connect
            user_id: Admin user making the request
            api_key: Exchange API key
            api_secret: Exchange API secret
            wallet_address: Wallet address (for Hyperliquid)
        """
        async with self._lock:
            if entity_id not in self.entity_accounts:
                return {"success": False, "error": "Entity not found"}
            
            entity = self.entity_accounts[entity_id]
            
            # Check authorization
            if not entity.can_trade(user_id):
                return {"success": False, "error": "Not authorized for this entity"}
            
            try:
                # Store credentials securely
                self.vault.store_credentials(
                    user_id=f"entity:{entity_id}",
                    exchange="hyperliquid",
                    api_key=api_key,
                    api_secret=api_secret,
                    wallet_address=wallet_address
                )
                
                # Create Hyperliquid client
                client = HyperliquidClient()
                client.set_credentials(api_key, api_secret, wallet_address)
                
                if not client.connected:
                    return {"success": False, "error": "Failed to connect to exchange"}
                
                # Get initial state
                account_state = await client.get_account_state()
                entity.balance = float(account_state.get("marginSummary", {}).get("accountValue", 0))
                entity.status = TradingStatus.ACTIVE
                
                self.entity_clients[entity_id] = client
                
                logger.info(f"Connected entity {entity.entity_name} to Hyperliquid: ${entity.balance:.2f}")
                
                return {
                    "success": True,
                    "entity_id": entity_id,
                    "balance": entity.balance,
                    "message": f"Entity connected with ${entity.balance:,.2f} balance"
                }
                
            except Exception as e:
                logger.error(f"Error connecting entity {entity_id}: {e}")
                return {"success": False, "error": str(e)}
    
    async def add_authorized_user(
        self,
        entity_id: str,
        admin_user_id: str,
        new_user_id: str
    ) -> Dict[str, Any]:
        """Add an authorized user to an entity account."""
        if entity_id not in self.entity_accounts:
            return {"success": False, "error": "Entity not found"}
        
        entity = self.entity_accounts[entity_id]
        
        if entity.primary_admin != admin_user_id:
            return {"success": False, "error": "Only primary admin can add users"}
        
        if new_user_id in entity.authorized_users:
            return {"success": False, "error": "User already authorized"}
        
        entity.authorized_users.append(new_user_id)
        
        logger.info(f"Added user {new_user_id} to entity {entity.entity_name}")
        return {"success": True, "message": f"User added to {entity.entity_name}"}
    
    async def remove_authorized_user(
        self,
        entity_id: str,
        admin_user_id: str,
        remove_user_id: str
    ) -> Dict[str, Any]:
        """Remove an authorized user from an entity account."""
        if entity_id not in self.entity_accounts:
            return {"success": False, "error": "Entity not found"}
        
        entity = self.entity_accounts[entity_id]
        
        if entity.primary_admin != admin_user_id:
            return {"success": False, "error": "Only primary admin can remove users"}
        
        if remove_user_id == entity.primary_admin:
            return {"success": False, "error": "Cannot remove primary admin"}
        
        if remove_user_id in entity.authorized_users:
            entity.authorized_users.remove(remove_user_id)
            logger.info(f"Removed user {remove_user_id} from entity {entity.entity_name}")
            return {"success": True, "message": f"User removed from {entity.entity_name}"}
        
        return {"success": False, "error": "User not found in entity"}
    
    async def get_entity_status(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get trading status for an entity."""
        if entity_id not in self.entity_accounts:
            return None
        
        entity = self.entity_accounts[entity_id]
        
        return {
            "entity_id": entity.entity_id,
            "entity_name": entity.entity_name,
            "account_type": entity.account_type.value,
            "status": entity.status.value,
            "balance": entity.balance,
            "open_positions": len(entity.open_positions),
            "daily_pnl": entity.daily_pnl,
            "total_pnl": entity.total_pnl,
            "daily_volume": entity.daily_volume,
            "daily_limit": entity.daily_limit_uc,
            "trades_today": entity.trades_today,
            "authorized_users": len(entity.authorized_users),
            "primary_admin": entity.primary_admin,
            "last_trade": entity.last_trade_time.isoformat() if entity.last_trade_time else None,
            "created_at": entity.created_at.isoformat(),
            "error": entity.error_message
        }
    
    async def get_user_entities(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all entities a user is authorized for."""
        entities = []
        
        for entity_id, entity in self.entity_accounts.items():
            if entity.can_trade(user_id):
                status = await self.get_entity_status(entity_id)
                if status:
                    entities.append(status)
        
        return entities


# Singleton instance
_manager: Optional[MultiUserTradingManager] = None


def get_multi_user_manager() -> MultiUserTradingManager:
    """Get the singleton manager instance."""
    global _manager
    if _manager is None:
        _manager = MultiUserTradingManager()
    return _manager

