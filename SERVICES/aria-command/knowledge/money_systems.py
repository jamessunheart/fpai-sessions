# SERVICES/aria-command/knowledge/money_systems.py
"""
Aria's knowledge of Full Potential money management systems.
This module provides structured awareness of Zend, UC, Commons, and trading integrations.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

# =============================================================================
# SERVICE ARCHITECTURE
# =============================================================================

SERVICE_ARCHITECTURE = {
    "credits_gateway": {
        "name": "FP Credits Gateway",
        "port": 8765,
        "purpose": "UC ledger, commons reserve, credit operations",
        "endpoints": {
            "balance": "GET /api/balance/{user_id}",
            "debit": "POST /api/debit",
            "credit": "POST /api/credit",
            "commons_balance": "GET /api/treasury/allocations",
            "protocol": "GET /api/protocol"
        },
        "ledger_accounts": {
            "commons": "system:commons",
            "reserve": "system:reserve",
            "marketplace_escrow": "system:marketplace_escrow"
        }
    },
    "zend_wallet": {
        "name": "Zend Wallet",
        "port": 8580,
        "purpose": "UC balance, entity distribution, AI drafting",
        "endpoints": {
            "balance": "GET /api/zend/wallet/{member_id}",
            "entities": "GET /api/zend/entities",
            "distribute": "POST /api/zend/entities/{entity_id}/distribute"
        }
    },
    "zend_payments": {
        "name": "Zend Payments",
        "port": 8581,
        "purpose": "PaymentIntent, ZendLink, receipts",
        "endpoints": {
            "create_intent": "POST /api/zend/intents",
            "create_link": "POST /api/zend/links"
        }
    },
    "zend_clerk": {
        "name": "Zend Clerk",
        "port": 8582,
        "purpose": "Telegram/WhatsApp POS agent"
    },
    "zend_ton": {
        "name": "Zend TON",
        "port": 8583,
        "purpose": "TON Connect, USDT balance, transfer links",
        "endpoints": {
            "connect": "POST /api/ton/connect",
            "wallet": "GET /api/ton/wallet/{member_id}",
            "transfer": "POST /api/ton/transfer"
        }
    },
    "zend_marketplace": {
        "name": "Zend Marketplace",
        "port": 8584,
        "purpose": "P2P order book, UC/USDT exchange",
        "endpoints": {
            "create_order": "POST /api/marketplace/orders",
            "liquidity": "POST /api/marketplace/liquidity/register"
        }
    },
    "trust_index": {
        "name": "Trust Index",
        "port": 8560,
        "purpose": "Trust Index calculation for commons policy",
        "components": {
            "solvency": "40% weight (from THS)",
            "commons_health": "30% weight",
            "participation": "30% weight"
        }
    },
    "contribution_tracker": {
        "name": "Contribution Tracker",
        "port": 8570,
        "purpose": "Activity logging for TRUST earning"
    },
    "aria_trading": {
        "name": "Aria Trading",
        "port": 8750,
        "purpose": "Automated trading via Hyperliquid",
        "endpoints": {
            "status": "GET /api/trading/status",
            "signals": "GET /api/trading/signals",
            "execute": "POST /api/trading/execute"
        }
    }
}

# =============================================================================
# UC CREDITS PROTOCOL
# =============================================================================

UC_PROTOCOL = {
    "rate": "1 UC = $1.00 USD (fixed, always)",
    "nature": "Prepaid service credit, NOT money",
    "properties": {
        "is_money": False,
        "yield_bearing": False,
        "cash_redemption": False,
        "transferable": "Only within services",
        "public_market": False
    },
    "phases": [
        "Anchor (current): 1 UC = $1, fixed",
        "Stabilization: stronger guardrails, audits",
        "Sovereignty: mature governance, safety brakes",
        "Transition: migration paths for legacy"
    ],
    "canonical_doc": "docs/protocols/UNIVERSAL_CREDITS_PROTOCOL.md"
}

# =============================================================================
# ZEND PAYMENT SYSTEM
# =============================================================================

ZEND_SYSTEM = {
    "vision": "Ministry of Flow — regenerative payment facilitation",
    "principles": [
        "Optimization over Extraction: Fees heal, fund, empower",
        "Autonomy over Dependency: Users control money, Zend facilitates",
        "Consciousness over Computation: Payment as spiritual practice"
    ],
    "two_layer_model": {
        "external": "Real money (USD/USDC via Stripe/Solana)",
        "internal": "UC Credits for friction reduction, rewards"
    },
    "locked_rule": "Money moves outside. Ease lives inside.",
    "fee_circulation": {
        "ops": "40% - Infrastructure, partners, compliance",
        "commons": "30% - Commons Reserve Fund",
        "circulation": "30% - Sponsored sends, experiences"
    },
    "settlement_rails": ["Stripe (fiat)", "Solana USDC", "TON USDT"]
}

# =============================================================================
# COMMONS RESERVE
# =============================================================================

COMMONS_RESERVE = {
    "purpose": "Needs-meeting fund for members",
    "location": "Within Sunheart Private Trust",
    "ledger_account": "system:commons",
    "revenue_sources": {
        "uc_protocol_fees": "30%",
        "fi_transaction_fees": "30%",
        "llc_profits": "30%",
        "member_donations": "80%",
        "treasury_yields": "30% of surplus",
        "service_margins": "20%",
        "trading_fees": "30% (NEW)"
    },
    "allocation_categories": {
        "survival": "40% - Food, shelter, health",
        "stability": "25% - Debt relief, emergency",
        "growth": "20% - Education, tools",
        "contribution": "10% - Contributor recognition",
        "infrastructure": "5% - Commons infrastructure"
    },
    "hard_guardrails": {
        "minimum_reserve_ratio": "120% of committed",
        "max_daily_change": "5%",
        "emergency_freeze": "THS < 0.8 or Trust Index < 0.2",
        "human_override": "Always available"
    }
}

# =============================================================================
# TRUST EARNING (PROOF OF CONTRIBUTION)
# =============================================================================

TRUST_EARNING = {
    "principle": "TRUST is EARNED, not purchased",
    "activities": {
        "service_to_others": {"score": 10, "unit": "per hour"},
        "governance_vote": {"score": 5, "unit": "per vote"},
        "art_creation": {"score": "variable", "unit": "per piece"},
        "referral": {"score": 50, "unit": "per member"},
        "financial_contribution": {"score": 1, "unit": "per UC"},
        "community_building": {"score": "variable", "unit": "per activity"},
        # NEW: Trading activities
        "successful_trade": {"score": 5, "unit": "per profit trade"},
        "weekly_trading": {"score": 10, "unit": "per active week"},
        "monthly_profit_5pct": {"score": 25, "unit": "per month"},
        "referred_trader": {"score": 50, "unit": "per trader"}
    },
    "minimum_for_benefits": 100,  # per quarter
    "tiers": {
        "active": "100+ quarterly score - Full eligibility",
        "engaged": "50-99 quarterly score - Reduced eligibility",
        "inactive": "<50 quarterly score - No eligibility"
    }
}

# =============================================================================
# ENTITY SUPPORT
# =============================================================================

ENTITY_TYPES = {
    "individual": {
        "daily_buy_limit_uc": 1000,
        "daily_distribute_uc": 1000,
        "can_provide_liquidity": False
    },
    "trust": {
        "daily_buy_limit_uc": 50000,
        "daily_distribute_uc": 25000,
        "can_provide_liquidity": True
    },
    "llc": {
        "daily_buy_limit_uc": 25000,
        "daily_distribute_uc": 10000,
        "can_provide_liquidity": True
    },
    "church": {
        "daily_buy_limit_uc": 100000,
        "daily_distribute_uc": 50000,
        "can_provide_liquidity": True
    },
    "family_office": {
        "daily_buy_limit_uc": 500000,
        "daily_distribute_uc": 250000,
        "can_provide_liquidity": True
    }
}

# =============================================================================
# TRADING INTEGRATION
# =============================================================================

TRADING_INTEGRATION = {
    "service": "Aria Trading (Stewardship Ministry)",
    "exchange": "Hyperliquid (decentralized perps)",
    "non_custodial": True,
    "fee_structure": {
        "tier_1_subscription": "50-200 UC/month",
        "tier_2_performance": "10% of gains in UC"
    },
    "commons_contribution": "30% of all trading fees → Commons Reserve",
    "trust_earning": {
        "successful_trade": 5,
        "weekly_activity": 10,
        "monthly_profit_5pct": 25,
        "referred_trader": 50
    }
}

# =============================================================================
# COMBINED SYSTEMS
# =============================================================================

MONEY_SYSTEMS = {
    "services": SERVICE_ARCHITECTURE,
    "uc_protocol": UC_PROTOCOL,
    "zend": ZEND_SYSTEM,
    "commons_reserve": COMMONS_RESERVE,
    "trust_earning": TRUST_EARNING,
    "entity_types": ENTITY_TYPES,
    "trading": TRADING_INTEGRATION
}

# =============================================================================
# CONTEXT GENERATORS
# =============================================================================

def get_money_context() -> str:
    """Generate money systems context for Aria's system prompt."""
    return f"""
## MONEY MANAGEMENT SYSTEMS AWARENESS

You manage member finances across multiple integrated systems:

### UC Credits (Universal Credits)
- Rate: 1 UC = $1.00 USD (FIXED, ALWAYS)
- Nature: Service credits, NOT money
- No cash redemption, no yield, not transferable outside
- Gateway: fp-credits-gateway (port 8765)

### Zend Payment System
- Purpose: Regenerative payment facilitation
- Principle: "Money moves outside. Ease lives inside."
- Settlement: Stripe (fiat), Solana USDC, TON USDT
- Fee Split: 40% ops, 30% commons, 30% circulation

### Service Ports
- Credits Gateway: 8765 (UC ledger)
- Zend Wallet: 8580 (UC balance, entities)
- Zend Payments: 8581 (PaymentIntent)
- Zend TON: 8583 (TON wallet)
- Zend Marketplace: 8584 (P2P exchange)
- Trust Index: 8560 (commons policy)
- Contribution Tracker: 8570 (TRUST earning)
- Aria Trading: 8750 (trading API)

### Commons Reserve
- Location: system:commons ledger account
- Sources: 30% of UC fees, $FI fees, trading fees, LLC profits
- Purpose: Needs-meeting for members (NOT financial returns)
- Guardrails: 120% minimum reserve, 5% max daily change

### TRUST Earning
Members earn TRUST through:
- Service to others: 10/hour
- Governance votes: 5/vote
- Trading activity: 5/trade profit, 10/week active, 25/month if >5% profit
- Referrals: 50/member
- Financial contribution: 1/UC

Minimum 100 points/quarter for Commons benefits.

### Entity Types
- Individual: 1,000 UC daily limits
- Trust: 50,000 UC limits, can provide liquidity
- LLC: 25,000 UC limits, can provide liquidity
- Church: 100,000 UC limits, can provide liquidity

### Trading Integration
- 30% of trading fees flow to Commons Reserve
- Trading activity earns TRUST
- Members can convert trading profits to UC via Zend Marketplace
"""

def get_service_url(service_name: str) -> Optional[str]:
    """Get the URL for a service."""
    service = SERVICE_ARCHITECTURE.get(service_name)
    if service:
        port = service.get("port")
        if port:
            # Primary server for most services
            if service_name in ["aria_trading"]:
                return f"http://162.0.208.88:{port}"
            return f"http://198.54.123.234:{port}"
    return None

def get_contribution_score(activity: str) -> Optional[int]:
    """Get the TRUST contribution score for an activity."""
    activity_info = TRUST_EARNING["activities"].get(activity)
    if activity_info:
        score = activity_info.get("score")
        if isinstance(score, int):
            return score
    return None

def get_commons_allocation(source: str) -> Optional[str]:
    """Get the commons allocation percentage for a revenue source."""
    return COMMONS_RESERVE["revenue_sources"].get(source)









