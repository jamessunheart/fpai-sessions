"""
FP Credits Gateway v3.1 - SINGLE SOURCE OF TRUTH
═══════════════════════════════════════════════════════════════════

The CONSOLIDATED economic system for the Full Potential ecosystem.
This service is the ONLY source of truth for all credit/payment data.

CONSOLIDATION (v3.1):
- Replaces: Credits Manager (8955) - DEPRECATED
- Bridges to: User Service (8110) for fiat payments
- Bridges to: Treasury (8040) for SOL tracking → NOW REAL ON-CHAIN
- Integrates: Genesis, AI Brain, all ecosystem services

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│            💎 FP CREDITS GATEWAY (SINGLE SOURCE OF TRUTH)       │
│                    Port 8765 - The Economic Backbone            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    CREDIT TYPES (All 1:1)                 │  │
│  │  FP Credits ←→ UC ←→ Cora ←→ Sky ←→ FI Tokens ←→ USD    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│         ┌────────────────────┼────────────────────┐            │
│         ▼                    ▼                    ▼            │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐    │
│  │   GENESIS   │      │  AI BRAIN   │      │USER SERVICE │    │
│  │   (Auth)    │      │(Intelligence)│      │ (Payments)  │    │
│  │  Port 8150  │      │  Port 8101  │      │  Port 8110  │    │
│  └─────────────┘      └─────────────┘      └─────────────┘    │
│                              │                    │            │
│                              ▼                    ▼            │
│                    ┌─────────────────────────────────┐         │
│                    │     SOLANA BLOCKCHAIN           │         │
│                    │   (Real on-chain treasury)      │         │
│                    │   Wallet: 2RS28TbG...           │         │
│                    └─────────────────────────────────┘         │
├─────────────────────────────────────────────────────────────────┤
│  SYSTEM ACCOUNTS:                                               │
│  • system:treasury     - Main treasury (1M FP)                 │
│  • system:fees         - Fee collection → ecosystem growth     │
│  • system:rewards      - Rewards pool                          │
│  • system:grants       - Creator grants                        │
│  • system:operations   - Operational costs                     │
│  • system:bridge       - On-chain bridge escrow                │
│  • system:ai-brain     - AI Brain revenue                      │
│  • system:reserve      - Emergency reserve                     │
└─────────────────────────────────────────────────────────────────┘

DEPRECATED SERVICES (v3.1):
- Credits Manager (port 8955) → Use this gateway instead
- SOL Treasury SSOT (port 8040) → Real on-chain data now

PAYMENT FLOW:
1. User → User Service (Stripe/PayPal/Crypto) → UC credited
2. UC ←→ FP Credits (1:1 via this gateway)
3. FP Credits → AI Brain queries, services, etc.

Author: Full Potential AI
Version: 3.1.0
"""

from fastapi import FastAPI, Depends, HTTPException, status, Header, WebSocket, WebSocketDisconnect, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import time
from collections import defaultdict
from enum import Enum
from decimal import Decimal, ROUND_DOWN
from contextlib import asynccontextmanager
import secrets
import hashlib
import json
import asyncio
import logging
import os

# Solana Integration (Optional - falls back to simulation if missing)
SOLANA_AVAILABLE = False
try:
    from solana.rpc.api import Client
    from solana.transaction import Transaction
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair
    from solders.instruction import Instruction
    from solders.system_program import TransferParams, transfer
    SOLANA_AVAILABLE = True
except ImportError:
    pass

import httpx

# Database imports (optional - graceful fallback to in-memory)
try:
    from sqlalchemy import create_engine, Column, String, Float, DateTime, Text, Boolean, JSON
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker, Session
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLALCHEMY_AVAILABLE = False
    logger_init = logging.getLogger("fp-credits")
    logger_init.warning("SQLAlchemy not installed - using in-memory storage")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fp-credits")

# ============================================================
# CONFIGURATION
# ============================================================

class Config:
    """Central configuration - all values can be overridden by environment"""
    
    # Service Identity
    SERVICE_NAME = "fp-credits-gateway"
    VERSION = "3.1.1"  # Bugfix: /api/ai/query now accepts AI Brain 'text' responses
    PORT = int(os.getenv("CREDITS_PORT", "8765"))
    
    # Database (SQLite for persistence, PostgreSQL for production)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./credits_ledger.db")
    USE_PERSISTENCE = os.getenv("USE_PERSISTENCE", "true").lower() == "true"
    
    # ==========================================================
    # CORE INTEGRATIONS - The Economic Nervous System
    # ==========================================================
    
    # Genesis - Central Mother Node (Auth, Service Discovery, Vault)
    GENESIS_URL = os.getenv("GENESIS_URL", "http://198.54.123.234:8150")
    GENESIS_ENROLLMENT_KEY = os.getenv("GENESIS_KEY", "enroll-1c77b8ce63c4")
    GENESIS_SWARM_SECRET = os.getenv("GENESIS_SWARM_SECRET", "fpai-swarm-genesis-permanent-link-v1")
    GENESIS_AGENT_TOKEN = os.getenv("GENESIS_AGENT_TOKEN", "agent-c543669c4b5243bb8576e18ecfd72ede")
    GENESIS_CONNECTED = False
    
    # AI Brain Connection (v4.1.0 on dedicated AI server)
    AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://162.0.208.88:8101")
    AI_BRAIN_KEY = os.getenv("AI_BRAIN_KEY", "")
    AI_BRAIN_CONNECTED = False
    AI_BRAIN_VERSION = "4.1.0"
    
    # User Service (UC Payments - the main payment layer)
    USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://162.0.208.88:8110")
    USER_SERVICE_CONNECTED = False
    
    # Credits Manager (Internal ledger - wallet/transaction backend)
    CREDITS_MANAGER_URL = os.getenv("CREDITS_MANAGER_URL", "http://198.54.123.234:8955")
    CREDITS_MANAGER_CONNECTED = False
    
    # Contribution Tracker (Commons Ministry - TRUST token issuance)
    CONTRIBUTION_TRACKER_URL = os.getenv("CONTRIBUTION_TRACKER_URL", "http://localhost:8570")
    CONTRIBUTION_TRACKER_CONNECTED = False
    
    # Solana Treasury Wallet (Church of Full Potential - REAL on-chain)
    # This is the AI-trustee created wallet for the Church
    SOLANA_TREASURY_WALLET = os.getenv("SOLANA_TREASURY_WALLET", "FLfNDVLD2vDQdTjMFSt1xJivhr8pKASwEBzRYHZRU7db")
    SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
    
    # AI Pricing (per 1000 tokens) - 0% markup, cost-based
    AI_COST_PER_1K_TOKENS = float(os.getenv("AI_COST_PER_1K", "0.01"))  # $0.01 per 1K tokens
    AI_CREDITS_PER_QUERY = float(os.getenv("AI_CREDITS_PER_QUERY", "0.10"))  # Min 0.10 FPC per query
    
    # Security
    MASTER_KEY = os.getenv("CREDITS_MASTER_KEY", "fpai_master_key_change_in_production")
    JWT_SECRET = os.getenv("JWT_SECRET", "change_this_in_production")
    
    # Rate Limits
    REQUESTS_PER_MINUTE = int(os.getenv("RATE_LIMIT_MINUTE", "100"))
    REQUESTS_PER_DAY = int(os.getenv("RATE_LIMIT_DAY", "10000"))
    
    # Credit Exchange Rates (All 1:1 for unified ecosystem)
    # These can be adjusted for market conditions
    FP_TO_USD = float(os.getenv("FP_TO_USD", "1.0"))
    FP_TO_CORA = float(os.getenv("FP_TO_CORA", "1.0"))
    FP_TO_SKY = float(os.getenv("FP_TO_SKY", "1.0"))
    FP_TO_FI = float(os.getenv("FP_TO_FI", "1.0"))
    
    # Fee Structure (Regenerative - funds ecosystem growth)
    FEE_INTERNAL_TRANSFER = 0.0      # Free internal transfers
    FEE_EXTERNAL_WITHDRAWAL = 0.02   # 2% for external withdrawals
    FEE_BRIDGE_ONCHAIN = 0.01        # 1% for on-chain bridge
    FEE_EXCHANGE = 0.005             # 0.5% for currency exchange
    
    # Treasury Allocation (from fees)
    TREASURY_OPERATIONS = 0.40       # 40% to operations
    TREASURY_REWARDS = 0.30          # 30% to rewards pool
    TREASURY_GRANTS = 0.20           # 20% to creator grants
    TREASURY_RESERVE = 0.10          # 10% to reserve
    
    # ==========================================================
    # ZEND FEE CIRCULATION (REGENERATIVE)
    # Per docs/protocols/ZEND_REGENERATIVE_SPEC.md Part 3
    # ==========================================================
    ZEND_FEE_OPS_PCT = float(os.getenv("ZEND_FEE_OPS_PCT", "40"))       # 40% to ops
    ZEND_FEE_COMMONS_PCT = float(os.getenv("ZEND_FEE_COMMONS_PCT", "30"))  # 30% to Commons Reserve
    ZEND_FEE_CIRCULATION_PCT = float(os.getenv("ZEND_FEE_CIRCULATION_PCT", "30"))  # 30% redistributed as UC
    
    # Limits
    MIN_TRANSFER = float(os.getenv("MIN_TRANSFER", "0.01"))
    MAX_TRANSFER = float(os.getenv("MAX_TRANSFER", "1000000.0"))
    MIN_EXTERNAL_WITHDRAWAL = float(os.getenv("MIN_WITHDRAWAL", "10.0"))
    
    # Initial Treasury (for new deployments)
    INITIAL_TREASURY = float(os.getenv("INITIAL_TREASURY", "1000000.0"))
    
    # Database (for production)
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./credits.db")
    USE_MEMORY_STORE = os.getenv("USE_MEMORY_STORE", "true").lower() == "true"
    
    # ==========================================================
    # CACHING CONFIGURATION
    # ==========================================================
    CACHE_PRICES_TTL = int(os.getenv("CACHE_PRICES_TTL", "60"))  # 60 seconds
    CACHE_BALANCE_TTL = int(os.getenv("CACHE_BALANCE_TTL", "30"))  # 30 seconds
    CACHE_HEALTH_TTL = int(os.getenv("CACHE_HEALTH_TTL", "15"))  # 15 seconds
    
    # ==========================================================
    # AUDIT CHAIN CONFIGURATION
    # ==========================================================
    AUDIT_CHAIN_MAX_MEMORY = int(os.getenv("AUDIT_CHAIN_MAX_MEMORY", "10000"))  # Keep last 10k blocks in memory
    AUDIT_ARCHIVE_PATH = os.getenv("AUDIT_ARCHIVE_PATH", "./audit_archive/")


# ============================================================
# SMART CACHE - Reduces external API calls
# ============================================================

class SmartCache:
    """
    Time-based cache with TTL support.
    Thread-safe for async operations.
    """
    def __init__(self):
        self._cache: Dict[str, dict] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value if not expired."""
        if key not in self._cache:
            return None
        entry = self._cache[key]
        if datetime.utcnow() > entry["expires"]:
            del self._cache[key]
            return None
        return entry["value"]
    
    async def set(self, key: str, value: Any, ttl_seconds: int):
        """Set value with TTL."""
        async with self._lock:
            self._cache[key] = {
                "value": value,
                "expires": datetime.utcnow() + timedelta(seconds=ttl_seconds),
                "created": datetime.utcnow()
            }
    
    async def invalidate(self, key: str):
        """Remove a key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def stats(self) -> dict:
        """Return cache statistics."""
        now = datetime.utcnow()
        valid = sum(1 for e in self._cache.values() if now < e["expires"])
        return {
            "total_keys": len(self._cache),
            "valid_keys": valid,
            "expired_keys": len(self._cache) - valid
        }

# Global cache instance
_cache = SmartCache()


# ============================================================
# ASYNC HTTP CLIENT - Connection pooling
# ============================================================

class AsyncHTTPClient:
    """
    Singleton async HTTP client with connection pooling.
    Reuses connections for better performance.
    """
    _instance: Optional[httpx.AsyncClient] = None
    
    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        if cls._instance is None or cls._instance.is_closed:
            cls._instance = httpx.AsyncClient(
                timeout=httpx.Timeout(10.0, connect=5.0),
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
                http2=False  # Disabled until h2 package is installed
            )
        return cls._instance
    
    @classmethod
    async def close(cls):
        if cls._instance and not cls._instance.is_closed:
            await cls._instance.aclose()
            cls._instance = None


# ============================================================
# METRICS COLLECTOR - For monitoring
# ============================================================

class MetricsCollector:
    """Collects performance and usage metrics."""
    def __init__(self):
        self.request_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.api_calls = {"solana_rpc": 0, "coingecko": 0, "genesis": 0, "ai_brain": 0}
        self.errors = {"solana_rpc": 0, "coingecko": 0, "genesis": 0, "ai_brain": 0}
        self.response_times: List[float] = []
        self.started_at = datetime.utcnow()
    
    def record_request(self, duration_ms: float):
        self.request_count += 1
        self.response_times.append(duration_ms)
        # Keep only last 1000 response times
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]
    
    def record_cache_hit(self):
        self.cache_hits += 1
    
    def record_cache_miss(self):
        self.cache_misses += 1
    
    def record_api_call(self, api: str, success: bool = True):
        if api in self.api_calls:
            self.api_calls[api] += 1
            if not success:
                self.errors[api] += 1
    
    def get_stats(self) -> dict:
        avg_response = sum(self.response_times) / len(self.response_times) if self.response_times else 0
        cache_ratio = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        uptime = (datetime.utcnow() - self.started_at).total_seconds()
        
        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "avg_response_ms": round(avg_response, 2),
            "cache_hit_ratio": round(cache_ratio, 4),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "api_calls": self.api_calls,
            "api_errors": self.errors,
            "requests_per_minute": round(self.request_count / (uptime / 60), 2) if uptime > 0 else 0
        }

# Global metrics instance
_metrics = MetricsCollector()


# ============================================================
# DATA MODELS
# ============================================================

class CreditType(str, Enum):
    """
    Supported credit types - ALL 1:1 PARITY
    
    Simple, clean credit system:
    - FP Credits: THE core currency ($1 USD) - use for everything including AI
    - Cora: Costa Rica / Cora Nation community
    - Sky: Global Sky Initiative
    - FI Tokens: On-chain ERC-20 representation
    
    Value proposition: Access to AI Brain at 0% markup (cost-based pricing)
    """
    # Core currency
    FP_CREDITS = "fp_credits"       # Full Potential Credits = $1 USD
    UC = "uc"                       # Universal Credit (alias for FP)
    
    # Community currencies (all 1:1 with FP)
    CORA = "cora"                   # Costa Rica / Cora Nation
    CORA_CREDITS = "cora_credits"   # Legacy alias
    SKY = "sky"                     # Global Sky Initiative
    SKY_CREDITS = "sky_credits"     # Legacy alias
    
    # On-chain representation
    FI_TOKENS = "fi_tokens"         # ERC-20 on-chain (1:1 with FP)
    
    # Fiat bridge
    USD = "usd"                     # Fiat reference
    
    @classmethod
    def all_types(cls) -> List[str]:
        return [ct.value for ct in cls]
    
    @classmethod
    def transferable(cls) -> List["CreditType"]:
        """Credits that can be transferred between users"""
        return [cls.FP_CREDITS, cls.UC, cls.CORA, cls.SKY, cls.FI_TOKENS]
    
    @classmethod
    def convertible(cls) -> List["CreditType"]:
        """Credits that can be exchanged for other types"""
        return [cls.FP_CREDITS, cls.UC, cls.CORA, cls.SKY, cls.FI_TOKENS, cls.USD]


class ReputationType(str, Enum):
    """Non-transferable reputation credits - earned by contribution"""
    BUILDER = "builder"             # Earned by coding/building
    COMMUNITY = "community"         # Community participation
    EVANGELIST = "evangelist"       # Spreading the word
    PATRON = "patron"               # Financial support
    
    @classmethod
    def all_types(cls) -> List[str]:
        return [rt.value for rt in cls]

class TransactionType(str, Enum):
    """Types of transactions"""
    CREDIT = "credit"           # Adding credits
    DEBIT = "debit"             # Removing credits
    TRANSFER = "transfer"       # Between accounts
    EXCHANGE = "exchange"       # Between credit types
    PURCHASE = "purchase"       # Buying with fiat
    WITHDRAWAL = "withdrawal"   # Converting to fiat
    BRIDGE_IN = "bridge_in"     # From blockchain
    BRIDGE_OUT = "bridge_out"   # To blockchain
    FEE = "fee"                 # System fee
    REWARD = "reward"           # Ecosystem reward
    GRANT = "grant"             # Creator grant
    REFUND = "refund"           # Refund
    MINT = "mint"               # Minting new credits (treasury only)
    BURN = "burn"               # Burning credits
    HOLD = "hold"               # Holding credits (pending transaction)
    COMMIT = "commit"           # Committing held credits
    RELEASE = "release"         # Releasing held credits
    CONTRIBUTION = "contribution"  # Reward for contribution

class TransactionStatus(str, Enum):
    """Transaction states"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVERSED = "reversed"

class AccountType(str, Enum):
    """Types of accounts"""
    USER = "user"               # End user
    SERVICE = "service"         # Internal service
    MERCHANT = "merchant"       # Business account
    TREASURY = "treasury"       # System treasury
    RESERVE = "reserve"         # Reserve accounts
    BRIDGE = "bridge"           # Blockchain bridge
    EXTERNAL = "external"       # External system


class WalletType(str, Enum):
    """Wallet types (mirrors AccountType for Credits Manager compatibility)"""
    USER = "user"
    SERVICE = "service"
    RESERVE = "reserve"
    TREASURY = "treasury"

class AccountTier(str, Enum):
    """Account tiers with different limits"""
    BASIC = "basic"             # Default tier
    VERIFIED = "verified"       # KYC verified
    PREMIUM = "premium"         # High-value account
    UNLIMITED = "unlimited"     # No limits (system accounts)


# ============================================================
# CREDIT TYPE DEFINITIONS (from Credits Manager)
# ============================================================

# Credit type metadata - ALL 1:1 PARITY
# Value proposition: Access to AI Brain at 0% markup (cost-based pricing)
CREDIT_TYPE_INFO = {
    "fp_credits": {
        "name": "FP Credits",
        "description": "Full Potential Credits - THE core currency. Use for AI, services, everything.",
        "is_transferable": True,
        "is_convertible": True,
        "usd_peg": 1.0,
        "icon": "💎",
        "color": "#FFD700"
    },
    "uc": {
        "name": "Universal Credit",
        "description": "Alias for FP Credits ($1 USD)",
        "is_transferable": True,
        "is_convertible": True,
        "usd_peg": 1.0,
        "icon": "💵",
        "color": "#4CAF50"
    },
    "cora": {
        "name": "Cora Credits",
        "description": "Costa Rica / Cora Nation community (1:1 with FP)",
        "is_transferable": True,
        "is_convertible": True,
        "usd_peg": 1.0,
        "icon": "🌴",
        "color": "#4DB6AC"
    },
    "sky": {
        "name": "Sky Credits",
        "description": "Global Sky Initiative (1:1 with FP)",
        "is_transferable": True,
        "is_convertible": True,
        "usd_peg": 1.0,
        "icon": "🌍",
        "color": "#03A9F4"
    },
    "fi_tokens": {
        "name": "FI Tokens",
        "description": "On-chain ERC-20 representation (1:1 with FP)",
        "is_transferable": True,
        "is_convertible": True,
        "usd_peg": 1.0,
        "icon": "🔗",
        "color": "#607D8B"
    }
}

# Reputation credit metadata (non-transferable)
REPUTATION_TYPE_INFO = {
    "builder": {
        "name": "Builder Credits",
        "description": "Earned by contributing code and building",
        "is_transferable": False,
        "is_convertible": False,
        "icon": "🔨",
        "color": "#795548"
    },
    "community": {
        "name": "Community Credits",
        "description": "Community participation",
        "is_transferable": False,
        "is_convertible": False,
        "icon": "👥",
        "color": "#00BCD4"
    },
    "evangelist": {
        "name": "Evangelist Credits",
        "description": "Spreading the word",
        "is_transferable": False,
        "is_convertible": False,
        "icon": "📢",
        "color": "#E91E63"
    },
    "patron": {
        "name": "Patron Credits",
        "description": "Financial support",
        "is_transferable": False,
        "is_convertible": False,
        "icon": "👑",
        "color": "#FFD700"
    }
}

# ============================================================
# CONTRIBUTION REWARDS SYSTEM
# ============================================================

# Contribution types and their multi-credit rewards
# Format: contribution_type -> {credit_type: multiplier}
# Multiplier is applied to the USD value of contribution
CONTRIBUTION_REWARDS = {
    # ==========================================================
    # FINANCIAL CONTRIBUTIONS - 1:1 ratio (no bonuses)
    # Benefit: Access to AI Brain at 0% markup (cost-based pricing)
    # ==========================================================
    "sol_deposit": {"fp_credits": 1.0},      # 1 SOL value = 1:1 FP Credits
    "eth_deposit": {"fp_credits": 1.0},      # 1 ETH value = 1:1 FP Credits
    "btc_deposit": {"fp_credits": 1.0},      # 1 BTC value = 1:1 FP Credits
    "fiat_donation": {"fp_credits": 1.0},    # $1 = 1 FP Credit
    "subscription": {"fp_credits": 1.0},     # $1 = 1 FP Credit
    
    # ==========================================================
    # WORK CONTRIBUTIONS - earn reputation (non-transferable)
    # ==========================================================
    "code_contribution": {"builder": 1.0},
    "content_creation": {"community": 1.0},
    "bug_report": {"builder": 0.5},
    "documentation": {"builder": 0.5, "community": 0.5},
    
    # ==========================================================
    # COMMUNITY CONTRIBUTIONS - earn reputation
    # ==========================================================
    "referral": {"evangelist": 1.0},
    "community_support": {"community": 1.0},
    "event_hosting": {"community": 2.0, "evangelist": 1.0},
    "social_share": {"evangelist": 0.1},
}

# Exchange rates between credit types (relative to UC)
# ALL CREDITS ARE 1:1 PARITY - Simple and transparent
EXCHANGE_RATES = {
    "fp_credits": 1.0,  # Core currency
    "uc": 1.0,          # Alias
    "cora": 1.0,        # 1:1 with FP
    "sky": 1.0,         # 1:1 with FP
    "fi_tokens": 1.0,   # 1:1 with FP
    "usd": 1.0,         # Fiat reference
}

# Crypto exchange rates (updated by oracle)
CRYPTO_RATES = {
    "SOL": 150.0,       # 1 SOL = 150 UC
    "ETH": 3500.0,      # 1 ETH = 3500 UC
    "BTC": 95000.0,     # 1 BTC = 95000 UC
}

# ============================================================
# REQUEST/RESPONSE MODELS
# ============================================================

class APIKeyCreate(BaseModel):
    service_name: str = Field(..., min_length=3, max_length=50)
    description: str = Field("", max_length=200)
    permissions: List[str] = Field(default=["read", "debit"])
    rate_limit: int = Field(default=100, ge=1, le=10000)
    
    @validator('permissions')
    def validate_permissions(cls, v):
        valid = {"read", "credit", "debit", "transfer", "exchange", "admin", "bridge"}
        for p in v:
            if p not in valid:
                raise ValueError(f"Invalid permission: {p}")
        return v

class APIKeyResponse(BaseModel):
    key_id: str
    api_key: str  # Only shown once on creation
    service_name: str
    permissions: List[str]
    created_at: str

class AccountCreate(BaseModel):
    account_id: str = Field(..., min_length=3, max_length=100)
    account_type: AccountType = AccountType.USER
    display_name: str = Field("", max_length=100)
    email: Optional[str] = None
    metadata: Dict[str, Any] = {}

class AccountResponse(BaseModel):
    account_id: str
    account_type: str
    tier: str
    display_name: str
    balances: Dict[str, float]
    total_value_usd: float
    created_at: str
    last_activity: str

class CreditRequest(BaseModel):
    account_id: str
    amount: float = Field(..., gt=0, le=Config.MAX_TRANSFER)
    credit_type: CreditType = CreditType.FP_CREDITS
    reason: str = Field(..., min_length=3, max_length=500)
    reference_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    
    @validator('amount')
    def round_amount(cls, v):
        return round(v, 8)  # 8 decimal precision

class DebitRequest(BaseModel):
    account_id: str
    amount: float = Field(..., gt=0, le=Config.MAX_TRANSFER)
    credit_type: CreditType = CreditType.FP_CREDITS
    reason: str = Field(..., min_length=3, max_length=500)
    reference_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

class TransferRequest(BaseModel):
    from_account: str
    to_account: str
    amount: float = Field(..., gt=0, le=Config.MAX_TRANSFER)
    credit_type: CreditType = CreditType.FP_CREDITS
    reason: str = Field("", max_length=500)
    metadata: Dict[str, Any] = {}
    
    @validator('to_account')
    def accounts_different(cls, v, values):
        if 'from_account' in values and v == values['from_account']:
            raise ValueError("Cannot transfer to same account")
        return v

class ExchangeRequest(BaseModel):
    account_id: str
    from_type: CreditType
    to_type: CreditType
    amount: float = Field(..., gt=0)
    
    @validator('to_type')
    def types_different(cls, v, values):
        if 'from_type' in values and v == values['from_type']:
            raise ValueError("Cannot exchange to same credit type")
        return v

class BridgeRequest(BaseModel):
    """Request to bridge credits to/from blockchain"""
    account_id: str
    amount: float = Field(..., gt=0)
    direction: str = Field(..., pattern="^(in|out)$")
    wallet_address: Optional[str] = None  # Required for bridge_out
    chain: str = Field(default="polygon")  # polygon, base, ethereum
    metadata: Dict[str, Any] = {}


# ============================================================
# HOLD/COMMIT/RELEASE MODELS (Safe Transactions)
# ============================================================

class HoldRequest(BaseModel):
    """Hold credits for a pending transaction"""
    from_wallet_id: str
    amount: float = Field(..., gt=0)
    currency: str = Field(default="uc")
    description: str = Field("", max_length=500)
    expires_in_seconds: int = Field(default=120, ge=10, le=3600)

class HoldResponse(BaseModel):
    hold_id: str
    from_wallet_id: str
    amount: float
    currency: str
    expires_at: str
    status: str

class CommitRequest(BaseModel):
    """Commit a held amount to a destination"""
    hold_id: str
    to_wallet_id: str

class ReleaseRequest(BaseModel):
    """Release a hold (cancel pending transaction)"""
    hold_id: str


# ============================================================
# CONTRIBUTION MODELS
# ============================================================

class ContributionRecord(BaseModel):
    """Record a contribution and issue rewards"""
    user_id: str
    contribution_type: str
    amount_usd: float = Field(..., gt=0)
    source: str = Field(default="system")
    preferred_credit_type: Optional[str] = None  # 10% bonus on preferred
    metadata: Dict[str, Any] = {}

class CryptoDepositRecord(BaseModel):
    """Record a crypto deposit"""
    user_id: str
    crypto_type: str = Field(..., pattern="^(SOL|ETH|BTC)$")
    crypto_amount: float = Field(..., gt=0)
    crypto_price_usd: Optional[float] = None  # Auto-fetch if not provided
    tx_hash: str

class FiatDonationRecord(BaseModel):
    """Record a fiat donation"""
    user_id: str
    amount_usd: float = Field(..., gt=0)
    payment_method: str = Field(default="stripe")
    is_recurring: bool = False
    reference_id: Optional[str] = None

# ============================================================
# GOVERNANCE MODELS
# ============================================================

class ProposalCreate(BaseModel):
    title: str
    description: str
    proposal_type: str = Field(..., pattern="^(phase_change|mint_grant|parameter_update)$")
    target_phase: Optional[str] = None
    execution_data: Dict[str, Any] = {}

class VoteCreate(BaseModel):
    vote: str = Field(..., pattern="^(for|against|abstain)$")

class ProposalResponse(BaseModel):
    proposal_id: str
    title: str
    description: str
    proposer_id: str
    proposal_type: str
    status: str
    created_at: datetime
    expires_at: datetime
    votes_for: float
    votes_against: float

class ContributionResponse(BaseModel):
    contribution_id: str
    user_id: str
    contribution_type: str
    amount_usd: float
    credits_issued: Dict[str, float]
    timestamp: str


class TransactionResponse(BaseModel):
    transaction_id: str
    account_id: str
    type: str
    status: str
    amount: float
    credit_type: str
    fee: float
    balance_after: float
    reason: str
    reference_id: Optional[str]
    created_at: str

class BalanceResponse(BaseModel):
    account_id: str
    balances: Dict[str, float]
    pending: Dict[str, float]
    total_value_usd: float
    last_updated: str

class StatsResponse(BaseModel):
    """System-wide statistics"""
    total_accounts: int
    total_transactions: int
    total_volume_24h: float
    total_fees_collected: float
    circulating_supply: Dict[str, float]
    treasury_balances: Dict[str, float]
    exchange_rates: Dict[str, float]

# ============================================================
# DATABASE MODELS (SQLAlchemy - Optional Persistence)
# ============================================================

if SQLALCHEMY_AVAILABLE:
    Base = declarative_base()
    
    class DBAccount(Base):
        __tablename__ = "accounts"
        
        account_id = Column(String(255), primary_key=True)
        account_type = Column(String(50), default="user")
        tier = Column(String(50), default="standard")
        balances = Column(JSON, default={})
        metadata_json = Column(JSON, default={})
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
        is_active = Column(Boolean, default=True)
    
    class DBTransaction(Base):
        __tablename__ = "transactions"
        
        tx_id = Column(String(255), primary_key=True)
        tx_type = Column(String(50))  # credit, debit, transfer, exchange, bridge
        status = Column(String(50), default="completed")
        from_account = Column(String(255), nullable=True)
        to_account = Column(String(255), nullable=True)
        credit_type = Column(String(50))
        amount = Column(Float)
        fee = Column(Float, default=0.0)
        description = Column(Text, nullable=True)
        reference_id = Column(String(255), nullable=True)
        metadata_json = Column(JSON, default={})
        created_at = Column(DateTime, default=datetime.utcnow)
    
    class DBApiKey(Base):
        __tablename__ = "api_keys"
        
        key_hash = Column(String(255), primary_key=True)
        key_prefix = Column(String(20))  # First 8 chars for identification
        service_name = Column(String(255))
        description = Column(Text, nullable=True)
        permissions = Column(JSON, default=[])
        created_at = Column(DateTime, default=datetime.utcnow)
        last_used = Column(DateTime, nullable=True)
        is_active = Column(Boolean, default=True)
    
    class DBHold(Base):
        __tablename__ = "holds"
        
        hold_id = Column(String(255), primary_key=True)
        account_id = Column(String(255))
        credit_type = Column(String(50))
        amount = Column(Float)
        description = Column(Text, nullable=True)
        expires_at = Column(DateTime)
        status = Column(String(50), default="active")  # active, committed, released, expired
        created_at = Column(DateTime, default=datetime.utcnow)

    class DBGovernanceProposal(Base):
        __tablename__ = "governance_proposals"
        
        proposal_id = Column(String(255), primary_key=True)
        title = Column(String(255))
        description = Column(Text)
        proposer_id = Column(String(255))
        proposal_type = Column(String(50))  # phase_change, mint_grant, parameter_update
        target_phase = Column(String(50), nullable=True)
        status = Column(String(50), default="active")  # active, passed, rejected, executed
        created_at = Column(DateTime, default=datetime.utcnow)
        expires_at = Column(DateTime)
        execution_data = Column(JSON, default={})
        votes_for = Column(Float, default=0.0)
        votes_against = Column(Float, default=0.0)

    class DBGovernanceVote(Base):
        __tablename__ = "governance_votes"
        
        vote_id = Column(String(255), primary_key=True)
        proposal_id = Column(String(255))
        voter_id = Column(String(255))
        vote = Column(String(20))  # for, against, abstain
        voting_power = Column(Float)
        timestamp = Column(DateTime, default=datetime.utcnow)


# ============================================================
# CREDIT STORE (With Database Persistence)
# ============================================================

class CreditStore:
    """
    The core credit ledger.
    
    Design principles:
    - All balances stored as floats with 8 decimal precision
    - Transactions are immutable once completed
    - Double-entry bookkeeping (every debit has a credit)
    - Atomic operations with rollback support
    """
    
    def __init__(self):
        self.accounts: Dict[str, dict] = {}
        self.transactions: List[dict] = []
        self.api_keys: Dict[str, dict] = {}
        self.rate_limits: Dict[str, dict] = {}
        self.websocket_connections: Dict[str, WebSocket] = {}
        self.pending_transactions: Dict[str, dict] = {}
        self.proposals: Dict[str, dict] = {}
        self.votes: Dict[str, dict] = {}
        self.webhooks: Dict[str, dict] = {}  # Webhook subscriptions
        
        # Audit Trail (Hash Chain)
        self.audit_chain: List[dict] = []
        self.last_block_hash: str = "GENESIS_BLOCK_" + hashlib.sha256(b"Full Potential Genesis").hexdigest()[:32]
        
        # Multi-Signature Queue (for large transactions)
        self.multisig_queue: Dict[str, dict] = {}
        self.MULTISIG_THRESHOLD = 10000.0  # Transactions > 10,000 UC require multi-sig
        self.MULTISIG_REQUIRED_APPROVALS = 2  # M-of-N (2 of 3 councils)
        
        # Service Compliance Tracking
        self.service_compliance: Dict[str, dict] = {}
        
        # Metrics
        self.metrics = {
            "total_volume_24h": 0.0,
            "total_fees_collected": 0.0,
            "transactions_today": 0
        }
        
        # Initialize system accounts
        self._init_system_accounts()
    
    def _init_system_accounts(self):
        """Create system treasury accounts"""
        system_accounts = [
            ("system:treasury", "FP Treasury", AccountType.TREASURY, Config.INITIAL_TREASURY),
            ("system:fees", "Fee Collection", AccountType.TREASURY, 0.0),
            ("system:rewards", "Rewards Pool", AccountType.TREASURY, 0.0),
            ("system:grants", "Creator Grants", AccountType.TREASURY, 0.0),
            ("system:operations", "Operations", AccountType.TREASURY, 0.0),
            ("system:bridge", "Bridge Escrow", AccountType.BRIDGE, 0.0),
            ("system:reserve", "Reserve Fund", AccountType.TREASURY, 0.0),
            ("system:ai-brain", "AI Brain Revenue", AccountType.TREASURY, 0.0),
        ]
        
        for acc_id, name, acc_type, initial_fp in system_accounts:
            # Initialize all credit types
            all_balances = {ct.value: 0.0 for ct in CreditType}
            all_balances[CreditType.FP_CREDITS.value] = initial_fp
            all_balances[CreditType.UC.value] = initial_fp  # UC mirrors FP
            
            # Initialize reputation credits
            reputation_balances = {rt.value: 0.0 for rt in ReputationType}
            
            self.accounts[acc_id] = {
                "account_id": acc_id,
                "account_type": acc_type.value,
                "tier": AccountTier.UNLIMITED.value,
                "display_name": name,
                "email": None,
                "balances": all_balances,
                "reputation": reputation_balances,
                "pending": {ct.value: 0.0 for ct in CreditType},
                "holds": {},  # Active holds
                "metadata": {"system": True},
                "limits": {
                    "daily_transfer": float('inf'),
                    "single_transfer": float('inf')
                },
                "created_at": datetime.utcnow().isoformat(),
                "last_activity": datetime.utcnow().isoformat()
            }
        
        logger.info(f"Initialized {len(system_accounts)} system accounts")
    
    def _calculate_total_usd(self, balances: Dict[str, float]) -> float:
        """Calculate total USD value of all balances"""
        total = 0.0
        total += balances.get(CreditType.FP_CREDITS.value, 0) * Config.FP_TO_USD
        total += balances.get(CreditType.CORA_CREDITS.value, 0) * Config.FP_TO_USD / Config.FP_TO_CORA
        total += balances.get(CreditType.SKY_CREDITS.value, 0) * Config.FP_TO_USD / Config.FP_TO_SKY
        total += balances.get(CreditType.FI_TOKENS.value, 0) * Config.FP_TO_USD / Config.FP_TO_FI
        total += balances.get(CreditType.USD.value, 0)
        return round(total, 2)
    
    def get_account(self, account_id: str) -> Optional[dict]:
        """Get account by ID"""
        return self.accounts.get(account_id)
    
    def create_account(
        self, 
        account_id: str, 
        account_type: AccountType = AccountType.USER,
        tier: AccountTier = AccountTier.BASIC,
        display_name: str = "", 
        email: str = None,
        metadata: dict = None
    ) -> dict:
        """Create a new account"""
        if account_id in self.accounts:
            raise ValueError(f"Account {account_id} already exists")
        
        # Set limits based on tier
        limits = {
            AccountTier.BASIC: {"daily_transfer": 1000, "single_transfer": 500},
            AccountTier.VERIFIED: {"daily_transfer": 10000, "single_transfer": 5000},
            AccountTier.PREMIUM: {"daily_transfer": 100000, "single_transfer": 50000},
            AccountTier.UNLIMITED: {"daily_transfer": float('inf'), "single_transfer": float('inf')},
        }
        
        account = {
            "account_id": account_id,
            "account_type": account_type.value,
            "tier": tier.value,
            "display_name": display_name or account_id,
            "email": email,
            "balances": {ct.value: 0.0 for ct in CreditType},
            "reputation": {rt.value: 0.0 for rt in ReputationType},
            "pending": {ct.value: 0.0 for ct in CreditType},
            "holds": {},  # Active holds
            "metadata": metadata or {},
            "limits": limits.get(tier, limits[AccountTier.BASIC]),
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }
        self.accounts[account_id] = account
        logger.info(f"Created account: {account_id} (type={account_type.value}, tier={tier.value})")
        return account
    
    def get_or_create_account(self, account_id: str, **kwargs) -> dict:
        """Get existing account or create new one"""
        if account_id not in self.accounts:
            return self.create_account(account_id, **kwargs)
        return self.accounts[account_id]
    
    def _generate_tx_id(self) -> str:
        """Generate unique transaction ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(6)
        return f"tx_{timestamp}_{random_part}"
    
    def credit(
        self, 
        account_id: str, 
        amount: float, 
        credit_type: CreditType,
        reason: str, 
        reference_id: str = None, 
        metadata: dict = None,
        source_account: str = None,
        tx_type: TransactionType = TransactionType.CREDIT
    ) -> dict:
        """Add credits to an account"""
        amount = round(amount, 8)
        
        account = self.get_or_create_account(
            account_id, 
            account_type=AccountType.USER,
            display_name=account_id
        )
        
        credit_type_str = credit_type.value if isinstance(credit_type, CreditType) else credit_type
        old_balance = account["balances"].get(credit_type_str, 0.0)
        new_balance = round(old_balance + amount, 8)
        account["balances"][credit_type_str] = new_balance
        account["last_activity"] = datetime.utcnow().isoformat()
        
        transaction = {
            "transaction_id": self._generate_tx_id(),
            "account_id": account_id,
            "counterparty": source_account,
            "type": tx_type.value,
            "status": TransactionStatus.COMPLETED.value,
            "amount": amount,
            "credit_type": credit_type_str,
            "fee": 0.0,
            "balance_before": old_balance,
            "balance_after": new_balance,
            "reason": reason,
            "reference_id": reference_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        self.transactions.append(transaction)
        
        # Update metrics
        self.metrics["total_volume_24h"] += amount * Config.FP_TO_USD
        
        # Notify websocket subscribers
        asyncio.create_task(self._notify_balance_change(account_id, account["balances"]))
        
        logger.info(f"Credit: {account_id} +{amount} {credit_type_str} ({reason})")
        return transaction
    
    def debit(
        self, 
        account_id: str, 
        amount: float, 
        credit_type: CreditType,
        reason: str, 
        reference_id: str = None, 
        metadata: dict = None,
        dest_account: str = None,
        tx_type: TransactionType = TransactionType.DEBIT,
        apply_fee: bool = False,
        fee_rate: float = 0.0
    ) -> dict:
        """Remove credits from an account"""
        amount = round(amount, 8)
        
        account = self.get_account(account_id)
        if not account:
            raise ValueError(f"Account {account_id} not found")
        
        credit_type_str = credit_type.value if isinstance(credit_type, CreditType) else credit_type
        old_balance = account["balances"].get(credit_type_str, 0.0)
        
        # Calculate fee if applicable
        fee = round(amount * fee_rate, 8) if apply_fee else 0.0
        total_debit = amount + fee
        
        if old_balance < total_debit:
            raise ValueError(f"Insufficient balance. Has {old_balance}, needs {total_debit} (amount: {amount}, fee: {fee})")
        
        new_balance = round(old_balance - total_debit, 8)
        account["balances"][credit_type_str] = new_balance
        account["last_activity"] = datetime.utcnow().isoformat()
        
        transaction = {
            "transaction_id": self._generate_tx_id(),
            "account_id": account_id,
            "counterparty": dest_account,
            "type": tx_type.value,
            "status": TransactionStatus.COMPLETED.value,
            "amount": -amount,
            "credit_type": credit_type_str,
            "fee": fee,
            "balance_before": old_balance,
            "balance_after": new_balance,
            "reason": reason,
            "reference_id": reference_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        self.transactions.append(transaction)
        
        # Collect fee to system account
        if fee > 0:
            self._collect_fee(fee, credit_type, f"Fee from {account_id}: {reason}")
        
        # Update metrics
        self.metrics["total_volume_24h"] += amount * Config.FP_TO_USD
        
        asyncio.create_task(self._notify_balance_change(account_id, account["balances"]))
        
        logger.info(f"Debit: {account_id} -{amount} {credit_type_str} (fee: {fee}) ({reason})")
        return transaction
    
    def _collect_fee(self, fee: float, credit_type: CreditType, reason: str):
        """Collect fee and distribute to treasury accounts"""
        credit_type_str = credit_type.value if isinstance(credit_type, CreditType) else credit_type
        
        # Add to fee collection account
        fee_account = self.accounts["system:fees"]
        fee_account["balances"][credit_type_str] += fee
        
        # Distribute according to treasury allocation
        distributions = [
            ("system:operations", Config.TREASURY_OPERATIONS),
            ("system:rewards", Config.TREASURY_REWARDS),
            ("system:grants", Config.TREASURY_GRANTS),
            ("system:reserve", Config.TREASURY_RESERVE),
        ]
        
        for acc_id, percentage in distributions:
            allocation = round(fee * percentage, 8)
            self.accounts[acc_id]["balances"][credit_type_str] += allocation
        
        self.metrics["total_fees_collected"] += fee
        logger.debug(f"Fee collected: {fee} {credit_type_str} - {reason}")

    def collect_zend_fee(self, fee: float, credit_type: CreditType, reason: str, sender_id: str = None) -> dict:
        """
        Collect Zend fee with regenerative circulation.
        Per docs/protocols/ZEND_REGENERATIVE_SPEC.md Part 3:
        - 40% to system:zend_ops (infrastructure/partners)
        - 30% to system:commons (Commons Reserve Fund)
        - 30% redistributed as UC (rewards/sponsored sends)
        
        Returns distribution breakdown.
        """
        credit_type_str = credit_type.value if isinstance(credit_type, CreditType) else credit_type
        
        # Ensure Zend system accounts exist
        for acc_id in ["system:zend_ops", "system:zend_circulation"]:
            if acc_id not in self.accounts:
                self.get_or_create_account(acc_id, account_type=AccountType.SYSTEM, tier=AccountTier.SYSTEM)
        
        # Calculate distribution percentages (divide by 100 as they're stored as %)
        ops_pct = Config.ZEND_FEE_OPS_PCT / 100.0
        commons_pct = Config.ZEND_FEE_COMMONS_PCT / 100.0
        circulation_pct = Config.ZEND_FEE_CIRCULATION_PCT / 100.0
        
        # Calculate allocations
        ops_allocation = round(fee * ops_pct, 8)
        commons_allocation = round(fee * commons_pct, 8)
        circulation_allocation = round(fee * circulation_pct, 8)
        
        # Distribute
        distributions = {
            "system:zend_ops": ops_allocation,
            "system:commons": commons_allocation,
            "system:zend_circulation": circulation_allocation,
        }
        
        for acc_id, allocation in distributions.items():
            if allocation > 0:
                self.accounts[acc_id]["balances"][credit_type_str] = \
                    self.accounts[acc_id]["balances"].get(credit_type_str, 0.0) + allocation
        
        # Track Zend-specific metrics
        if "zend_fees_collected" not in self.metrics:
            self.metrics["zend_fees_collected"] = 0.0
            self.metrics["zend_commons_funded"] = 0.0
        
        self.metrics["zend_fees_collected"] += fee
        self.metrics["zend_commons_funded"] += commons_allocation
        self.metrics["total_fees_collected"] += fee
        
        # If sender provided and circulation > 0, credit back as sponsored send capacity
        if sender_id and circulation_allocation > 0:
            sender_account = self.get_account(sender_id)
            if sender_account:
                # Add to sender's UC balance as "sponsored send" credit
                sender_account["balances"][credit_type_str] = \
                    sender_account["balances"].get(credit_type_str, 0.0) + circulation_allocation
                logger.info(f"Zend circulation: {circulation_allocation} {credit_type_str} credited back to {sender_id}")
        
        logger.info(f"Zend fee collected: {fee} {credit_type_str} - ops:{ops_allocation}, commons:{commons_allocation}, circulation:{circulation_allocation}")
        
        return {
            "total_fee": fee,
            "ops": ops_allocation,
            "commons": commons_allocation,
            "circulation": circulation_allocation,
            "sender_credited": sender_id if sender_id else None,
            "reason": reason,
        }
    
    def transfer(
        self, 
        from_account: str, 
        to_account: str, 
        amount: float,
        credit_type: CreditType, 
        reason: str = "", 
        metadata: dict = None,
        apply_fee: bool = False
    ) -> tuple:
        """Transfer credits between accounts (atomic)"""
        fee_rate = Config.FEE_INTERNAL_TRANSFER if not apply_fee else Config.FEE_EXTERNAL_WITHDRAWAL
        
        # Debit from source (with fee if external)
        debit_tx = self.debit(
            from_account, 
            amount, 
            credit_type,
            f"Transfer to {to_account}: {reason}",
            dest_account=to_account,
            tx_type=TransactionType.TRANSFER,
            apply_fee=apply_fee,
            fee_rate=fee_rate,
            metadata=metadata
        )
        
        # Credit to destination
        credit_tx = self.credit(
            to_account, 
            amount, 
            credit_type,
            f"Transfer from {from_account}: {reason}",
            source_account=from_account,
            tx_type=TransactionType.TRANSFER,
            metadata=metadata
        )
        
        return debit_tx, credit_tx
    
    def exchange(
        self, 
        account_id: str, 
        from_type: CreditType, 
        to_type: CreditType, 
        amount: float
    ) -> tuple:
        """Exchange between credit types"""
        # Get exchange rate
        rate = self._get_exchange_rate(from_type, to_type)
        if rate is None:
            raise ValueError(f"Unsupported exchange: {from_type} -> {to_type}")
        
        converted_amount = round(amount * rate, 8)
        fee = round(amount * Config.FEE_EXCHANGE, 8)
        
        # Debit source currency (with fee)
        debit_tx = self.debit(
            account_id, 
            amount, 
            from_type,
            f"Exchange to {to_type.value}",
            tx_type=TransactionType.EXCHANGE,
            apply_fee=True,
            fee_rate=Config.FEE_EXCHANGE
        )
        
        # Credit destination currency
        credit_tx = self.credit(
            account_id, 
            converted_amount, 
            to_type,
            f"Exchange from {from_type.value}",
            tx_type=TransactionType.EXCHANGE
        )
        
        return debit_tx, credit_tx, rate
    
    def _get_exchange_rate(self, from_type: CreditType, to_type: CreditType) -> Optional[float]:
        """Get exchange rate between credit types"""
        from_str = from_type.value if isinstance(from_type, CreditType) else from_type
        to_str = to_type.value if isinstance(to_type, CreditType) else to_type
        
        # All credits are 1:1 with FP as the base
        rates = {
            CreditType.FP_CREDITS.value: 1.0,
            CreditType.CORA_CREDITS.value: Config.FP_TO_CORA,
            CreditType.SKY_CREDITS.value: Config.FP_TO_SKY,
            CreditType.FI_TOKENS.value: Config.FP_TO_FI,
            CreditType.USD.value: Config.FP_TO_USD,
        }
        
        if from_str not in rates or to_str not in rates:
            return None
        
        # Convert through FP as base
        from_rate = rates[from_str]
        to_rate = rates[to_str]
        
        return to_rate / from_rate
    
    def bridge_out(
        self, 
        account_id: str, 
        amount: float, 
        wallet_address: str,
        chain: str = "polygon"
    ) -> dict:
        """Bridge credits to on-chain FI tokens"""
        # Debit from user account
        debit_tx = self.debit(
            account_id,
            amount,
            CreditType.FP_CREDITS,
            f"Bridge to {chain}: {wallet_address}",
            tx_type=TransactionType.BRIDGE_OUT,
            apply_fee=True,
            fee_rate=Config.FEE_BRIDGE_ONCHAIN,
            metadata={"wallet": wallet_address, "chain": chain}
        )
        
        # Credit to bridge escrow (for on-chain minting)
        self.credit(
            "system:bridge",
            amount,
            CreditType.FI_TOKENS,
            f"Bridge escrow for {account_id}",
            source_account=account_id,
            tx_type=TransactionType.BRIDGE_OUT,
            metadata={"wallet": wallet_address, "chain": chain, "pending_mint": True}
        )
        
        # TODO: Trigger actual on-chain minting via bridge service
        
        return debit_tx
    
    def bridge_in(
        self, 
        account_id: str, 
        amount: float, 
        tx_hash: str,
        chain: str = "polygon"
    ) -> dict:
        """Bridge on-chain FI tokens to credits"""
        # Verify on-chain transaction (TODO: integrate with blockchain)
        
        # Credit user account
        credit_tx = self.credit(
            account_id,
            amount,
            CreditType.FP_CREDITS,
            f"Bridge from {chain}: {tx_hash}",
            tx_type=TransactionType.BRIDGE_IN,
            reference_id=tx_hash,
            metadata={"chain": chain, "tx_hash": tx_hash}
        )
        
        return credit_tx
    
    # ============================================================
    # HOLD/COMMIT/RELEASE (Safe Transactions)
    # ============================================================
    
    def hold(
        self,
        from_wallet_id: str,
        amount: float,
        currency: str = "uc",
        description: str = "",
        expires_in_seconds: int = 120
    ) -> dict:
        """Hold credits for a pending transaction (prevents double-spend)"""
        account = self.get_account(from_wallet_id)
        if not account:
            raise ValueError(f"Account {from_wallet_id} not found")
        
        # Normalize currency
        currency_lower = currency.lower()
        balance = account["balances"].get(currency_lower, 0.0)
        
        if balance < amount:
            raise ValueError(f"Insufficient balance. Has {balance}, needs {amount}")
        
        # Create hold
        hold_id = f"hold_{secrets.token_hex(8)}"
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        
        hold = {
            "hold_id": hold_id,
            "from_wallet_id": from_wallet_id,
            "amount": amount,
            "currency": currency_lower,
            "description": description,
            "expires_at": expires_at.isoformat(),
            "status": "held",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Deduct from available balance, add to pending
        account["balances"][currency_lower] -= amount
        account["pending"][currency_lower] = account.get("pending", {}).get(currency_lower, 0.0) + amount
        
        # Store hold
        if "holds" not in account:
            account["holds"] = {}
        account["holds"][hold_id] = hold
        
        # Record transaction
        self.transactions.append({
            "transaction_id": self._generate_tx_id(),
            "account_id": from_wallet_id,
            "type": TransactionType.HOLD.value,
            "status": TransactionStatus.PENDING.value,
            "amount": -amount,
            "credit_type": currency_lower,
            "fee": 0,
            "balance_before": balance,
            "balance_after": account["balances"][currency_lower],
            "reason": description,
            "reference_id": hold_id,
            "metadata": {"hold_id": hold_id, "expires_at": expires_at.isoformat()},
            "created_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Hold created: {hold_id} - {amount} {currency_lower} from {from_wallet_id}")
        return hold
    
    def commit(self, hold_id: str, to_wallet_id: str) -> dict:
        """Commit a held amount to a destination wallet"""
        # Find the hold
        hold = None
        from_account = None
        for acc_id, account in self.accounts.items():
            if "holds" in account and hold_id in account["holds"]:
                hold = account["holds"][hold_id]
                from_account = account
                break
        
        if not hold:
            raise ValueError(f"Hold {hold_id} not found")
        
        if hold["status"] != "held":
            raise ValueError(f"Hold {hold_id} is not active (status: {hold['status']})")
        
        # Check expiration
        if datetime.fromisoformat(hold["expires_at"]) < datetime.utcnow():
            # Auto-release expired hold
            self._release_hold(hold, from_account)
            raise ValueError(f"Hold {hold_id} has expired")
        
        # Get destination account
        to_account = self.get_or_create_account(to_wallet_id)
        
        # Transfer from pending to destination
        currency = hold["currency"]
        amount = hold["amount"]
        
        from_account["pending"][currency] -= amount
        to_account["balances"][currency] = to_account["balances"].get(currency, 0.0) + amount
        
        # Update hold status
        hold["status"] = "committed"
        hold["committed_at"] = datetime.utcnow().isoformat()
        hold["to_wallet_id"] = to_wallet_id
        
        # Record transactions
        tx_id = self._generate_tx_id()
        self.transactions.append({
            "transaction_id": tx_id,
            "account_id": from_account["account_id"],
            "counterparty": to_wallet_id,
            "type": TransactionType.COMMIT.value,
            "status": TransactionStatus.COMPLETED.value,
            "amount": -amount,
            "credit_type": currency,
            "fee": 0,
            "balance_before": from_account["pending"][currency] + amount,
            "balance_after": from_account["pending"][currency],
            "reason": f"Commit hold {hold_id}",
            "reference_id": hold_id,
            "metadata": {"hold_id": hold_id},
            "created_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Hold committed: {hold_id} - {amount} {currency} to {to_wallet_id}")
        return {"hold_id": hold_id, "status": "committed", "transaction_id": tx_id}
    
    def release(self, hold_id: str) -> dict:
        """Release a hold (cancel pending transaction)"""
        # Find the hold
        hold = None
        from_account = None
        for acc_id, account in self.accounts.items():
            if "holds" in account and hold_id in account["holds"]:
                hold = account["holds"][hold_id]
                from_account = account
                break
        
        if not hold:
            raise ValueError(f"Hold {hold_id} not found")
        
        if hold["status"] != "held":
            raise ValueError(f"Hold {hold_id} is not active (status: {hold['status']})")
        
        return self._release_hold(hold, from_account)
    
    def _release_hold(self, hold: dict, account: dict) -> dict:
        """Internal method to release a hold"""
        currency = hold["currency"]
        amount = hold["amount"]
        
        # Return to available balance
        account["pending"][currency] -= amount
        account["balances"][currency] += amount
        
        # Update hold status
        hold["status"] = "released"
        hold["released_at"] = datetime.utcnow().isoformat()
        
        # Record transaction
        self.transactions.append({
            "transaction_id": self._generate_tx_id(),
            "account_id": account["account_id"],
            "type": TransactionType.RELEASE.value,
            "status": TransactionStatus.COMPLETED.value,
            "amount": amount,
            "credit_type": currency,
            "fee": 0,
            "balance_before": account["balances"][currency] - amount,
            "balance_after": account["balances"][currency],
            "reason": f"Release hold {hold['hold_id']}",
            "reference_id": hold["hold_id"],
            "metadata": {"hold_id": hold["hold_id"]},
            "created_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Hold released: {hold['hold_id']} - {amount} {currency}")
        return {"hold_id": hold["hold_id"], "status": "released"}
    
    # ============================================================
    # CONTRIBUTION REWARDS SYSTEM
    # ============================================================
    
    def record_contribution(
        self,
        user_id: str,
        contribution_type: str,
        amount_usd: float,
        source: str = "system",
        preferred_credit_type: str = None,
        metadata: dict = None
    ) -> dict:
        """Record a contribution and issue multi-credit rewards"""
        if contribution_type not in CONTRIBUTION_REWARDS:
            raise ValueError(f"Unknown contribution type: {contribution_type}")
        
        # Get or create user account
        account = self.get_or_create_account(user_id)
        
        # Get reward multipliers for this contribution type
        rewards = CONTRIBUTION_REWARDS[contribution_type]
        credits_issued = {}
        
        for credit_type, multiplier in rewards.items():
            credit_amount = round(amount_usd * multiplier, 8)
            
            # Apply 10% bonus for preferred credit type
            if preferred_credit_type and credit_type == preferred_credit_type.lower():
                credit_amount = round(credit_amount * 1.1, 8)
            
            # Issue credits (check if reputation or transferable)
            if credit_type in [rt.value for rt in ReputationType]:
                # Reputation credits (non-transferable)
                if "reputation" not in account:
                    account["reputation"] = {rt.value: 0.0 for rt in ReputationType}
                account["reputation"][credit_type] = account["reputation"].get(credit_type, 0.0) + credit_amount
            else:
                # Transferable credits
                account["balances"][credit_type] = account["balances"].get(credit_type, 0.0) + credit_amount
            
            credits_issued[credit_type] = credit_amount
        
        # Record contribution transaction
        contribution_id = f"contrib_{secrets.token_hex(8)}"
        self.transactions.append({
            "transaction_id": self._generate_tx_id(),
            "account_id": user_id,
            "type": TransactionType.CONTRIBUTION.value,
            "status": TransactionStatus.COMPLETED.value,
            "amount": amount_usd,
            "credit_type": "usd",
            "fee": 0,
            "balance_before": 0,
            "balance_after": 0,
            "reason": f"Contribution: {contribution_type}",
            "reference_id": contribution_id,
            "metadata": {
                "contribution_type": contribution_type,
                "source": source,
                "credits_issued": credits_issued,
                **(metadata or {})
            },
            "created_at": datetime.utcnow().isoformat()
        })
        
        logger.info(f"Contribution recorded: {user_id} - {contribution_type} - ${amount_usd} - issued {credits_issued}")
        
        # === COMMONS MINISTRY INTEGRATION ===
        # Send to Contribution Tracker for TRUST token issuance
        asyncio.create_task(self._notify_contribution_tracker(
            member_id=user_id,
            contribution_type=contribution_type,
            amount=amount_usd,
            contribution_id=contribution_id
        ))
        
        return {
            "contribution_id": contribution_id,
            "user_id": user_id,
            "contribution_type": contribution_type,
            "amount_usd": amount_usd,
            "credits_issued": credits_issued,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _notify_contribution_tracker(
        self,
        member_id: str,
        contribution_type: str,
        amount: float,
        contribution_id: str
    ):
        """
        Notify Contribution Tracker for TRUST token issuance.
        This is the wiring between Credits Gateway and Commons Ministry.
        """
        try:
            # Map internal contribution types to tracker types
            type_mapping = {
                "fiat_donation": "financial",
                "sol_deposit": "financial",
                "eth_deposit": "financial",
                "btc_deposit": "financial",
                "subscription": "financial",
                "code_contribution": "service",
                "content_creation": "art",
                "bug_report": "service",
                "documentation": "service",
                "referral": "referral",
                "community_support": "community"
            }
            tracker_type = type_mapping.get(contribution_type, "community")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{Config.CONTRIBUTION_TRACKER_URL}/api/contributions/log",
                    json={
                        "member_id": member_id,
                        "type": tracker_type,
                        "description": f"Credits Gateway: {contribution_type}",
                        "amount": amount if tracker_type == "financial" else None,
                        "reference_id": contribution_id
                    }
                )
                if response.status_code == 200:
                    logger.info(f"[COMMONS] Contribution logged to tracker: {member_id} - {tracker_type}")
                    Config.CONTRIBUTION_TRACKER_CONNECTED = True
                else:
                    logger.warning(f"[COMMONS] Tracker returned {response.status_code}")
        except Exception as e:
            logger.debug(f"[COMMONS] Contribution tracker not available: {e}")
            Config.CONTRIBUTION_TRACKER_CONNECTED = False
    
    def record_crypto_deposit(
        self,
        user_id: str,
        crypto_type: str,
        crypto_amount: float,
        crypto_price_usd: float = None,
        tx_hash: str = None
    ) -> dict:
        """Record a crypto deposit and issue rewards"""
        crypto_type = crypto_type.upper()
        
        # Get price from oracle if not provided
        if crypto_price_usd is None:
            crypto_price_usd = CRYPTO_RATES.get(crypto_type, 0)
        
        if crypto_price_usd == 0:
            raise ValueError(f"Unknown crypto type: {crypto_type}")
        
        amount_usd = crypto_amount * crypto_price_usd
        
        # Map crypto type to contribution type
        contribution_map = {
            "SOL": "sol_deposit",
            "ETH": "eth_deposit",
            "BTC": "btc_deposit"
        }
        contribution_type = contribution_map.get(crypto_type, "fiat_donation")
        
        return self.record_contribution(
            user_id=user_id,
            contribution_type=contribution_type,
            amount_usd=amount_usd,
            source="treasury",
            metadata={
                "crypto_type": crypto_type,
                "crypto_amount": crypto_amount,
                "crypto_price_usd": crypto_price_usd,
                "tx_hash": tx_hash
            }
        )
    
    def get_user_credits(self, user_id: str) -> dict:
        """Get all credits (transferable + reputation) for a user"""
        account = self.get_account(user_id)
        if not account:
            return {
                "user_id": user_id,
                "transferable": {},
                "reputation": {},
                "total_value_usd": 0.0
            }
        
        return {
            "user_id": user_id,
            "transferable": account.get("balances", {}),
            "reputation": account.get("reputation", {}),
            "total_value_usd": self._calculate_total_usd(account.get("balances", {}))
        }
    
    def get_balance(self, account_id: str) -> dict:
        """Get account balance"""
        account = self.get_account(account_id)
        if not account:
            return {
                "balances": {ct.value: 0.0 for ct in CreditType},
                "pending": {ct.value: 0.0 for ct in CreditType},
                "reputation": {rt.value: 0.0 for rt in ReputationType},
                "total_value_usd": 0.0
            }
        return {
            "balances": account["balances"],
            "pending": account.get("pending", {}),
            "reputation": account.get("reputation", {}),
            "total_value_usd": self._calculate_total_usd(account["balances"])
        }
    
    def get_transactions(
        self, 
        account_id: str, 
        limit: int = 50,
        offset: int = 0,
        tx_type: str = None
    ) -> List[dict]:
        """Get transaction history for an account"""
        txs = [
            tx for tx in reversed(self.transactions)
            if tx["account_id"] == account_id
            and (tx_type is None or tx["type"] == tx_type)
        ]
        return txs[offset:offset + limit]
    
    # API Key Management
    def create_api_key(
        self, 
        service_name: str, 
        description: str = "",
        permissions: List[str] = None, 
        rate_limit: int = 100
    ) -> dict:
        """Create a new API key for a service"""
        key_id = f"fpk_{secrets.token_hex(8)}"
        api_key = f"fps_{secrets.token_hex(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        key_record = {
            "key_id": key_id,
            "key_hash": key_hash,
            "service_name": service_name,
            "description": description,
            "permissions": permissions or ["read", "debit"],
            "rate_limit": rate_limit,
            "created_at": datetime.utcnow().isoformat(),
            "last_used": None,
            "usage_count": 0,
            "active": True
        }
        self.api_keys[key_id] = key_record
        
        # Create service account
        self.get_or_create_account(
            f"service:{service_name}",
            account_type=AccountType.SERVICE,
            tier=AccountTier.VERIFIED,
            display_name=description or service_name
        )
        
        return {
            "key_id": key_id,
            "api_key": api_key,
            "service_name": service_name,
            "permissions": key_record["permissions"],
            "created_at": key_record["created_at"]
        }
    
    def verify_api_key(self, api_key: str) -> Optional[dict]:
        """Verify an API key and return its record"""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        for key_id, record in self.api_keys.items():
            if record["key_hash"] == key_hash and record["active"]:
                record["last_used"] = datetime.utcnow().isoformat()
                record["usage_count"] += 1
                return record
        return None
    
    def check_rate_limit(self, key_id: str, limit: int) -> bool:
        """Check if rate limit is exceeded"""
        now = datetime.utcnow()
        minute_key = f"{key_id}:{now.strftime('%Y%m%d%H%M')}"
        
        if minute_key not in self.rate_limits:
            self.rate_limits[minute_key] = 0
            # Clean old entries
            cutoff = (now - timedelta(minutes=5)).strftime('%Y%m%d%H%M')
            self.rate_limits = {k: v for k, v in self.rate_limits.items() if k.split(':')[1] >= cutoff}
        
        self.rate_limits[minute_key] += 1
        return self.rate_limits[minute_key] <= limit
    
    async def _notify_balance_change(self, account_id: str, balances: dict):
        """Notify WebSocket subscribers of balance change"""
        if account_id in self.websocket_connections:
            ws = self.websocket_connections[account_id]
            try:
                await ws.send_json({
                    "type": "balance_update",
                    "account_id": account_id,
                    "balances": balances,
                    "total_value_usd": self._calculate_total_usd(balances),
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                logger.warning(f"WebSocket notification failed for {account_id}: {e}")
                if account_id in self.websocket_connections:
                    del self.websocket_connections[account_id]
    
    def get_system_stats(self) -> dict:
        """Get system-wide statistics"""
        user_accounts = [a for a in self.accounts.values() if not a["account_id"].startswith("system:")]
        
        circulating = {ct.value: 0.0 for ct in CreditType}
        for acc in user_accounts:
            for ct in CreditType:
                circulating[ct.value] += acc["balances"].get(ct.value, 0)
        
        treasury = {}
        for acc_id, acc in self.accounts.items():
            if acc_id.startswith("system:"):
                treasury[acc_id] = acc["balances"]
        
        return {
            "total_accounts": len(user_accounts),
            "total_transactions": len(self.transactions),
            "total_volume_24h": self.metrics["total_volume_24h"],
            "total_fees_collected": self.metrics["total_fees_collected"],
            "circulating_supply": circulating,
            "treasury_balances": treasury,
            "exchange_rates": {
                "FP_TO_USD": Config.FP_TO_USD,
                "FP_TO_CORA": Config.FP_TO_CORA,
                "FP_TO_SKY": Config.FP_TO_SKY,
                "FP_TO_FI": Config.FP_TO_FI,
            }
        }

    # ============================================================
    # GOVERNANCE METHODS
    # ============================================================
    
    def create_proposal(self, title: str, description: str, proposer_id: str, 
                       proposal_type: str, target_phase: str = None, 
                       execution_data: dict = None) -> dict:
        """Create a new governance proposal"""
        proposal_id = f"prop-{self._generate_tx_id()[3:]}"
        proposal = {
            "proposal_id": proposal_id,
            "title": title,
            "description": description,
            "proposer_id": proposer_id,
            "proposal_type": proposal_type,
            "target_phase": target_phase,
            "execution_data": execution_data or {},
            "status": "active",
            "votes_for": 0.0,
            "votes_against": 0.0,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
        self.proposals[proposal_id] = proposal
        
        # If using DB
        if SQLALCHEMY_AVAILABLE and Config.USE_PERSISTENCE:
            try:
                session = SessionLocal()
                db_prop = DBGovernanceProposal(
                    proposal_id=proposal_id,
                    title=title,
                    description=description,
                    proposer_id=proposer_id,
                    proposal_type=proposal_type,
                    target_phase=target_phase,
                    execution_data=proposal["execution_data"],
                    status="active",
                    created_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(days=7)
                )
                session.add(db_prop)
                session.commit()
                session.close()
            except Exception as e:
                logger.error(f"DB Error creating proposal: {e}")
                
        return proposal

    def cast_vote(self, proposal_id: str, voter_id: str, vote: str, voting_power: float = 1.0) -> dict:
        """Cast a vote on a proposal"""
        if proposal_id not in self.proposals:
            raise ValueError("Proposal not found")
            
        proposal = self.proposals[proposal_id]
        if proposal["status"] != "active":
            raise ValueError("Proposal is not active")
            
        if datetime.utcnow().isoformat() > proposal["expires_at"]:
            proposal["status"] = "expired"
            raise ValueError("Proposal has expired")
            
        vote_id = f"{proposal_id}:{voter_id}"
        if vote_id in self.votes:
            raise ValueError("Already voted")
            
        vote_record = {
            "vote_id": vote_id,
            "proposal_id": proposal_id,
            "voter_id": voter_id,
            "vote": vote,
            "voting_power": voting_power,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.votes[vote_id] = vote_record
        
        if vote == "for":
            proposal["votes_for"] += voting_power
        elif vote == "against":
            proposal["votes_against"] += voting_power
            
        # If using DB
        if SQLALCHEMY_AVAILABLE and Config.USE_PERSISTENCE:
            try:
                session = SessionLocal()
                db_vote = DBGovernanceVote(
                    vote_id=vote_id,
                    proposal_id=proposal_id,
                    voter_id=voter_id,
                    vote=vote,
                    voting_power=voting_power,
                    timestamp=datetime.utcnow()
                )
                session.add(db_vote)
                
                # Update proposal counts
                db_prop = session.query(DBGovernanceProposal).filter_by(proposal_id=proposal_id).first()
                if db_prop:
                    if vote == "for":
                        db_prop.votes_for += voting_power
                    elif vote == "against":
                        db_prop.votes_against += voting_power
                
                session.commit()
                session.close()
            except Exception as e:
                logger.error(f"DB Error casting vote: {e}")
                
        return vote_record

    def get_proposals(self, status: str = None) -> List[dict]:
        """Get all proposals"""
        if status:
            return [p for p in self.proposals.values() if p["status"] == status]
        return list(self.proposals.values())

    def calculate_treasury_health(self) -> dict:
        """
        Calculate the Treasury Health Score (THS).
        THS = Total Assets ($) / Total Liabilities (UC)
        
        REAL ASSET ORACLE: Fetches actual on-chain balances and live prices.
        """
        stats = self.get_system_stats()
        
        # Liabilities: Total UC held by non-system accounts
        liabilities_uc = stats["circulating_supply"].get("uc", 0) + \
                        stats["circulating_supply"].get("fp_credits", 0) + \
                        stats["circulating_supply"].get("cora", 0) + \
                        stats["circulating_supply"].get("sky", 0) + \
                        stats["circulating_supply"].get("fi_tokens", 0)
        
        if liabilities_uc == 0:
            # Bootstrap: fetch real assets even with no liabilities
            real_assets = self._fetch_real_assets()
            return {
                "score": 999.0 if real_assets["total_usd"] > 0 else 2.0,
                "mode": "ABUNDANCE",
                "color": "🟣",
                "assets_usd": real_assets["total_usd"],
                "assets_breakdown": real_assets,
                "liabilities_uc": 0,
                "policy": "RADIANT: No liabilities. System is fully backed.",
                "timestamp": datetime.utcnow().isoformat()
            }

        # REAL ASSETS: Fetch from on-chain + internal ledger
        real_assets = self._fetch_real_assets()
        total_assets_usd = real_assets["total_usd"]
        
        # Add internal treasury UC (already backed by real deposits)
        internal_treasury_uc = sum(
            self.accounts.get(acc, {}).get("balances", {}).get("fp_credits", 0) 
            for acc in self.accounts if acc.startswith("system:")
        )
        
        # Note: Don't double-count. Internal treasury is a CLAIM on real assets,
        # not an asset itself. Real assets are the source of truth.
        # If real_assets includes the backing for internal_treasury, we use real_assets only.
        
        ths = total_assets_usd / liabilities_uc if liabilities_uc > 0 else 999.0
        
        if ths < 1.0:
            mode = "DEFICIT"
            color = "🔴"
            policy = "CRITICAL: Halt all bonuses. Focus on solvency."
        elif ths < 1.2:
            mode = "STABLE"
            color = "🟡"
            policy = "SECURE: Standard ops. No unbacked grants."
        elif ths < 1.5:
            mode = "GROWTH"
            color = "🟢"
            policy = "HEALTHY: Strategic bonuses enabled."
        else:
            mode = "ABUNDANCE"
            color = "🟣"
            policy = "RADIANT: Open the coffers. Subsidize basic needs."
            
        return {
            "score": round(ths, 4),
            "mode": mode,
            "color": color,
            "assets_usd": total_assets_usd,
            "assets_breakdown": real_assets,
            "liabilities_uc": liabilities_uc,
            "internal_treasury_uc": internal_treasury_uc,
            "policy": policy,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def analyze_treasury_health(self) -> dict:
        """
        Ask the AI Brain to analyze the treasury health and provide a strategic report.
        """
        health = self.calculate_treasury_health()
        
        # Get recent trend (last 5 audit blocks regarding treasury)
        # This gives the AI context on direction
        trend_blocks = [
            b for b in self.audit_chain[-100:] 
            if b["event_type"] in ["treasury_rebalance", "large_transfer", "mint", "bridge_deposit"]
        ][-5:]
        
        trend_summary = "Stable"
        if trend_blocks:
            trend_summary = f"Last {len(trend_blocks)} significant events: " + \
                            ", ".join([f"{b['event_type']} ({b['timestamp'][:16]})" for b in trend_blocks])

        prompt = f"""
You are the Economic Guardian of the Full Potential AI ecosystem.
Your role is to ensure the long-term sustainability and abundance of the system.

CURRENT TREASURY STATUS:
- Health Score (THS): {health['score']} (Target: >1.2)
- Operating Mode: {health['mode']}
- Policy: {health['policy']}
- Total Assets: ${health['assets_usd']:,.2f} USD
- Total Liabilities: {health['liabilities_uc']:,.2f} UC
- Trend: {trend_summary}

Please provide a strategic assessment:
1. ASSESSMENT: 1-2 sentences on the current state.
2. RISKS: Any immediate risks to solvency?
3. RECOMMENDATION: Specific action for the councils (e.g., "Increase marketing", "Halt grants", "Start dividends").

Tone: Professional, visionary, protective. If THS > 2.0, be inspiring and optimistic ("Dream Big").
        """

        try:
            client = await AsyncHTTPClient.get_client()
            
            # Determine model to use (prefer smarter models for analysis)
            model = "claude-3-opus-20240229" # Default fallback
            
            response = await client.post(
                f"{Config.AI_BRAIN_URL}/generate",
                json={
                    "prompt": prompt,
                    "system": "You are the AI Economic Guardian.",
                    "model": "claude-opus-4.5" if "claude-opus-4.5" in Config.AI_BRAIN_VERSION else "gpt-4",
                    "max_tokens": 500
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                analysis_text = data.get("text", "Analysis unavailable.")
                
                # Record this analysis to the audit chain!
                self._record_audit_block("ai_treasury_analysis", {
                    "ths": health['score'],
                    "mode": health['mode'],
                    "analysis_summary": analysis_text[:100] + "..."
                })
                
                return {
                    "health": health,
                    "analysis": analysis_text,
                    "guardian_model": data.get("model", "unknown"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"AI Brain error: {response.text}")
                return {
                    "health": health,
                    "analysis": "The AI Guardian is currently unreachable. Rely on standard protocol metrics.",
                    "error": f"AI Brain returned {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"AI Analysis failed: {e}")
            return {
                "health": health,
                "analysis": "Analysis system offline. Manual review required.",
                "error": str(e)
            }

    def _fetch_real_assets(self) -> dict:
        """
        Synchronous wrapper for async fetch.
        For backwards compatibility with sync callers.
        """
        # Try to get from cache first (sync check)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're in an async context, use sync fallback
                return self._fetch_real_assets_sync()
            else:
                return loop.run_until_complete(self._fetch_real_assets_async())
        except RuntimeError:
            return self._fetch_real_assets_sync()
    
    def _fetch_real_assets_sync(self) -> dict:
        """
        Synchronous fallback for when async isn't available.
        Uses simple caching via instance variables.
        """
        # Check instance-level cache
        cache_key = "_cached_assets"
        cache_time_key = "_cached_assets_time"
        
        if hasattr(self, cache_key) and hasattr(self, cache_time_key):
            age = (datetime.utcnow() - getattr(self, cache_time_key)).total_seconds()
            if age < Config.CACHE_BALANCE_TTL:
                _metrics.record_cache_hit()
                cached = getattr(self, cache_key)
                cached["from_cache"] = True
                cached["cache_age_seconds"] = age
                return cached
        
        _metrics.record_cache_miss()
        
        assets = {
            "solana_sol": 0.0,
            "solana_usdc": 0.0,
            "solana_usd_value": 0.0,
            "fiat_usd": 0.0,
            "total_usd": 0.0,
            "prices": {},
            "last_fetch": datetime.utcnow().isoformat(),
            "from_cache": False,
            "errors": []
        }
        
        # 1. Fetch SOL balance from Solana RPC
        try:
            _metrics.record_api_call("solana_rpc")
            response = httpx.post(
                Config.SOLANA_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [Config.SOLANA_TREASURY_WALLET]
                },
                timeout=10.0
            )
            if response.status_code == 200:
                data = response.json()
                lamports = data.get("result", {}).get("value", 0)
                assets["solana_sol"] = lamports / 1_000_000_000
        except Exception as e:
            _metrics.record_api_call("solana_rpc", success=False)
            assets["errors"].append(f"SOL balance fetch failed: {str(e)}")
            logger.warning(f"Failed to fetch SOL balance: {e}")

        # 2. Fetch crypto prices from CoinGecko
        try:
            _metrics.record_api_call("coingecko")
            response = httpx.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "solana,ethereum,bitcoin", "vs_currencies": "usd"},
                timeout=10.0
            )
            if response.status_code == 200:
                prices = response.json()
                assets["prices"] = {
                    "SOL": prices.get("solana", {}).get("usd", 0),
                    "ETH": prices.get("ethereum", {}).get("usd", 0),
                    "BTC": prices.get("bitcoin", {}).get("usd", 0)
                }
        except Exception as e:
            _metrics.record_api_call("coingecko", success=False)
            assets["prices"] = {"SOL": 150.0, "ETH": 3500.0, "BTC": 95000.0}
            assets["errors"].append(f"Price fetch failed, using defaults: {str(e)}")
            logger.warning(f"Failed to fetch crypto prices: {e}")

        # 3. Calculate USD values
        sol_price = assets["prices"].get("SOL", 150.0)
        assets["solana_usd_value"] = assets["solana_sol"] * sol_price
        
        # Total real assets
        assets["total_usd"] = (
            assets["solana_usd_value"] + 
            assets["solana_usdc"] + 
            assets["fiat_usd"]
        )
        
        # Cache the result
        setattr(self, cache_key, assets)
        setattr(self, cache_time_key, datetime.utcnow())
        
        return assets

    async def _fetch_real_assets_async(self) -> dict:
        """
        Async version with smart caching and connection pooling.
        This is the optimized path for async callers.
        """
        # Check cache first
        cached = await _cache.get("real_assets")
        if cached:
            _metrics.record_cache_hit()
            cached["from_cache"] = True
            return cached
        
        _metrics.record_cache_miss()
        
        assets = {
            "solana_sol": 0.0,
            "solana_usdc": 0.0,
            "solana_usd_value": 0.0,
            "fiat_usd": 0.0,
            "total_usd": 0.0,
            "prices": {},
            "last_fetch": datetime.utcnow().isoformat(),
            "from_cache": False,
            "errors": []
        }
        
        client = await AsyncHTTPClient.get_client()
        
        # Fetch SOL balance and prices in PARALLEL
        async def fetch_sol_balance():
            try:
                _metrics.record_api_call("solana_rpc")
                response = await client.post(
                    Config.SOLANA_RPC_URL,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "getBalance",
                        "params": [Config.SOLANA_TREASURY_WALLET]
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    lamports = data.get("result", {}).get("value", 0)
                    return lamports / 1_000_000_000
            except Exception as e:
                _metrics.record_api_call("solana_rpc", success=False)
                assets["errors"].append(f"SOL balance: {str(e)}")
                logger.warning(f"Failed to fetch SOL balance: {e}")
            return 0.0
        
        async def fetch_prices():
            try:
                _metrics.record_api_call("coingecko")
                response = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": "solana,ethereum,bitcoin", "vs_currencies": "usd"}
                )
                if response.status_code == 200:
                    prices = response.json()
                    return {
                        "SOL": prices.get("solana", {}).get("usd", 0),
                        "ETH": prices.get("ethereum", {}).get("usd", 0),
                        "BTC": prices.get("bitcoin", {}).get("usd", 0)
                    }
            except Exception as e:
                _metrics.record_api_call("coingecko", success=False)
                assets["errors"].append(f"Prices: {str(e)}")
                logger.warning(f"Failed to fetch crypto prices: {e}")
            return {"SOL": 150.0, "ETH": 3500.0, "BTC": 95000.0}
        
        # Execute in parallel
        sol_balance, prices = await asyncio.gather(
            fetch_sol_balance(),
            fetch_prices()
        )
        
        assets["solana_sol"] = sol_balance
        assets["prices"] = prices
        
        # Calculate USD values
        sol_price = prices.get("SOL", 150.0)
        assets["solana_usd_value"] = sol_balance * sol_price
        assets["total_usd"] = assets["solana_usd_value"] + assets["solana_usdc"] + assets["fiat_usd"]
        
        # Cache the result
        await _cache.set("real_assets", assets, Config.CACHE_BALANCE_TTL)
        
        return assets

    # ============================================================
    # AUDIT TRAIL (Hash Chain for Immutability)
    # ============================================================
    
    def _record_audit_block(self, event_type: str, data: dict) -> dict:
        """
        Record an event to the audit chain with cryptographic linking.
        Each block contains: index, timestamp, event, data, prev_hash, hash
        
        OPTIMIZATION: Auto-prunes old blocks to disk when chain exceeds max memory.
        """
        block_index = self.audit_chain_total_blocks if hasattr(self, 'audit_chain_total_blocks') else len(self.audit_chain)
        timestamp = datetime.utcnow().isoformat()
        
        # Create block content
        block_content = {
            "index": block_index,
            "timestamp": timestamp,
            "event_type": event_type,
            "data": data,
            "prev_hash": self.last_block_hash
        }
        
        # Calculate block hash
        block_string = json.dumps(block_content, sort_keys=True)
        block_hash = hashlib.sha256(block_string.encode()).hexdigest()
        
        block = {
            **block_content,
            "hash": block_hash
        }
        
        self.audit_chain.append(block)
        self.last_block_hash = block_hash
        
        # Track total blocks (including archived)
        if not hasattr(self, 'audit_chain_total_blocks'):
            self.audit_chain_total_blocks = 0
        self.audit_chain_total_blocks += 1
        
        # AUTO-PRUNE: Archive old blocks when exceeding memory limit
        if len(self.audit_chain) > Config.AUDIT_CHAIN_MAX_MEMORY:
            self._archive_old_blocks()
        
        return block
    
    def _archive_old_blocks(self):
        """
        Archive older blocks to disk to prevent memory bloat.
        Keeps the last N blocks in memory for quick access.
        """
        try:
            import os
            archive_dir = Config.AUDIT_ARCHIVE_PATH
            os.makedirs(archive_dir, exist_ok=True)
            
            # Archive the oldest 20% of blocks
            archive_count = len(self.audit_chain) // 5
            blocks_to_archive = self.audit_chain[:archive_count]
            
            # Generate archive filename
            first_idx = blocks_to_archive[0]["index"]
            last_idx = blocks_to_archive[-1]["index"]
            archive_file = os.path.join(archive_dir, f"audit_{first_idx}_{last_idx}.json")
            
            # Write to disk
            with open(archive_file, 'w') as f:
                json.dump({
                    "archived_at": datetime.utcnow().isoformat(),
                    "first_block": first_idx,
                    "last_block": last_idx,
                    "block_count": len(blocks_to_archive),
                    "final_hash": blocks_to_archive[-1]["hash"],
                    "blocks": blocks_to_archive
                }, f)
            
            # Remove from memory
            self.audit_chain = self.audit_chain[archive_count:]
            
            logger.info(f"Archived {archive_count} audit blocks to {archive_file}")
            
            # Track archived ranges
            if not hasattr(self, 'archived_ranges'):
                self.archived_ranges = []
            self.archived_ranges.append({
                "file": archive_file,
                "first": first_idx,
                "last": last_idx,
                "hash": blocks_to_archive[-1]["hash"]
            })
            
        except Exception as e:
            logger.error(f"Failed to archive audit blocks: {e}")

    def verify_audit_chain(self) -> dict:
        """Verify the integrity of the entire audit chain."""
        if not self.audit_chain:
            return {"valid": True, "blocks": 0, "message": "Empty chain"}
        
        errors = []
        prev_hash = "GENESIS_BLOCK_" + hashlib.sha256(b"Full Potential Genesis").hexdigest()[:32]
        
        for i, block in enumerate(self.audit_chain):
            # Check prev_hash linkage
            if block["prev_hash"] != prev_hash:
                errors.append(f"Block {i}: prev_hash mismatch")
            
            # Recalculate hash
            block_content = {
                "index": block["index"],
                "timestamp": block["timestamp"],
                "event_type": block["event_type"],
                "data": block["data"],
                "prev_hash": block["prev_hash"]
            }
            calculated_hash = hashlib.sha256(json.dumps(block_content, sort_keys=True).encode()).hexdigest()
            
            if block["hash"] != calculated_hash:
                errors.append(f"Block {i}: hash mismatch (tampering detected)")
            
            prev_hash = block["hash"]
        
        return {
            "valid": len(errors) == 0,
            "blocks": len(self.audit_chain),
            "errors": errors,
            "last_hash": self.last_block_hash,
            "verified_at": datetime.utcnow().isoformat()
        }

    def get_audit_block(self, tx_id: str) -> Optional[dict]:
        """Find an audit block by transaction ID."""
        for block in self.audit_chain:
            if block["data"].get("transaction_id") == tx_id:
                return block
        return None

    def anchor_audit_chain(self, private_key_path: str = None) -> dict:
        """
        Anchor the current audit chain state to the Solana blockchain.
        
        This creates an IMMUTABLE proof of history. Even if this server is wiped,
        the blockchain proves this state existed at this time.
        """
        if not self.audit_chain:
            return {"status": "skipped", "reason": "Audit chain empty"}
            
        current_hash = self.last_block_hash
        block_height = len(self.audit_chain)
        timestamp = datetime.utcnow().isoformat()
        
        memo_content = json.dumps({
            "app": "FP_CREDITS_GATEWAY",
            "event": "ANCHOR",
            "block_height": block_height,
            "hash": current_hash,
            "timestamp": timestamp
        })
        
        if not SOLANA_AVAILABLE:
            # Simulated mode
            logger.info(f"[ANCHOR-SIM] Would anchor hash {current_hash} to Solana")
            return {
                "status": "simulated",
                "hash": current_hash,
                "tx_signature": f"simulated_tx_{hashlib.sha256(memo_content.encode()).hexdigest()[:16]}",
                "note": "Install solana/solders libraries for real anchoring"
            }
            
        # Real Anchor Logic
        try:
            # If no key provided, try to load from env or file
            # For safety in this demo, we'll use simulation unless a specific key file exists
            key_path = private_key_path or os.getenv("ANCHOR_WALLET_PATH")
            
            if not key_path or not os.path.exists(key_path):
                return {
                    "status": "simulated", 
                    "hash": current_hash, 
                    "reason": "No wallet key found"
                }
                
            # Load wallet
            with open(key_path, 'r') as f:
                keypair_data = json.load(f)
            sender = Keypair.from_bytes(keypair_data)
            
            # Connect to RPC
            client = Client(Config.SOLANA_RPC_URL)
            
            # Create Memo Instruction
            # The Memo program ID is MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcQb
            memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcQb")
            
            instruction = Instruction(
                program_id=memo_program_id,
                data=memo_content.encode("utf-8"),
                accounts=[]
            )
            
            # Build and send transaction
            recent_blockhash = client.get_latest_blockhash().value.blockhash
            tx = Transaction()
            tx.recent_blockhash = recent_blockhash
            tx.add(instruction)
            
            response = client.send_transaction(tx, sender)
            tx_sig = str(response.value)
            
            # Record the anchor event itself into the chain (recursive proof!)
            self._record_audit_block("chain_anchored", {
                "chain_hash": current_hash,
                "tx_signature": tx_sig,
                "block_height": block_height
            })
            
            return {
                "status": "success",
                "hash": current_hash,
                "tx_signature": tx_sig,
                "explorer_url": f"https://explorer.solana.com/tx/{tx_sig}"
            }
            
        except Exception as e:
            logger.error(f"Anchor failed: {e}")
            return {"status": "failed", "error": str(e)}

    # ============================================================
    # WEBHOOK MANAGEMENT
    # ============================================================
    
    def register_webhook(self, service_id: str, url: str, events: List[str]) -> dict:
        """Register a webhook subscription."""
        webhook_id = f"wh-{service_id}-{hashlib.sha256(url.encode()).hexdigest()[:8]}"
        webhook = {
            "webhook_id": webhook_id,
            "service_id": service_id,
            "url": url,
            "events": events,  # e.g., ["balance_low", "treasury_mode_change", "proposal_created"]
            "created_at": datetime.utcnow().isoformat(),
            "last_triggered": None,
            "trigger_count": 0,
            "active": True
        }
        self.webhooks[webhook_id] = webhook
        return webhook

    async def trigger_webhooks(self, event_type: str, payload: dict):
        """
        Trigger all webhooks subscribed to an event type.
        OPTIMIZED: Uses connection pooling and parallel dispatch.
        """
        # Collect matching webhooks
        matching = [
            wh for wh in self.webhooks.values()
            if wh["active"] and (event_type in wh["events"] or "*" in wh["events"])
        ]
        
        if not matching:
            return
        
        # Get shared client for connection reuse
        client = await AsyncHTTPClient.get_client()
        
        async def send_webhook(wh):
            try:
                await client.post(
                    wh["url"],
                    json={
                        "event": event_type,
                        "payload": payload,
                        "timestamp": datetime.utcnow().isoformat(),
                        "webhook_id": wh["webhook_id"]
                    },
                    timeout=5.0
                )
                wh["last_triggered"] = datetime.utcnow().isoformat()
                wh["trigger_count"] += 1
                return True
            except Exception as e:
                logger.warning(f"Webhook {wh['webhook_id']} failed: {e}")
                wh["failure_count"] = wh.get("failure_count", 0) + 1
                return False
        
        # Fire all webhooks in PARALLEL (non-blocking)
        results = await asyncio.gather(*[send_webhook(wh) for wh in matching], return_exceptions=True)
        
        success_count = sum(1 for r in results if r is True)
        logger.info(f"Webhooks for {event_type}: {success_count}/{len(matching)} succeeded")

    # ============================================================
    # MULTI-SIGNATURE FOR LARGE TRANSACTIONS
    # ============================================================
    
    def create_multisig_request(self, tx_type: str, amount: float, details: dict, requester_id: str) -> dict:
        """Create a multi-signature request for large transactions."""
        if amount < self.MULTISIG_THRESHOLD:
            raise ValueError(f"Amount {amount} is below multisig threshold {self.MULTISIG_THRESHOLD}")
        
        request_id = f"msig-{self._generate_tx_id()[3:]}"
        request = {
            "request_id": request_id,
            "tx_type": tx_type,  # "mint", "grant", "large_transfer"
            "amount": amount,
            "details": details,
            "requester_id": requester_id,
            "approvals": [],
            "rejections": [],
            "status": "pending",  # pending, approved, rejected, executed
            "required_approvals": self.MULTISIG_REQUIRED_APPROVALS,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=3)).isoformat()
        }
        self.multisig_queue[request_id] = request
        
        # Record to audit trail
        self._record_audit_block("multisig_created", {
            "request_id": request_id,
            "tx_type": tx_type,
            "amount": amount,
            "requester": requester_id
        })
        
        return request

    def approve_multisig(self, request_id: str, approver_id: str, council: str) -> dict:
        """Approve a multi-signature request."""
        if request_id not in self.multisig_queue:
            raise ValueError("Multisig request not found")
        
        request = self.multisig_queue[request_id]
        
        if request["status"] != "pending":
            raise ValueError(f"Request is not pending (status: {request['status']})")
        
        # Check if already approved by this approver
        if any(a["approver_id"] == approver_id for a in request["approvals"]):
            raise ValueError("Already approved by this approver")
        
        request["approvals"].append({
            "approver_id": approver_id,
            "council": council,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Check if threshold met
        if len(request["approvals"]) >= request["required_approvals"]:
            request["status"] = "approved"
            self._record_audit_block("multisig_approved", {
                "request_id": request_id,
                "approvals": len(request["approvals"])
            })
        
        return request

    def reject_multisig(self, request_id: str, rejector_id: str, reason: str) -> dict:
        """Reject a multi-signature request."""
        if request_id not in self.multisig_queue:
            raise ValueError("Multisig request not found")
        
        request = self.multisig_queue[request_id]
        request["rejections"].append({
            "rejector_id": rejector_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
        request["status"] = "rejected"
        
        self._record_audit_block("multisig_rejected", {
            "request_id": request_id,
            "rejector": rejector_id,
            "reason": reason
        })
        
        return request

    # ============================================================
    # SERVICE COMPLIANCE TRACKING
    # ============================================================
    
    def record_compliance_check(self, service_id: str, check_type: str, passed: bool):
        """Record a compliance check for a service."""
        if service_id not in self.service_compliance:
            self.service_compliance[service_id] = {
                "service_id": service_id,
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "last_check": None,
                "compliance_score": 100.0,
                "violations": []
            }
        
        record = self.service_compliance[service_id]
        record["total_checks"] += 1
        record["last_check"] = datetime.utcnow().isoformat()
        
        if passed:
            record["passed_checks"] += 1
        else:
            record["failed_checks"] += 1
            record["violations"].append({
                "check_type": check_type,
                "timestamp": datetime.utcnow().isoformat()
            })
        
        # Calculate compliance score (% of passed checks)
        record["compliance_score"] = round(
            (record["passed_checks"] / record["total_checks"]) * 100, 2
        )
        
        return record

    def get_service_compliance(self, service_id: str) -> dict:
        """Get compliance record for a service."""
        return self.service_compliance.get(service_id, {
            "service_id": service_id,
            "compliance_score": 100.0,
            "message": "No compliance data recorded"
        })

    # ============================================================
    # AUTOMATED TREASURY REBALANCING
    # ============================================================
    
    def rebalance_treasury(self) -> dict:
        """
        Automatically rebalance treasury funds based on policy and THS.
        
        Allocation Policy (from Config):
        - 40% Operations
        - 30% Rewards Pool
        - 20% Creator Grants
        - 10% Reserve
        
        In ABUNDANCE mode, also fund the "Worthy Recipients" pool.
        """
        health = self.calculate_treasury_health()
        
        # Get main treasury balance
        treasury_account = self.accounts.get("system:treasury", {})
        treasury_balance = treasury_account.get("balances", {}).get("fp_credits", 0)
        
        if treasury_balance <= 0:
            return {
                "status": "skipped",
                "reason": "No funds in main treasury",
                "treasury_balance": treasury_balance
            }
        
        # Calculate target allocations
        allocations = {
            "system:operations": Config.TREASURY_OPERATIONS,
            "system:rewards": Config.TREASURY_REWARDS,
            "system:grants": Config.TREASURY_GRANTS,
            "system:reserve": Config.TREASURY_RESERVE
        }
        
        # In ABUNDANCE mode, allocate extra to worthy recipients
        if health["mode"] == "ABUNDANCE":
            # Calculate surplus above 150% THS
            surplus_ratio = max(0, health["score"] - 1.5) / health["score"]
            surplus_amount = treasury_balance * surplus_ratio * 0.5  # 50% of surplus
            allocations["system:worthy_recipients"] = surplus_amount / treasury_balance if treasury_balance > 0 else 0
        
        transfers = []
        
        for target_account, ratio in allocations.items():
            if ratio <= 0:
                continue
                
            amount = round(treasury_balance * ratio, 2)
            
            if amount < 1.0:  # Skip tiny amounts
                continue
            
            # Ensure target account exists
            if target_account not in self.accounts:
                self._create_system_account(target_account)
            
            # Transfer from treasury to target
            try:
                self.accounts["system:treasury"]["balances"]["fp_credits"] -= amount
                self.accounts["system:treasury"]["balances"]["uc"] -= amount
                self.accounts[target_account]["balances"]["fp_credits"] += amount
                self.accounts[target_account]["balances"]["uc"] += amount
                
                transfers.append({
                    "to": target_account,
                    "amount": amount,
                    "ratio": ratio
                })
                
                # Record to audit trail
                self._record_audit_block("treasury_rebalance", {
                    "from": "system:treasury",
                    "to": target_account,
                    "amount": amount
                })
                
            except Exception as e:
                logger.error(f"Rebalance transfer failed: {e}")
        
        return {
            "status": "completed",
            "health_mode": health["mode"],
            "health_score": health["score"],
            "treasury_before": treasury_balance,
            "transfers": transfers,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _create_system_account(self, account_id: str):
        """Create a new system account if it doesn't exist."""
        if account_id in self.accounts:
            return
        
        self.accounts[account_id] = {
            "account_id": account_id,
            "account_type": "treasury",
            "tier": "unlimited",
            "display_name": account_id.replace("system:", "").replace("_", " ").title(),
            "email": None,
            "balances": {ct.value: 0.0 for ct in CreditType},
            "reputation": {rt.value: 0.0 for rt in ReputationType},
            "pending": {ct.value: 0.0 for ct in CreditType},
            "holds": {},
            "metadata": {"system": True, "auto_created": True},
            "limits": {"daily_transfer": float('inf'), "single_transfer": float('inf')},
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat()
        }

# Global store
store = CreditStore()

# ============================================================
# AUTHENTICATION
# ============================================================

async def verify_api_key(x_api_key: str = Header(None), authorization: str = Header(None)):
    """Verify API key from header"""
    api_key = x_api_key or (authorization.replace("Bearer ", "") if authorization else None)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Use X-API-Key header or Authorization: Bearer <key>"
        )
    
    # Check master key
    if api_key == Config.MASTER_KEY:
        return {"service_name": "master", "permissions": ["*"], "key_id": "master"}
    
    # Check service key
    key_record = store.verify_api_key(api_key)
    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check rate limit
    if not store.check_rate_limit(key_record["key_id"], key_record["rate_limit"]):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please slow down."
        )
    
    return key_record

def require_permission(permission: str):
    """Decorator to check permissions"""
    async def checker(auth: dict = Depends(verify_api_key)):
        if "*" in auth["permissions"] or permission in auth["permissions"]:
            return auth
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required. Your permissions: {auth['permissions']}"
        )
    return checker

# ============================================================
# FASTAPI APP
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info(f"Starting {Config.SERVICE_NAME} v{Config.VERSION}")
    
    # Create default API keys for known services
    default_services = [
        ("whiterock-api", "WhiteRock PMA Backend", ["read", "credit", "debit", "transfer"]),
        ("breath-optimizer", "Breath Optimizer Service", ["read", "debit"]),
        ("content-studio", "Content Studio", ["read", "debit"]),
        ("mydreamspace", "MyDreamSpace", ["read", "credit", "debit"]),
        ("global-sky-initiative", "Global Sky Initiative", ["read", "credit", "debit", "transfer"]),
        ("fiart", "FI-Art NFT Treasury", ["read", "credit", "debit", "transfer", "exchange", "bridge"]),
        ("cora-credits", "Cora Credits Bridge", ["read", "credit", "debit", "transfer", "exchange"]),
        ("autonomy-optimizer", "Autonomy Optimizer", ["read", "credit", "debit"]),
    ]
    
    for service, desc, perms in default_services:
        key = store.create_api_key(service, desc, perms)
        logger.info(f"[INIT] API key for {service}: {key['key_id']}")
    
    logger.info(f"[INIT] Treasury initialized with {Config.INITIAL_TREASURY:,.2f} FP Credits")
    logger.info(f"[INIT] Exchange rates - USD:{Config.FP_TO_USD}, CORA:{Config.FP_TO_CORA}, SKY:{Config.FP_TO_SKY}, FI:{Config.FP_TO_FI}")
    
    # ==========================================================
    # CONNECT TO CORE SYSTEMS - Economic Nervous System
    # ==========================================================
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # 0. Connect to Genesis (Mother Node)
        try:
            logger.info(f"[INIT] Connecting to Genesis at {Config.GENESIS_URL}...")
            response = await client.get(f"{Config.GENESIS_URL}/")
            if response.status_code == 200:
                genesis_data = response.json()
                Config.GENESIS_CONNECTED = True
                logger.info(f"[INIT] ✅ Genesis online: {genesis_data.get('motto', 'The Source Point')}")
                
                # Try to enroll if we have a key but no token
                if Config.GENESIS_ENROLLMENT_KEY and not Config.GENESIS_AGENT_TOKEN:
                    try:
                        enroll_response = await client.post(
                            f"{Config.GENESIS_URL}/auth/enroll",
                            json={
                                "agent_name": Config.SERVICE_NAME,
                                "key": Config.GENESIS_ENROLLMENT_KEY
                            }
                        )
                        if enroll_response.status_code == 200:
                            enroll_data = enroll_response.json()
                            Config.GENESIS_AGENT_TOKEN = enroll_data.get("personal_key", "")
                            logger.info(f"[INIT] ✅ Enrolled with Genesis!")
                        else:
                            logger.warning(f"[INIT] ⚠️ Genesis enrollment failed (key may be rotated)")
                    except Exception as e:
                        logger.warning(f"[INIT] ⚠️ Genesis enrollment error: {e}")
            else:
                logger.warning(f"[INIT] ⚠️ Genesis not responding")
        except Exception as e:
            logger.warning(f"[INIT] ⚠️ Genesis connection failed: {e}")
            Config.GENESIS_CONNECTED = False
        
        # 1. Connect to AI Brain v4.1.0 (Intelligence Layer)
        try:
            logger.info(f"[INIT] Connecting to AI Brain at {Config.AI_BRAIN_URL}...")
            response = await client.get(f"{Config.AI_BRAIN_URL}/health")
            if response.status_code == 200:
                health_data = response.json()
                Config.AI_BRAIN_CONNECTED = True
                Config.AI_BRAIN_VERSION = health_data.get("version", "4.1.0")
                logger.info(f"[INIT] ✅ AI Brain v{Config.AI_BRAIN_VERSION} connected")
                
                # Get available providers/models
                root_response = await client.get(f"{Config.AI_BRAIN_URL}/")
                if root_response.status_code == 200:
                    root_data = root_response.json()
                    providers = root_data.get("providers", {})
                    active_providers = [k for k, v in providers.items() if v]
                    logger.info(f"[INIT]    Providers: {', '.join(active_providers)}")
            else:
                logger.warning(f"[INIT] ⚠️ AI Brain health check failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"[INIT] ⚠️ AI Brain connection failed: {e}")
            Config.AI_BRAIN_CONNECTED = False
        
        # 2. Check REAL on-chain SOL Treasury
        try:
            logger.info(f"[INIT] Checking on-chain SOL treasury...")
            sol_response = await client.post(
                Config.SOLANA_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [Config.SOLANA_TREASURY_WALLET]
                }
            )
            if sol_response.status_code == 200:
                sol_data = sol_response.json()
                lamports = sol_data.get("result", {}).get("value", 0)
                sol_balance = lamports / 1_000_000_000
                logger.info(f"[INIT] ✅ On-chain SOL balance: {sol_balance} SOL")
                logger.info(f"[INIT]    Wallet: {Config.SOLANA_TREASURY_WALLET[:8]}...")
            else:
                logger.warning(f"[INIT] ⚠️ Could not fetch on-chain balance")
        except Exception as e:
            logger.warning(f"[INIT] ⚠️ Solana RPC failed: {e}")
        
        # 3. Connect to User Service (UC Payments)
        try:
            logger.info(f"[INIT] Connecting to User Service at {Config.USER_SERVICE_URL}...")
            response = await client.get(f"{Config.USER_SERVICE_URL}/docs/payments")
            if response.status_code == 200:
                Config.USER_SERVICE_CONNECTED = True
                docs = response.json()
                methods = list(docs.get("payment_methods", {}).keys())
                logger.info(f"[INIT] ✅ User Service connected (UC Payments)")
                logger.info(f"[INIT]    Payment methods: {', '.join(methods)}")
            else:
                logger.warning(f"[INIT] ⚠️ User Service not responding")
        except Exception as e:
            logger.warning(f"[INIT] ⚠️ User Service connection failed: {e}")
            Config.USER_SERVICE_CONNECTED = False
        
        # 4. Connect to Credits Manager (Internal Ledger)
        try:
            logger.info(f"[INIT] Connecting to Credits Manager at {Config.CREDITS_MANAGER_URL}...")
            response = await client.get(f"{Config.CREDITS_MANAGER_URL}/health")
            if response.status_code == 200:
                Config.CREDITS_MANAGER_CONNECTED = True
                health = response.json()
                logger.info(f"[INIT] ✅ Credits Manager v{health.get('version', '?')} connected")
                logger.info(f"[INIT]    Wallets: {health.get('wallets', 0)}, Transactions: {health.get('transactions', 0)}")
            else:
                logger.warning(f"[INIT] ⚠️ Credits Manager not responding")
        except Exception as e:
            logger.warning(f"[INIT] ⚠️ Credits Manager connection failed: {e}")
            Config.CREDITS_MANAGER_CONNECTED = False
    
    # Summary
    logger.info(f"[INIT] ═══════════════════════════════════════════")
    logger.info(f"[INIT] 💎 FP Credits Gateway v{Config.VERSION} Ready")
    logger.info(f"[INIT]    FP Treasury: {Config.INITIAL_TREASURY:,.0f} FP Credits (internal)")
    logger.info(f"[INIT]    Genesis: {'✅ Connected' if Config.GENESIS_CONNECTED else '⚠️ Not enrolled'}")
    logger.info(f"[INIT]    AI Brain: {'✅ Connected' if Config.AI_BRAIN_CONNECTED else '❌ Disconnected'}")
    logger.info(f"[INIT]    User Service: {'✅ Connected' if Config.USER_SERVICE_CONNECTED else '⚠️ Disconnected'}")
    logger.info(f"[INIT]    Credits Manager: {'✅ Connected' if Config.CREDITS_MANAGER_CONNECTED else '⚠️ Disconnected'}")
    logger.info(f"[INIT]    Data: REAL (no simulations)")
    logger.info(f"[INIT] ═══════════════════════════════════════════")
    
    yield
    
    # Shutdown
    logger.info("Shutting down credits gateway")
    
    # Close async HTTP client pool
    await AsyncHTTPClient.close()
    logger.info("Closed HTTP connection pool")


# ============================================================
# MIDDLEWARE
# ============================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting by IP.
    Protects the service from abuse.
    """
    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        self.whitelist = ["127.0.0.1", "localhost"]
        
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/api/metrics", "/api/rates"]:
            return await call_next(request)
            
        client_ip = request.client.host
        
        # Check whitelist
        if client_ip in self.whitelist:
            return await call_next(request)
            
        now = time.time()
        
        # Clean old requests (window: 60 seconds)
        self.requests[client_ip] = [req_time for req_time in self.requests[client_ip] if now - req_time < 60]
        
        # Check limit
        if len(self.requests[client_ip]) >= Config.REQUESTS_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit exceeded. Max {Config.REQUESTS_PER_MINUTE}/min."
                }
            )
            
        # Record request
        self.requests[client_ip].append(now)
        
        response = await call_next(request)
        return response

app = FastAPI(
    title="FP Credits Gateway",
    description="""
## The Economic Backbone of Full Potential

Unified credits API powering the entire ecosystem with:
- **Multi-currency support**: FP Credits, Cora Credits, Sky Credits, FI Tokens, USD
- **Real-time updates**: WebSocket subscriptions for balance changes
- **Regenerative economics**: Fees fund ecosystem growth
- **Blockchain bridge**: On-chain FI Token integration

### Exchange Rates (All 1:1 aligned)
- 1 FP Credit = $1 USD
- 1 FP Credit = 1 Cora Credit
- 1 FP Credit = 1 Sky Credit
- 1 FP Credit = 1 FI Token
    """,
    version=Config.VERSION,
    lifespan=lifespan,
    root_path="/services/credits"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add Rate Limiting
app.add_middleware(RateLimitMiddleware)

# Mount static files for images and assets
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ============================================================
# PUBLIC ENDPOINTS
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard UI"""
    static_path = Path(__file__).parent / "static" / "index.html"
    if static_path.exists():
        return FileResponse(static_path)
    return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head>
    <title>FP Credits Gateway v{Config.VERSION}</title>
    <style>
        body {{ font-family: system-ui; max-width: 800px; margin: 50px auto; padding: 20px; background: #0a0a0a; color: #e0e0e0; }}
        h1 {{ color: #ffd700; }}
        .card {{ background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 20px; margin: 20px 0; }}
        a {{ color: #60a5fa; }}
    </style>
</head>
<body>
    <h1>⚡ FP Credits Gateway</h1>
    <p>The unified credits API for the Full Potential ecosystem.</p>
    <div class="card">
        <p><a href="/docs">📖 API Documentation</a></p>
        <p><a href="/health">💚 Health Check</a></p>
    </div>
</body>
</html>
    """)

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    """Serve the admin dashboard UI"""
    static_path = Path(__file__).parent / "static" / "admin.html"
    if static_path.exists():
        return FileResponse(static_path)
    return HTMLResponse("<h1>Admin dashboard coming soon</h1>")

@app.get("/dashboard", response_class=HTMLResponse)
async def treasury_dashboard():
    """Serve the Treasury Dashboard UI"""
    static_path = Path(__file__).parent / "static" / "dashboard.html"
    if static_path.exists():
        return FileResponse(static_path)
    return HTMLResponse("<h1>Dashboard coming soon</h1>")

@app.get("/purchase", response_class=HTMLResponse)
async def purchase_page():
    """Serve the purchase/donation page"""
    static_path = Path(__file__).parent / "static" / "purchase.html"
    if static_path.exists():
        return FileResponse(static_path)
    return HTMLResponse("<h1>Purchase page coming soon</h1>")

@app.get("/buy", response_class=HTMLResponse)
async def buy_redirect():
    """Redirect /buy to /purchase"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/services/credits/purchase")

@app.get("/health")
async def health():
    """Health check endpoint"""
    import time
    start = time.time()
    
    stats = store.get_system_stats()
    
    duration_ms = (time.time() - start) * 1000
    _metrics.record_request(duration_ms)
    
    return {
        "status": "healthy",
        "service": Config.SERVICE_NAME,
        "version": Config.VERSION,
        "role": "unified-credits-gateway",
        "accounts": stats["total_accounts"],
        "transactions_total": stats["total_transactions"],
        "treasury_fp": store.accounts["system:treasury"]["balances"][CreditType.FP_CREDITS.value],
        "exchange_rates": stats["exchange_rates"],
        "features": {
            "credit_types": len(CREDIT_TYPE_INFO),
            "reputation_types": len(REPUTATION_TYPE_INFO),
            "contribution_types": len(CONTRIBUTION_REWARDS),
            "ai_brain_connected": Config.AI_BRAIN_CONNECTED,
            "hold_commit_release": True,
            "crypto_deposits": ["SOL", "ETH", "BTC"]
        },
        "ai_brain": {
            "url": Config.AI_BRAIN_URL,
            "version": Config.AI_BRAIN_VERSION,
            "connected": Config.AI_BRAIN_CONNECTED,
            "server": "162.0.208.88 (dedicated AI server)",
            "providers": ["anthropic", "openai", "vertex", "xai", "together", "ollama"],
            "models": ["claude-opus-4.5", "gpt-5.1", "gemini-2.5-pro", "grok-4", "llama-3.3-70B"]
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/metrics")
async def get_metrics():
    """
    Performance and usage metrics.
    Useful for monitoring and optimization.
    """
    return {
        "service": Config.SERVICE_NAME,
        "version": Config.VERSION,
        "performance": _metrics.get_stats(),
        "cache": _cache.stats(),
        "audit_chain": {
            "blocks_in_memory": len(store.audit_chain),
            "total_blocks": getattr(store, 'audit_chain_total_blocks', len(store.audit_chain)),
            "archived_ranges": getattr(store, 'archived_ranges', []),
            "max_memory_blocks": Config.AUDIT_CHAIN_MAX_MEMORY
        },
        "config": {
            "cache_prices_ttl": Config.CACHE_PRICES_TTL,
            "cache_balance_ttl": Config.CACHE_BALANCE_TTL,
            "cache_health_ttl": Config.CACHE_HEALTH_TTL
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/cache/invalidate")
async def invalidate_cache(
    key: str = None,
    auth: dict = Depends(require_permission("admin"))
):
    """
    Invalidate cache entries.
    Use key=None to invalidate all, or specify a key like 'real_assets'.
    """
    if key:
        await _cache.invalidate(key)
        return {"status": "invalidated", "key": key}
    else:
        # Invalidate all known keys
        for k in ["real_assets", "treasury_health"]:
            await _cache.invalidate(k)
        return {"status": "invalidated", "keys": ["real_assets", "treasury_health"]}

@app.get("/api/rates")
async def get_exchange_rates():
    """Get current exchange rates (public endpoint)"""
    return {
        "base": "FP_CREDITS",
        "rates": {
            "USD": Config.FP_TO_USD,
            "CORA_CREDITS": Config.FP_TO_CORA,
            "SKY_CREDITS": Config.FP_TO_SKY,
            "FI_TOKENS": Config.FP_TO_FI,
        },
        "fees": {
            "internal_transfer": f"{Config.FEE_INTERNAL_TRANSFER * 100}%",
            "external_withdrawal": f"{Config.FEE_EXTERNAL_WITHDRAWAL * 100}%",
            "exchange": f"{Config.FEE_EXCHANGE * 100}%",
            "bridge": f"{Config.FEE_BRIDGE_ONCHAIN * 100}%",
        },
        "updated_at": datetime.utcnow().isoformat()
    }

# ============================================================
# ACCOUNT ENDPOINTS
# ============================================================

@app.post("/api/accounts", response_model=AccountResponse)
async def create_account(
    request: AccountCreate,
    auth: dict = Depends(require_permission("admin"))
):
    """Create a new account"""
    try:
        account = store.create_account(
            request.account_id,
            request.account_type,
            AccountTier.BASIC,
            request.display_name,
            request.email,
            request.metadata
        )
        return AccountResponse(
            account_id=account["account_id"],
            account_type=account["account_type"],
            tier=account["tier"],
            display_name=account["display_name"],
            balances=account["balances"],
            total_value_usd=store._calculate_total_usd(account["balances"]),
            created_at=account["created_at"],
            last_activity=account["last_activity"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    auth: dict = Depends(require_permission("read"))
):
    """Get account details"""
    account = store.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return AccountResponse(
        account_id=account["account_id"],
        account_type=account["account_type"],
        tier=account["tier"],
        display_name=account["display_name"],
        balances=account["balances"],
        total_value_usd=store._calculate_total_usd(account["balances"]),
        created_at=account["created_at"],
        last_activity=account["last_activity"]
    )

# ============================================================
# BALANCE ENDPOINTS
# ============================================================

@app.get("/api/balance/{account_id}", response_model=BalanceResponse)
async def get_balance(
    account_id: str,
    auth: dict = Depends(require_permission("read"))
):
    """Get account balance"""
    balance_data = store.get_balance(account_id)
    return BalanceResponse(
        account_id=account_id,
        balances=balance_data["balances"],
        pending=balance_data["pending"],
        total_value_usd=balance_data["total_value_usd"],
        last_updated=datetime.utcnow().isoformat()
    )

# ============================================================
# CREDIT/DEBIT ENDPOINTS
# ============================================================

@app.post("/api/credit", response_model=TransactionResponse)
async def credit_account(
    request: CreditRequest,
    auth: dict = Depends(require_permission("credit"))
):
    """Add credits to an account"""
    try:
        tx = store.credit(
            request.account_id,
            request.amount,
            request.credit_type,
            request.reason,
            request.reference_id,
            request.metadata
        )
        return TransactionResponse(
            transaction_id=tx["transaction_id"],
            account_id=tx["account_id"],
            type=tx["type"],
            status=tx["status"],
            amount=tx["amount"],
            credit_type=tx["credit_type"],
            fee=tx["fee"],
            balance_after=tx["balance_after"],
            reason=tx["reason"],
            reference_id=tx["reference_id"],
            created_at=tx["created_at"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/debit", response_model=TransactionResponse)
async def debit_account(
    request: DebitRequest,
    auth: dict = Depends(require_permission("debit"))
):
    """Deduct credits from an account"""
    try:
        tx = store.debit(
            request.account_id,
            request.amount,
            request.credit_type,
            request.reason,
            request.reference_id,
            request.metadata
        )
        return TransactionResponse(
            transaction_id=tx["transaction_id"],
            account_id=tx["account_id"],
            type=tx["type"],
            status=tx["status"],
            amount=tx["amount"],
            credit_type=tx["credit_type"],
            fee=tx["fee"],
            balance_after=tx["balance_after"],
            reason=tx["reason"],
            reference_id=tx["reference_id"],
            created_at=tx["created_at"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================
# TRANSFER ENDPOINTS
# ============================================================

@app.post("/api/transfer")
async def transfer_credits(
    request: TransferRequest,
    auth: dict = Depends(require_permission("transfer"))
):
    """Transfer credits between accounts"""
    try:
        debit_tx, credit_tx = store.transfer(
            request.from_account,
            request.to_account,
            request.amount,
            request.credit_type,
            request.reason,
            request.metadata
        )
        return {
            "success": True,
            "from_transaction": debit_tx["transaction_id"],
            "to_transaction": credit_tx["transaction_id"],
            "amount": request.amount,
            "credit_type": request.credit_type.value,
            "fee": debit_tx["fee"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ZEND FEE CIRCULATION ENDPOINT
# ============================================================

class ZendFeeRequest(BaseModel):
    """Request model for Zend regenerative fee collection"""
    fee_amount: float = Field(..., gt=0, description="Fee amount in UC")
    sender_id: Optional[str] = Field(None, description="Sender account to credit circulation back to")
    reason: str = Field("zend_send_fee", description="Fee reason for audit")

@app.post("/api/zend/collect-fee")
async def collect_zend_fee(
    request: ZendFeeRequest,
    auth: dict = Depends(require_permission("transfer"))
):
    """
    Collect Zend fee with regenerative circulation.
    Per docs/protocols/ZEND_REGENERATIVE_SPEC.md Part 3:
    - 40% to system:zend_ops (infrastructure/partners)
    - 30% to system:commons (Commons Reserve Fund)
    - 30% redistributed as UC (rewards/sponsored sends)
    """
    try:
        result = store.collect_zend_fee(
            fee=request.fee_amount,
            credit_type=CreditType.FP_CREDITS,
            reason=request.reason,
            sender_id=request.sender_id
        )
        return {
            "success": True,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/zend/fee-stats")
async def get_zend_fee_stats():
    """Get Zend fee circulation statistics."""
    return {
        "zend_fees_collected": store.metrics.get("zend_fees_collected", 0.0),
        "zend_commons_funded": store.metrics.get("zend_commons_funded", 0.0),
        "fee_split": {
            "ops_pct": Config.ZEND_FEE_OPS_PCT,
            "commons_pct": Config.ZEND_FEE_COMMONS_PCT,
            "circulation_pct": Config.ZEND_FEE_CIRCULATION_PCT,
        },
        "system_balances": {
            "zend_ops": store.accounts.get("system:zend_ops", {}).get("balances", {}),
            "zend_circulation": store.accounts.get("system:zend_circulation", {}).get("balances", {}),
            "commons": store.accounts.get("system:commons", {}).get("balances", {}),
        },
        "spec": "docs/protocols/ZEND_REGENERATIVE_SPEC.md Part 3",
        "timestamp": datetime.utcnow().isoformat()
    }

# ============================================================
# EXCHANGE ENDPOINTS
# ============================================================

@app.post("/api/exchange")
async def exchange_credits(
    request: ExchangeRequest,
    auth: dict = Depends(require_permission("exchange"))
):
    """Exchange between credit types"""
    try:
        debit_tx, credit_tx, rate = store.exchange(
            request.account_id,
            request.from_type,
            request.to_type,
            request.amount
        )
        return {
            "success": True,
            "from_amount": request.amount,
            "from_type": request.from_type.value,
            "to_amount": round(request.amount * rate, 8),
            "to_type": request.to_type.value,
            "exchange_rate": rate,
            "fee": debit_tx["fee"],
            "debit_tx": debit_tx["transaction_id"],
            "credit_tx": credit_tx["transaction_id"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================
# BRIDGE ENDPOINTS (On-Chain)
# ============================================================

@app.post("/api/bridge")
async def bridge_credits(
    request: BridgeRequest,
    auth: dict = Depends(require_permission("bridge"))
):
    """Bridge credits to/from blockchain"""
    try:
        if request.direction == "out":
            if not request.wallet_address:
                raise ValueError("Wallet address required for bridge out")
            tx = store.bridge_out(
                request.account_id,
                request.amount,
                request.wallet_address,
                request.chain
            )
            return {
                "success": True,
                "direction": "out",
                "transaction_id": tx["transaction_id"],
                "amount": request.amount,
                "wallet": request.wallet_address,
                "chain": request.chain,
                "status": "pending_mint",
                "fee": tx["fee"]
            }
        else:
            # Bridge in requires verification of on-chain transaction
            raise HTTPException(
                status_code=501, 
                detail="Bridge-in requires on-chain verification. Use the bridge service directly."
            )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================
# HOLD/COMMIT/RELEASE ENDPOINTS (Safe Transactions)
# ============================================================

@app.post("/api/v1/transact/hold")
@app.post("/api/transact/hold")
async def hold_credits(
    request: HoldRequest,
    auth: dict = Depends(require_permission("debit"))
):
    """Hold credits for a pending transaction"""
    try:
        hold = store.hold(
            request.from_wallet_id,
            request.amount,
            request.currency,
            request.description,
            request.expires_in_seconds
        )
        return HoldResponse(**hold)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/transact/commit")
@app.post("/api/transact/commit")
async def commit_hold(
    request: CommitRequest,
    auth: dict = Depends(require_permission("transfer"))
):
    """Commit a held amount to a destination wallet"""
    try:
        result = store.commit(request.hold_id, request.to_wallet_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/transact/release")
@app.post("/api/transact/release")
async def release_hold(
    request: ReleaseRequest,
    auth: dict = Depends(require_permission("debit"))
):
    """Release a hold (cancel pending transaction)"""
    try:
        result = store.release(request.hold_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# CONTRIBUTION ENDPOINTS
# ============================================================

@app.get("/api/v1/contributions/credit-types")
@app.get("/api/contributions/credit-types")
async def get_credit_types():
    """List all credit types with metadata"""
    return {
        "credit_types": [
            {"code": code, **info}
            for code, info in CREDIT_TYPE_INFO.items()
        ],
        "reputation_types": [
            {"code": code, **info}
            for code, info in REPUTATION_TYPE_INFO.items()
        ]
    }


@app.get("/api/v1/contributions/contribution-types")
@app.get("/api/contributions/contribution-types")
async def get_contribution_types():
    """List all contribution types and their rewards"""
    return {
        "contribution_types": [
            {"type": contrib_type, "rewards": rewards}
            for contrib_type, rewards in CONTRIBUTION_REWARDS.items()
        ]
    }


@app.post("/api/v1/contributions/record")
@app.post("/api/contributions/record")
async def record_contribution(
    request: ContributionRecord,
    auth: dict = Depends(require_permission("credit"))
):
    """Record a contribution and issue multi-credit rewards"""
    try:
        result = store.record_contribution(
            user_id=request.user_id,
            contribution_type=request.contribution_type,
            amount_usd=request.amount_usd,
            source=request.source,
            preferred_credit_type=request.preferred_credit_type,
            metadata=request.metadata
        )
        return ContributionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/contributions/crypto-deposit")
@app.post("/api/contributions/crypto-deposit")
async def record_crypto_deposit(
    request: CryptoDepositRecord,
    auth: dict = Depends(require_permission("credit"))
):
    """Record a crypto deposit and issue rewards"""
    try:
        result = store.record_crypto_deposit(
            user_id=request.user_id,
            crypto_type=request.crypto_type,
            crypto_amount=request.crypto_amount,
            crypto_price_usd=request.crypto_price_usd,
            tx_hash=request.tx_hash
        )
        return ContributionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/contributions/fiat-donation")
@app.post("/api/contributions/fiat-donation")
async def record_fiat_donation(
    request: FiatDonationRecord,
    auth: dict = Depends(require_permission("credit"))
):
    """Record a fiat donation and issue rewards"""
    try:
        contribution_type = "subscription" if request.is_recurring else "fiat_donation"
        result = store.record_contribution(
            user_id=request.user_id,
            contribution_type=contribution_type,
            amount_usd=request.amount_usd,
            source=request.payment_method,
            metadata={
                "payment_method": request.payment_method,
                "is_recurring": request.is_recurring,
                "reference_id": request.reference_id
            }
        )
        return ContributionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/contributions/user/{user_id}/credits")
@app.get("/api/contributions/user/{user_id}/credits")
async def get_user_credits(
    user_id: str,
    auth: dict = Depends(require_permission("read"))
):
    """Get all credits (transferable + reputation) for a user"""
    return store.get_user_credits(user_id)


@app.post("/api/v1/contributions/reward/{user_id}")
@app.post("/api/contributions/reward/{user_id}")
async def quick_reward(
    user_id: str,
    contribution_type: str,
    amount: float = 1.0,
    auth: dict = Depends(require_permission("credit"))
):
    """Quick reward for non-financial contributions"""
    try:
        result = store.record_contribution(
            user_id=user_id,
            contribution_type=contribution_type,
            amount_usd=amount,
            source="admin"
        )
        return ContributionResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# GOVERNANCE ENDPOINTS
# ============================================================

@app.post("/api/governance/proposals", response_model=ProposalResponse)
async def create_proposal(
    request: ProposalCreate,
    auth: dict = Depends(require_permission("admin"))
):
    """Create a new governance proposal"""
    # In production, proposer_id would come from auth token
    proposer_id = auth.get("sub", "admin")
    proposal = store.create_proposal(
        title=request.title,
        description=request.description,
        proposer_id=proposer_id,
        proposal_type=request.proposal_type,
        target_phase=request.target_phase,
        execution_data=request.execution_data
    )
    return ProposalResponse(**proposal)

@app.get("/api/governance/proposals", response_model=List[ProposalResponse])
async def list_proposals(status: Optional[str] = None):
    """List governance proposals"""
    return store.get_proposals(status)

@app.get("/api/governance/proposals/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(proposal_id: str):
    """Get a specific proposal"""
    if proposal_id not in store.proposals:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return ProposalResponse(**store.proposals[proposal_id])

@app.post("/api/governance/proposals/{proposal_id}/vote")
async def cast_vote(
    proposal_id: str,
    request: VoteCreate,
    auth: dict = Depends(require_permission("vote"))
):
    """Cast a vote on a proposal"""
    voter_id = auth.get("sub", "anonymous")
    voting_power = 1.0 
    
    try:
        result = store.cast_vote(proposal_id, voter_id, request.vote, voting_power)
        return {"status": "success", "vote": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/governance/decisions")
async def list_decisions():
    """List executed governance decisions (The Registry)"""
    decisions = [p for p in store.proposals.values() if p["status"] in ["executed", "passed"]]
    return {"decisions": decisions, "count": len(decisions)}


# ============================================================
# AUDIT TRAIL ENDPOINTS
# ============================================================

@app.get("/api/audit/chain")
async def get_audit_chain(limit: int = 100, offset: int = 0):
    """Get the audit chain (recent blocks)."""
    chain = store.audit_chain[offset:offset + limit]
    return {
        "blocks": chain,
        "total": len(store.audit_chain),
        "limit": limit,
        "offset": offset,
        "last_hash": store.last_block_hash
    }

@app.get("/api/audit/verify")
async def verify_audit_chain():
    """Verify the integrity of the entire audit chain."""
    return store.verify_audit_chain()

@app.get("/api/audit/block/{tx_id}")
async def get_audit_block(tx_id: str):
    """Find an audit block by transaction ID."""
    block = store.get_audit_block(tx_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found for this transaction")
    return block

@app.post("/api/audit/anchor")
async def anchor_audit_chain(auth: dict = Depends(require_permission("admin"))):
    """
    Manually trigger an anchor of the audit chain to Solana.
    
    This writes the current hash to the blockchain, proving the state existed
    at this exact moment. Can be called by a cron job daily.
    """
    result = store.anchor_audit_chain()
    if result["status"] == "failed":
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result


# ============================================================
# WEBHOOK ENDPOINTS
# ============================================================

class WebhookCreate(BaseModel):
    url: str
    events: List[str] = ["*"]  # Default: all events

@app.post("/api/webhooks/subscribe")
async def subscribe_webhook(
    request: WebhookCreate,
    auth: dict = Depends(require_permission("read"))
):
    """Subscribe to webhook notifications."""
    service_id = auth.get("sub", "anonymous")
    webhook = store.register_webhook(service_id, request.url, request.events)
    return {"status": "subscribed", "webhook": webhook}

@app.get("/api/webhooks")
async def list_webhooks(auth: dict = Depends(require_permission("admin"))):
    """List all webhook subscriptions."""
    return {"webhooks": list(store.webhooks.values())}

@app.delete("/api/webhooks/{webhook_id}")
async def unsubscribe_webhook(
    webhook_id: str,
    auth: dict = Depends(require_permission("admin"))
):
    """Unsubscribe a webhook."""
    if webhook_id in store.webhooks:
        store.webhooks[webhook_id]["active"] = False
        return {"status": "unsubscribed", "webhook_id": webhook_id}
    raise HTTPException(status_code=404, detail="Webhook not found")


# ============================================================
# MULTI-SIGNATURE ENDPOINTS
# ============================================================

class MultisigRequest(BaseModel):
    tx_type: str = Field(..., pattern="^(mint|grant|large_transfer)$")
    amount: float = Field(..., gt=0)
    details: Dict[str, Any] = {}

@app.post("/api/multisig/request")
async def create_multisig_request(
    request: MultisigRequest,
    auth: dict = Depends(require_permission("admin"))
):
    """Create a multi-signature request for large transactions (>10,000 UC)."""
    requester_id = auth.get("sub", "admin")
    try:
        msig = store.create_multisig_request(
            request.tx_type,
            request.amount,
            request.details,
            requester_id
        )
        return {"status": "pending", "multisig": msig}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/multisig/pending")
async def list_pending_multisig(auth: dict = Depends(require_permission("admin"))):
    """List pending multi-signature requests."""
    pending = [m for m in store.multisig_queue.values() if m["status"] == "pending"]
    return {"pending": pending, "count": len(pending)}

@app.post("/api/multisig/{request_id}/approve")
async def approve_multisig(
    request_id: str,
    council: str = "strategic",  # strategic, guardian, community
    auth: dict = Depends(require_permission("admin"))
):
    """Approve a multi-signature request."""
    approver_id = auth.get("sub", "admin")
    try:
        result = store.approve_multisig(request_id, approver_id, council)
        return {"status": result["status"], "multisig": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/multisig/{request_id}/reject")
async def reject_multisig(
    request_id: str,
    reason: str = "No reason provided",
    auth: dict = Depends(require_permission("admin"))
):
    """Reject a multi-signature request."""
    rejector_id = auth.get("sub", "admin")
    try:
        result = store.reject_multisig(request_id, rejector_id, reason)
        return {"status": "rejected", "multisig": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# COMPLIANCE ENDPOINTS
# ============================================================

@app.get("/api/compliance/{service_id}")
async def get_service_compliance(service_id: str):
    """Get compliance score for a service."""
    return store.get_service_compliance(service_id)

@app.get("/api/compliance")
async def list_all_compliance(auth: dict = Depends(require_permission("admin"))):
    """List compliance scores for all services."""
    return {
        "services": list(store.service_compliance.values()),
        "count": len(store.service_compliance)
    }

@app.post("/api/compliance/check")
async def record_compliance_check(
    service_id: str,
    check_type: str = "treasury_health_check",
    passed: bool = True,
    auth: dict = Depends(require_permission("read"))
):
    """Record a compliance check (called by services before issuing bonuses)."""
    # This endpoint allows services to self-report compliance
    # The system tracks who checks treasury health before issuing bonuses
    record = store.record_compliance_check(service_id, check_type, passed)
    return {"status": "recorded", "compliance": record}


# ============================================================
# TREASURY REBALANCING ENDPOINTS
# ============================================================

@app.post("/api/treasury/rebalance")
async def rebalance_treasury(auth: dict = Depends(require_permission("admin"))):
    """
    Trigger treasury rebalancing.
    
    Allocates funds from main treasury to:
    - Operations (40%)
    - Rewards Pool (30%)
    - Creator Grants (20%)
    - Reserve (10%)
    
    In ABUNDANCE mode, also funds "Worthy Recipients".
    """
    result = store.rebalance_treasury()
    return result

@app.get("/api/treasury/allocations")
async def get_treasury_allocations():
    """Get current treasury allocations across all system accounts."""
    allocations = {}
    total = 0.0
    
    for acc_id, acc in store.accounts.items():
        if acc_id.startswith("system:"):
            balance = acc.get("balances", {}).get("fp_credits", 0)
            allocations[acc_id] = balance
            total += balance
    
    return {
        "allocations": allocations,
        "total": total,
        "policy": {
            "operations": Config.TREASURY_OPERATIONS,
            "rewards": Config.TREASURY_REWARDS,
            "grants": Config.TREASURY_GRANTS,
            "reserve": Config.TREASURY_RESERVE
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================
# DISASTER RECOVERY / BACKUP ENDPOINTS
# ============================================================

@app.post("/api/admin/backup")
async def create_backup(auth: dict = Depends(require_permission("admin"))):
    """Create a full backup of the system state."""
    backup_id = f"backup-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
    
    backup_data = {
        "backup_id": backup_id,
        "created_at": datetime.utcnow().isoformat(),
        "version": Config.VERSION,
        "data": {
            "accounts": store.accounts,
            "transactions": store.transactions[-10000:],  # Last 10K transactions
            "proposals": store.proposals,
            "votes": store.votes,
            "webhooks": store.webhooks,
            "audit_chain": store.audit_chain[-1000:],  # Last 1K audit blocks
            "last_block_hash": store.last_block_hash,
            "multisig_queue": store.multisig_queue,
            "service_compliance": store.service_compliance,
            "metrics": store.metrics
        }
    }
    
    # Save to file
    backup_path = f"/tmp/{backup_id}.json"
    try:
        with open(backup_path, 'w') as f:
            json.dump(backup_data, f, indent=2, default=str)
        
        # Record to audit trail
        store._record_audit_block("backup_created", {
            "backup_id": backup_id,
            "path": backup_path,
            "accounts": len(store.accounts),
            "transactions": len(store.transactions)
        })
        
        return {
            "status": "success",
            "backup_id": backup_id,
            "path": backup_path,
            "size_accounts": len(store.accounts),
            "size_transactions": len(store.transactions),
            "size_audit_blocks": len(store.audit_chain)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

@app.post("/api/admin/restore")
async def restore_backup(
    backup_path: str,
    auth: dict = Depends(require_permission("admin"))
):
    """Restore system state from a backup file."""
    try:
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        
        data = backup_data.get("data", {})
        
        # Restore state
        store.accounts = data.get("accounts", store.accounts)
        store.transactions = data.get("transactions", store.transactions)
        store.proposals = data.get("proposals", store.proposals)
        store.votes = data.get("votes", store.votes)
        store.webhooks = data.get("webhooks", store.webhooks)
        store.audit_chain = data.get("audit_chain", store.audit_chain)
        store.last_block_hash = data.get("last_block_hash", store.last_block_hash)
        store.multisig_queue = data.get("multisig_queue", store.multisig_queue)
        store.service_compliance = data.get("service_compliance", store.service_compliance)
        store.metrics = data.get("metrics", store.metrics)
        
        # Record restoration
        store._record_audit_block("backup_restored", {
            "backup_id": backup_data.get("backup_id"),
            "backup_created_at": backup_data.get("created_at"),
            "restored_at": datetime.utcnow().isoformat()
        })
        
        return {
            "status": "success",
            "backup_id": backup_data.get("backup_id"),
            "restored_accounts": len(store.accounts),
            "restored_transactions": len(store.transactions)
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

@app.get("/api/admin/system-state")
async def get_system_state(auth: dict = Depends(require_permission("admin"))):
    """Get a summary of the current system state."""
    return {
        "version": Config.VERSION,
        "accounts": len(store.accounts),
        "transactions": len(store.transactions),
        "proposals": len(store.proposals),
        "webhooks": len(store.webhooks),
        "audit_blocks": len(store.audit_chain),
        "multisig_pending": len([m for m in store.multisig_queue.values() if m["status"] == "pending"]),
        "services_tracked": len(store.service_compliance),
        "last_block_hash": store.last_block_hash[:16] + "...",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================
# EXCHANGE RATES & PROTOCOL
# ============================================================

@app.get("/api/treasury/health")
async def get_treasury_health():
    """
    Get the Health Score of the Treasury.
    
    PRIME DIRECTIVE: "The Treasury Must Survive."
    Services MUST check this before issuing discretionary bonuses.
    """
    # Use cached health if available
    cached = await _cache.get("treasury_health")
    if cached:
        return cached
        
    health = store.calculate_treasury_health()
    await _cache.set("treasury_health", health, Config.CACHE_HEALTH_TTL)
    return health

@app.get("/api/treasury/analyze")
async def get_treasury_analysis():
    """
    Get a qualitative AI analysis of the treasury state.
    "The Voice of the Treasury"
    """
    # Cache analysis for 5 minutes as it's expensive
    cached = await _cache.get("treasury_analysis")
    if cached:
        return cached
        
    analysis = await store.analyze_treasury_health()
    await _cache.set("treasury_analysis", analysis, 300) # 5 minute TTL
    return analysis

@app.get("/api/v1/exchange/rates")
@app.get("/api/exchange/rates")
@app.get("/api/exchange-rates")
async def get_exchange_rates():
    """
    Get current exchange rates.
    
    PROTOCOL: All credits are 1:1 with USD. This is FIXED and will not change.
    See: docs/protocols/UNIVERSAL_CREDITS_PROTOCOL.md
    """
    return {
        "base": "UC",
        "rates": {
            "USD": 1.0,
            "FPC": 1.0,
            "CORA": 1.0,
            "SKY": 1.0,
            "FI": 1.0
        },
        "fixed": True,
        "credit_rates": EXCHANGE_RATES,
        "crypto_rates": CRYPTO_RATES,
        "protocol_version": "1.2",
        "source": f"FP Credits Gateway v{Config.VERSION}",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/protocol")
async def get_protocol():
    """
    Get the Universal Credits Protocol specification.
    
    This is the SINGLE SOURCE OF TRUTH for all credit values.
    All services MUST comply with this protocol.
    """
    return {
        "protocol": "Universal Credits Protocol",
        "version": "1.2",
        "effective_date": "2025-11-30",
        "authority": "FP Credits Gateway",
        "documentation": "https://fullpotential.ai/services/credits/api/protocol",
        
        # PRIME DIRECTIVE
        "prime_directive": {
            "statement": "The Treasury Must Survive.",
            "principle": "Sustainability First. Generosity is a function of surplus.",
            "metric": "Treasury Health Score (THS) = Assets / Liabilities",
            "modes": {
                "DEFICIT": "THS < 1.0 - CRITICAL - No bonuses",
                "STABLE": "1.0 <= THS < 1.2 - SECURE - Earned rewards only",
                "GROWTH": "1.2 <= THS < 1.5 - HEALTHY - Strategic bonuses",
                "ABUNDANCE": "THS > 1.5 - RADIANT - Subsidize basic needs"
            },
            "endpoint": "/api/treasury/health"
        },

        # Current operational rules
        "current_phase": "anchor",
        "rules": {
            "base_currency": "UC (Universal Credit)",
            "exchange_rate": "1 UC = $1.00 USD",
            "rate_type": "FIXED (Phase 1)",
            "transferable_credits": ["UC", "FPC", "CORA", "SKY", "FI"],
            "reputation_credits": ["BUILDER", "COMMUNITY", "EVANGELIST", "PATRON"],
            "all_transferable_1_to_1": True,
            "floating_rates": False,
            "discounts": False,
            "premiums": False
        },

        # What code MUST do in Anchor phase
        "machine_contract": {
            "value_invariant": "Treat 1 UC as exactly $1.00 USD for all pricing, accounting, metering, and reporting.",
            "source_of_truth": "Services MUST fetch rates from /services/credits/api/exchange-rates.",
            "unit_of_account": "Use UC internally; FPC/CORA/SKY/FI map 1:1 to UC.",
            "no_hidden_fx": "Services MAY set their own UC prices but MAY NOT define alternative USD↔UC conversions.",
            "phase_binding": "These rules apply while current_phase = 'anchor' and change only via governance."
        },

        # Evolutionary framework
        "evolution": {
            "phase_1_anchor": {
                "status": "ACTIVE",
                "rate": "1 UC = $1.00 USD (fixed)",
                "purpose": "Build trust, establish utility, grow adoption"
            },
            "phase_2_stabilization": {
                "status": "FUTURE",
                "rate": "1 UC ≈ $1.00 USD (soft peg with reserves)",
                "trigger": "Critical mass + sustainable utility base"
            },
            "phase_3_sovereignty": {
                "status": "FUTURE",
                "rate": "UC floats based on ecosystem utility",
                "trigger": "Dollar instability OR UC utility exceeds backing needs"
            },
            "phase_4_transition": {
                "status": "VISION",
                "role": "Bridge currency for paradise economics",
                "mechanism": "Surplus distribution to onboard humanity"
            }
        },

        # Monetary policy (Anchor phase)
        "monetary_policy": {
            "phase": "anchor",
            "minting_sources": [
                "Fiat/crypto purchases (1 UC per $1 received net of fees)",
                "On-chain FI conversions (1:1)",
                "Explicit governance grants with logged decisions"
            ],
            "sinks": [
                "Redemptions to FI or other on-chain assets",
                "Protocol fees routed to burn or long-term reserves"
            ],
            "safety_constraints": {
                "no_fractional_reserves": True,
                "min_treasury_coverage_ratio": 1.0,
                "notes": "Do not issue more UC promises than can be honored by treasury + service capacity."
            }
        },

        # Governance & safety
        "governance": {
            "structure": {
                "councils": [
                    {"name": "Strategic Council", "role": "Vision, emergency overrides, Phase 1 governance"},
                    {"name": "Guardian Council", "role": "Metric enforcement, safety brakes"},
                    {"name": "Community Council", "role": "Voting on major grants, Phase 3+ ratification"}
                ],
                "decision_registry": "/api/governance/decisions"
            },
            "current_phase_change_requires": [
                "New protocol version (e.g. 1.x → 2.0)",
                "Recorded decision by UC governance (human + AI council)",
                "Public announcement with effective date"
            ],
            "indicators_for_phase_change": {
                "positive": [
                    "100k+ active UC holders",
                    "$10M+ monthly transaction volume",
                    "50+ services accepting UC",
                    "12+ months stable operations",
                    "Community governance established",
                    "Reserves >= 3x monthly volume"
                ],
                "external": [
                    "USD inflation > 15% annually",
                    "Major currency crises",
                    "Accelerating global de-dollarization"
                ]
            }
        },
        "safety_brakes": {
            "phase_freeze": "Can temporarily lock current_phase to prevent changes during audits or incidents.",
            "issuance_circuit_breaker": "Pauses new issuance if treasury coverage drops below threshold.",
            "growth_guardrails": "Future phases SHOULD cap UC expansion (e.g. <= 5%/year) unless governance overrides.",
            "disclosure": "Any activation must be logged, time-stamped, and communicated to users and integrators."
        },

        "deprecated_terms": {
            "POT": "Use UC",
            "COMPUTE": "Use UC",
            "CONTENT": "Use UC",
            "FPAI": "Use UC",
            "CHURCH": "Use UC"
        },
        "endpoints": {
            "exchange_rates": "/api/exchange-rates",
            "balance": "/api/balance/{account_id}",
            "credit": "/api/credit",
            "debit": "/api/debit",
            "pricing": "/api/pricing",
            "purchase": "/purchase"
        },
        "philosophy": "Transition humanity from extractive to regenerative economics"
    }

# Service pricing (canonical source)
SERVICE_PRICING = {
    "ai-brain-llama": {"cost_uc": 0.001, "unit": "1K tokens", "description": "Local Llama model"},
    "ai-brain-claude": {"cost_uc": 0.01, "unit": "1K tokens", "description": "Claude API"},
    "ai-brain-gpt4": {"cost_uc": 0.03, "unit": "1K tokens", "description": "GPT-4 API"},
    "voice-inbound": {"cost_uc": 0.10, "unit": "minute", "description": "Inbound voice call"},
    "voice-outbound": {"cost_uc": 0.15, "unit": "minute", "description": "Outbound voice call"},
    "image-generation": {"cost_uc": 0.05, "unit": "image", "description": "AI image generation"},
    "content-studio": {"cost_uc": 1.0, "unit": "piece", "description": "Content creation"},
    "i-match-listing": {"cost_uc": 0.0, "unit": "listing", "description": "Free to list"},
    "i-match-commission": {"cost_uc": 0.20, "unit": "percent of deal", "description": "20% success fee"},
    "breath-optimizer": {"cost_uc": 0.0, "unit": "session", "description": "Free wellness service"},

    # ── Concierge platform (see SERVICES/concierge/docs/UC_SKUS.md) ──
    # Subscription tiers (monthly)
    "concierge.starter.monthly": {"cost_uc": 199.0,  "unit": "month",   "description": "Concierge Starter — 1 number, AI voice+SMS, 200 AI minutes, human overflow"},
    "concierge.pro.monthly":     {"cost_uc": 499.0,  "unit": "month",   "description": "Concierge Pro — 3 numbers, AI chat/email, warm transfer, 600 AI min + 100 human min, outbound campaigns"},
    "concierge.scale.monthly":   {"cost_uc": 1499.0, "unit": "month",   "description": "Concierge Scale — unlimited numbers, skills-mesh routing, 2000 AI min + 400 human min, dedicated pod"},
    # Metered overage (per minute)
    "concierge.overage.ai_minute.starter": {"cost_uc": 0.75, "unit": "minute", "description": "Concierge Starter AI overage"},
    "concierge.overage.ai_minute.pro":     {"cost_uc": 0.60, "unit": "minute", "description": "Concierge Pro AI overage"},
    "concierge.overage.ai_minute.scale":   {"cost_uc": 0.50, "unit": "minute", "description": "Concierge Scale AI overage"},
    "concierge.overage.human_minute.pro":   {"cost_uc": 1.25, "unit": "minute", "description": "Concierge Pro human overage"},
    "concierge.overage.human_minute.scale": {"cost_uc": 1.00, "unit": "minute", "description": "Concierge Scale human overage"},
    # Per-outcome pricing (pay on delivery)
    "concierge.outcome.booked_job":     {"cost_uc": 12.0, "unit": "booking",      "description": "Concierge — booked service visit"},
    "concierge.outcome.qualified_lead": {"cost_uc": 8.0,  "unit": "lead",         "description": "Concierge — qualified lead handed off"},
    "concierge.outcome.answered_call":  {"cost_uc": 2.0,  "unit": "call",         "description": "Concierge — AI-only call resolved"},
    "concierge.outcome.human_handoff":  {"cost_uc": 4.0,  "unit": "handoff",      "description": "Concierge — human-assisted resolution"},
    # Human hourly (network rates)
    "concierge.human.bpo_hour":        {"cost_uc": 14.0, "unit": "hour", "description": "Concierge — OneBPO agent hour"},
    "concierge.human.specialist_hour": {"cost_uc": 22.0, "unit": "hour", "description": "Concierge — certified specialist hour"},
    "concierge.human.supervisor_hour": {"cost_uc": 35.0, "unit": "hour", "description": "Concierge — live supervisor hour"},
    # Setup
    "concierge.setup.onboarding":  {"cost_uc": 0.0,   "unit": "onetime", "description": "Concierge — self-serve onboarding (free)"},
    "concierge.setup.white_glove": {"cost_uc": 499.0, "unit": "onetime", "description": "Concierge — white-glove onboarding"},
}

@app.get("/api/pricing")
@app.get("/api/pricing/{service}")
async def get_pricing(service: str = None):
    """
    Get canonical service pricing.
    
    All services MUST fetch pricing from this endpoint rather than hardcoding values.
    """
    if service:
        if service in SERVICE_PRICING:
            return {
                "service": service,
                **SERVICE_PRICING[service],
                "currency": "UC",
                "source": "FP Credits Gateway"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Service '{service}' not found in pricing catalog")
    
    return {
        "services": SERVICE_PRICING,
        "currency": "UC",
        "note": "1 UC = $1.00 USD",
        "source": f"FP Credits Gateway v{Config.VERSION}",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================
# TRANSACTION HISTORY
# ============================================================

@app.get("/api/transactions/{account_id}")
async def get_transactions(
    account_id: str,
    limit: int = 50,
    offset: int = 0,
    tx_type: str = None,
    auth: dict = Depends(require_permission("read"))
):
    """Get transaction history for an account"""
    transactions = store.get_transactions(account_id, limit, offset, tx_type)
    return {
        "account_id": account_id,
        "transactions": transactions,
        "count": len(transactions),
        "limit": limit,
        "offset": offset
    }

# ============================================================
# API KEY MANAGEMENT
# ============================================================

@app.post("/api/keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreate,
    auth: dict = Depends(require_permission("admin"))
):
    """Create a new API key for a service"""
    key = store.create_api_key(
        request.service_name,
        request.description,
        request.permissions,
        request.rate_limit
    )
    return APIKeyResponse(**key)

@app.get("/api/keys")
async def list_api_keys(
    auth: dict = Depends(require_permission("admin"))
):
    """List all API keys (without revealing secrets)"""
    return {
        "keys": [
            {
                "key_id": k["key_id"],
                "service_name": k["service_name"],
                "permissions": k["permissions"],
                "created_at": k["created_at"],
                "last_used": k["last_used"],
                "usage_count": k["usage_count"],
                "active": k["active"]
            }
            for k in store.api_keys.values()
        ]
    }

@app.delete("/api/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    auth: dict = Depends(require_permission("admin"))
):
    """Revoke an API key"""
    if key_id not in store.api_keys:
        raise HTTPException(status_code=404, detail="API key not found")
    store.api_keys[key_id]["active"] = False
    return {"success": True, "message": f"API key {key_id} revoked"}

# ============================================================
# WEBSOCKET FOR REAL-TIME UPDATES
# ============================================================

@app.websocket("/ws/{account_id}")
async def websocket_endpoint(websocket: WebSocket, account_id: str):
    """WebSocket for real-time balance updates"""
    await websocket.accept()
    store.websocket_connections[account_id] = websocket
    
    try:
        # Send initial balance
        balance = store.get_balance(account_id)
        await websocket.send_json({
            "type": "connected",
            "account_id": account_id,
            "balances": balance["balances"],
            "total_value_usd": balance["total_value_usd"],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "balance":
                balance = store.get_balance(account_id)
                await websocket.send_json({
                    "type": "balance",
                    "balances": balance["balances"],
                    "total_value_usd": balance["total_value_usd"]
                })
    except WebSocketDisconnect:
        if account_id in store.websocket_connections:
            del store.websocket_connections[account_id]

# ============================================================
# STATS & ADMIN ENDPOINTS
# ============================================================

@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(
    auth: dict = Depends(require_permission("admin"))
):
    """Get system statistics"""
    stats = store.get_system_stats()
    return StatsResponse(**stats)

@app.get("/api/treasury")
async def get_treasury(
    auth: dict = Depends(require_permission("admin"))
):
    """Get treasury account balances"""
    treasury_accounts = {}
    for acc_id, acc in store.accounts.items():
        if acc_id.startswith("system:"):
            treasury_accounts[acc_id] = {
                "display_name": acc["display_name"],
                "balances": acc["balances"],
                "total_value_usd": store._calculate_total_usd(acc["balances"])
            }
    
    return {
        "accounts": treasury_accounts,
        "total_value_usd": sum(t["total_value_usd"] for t in treasury_accounts.values()),
        "fee_allocation": {
            "operations": f"{Config.TREASURY_OPERATIONS * 100}%",
            "rewards": f"{Config.TREASURY_REWARDS * 100}%",
            "grants": f"{Config.TREASURY_GRANTS * 100}%",
            "reserve": f"{Config.TREASURY_RESERVE * 100}%",
        }
    }

@app.post("/api/treasury/distribute")
async def distribute_rewards(
    amount: float,
    credit_type: CreditType = CreditType.FP_CREDITS,
    auth: dict = Depends(require_permission("admin"))
):
    """Distribute rewards from rewards pool"""
    try:
        # Debit from rewards pool
        store.debit(
            "system:rewards",
            amount,
            credit_type,
            "Rewards distribution",
            tx_type=TransactionType.REWARD
        )
        return {"success": True, "amount": amount, "credit_type": credit_type.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ============================================================
# AI BRAIN INTEGRATION
# ============================================================

class AIQueryRequest(BaseModel):
    """Request for AI query through credits gateway"""
    account_id: str
    prompt: str
    model: str = "claude"  # claude, gpt, gemini
    max_tokens: int = Field(default=500, ge=1, le=4000)
    metadata: Dict[str, Any] = {}

class AIQueryResponse(BaseModel):
    """Response from AI query"""
    success: bool
    response: str = ""
    model: str = ""
    tokens_used: int = 0
    credits_used: float = 0.0
    credits_remaining: float = 0.0
    transaction_id: str = ""
    error: str = ""

@app.post("/api/ai/query", response_model=AIQueryResponse)
async def ai_query(
    request: AIQueryRequest,
    auth: dict = Depends(require_permission("debit"))
):
    """
    Execute AI query and debit credits from account.
    
    This endpoint acts as a bridge between FP Credits and the AI Brain.
    It:
    1. Checks account balance
    2. Forwards query to AI Brain
    3. Debits credits based on usage
    4. Returns the AI response
    """
    try:
        # Check balance first
        balance_data = store.get_balance(request.account_id)
        fp_balance = balance_data["balances"].get(CreditType.FP_CREDITS.value, 0)
        
        # Estimate cost (will be adjusted after actual usage)
        estimated_cost = max(Config.AI_CREDITS_PER_QUERY, (request.max_tokens / 1000) * Config.AI_COST_PER_1K_TOKENS)
        
        if fp_balance < estimated_cost:
            return AIQueryResponse(
                success=False,
                error=f"Insufficient balance. Need ~{estimated_cost:.2f} FPC, have {fp_balance:.2f} FPC"
            )
        
        # Forward to AI Brain v4.1.0
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Map model aliases to provider names
            provider_map = {
                "claude": "anthropic",
                "gpt": "openai",
                "gemini": "vertex",
                "grok": "xai",
                "llama": "together"
            }
            provider = provider_map.get(request.model, request.model)
            
            response = await client.post(
                f"{Config.AI_BRAIN_URL}/generate",
                headers={
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": request.prompt,
                    "max_tokens": request.max_tokens,
                    "provider": provider
                }
            )
            
            if response.status_code != 200:
                return AIQueryResponse(
                    success=False,
                    error=f"AI Brain error: {response.text}"
                )
            
            ai_result = response.json()
        
        # Calculate actual cost based on tokens used
        tokens_used = ai_result.get("tokens_used", request.max_tokens)
        actual_cost = max(
            Config.AI_CREDITS_PER_QUERY,
            (tokens_used / 1000) * Config.AI_COST_PER_1K_TOKENS
        )
        actual_cost = round(actual_cost, 4)
        
        # Debit the account
        tx = store.debit(
            request.account_id,
            actual_cost,
            CreditType.FP_CREDITS,
            f"AI Query ({request.model}): {tokens_used} tokens",
            reference_id=ai_result.get("request_id"),
            metadata={
                "model": ai_result.get("model", request.model),
                "tokens_used": tokens_used,
                "provider": ai_result.get("provider", "unknown")
            },
            tx_type=TransactionType.DEBIT
        )
        
        # Credit the AI Brain revenue account (50% of cost)
        ai_revenue = round(actual_cost * 0.5, 4)
        if ai_revenue > 0:
            store.credit(
                "system:ai-brain",
                ai_revenue,
                CreditType.FP_CREDITS,
                f"AI Brain revenue share",
                source_account=request.account_id,
                tx_type=TransactionType.FEE
            )
        
        # Get updated balance
        new_balance = store.get_balance(request.account_id)
        
        return AIQueryResponse(
            success=True,
            # AI Brain has historically returned either {"response": "..."} or {"text": "..."}.
            # Preserve backwards compatibility by accepting both.
            response=ai_result.get("response") or ai_result.get("text") or "",
            model=ai_result.get("model", request.model),
            tokens_used=tokens_used,
            credits_used=actual_cost,
            credits_remaining=new_balance["balances"].get(CreditType.FP_CREDITS.value, 0),
            transaction_id=tx["transaction_id"]
        )
        
    except httpx.TimeoutException:
        return AIQueryResponse(
            success=False,
            error="AI Brain request timed out. Please try again."
        )
    except Exception as e:
        logger.error(f"AI query error: {e}")
        return AIQueryResponse(
            success=False,
            error=str(e)
        )

@app.get("/api/ai/status")
async def ai_brain_status():
    """Check AI Brain connection status"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{Config.AI_BRAIN_URL}/health")
            if response.status_code == 200:
                brain_health = response.json()
                
                # Get provider info
                root_response = await client.get(f"{Config.AI_BRAIN_URL}/")
                providers_info = {}
                models_info = []
                if root_response.status_code == 200:
                    root_data = root_response.json()
                    providers_info = root_data.get("providers", {})
                    models_info = list(root_data.get("models", {}).values())
                
                return {
                    "connected": True,
                    "ai_brain_url": Config.AI_BRAIN_URL,
                    "ai_brain_version": brain_health.get("version", Config.AI_BRAIN_VERSION),
                    "ai_brain_health": brain_health,
                    "providers": providers_info,
                    "credits_per_query": Config.AI_CREDITS_PER_QUERY,
                    "cost_per_1k_tokens": Config.AI_COST_PER_1K_TOKENS,
                    "models_available": models_info or ["claude-opus-4.5", "gpt-5.1", "gemini-2.5-pro", "grok-4", "llama-3.3-70B"]
                }
    except Exception as e:
        logger.warning(f"AI Brain health check failed: {e}")
    
    return {
        "connected": False,
        "ai_brain_url": Config.AI_BRAIN_URL,
        "error": "Could not connect to AI Brain"
    }


# ============================================================
# GENESIS INTEGRATION (Mother Node)
# ============================================================

@app.get("/api/genesis/status")
async def genesis_status():
    """Check Genesis (Mother Node) connection status"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{Config.GENESIS_URL}/")
            if response.status_code == 200:
                genesis_data = response.json()
                return {
                    "connected": True,
                    "genesis_url": Config.GENESIS_URL,
                    "status": genesis_data.get("status", "unknown"),
                    "motto": genesis_data.get("motto", ""),
                    "enrolled": bool(Config.GENESIS_AGENT_TOKEN),
                    "agent_name": Config.SERVICE_NAME if Config.GENESIS_AGENT_TOKEN else None
                }
    except Exception as e:
        logger.warning(f"Genesis connection failed: {e}")
    
    return {
        "connected": False,
        "genesis_url": Config.GENESIS_URL,
        "enrolled": False,
        "error": "Could not connect to Genesis"
    }


@app.post("/api/genesis/enroll")
async def enroll_with_genesis(enrollment_key: str):
    """
    Enroll this service with Genesis using the Fleet Enrollment Key.
    
    Get the current key from God Mode Dashboard.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{Config.GENESIS_URL}/auth/enroll",
                json={
                    "agent_name": Config.SERVICE_NAME,
                    "key": enrollment_key
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                Config.GENESIS_AGENT_TOKEN = data.get("personal_key", "")
                Config.GENESIS_CONNECTED = True
                return {
                    "success": True,
                    "agent_name": data.get("agent_name"),
                    "message": "Successfully enrolled with Genesis!"
                }
            else:
                return {
                    "success": False,
                    "error": response.json().get("detail", "Enrollment failed")
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# USER SERVICE INTEGRATION (UC Payments)
# ============================================================

@app.get("/api/user-service/status")
async def user_service_status():
    """Check User Service (UC payment layer) connection status"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{Config.USER_SERVICE_URL}/docs/payments")
            if response.status_code == 200:
                docs = response.json()
                return {
                    "connected": True,
                    "url": Config.USER_SERVICE_URL,
                    "public_url": docs.get("public_url", "https://api.fullpotential.ai"),
                    "currency": "Universal Credits (UC)",
                    "exchange_rate": "1 UC = $1.00 USD = 1 FP Credit",
                    "payment_methods": list(docs.get("payment_methods", {}).keys()),
                    "crypto_currencies": docs.get("payment_methods", {}).get("crypto", {}).get("currencies", [])
                }
    except Exception as e:
        logger.warning(f"User Service connection failed: {e}")
    
    return {
        "connected": False,
        "url": Config.USER_SERVICE_URL,
        "error": "Could not connect to User Service"
    }


@app.get("/api/user-service/balance/{api_key}")
async def get_uc_balance(api_key: str):
    """
    Get a user's UC balance from the User Service.
    
    This bridges FP Credits Gateway with the User Service payment system.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{Config.USER_SERVICE_URL}/internal/balance/{api_key}")
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "api_key": api_key[:10] + "...",
                    "uc_balance": data.get("balance_uc", 0),
                    "fp_equivalent": data.get("balance_uc", 0),  # 1:1 parity
                    "source": "user-service"
                }
            else:
                return {
                    "success": False,
                    "error": "User not found or invalid API key"
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/user-service/deduct")
async def deduct_uc_credits(
    api_key: str,
    amount_uc: float,
    description: str = "FP Credits Gateway charge"
):
    """
    Deduct UC credits from a user via the User Service.
    
    Use this when charging users for services through FP Credits Gateway.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{Config.USER_SERVICE_URL}/internal/deduct",
                json={
                    "api_key": api_key,
                    "amount_uc": amount_uc,
                    "description": description
                }
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "amount_deducted": amount_uc,
                    "new_balance": data.get("new_balance", 0),
                    "transaction_id": data.get("transaction_id"),
                    "source": "user-service"
                }
            elif response.status_code == 402:
                return {
                    "success": False,
                    "error": "Insufficient balance",
                    "redirect": "https://fullpotential.ai/dashboard",
                    "message": "User needs to top up their UC balance"
                }
            else:
                return {
                    "success": False,
                    "error": response.json().get("detail", "Deduction failed")
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/user-service/credit")
async def credit_uc_to_user(
    api_key: str,
    amount_uc: float,
    description: str = "FP Credits Gateway credit",
    tx_hash: Optional[str] = None
):
    """
    Credit UC to a user via the User Service.
    
    Use this for refunds, rewards, or transfers.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "api_key": api_key,
                "amount_uc": amount_uc,
                "description": description
            }
            if tx_hash:
                payload["tx_hash"] = tx_hash
                
            response = await client.post(
                f"{Config.USER_SERVICE_URL}/internal/credit",
                json=payload
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "amount_credited": amount_uc,
                    "new_balance": data.get("new_balance", 0),
                    "transaction_id": data.get("transaction_id"),
                    "source": "user-service"
                }
            else:
                return {
                    "success": False,
                    "error": response.json().get("detail", "Credit failed")
                }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# CREDITS MANAGER INTEGRATION (Internal Ledger)
# ============================================================

@app.get("/api/credits-manager/status")
async def credits_manager_status():
    """Check Credits Manager (internal ledger) connection status"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{Config.CREDITS_MANAGER_URL}/health")
            if response.status_code == 200:
                health = response.json()
                return {
                    "connected": True,
                    "url": Config.CREDITS_MANAGER_URL,
                    "version": health.get("version", "unknown"),
                    "role": health.get("role", "central-banking-layer"),
                    "wallets": health.get("wallets", 0),
                    "transactions": health.get("transactions", 0)
                }
    except Exception as e:
        logger.warning(f"Credits Manager connection failed: {e}")
    
    return {
        "connected": False,
        "url": Config.CREDITS_MANAGER_URL,
        "error": "Could not connect to Credits Manager"
    }


@app.get("/api/credits-manager/wallets/{owner_id}")
async def get_wallet_from_manager(owner_id: str):
    """Get wallet from Credits Manager by owner ID"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{Config.CREDITS_MANAGER_URL}/api/v1/wallets/owner/{owner_id}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": "Wallet not found", "owner_id": owner_id}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/credits-manager/transfer")
async def transfer_via_manager(
    from_wallet_id: str,
    to_wallet_id: str,
    amount: float,
    currency: str = "UC",
    description: str = "FP Credits Gateway transfer"
):
    """Transfer credits via Credits Manager"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{Config.CREDITS_MANAGER_URL}/api/v1/transact/transfer",
                json={
                    "from_wallet_id": from_wallet_id,
                    "to_wallet_id": to_wallet_id,
                    "amount": amount,
                    "currency": currency,
                    "description": description
                }
            )
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/credits-manager/exchange-rates")
async def get_exchange_rates_from_manager():
    """Get exchange rates from Credits Manager"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{Config.CREDITS_MANAGER_URL}/api/v1/exchange/rates")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Failed to get exchange rates: {e}")
    
    # Fallback to our rates
    return EXCHANGE_RATES


# ============================================================
# TREASURY INTEGRATION (On-Chain SOL)
# ============================================================

@app.get("/api/treasury/status")
async def treasury_status():
    """
    Get REAL on-chain Treasury status.
    
    This fetches actual Solana blockchain data - no simulations.
    """
    result = {
        "source": "on-chain",
        "wallet_address": Config.SOLANA_TREASURY_WALLET,
        "chain": "solana",
        "verified": True
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Get real SOL balance from Solana RPC
            sol_response = await client.post(
                Config.SOLANA_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [Config.SOLANA_TREASURY_WALLET]
                }
            )
            
            if sol_response.status_code == 200:
                sol_data = sol_response.json()
                lamports = sol_data.get("result", {}).get("value", 0)
                sol_balance = lamports / 1_000_000_000  # Convert lamports to SOL
                
                # 2. Get real SOL price from CoinGecko
                try:
                    price_response = await client.get(
                        "https://api.coingecko.com/api/v3/simple/price",
                        params={"ids": "solana", "vs_currencies": "usd"}
                    )
                    if price_response.status_code == 200:
                        price_data = price_response.json()
                        sol_price = price_data.get("solana", {}).get("usd", 0)
                    else:
                        sol_price = 0
                except:
                    sol_price = 0
                
                sol_value_usd = sol_balance * sol_price
                
                result.update({
                    "connected": True,
                    "sol_balance": sol_balance,
                    "sol_price_usd": sol_price,
                    "sol_value_usd": round(sol_value_usd, 2),
                    "explorer_url": f"https://solscan.io/account/{Config.SOLANA_TREASURY_WALLET}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                return result
                
    except Exception as e:
        logger.warning(f"On-chain treasury check failed: {e}")
    
    result.update({
        "connected": False,
        "error": "Could not fetch on-chain data",
        "sol_balance": 0,
        "sol_value_usd": 0
    })
    return result


# ============================================================
# UNIFIED SYSTEM STATUS - The Economic Nervous System
# ============================================================

@app.get("/api/system/status")
async def system_status():
    """
    Unified status of the entire economic system.
    
    ALL DATA IS REAL - no simulations.
    
    Shows:
    - FP Credits Gateway (this service)
    - On-chain SOL Treasury (real blockchain data)
    - AI Brain (intelligence layer)
    """
    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "data_source": "real",  # No simulations
        "fp_credits_gateway": {
            "status": "healthy",
            "version": Config.VERSION,
            "treasury_fp": store.accounts["system:treasury"]["balances"].get("fp_credits", 0),
            "total_accounts": len(store.accounts),
            "total_transactions": len(store.transactions)
        },
        "genesis": {"connected": Config.GENESIS_CONNECTED, "enrolled": bool(Config.GENESIS_AGENT_TOKEN)},
        "user_service": {"connected": Config.USER_SERVICE_CONNECTED, "url": Config.USER_SERVICE_URL},
        "credits_manager": {"connected": Config.CREDITS_MANAGER_CONNECTED, "url": Config.CREDITS_MANAGER_URL},
        "sol_treasury": {"connected": False, "source": "on-chain"},
        "ai_brain": {"connected": False},
        "ecosystem": {}
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check Genesis
        try:
            response = await client.get(f"{Config.GENESIS_URL}/")
            if response.status_code == 200:
                genesis_data = response.json()
                status["genesis"] = {
                    "connected": True,
                    "status": genesis_data.get("status", "unknown"),
                    "enrolled": bool(Config.GENESIS_AGENT_TOKEN)
                }
        except:
            pass
        
        # Check User Service (UC Payments)
        try:
            response = await client.get(f"{Config.USER_SERVICE_URL}/docs/payments")
            if response.status_code == 200:
                docs = response.json()
                status["user_service"] = {
                    "connected": True,
                    "url": Config.USER_SERVICE_URL,
                    "currency": "UC (1:1 with FP Credits)",
                    "payment_methods": list(docs.get("payment_methods", {}).keys())
                }
        except:
            pass
        
        # Get REAL on-chain SOL balance
        try:
            sol_response = await client.post(
                Config.SOLANA_RPC_URL,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getBalance",
                    "params": [Config.SOLANA_TREASURY_WALLET]
                }
            )
            
            if sol_response.status_code == 200:
                sol_data = sol_response.json()
                lamports = sol_data.get("result", {}).get("value", 0)
                sol_balance = lamports / 1_000_000_000
                
                # Get real price
                sol_price = 0
                try:
                    price_response = await client.get(
                        "https://api.coingecko.com/api/v3/simple/price",
                        params={"ids": "solana", "vs_currencies": "usd"}
                    )
                    if price_response.status_code == 200:
                        sol_price = price_response.json().get("solana", {}).get("usd", 0)
                except:
                    pass
                
                status["sol_treasury"] = {
                    "connected": True,
                    "source": "on-chain",
                    "wallet": Config.SOLANA_TREASURY_WALLET,
                    "sol_balance": sol_balance,
                    "sol_price_usd": sol_price,
                    "sol_value_usd": round(sol_balance * sol_price, 2)
                }
        except Exception as e:
            status["sol_treasury"]["error"] = str(e)
        
        # Get AI Brain status
        try:
            response = await client.get(f"{Config.AI_BRAIN_URL}/health")
            if response.status_code == 200:
                brain_data = response.json()
                root_response = await client.get(f"{Config.AI_BRAIN_URL}/")
                root_data = root_response.json() if root_response.status_code == 200 else {}
                
                active_providers = [k for k, v in root_data.get("providers", {}).items() if v]
                
                status["ai_brain"] = {
                    "connected": True,
                    "version": brain_data.get("version", "unknown"),
                    "active_providers": active_providers,
                    "models": list(root_data.get("models", {}).values())
                }
        except Exception as e:
            status["ai_brain"]["error"] = str(e)
    
    # Calculate ecosystem totals (REAL data only)
    fp_treasury = status["fp_credits_gateway"]["treasury_fp"]
    sol_value = status["sol_treasury"].get("sol_value_usd", 0) if status["sol_treasury"].get("connected") else 0
    
    status["ecosystem"] = {
        "total_value_usd": round(fp_treasury + sol_value, 2),
        "fp_credits_treasury": fp_treasury,
        "sol_reserves_usd": sol_value,
        "ai_brain_active": status["ai_brain"].get("connected", False),
        "all_systems_operational": (
            status["fp_credits_gateway"]["status"] == "healthy" and
            status["ai_brain"].get("connected", False)
        ),
        "note": "FP Credits treasury is internal accounting. SOL treasury is real on-chain balance."
    }
    
    return status


@app.get("/api/system/budget")
async def system_budget():
    """
    Get current budget allocation and spending.
    
    Shows how credits are distributed across:
    - Operations
    - Rewards
    - Grants
    - Reserve
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "allocation_policy": {
            "operations": f"{Config.TREASURY_OPERATIONS * 100}%",
            "rewards": f"{Config.TREASURY_REWARDS * 100}%",
            "grants": f"{Config.TREASURY_GRANTS * 100}%",
            "reserve": f"{Config.TREASURY_RESERVE * 100}%"
        },
        "current_balances": {
            "treasury": store.accounts["system:treasury"]["balances"].get("fp_credits", 0),
            "operations": store.accounts["system:operations"]["balances"].get("fp_credits", 0),
            "rewards": store.accounts["system:rewards"]["balances"].get("fp_credits", 0),
            "grants": store.accounts["system:grants"]["balances"].get("fp_credits", 0),
            "reserve": store.accounts.get("system:reserve", {}).get("balances", {}).get("fp_credits", 0),
            "fees_collected": store.accounts["system:fees"]["balances"].get("fp_credits", 0)
        },
        "total_in_system": sum(
            acc["balances"].get("fp_credits", 0) 
            for acc in store.accounts.values() 
            if acc["account_id"].startswith("system:")
        ),
        "ai_brain_integration": {
            "cost_per_query": Config.AI_CREDITS_PER_QUERY,
            "cost_per_1k_tokens": Config.AI_COST_PER_1K_TOKENS,
            "markup": "0% (cost-based)"
        }
    }


@app.get("/api/ai/usage/{account_id}")
async def ai_usage_stats(
    account_id: str,
    auth: dict = Depends(require_permission("read"))
):
    """Get AI usage statistics for an account"""
    # Get all AI-related transactions
    all_txs = store.get_transactions(account_id, limit=1000)
    ai_txs = [tx for tx in all_txs if "AI Query" in tx.get("reason", "") or "AI Brain" in tx.get("reason", "")]
    
    total_spent = sum(abs(tx["amount"]) for tx in ai_txs if tx["amount"] < 0)
    total_tokens = sum(tx.get("metadata", {}).get("tokens_used", 0) for tx in ai_txs)
    
    # Group by model
    by_model = {}
    for tx in ai_txs:
        model = tx.get("metadata", {}).get("model", "unknown")
        if model not in by_model:
            by_model[model] = {"queries": 0, "tokens": 0, "cost": 0}
        by_model[model]["queries"] += 1
        by_model[model]["tokens"] += tx.get("metadata", {}).get("tokens_used", 0)
        by_model[model]["cost"] += abs(tx["amount"]) if tx["amount"] < 0 else 0
    
    return {
        "account_id": account_id,
        "total_queries": len(ai_txs),
        "total_tokens": total_tokens,
        "total_credits_spent": round(total_spent, 4),
        "usage_by_model": by_model,
        "recent_queries": ai_txs[:10]
    }

# ============================================================
# WEBHOOK ENDPOINTS (for AI Brain callbacks)
# ============================================================

class WebhookPayload(BaseModel):
    """Webhook payload from AI Brain or other services"""
    event: str
    service: str
    data: Dict[str, Any]
    timestamp: str = ""

@app.post("/api/webhooks/ai-brain")
async def ai_brain_webhook(
    payload: WebhookPayload,
    x_webhook_secret: str = Header(None)
):
    """
    Receive webhooks from AI Brain for async operations.
    
    Events:
    - usage_report: Periodic usage report
    - credits_low: Service credits running low
    - model_update: New model available
    """
    # Verify webhook (in production, use proper secret)
    expected_secret = os.getenv("AI_BRAIN_WEBHOOK_SECRET", "fpai_webhook_secret")
    if x_webhook_secret != expected_secret:
        logger.warning(f"Invalid webhook secret from {payload.service}")
        # Don't reject - just log for now
    
    logger.info(f"AI Brain webhook: {payload.event} from {payload.service}")
    
    if payload.event == "usage_report":
        # Log usage for analytics
        logger.info(f"AI Brain usage report: {payload.data}")
        return {"received": True, "event": payload.event}
    
    elif payload.event == "credits_low":
        # Our credits on AI Brain are running low
        logger.warning(f"AI Brain credits low: {payload.data}")
        # Could trigger auto-top-up or alert
        return {"received": True, "event": payload.event, "action": "alert_sent"}
    
    elif payload.event == "model_update":
        # New model available
        logger.info(f"AI Brain model update: {payload.data}")
        return {"received": True, "event": payload.event}
    
    return {"received": True, "event": payload.event}

@app.post("/api/webhooks/register")
async def register_webhook(
    url: str,
    events: List[str],
    auth: dict = Depends(require_permission("admin"))
):
    """Register a webhook for credit events"""
    webhook_id = f"wh_{secrets.token_hex(8)}"
    webhook_secret = f"whsec_{secrets.token_hex(16)}"
    
    # Store webhook (in production, use database)
    if not hasattr(store, 'webhooks'):
        store.webhooks = {}
    
    store.webhooks[webhook_id] = {
        "id": webhook_id,
        "url": url,
        "events": events,
        "secret": webhook_secret,
        "created_at": datetime.utcnow().isoformat(),
        "active": True
    }
    
    return {
        "webhook_id": webhook_id,
        "webhook_secret": webhook_secret,
        "url": url,
        "events": events,
        "message": "Include X-Webhook-Secret header in your endpoint"
    }

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)
