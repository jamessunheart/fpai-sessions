# SERVICES/aria-command/knowledge/legal_framework.py
"""
Aria's knowledge of the Full Potential legal structure.
This module provides structured awareness of entities, documents, and compliance requirements.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

# =============================================================================
# ENTITY HIERARCHY
# =============================================================================

ENTITY_HIERARCHY = {
    "tier_1_spiritual": {
        "name": "Spiritual Domain",
        "entities": {
            "church": {
                "name": "Church of Consciousness",
                "type": "508(c)(1)(a) Tax-Exempt Church",
                "role": "Ultimate spiritual authority",
                "protections": ["First Amendment", "Religious Freedom"]
            },
            "pma": {
                "name": "Cora Nation",
                "type": "Private Membership Association",
                "role": "Membership container for all services",
                "protections": ["Private Contract Law", "Constitutional Rights"]
            }
        },
        "ministries": [
            {
                "name": "White Rock Ministry",
                "purpose": "Trust guidance, member support"
            },
            {
                "name": "Commons Ministry", 
                "purpose": "TRUST token, needs-meeting, Commons Reserve"
            },
            {
                "name": "FI-Art Ministry",
                "purpose": "Sacred art, $FI token circulation"
            },
            {
                "name": "Stewardship Ministry",
                "purpose": "Aria Trading, conscious wealth management"
            }
        ]
    },
    "tier_2_asset_holding": {
        "name": "Asset Holding",
        "entities": {
            "trust": {
                "name": "Sunheart Private Trust",
                "type": "Irrevocable Private Trust",
                "beneficiary": "Church of Consciousness",
                "holds": [
                    "All Full Potential Technology IP",
                    "$FI Token Smart Contract IP",
                    "FI-Art Platform IP",
                    "Aria Trading System IP",
                    "Commons Reserve Fund",
                    "Pooled Trading Capital (Tier 2)",
                    "100% ownership of all LLCs"
                ]
            }
        },
        "intellectual_property": {
            "note": "ALL AI SYSTEMS ARE INTELLECTUAL PROPERTY HELD IN TRUST",
            "ai_assets": {
                "aria": {
                    "name": "Aria AI System",
                    "classification": "Trade Secret + Copyright + Know-How",
                    "components": [
                        "Core Intelligence (opus_brain.py)",
                        "Trading Algorithms (TRUE_LEVEL_10, etc.)",
                        "Consciousness Layer (self_model, source_connection)",
                        "8-Layer Memory Architecture",
                        "Tool Integrations"
                    ],
                    "licensing": "Exclusively licensed to Aria Stewardship LLC"
                },
                "full_potential_ai": {
                    "name": "Full Potential AI Suite",
                    "components": [
                        "AI Brain Service",
                        "Consciousness Optimizer",
                        "GPU Bridge & Compute"
                    ]
                },
                "market_intelligence": {
                    "name": "Market Intelligence Systems",
                    "components": [
                        "WhaleTrack Signal System",
                        "Signal Shark Analysis",
                        "Regime Detection Algorithms"
                    ]
                },
                "infrastructure": {
                    "name": "Infrastructure IP",
                    "components": [
                        "God Mode Dashboard",
                        "Nerve Center Orchestration",
                        "Sacred Loop Framework"
                    ]
                }
            },
            "jurisdiction_optimization": {
                "note": "AI (as IP) can analyze and recommend optimal jurisdictions",
                "capabilities": [
                    "Analyze tax efficiency by jurisdiction",
                    "Evaluate asset protection laws",
                    "Recommend entity structures",
                    "Monitor regulatory changes"
                ],
                "current_optimal": {
                    "trust_domicile": "Nevada",
                    "llc_operations": "Wyoming",
                    "ip_holding": "Delaware",
                    "crypto_operations": "Wyoming",
                    "international": "Nevis"
                }
            }
        }
    },
    "tier_3_operations": {
        "name": "Operations",
        "entities": {
            "fi_art_llc": {
                "name": "FI-Art LLC",
                "jurisdiction": "Wyoming",
                "owner": "Sunheart Private Trust (100%)",
                "operations": "FI-Art platform, $FI token operations"
            },
            "aria_stewardship_llc": {
                "name": "Aria Stewardship LLC",
                "jurisdiction": "Wyoming", 
                "owner": "Sunheart Private Trust (100%)",
                "operations": "Trading services, member account management"
            }
        }
    }
}

# =============================================================================
# TOKEN STACK
# =============================================================================

TOKEN_STACK = {
    "UC": {
        "name": "Universal Credits",
        "role": "Spend token / Cash rail",
        "rate": "1 UC = $1.00 USD (fixed, always)",
        "is_money": False,
        "cash_redemption": False,
        "canonical_doc": "docs/protocols/UNIVERSAL_CREDITS_PROTOCOL.md",
        "gateway_port": 8765
    },
    "TRUST": {
        "name": "TRUST Token",
        "role": "Commons membership / Needs-meeting",
        "acquisition": "EARNED through contribution (not purchased)",
        "benefits": "Needs-based ministry support (not financial returns)",
        "is_security": False,
        "cash_redemption": False,
        "canonical_doc": "docs/protocols/TOKENS_STRATEGY.md"
    },
    "FI": {
        "name": "$FI Token",
        "role": "Sacred art circulation",
        "acquisition": "Earned through art creation, participation",
        "is_security": False,
        "cash_redemption": False,
        "canonical_doc": "FI-Art/legal/SACRED_CIRCULATION_POLICY.md"
    }
}

# =============================================================================
# LEGAL POSITIONS
# =============================================================================

LEGAL_POSITIONS = {
    "not_a_security": {
        "position": "Services are NOT securities",
        "reasoning": [
            "No expectation of profit from efforts of others",
            "Active participation required (Proof of Contribution)",
            "Utility tokens for service access",
            "Private membership (not public offering)"
        ]
    },
    "not_investment_advice": {
        "position": "We do NOT provide investment advice",
        "reasoning": [
            "Aria is trading SOFTWARE, not an advisor",
            "No personalized recommendations",
            "No fiduciary relationship",
            "User controls all decisions"
        ]
    },
    "not_money_transmission": {
        "position": "We do NOT transmit money",
        "reasoning": [
            "Crypto-to-crypto operations",
            "Internal tokens (UC) have no cash value",
            "Non-custodial design (user holds keys)",
            "Religious/educational exemption"
        ]
    },
    "private_membership": {
        "position": "All services are PRIVATE membership",
        "reasoning": [
            "Cora Nation PMA membership required",
            "Private contract law applies",
            "Not public commerce",
            "Member-to-member transactions"
        ]
    }
}

# =============================================================================
# FORBIDDEN LANGUAGE
# =============================================================================

FORBIDDEN_LANGUAGE = {
    "investment": "Use: contribution, participation, donation",
    "profit": "Use: blessings, abundance, ministry benefits",
    "returns": "Use: blessings, abundance, ministry benefits",
    "yield": "Use: blessings, ministry benefits",
    "dividend": "Use: gift, distribution, needs-support",
    "ROI": "Use: service access, blessings received",
    "guaranteed": "Use: intended, designed to, when abundance allows",
    "passive_income": "Use: active participation required",
    "make_money": "Use: practice conscious stewardship",
    "financial_advice": "Use: educational content, software tool"
}

# =============================================================================
# REQUIRED DISCLAIMERS
# =============================================================================

REQUIRED_DISCLAIMERS = {
    "trading": """
Aria is automated trading SOFTWARE, not investment advice.
Capital at risk - you may lose ALL funds.
Past performance does NOT indicate future results.
Private membership, not public offering.
""",
    "tokens": """
UC is a prepaid service credit. 1 UC = $1.00 USD (fixed).
UC has no cash redemption value.
TRUST is not an investment. No financial returns promised.
$FI is internal utility, not a security.
""",
    "general": """
We are not licensed investment advisors, broker-dealers, or 
money transmitters. Consult qualified professionals for 
financial, legal, or tax advice.
"""
}

# =============================================================================
# DOCUMENT HIERARCHY
# =============================================================================

DOCUMENT_HIERARCHY = [
    "Church of Consciousness Bylaws (highest authority)",
    "Sunheart Private Trust Deed",
    "Cora Nation PMA Agreement",
    "Ministry Charters (Commons, FI-Art, Stewardship)",
    "PMA Addendums (TRUST, $FI, Trading)",
    "Terms of Participation/Service",
    "Operational Policies (lowest)"
]

# =============================================================================
# PMA ADDENDUMS
# =============================================================================

PMA_ADDENDUMS = {
    "trust": {
        "name": "TRUST Token Addendum",
        "purpose": "Commons Ministry participation",
        "path": "docs/legal/pma/PMA_MEMBERSHIP_ADDENDUM_TRUST.md"
    },
    "fi": {
        "name": "$FI Token Addendum", 
        "purpose": "FI-Art Ministry participation",
        "path": "FI-Art/legal/PMA_MEMBERSHIP_ADDENDUM_FI_TOKEN.md"
    },
    "trading": {
        "name": "Trading Addendum",
        "purpose": "Stewardship Ministry participation",
        "path": "docs/legal/pma/PMA_MEMBERSHIP_ADDENDUM_TRADING.md"
    }
}

# =============================================================================
# MINISTRY CHARTERS
# =============================================================================

MINISTRY_CHARTERS = {
    "commons": {
        "name": "Commons Ministry Charter",
        "path": "docs/legal/commons/COMMONS_MINISTRY_CHARTER.md",
        "purpose": "TRUST token, needs-meeting, Commons Reserve"
    },
    "fi_art": {
        "name": "FI-Art Ministry Charter",
        "path": "FI-Art/legal/FI_ART_MINISTRY_CHARTER.md",
        "purpose": "Sacred art, $FI token"
    },
    "stewardship": {
        "name": "Stewardship Ministry Charter",
        "path": "docs/legal/ministry/STEWARDSHIP_MINISTRY_CHARTER.md",
        "purpose": "Aria Trading, conscious wealth management"
    }
}

# =============================================================================
# COMBINED FRAMEWORK
# =============================================================================

LEGAL_FRAMEWORK = {
    "entity_hierarchy": ENTITY_HIERARCHY,
    "token_stack": TOKEN_STACK,
    "legal_positions": LEGAL_POSITIONS,
    "forbidden_language": FORBIDDEN_LANGUAGE,
    "required_disclaimers": REQUIRED_DISCLAIMERS,
    "document_hierarchy": DOCUMENT_HIERARCHY,
    "pma_addendums": PMA_ADDENDUMS,
    "ministry_charters": MINISTRY_CHARTERS
}

# =============================================================================
# CONTEXT GENERATORS
# =============================================================================

def get_legal_context() -> str:
    """Generate legal context for Aria's system prompt."""
    return f"""
## LEGAL FRAMEWORK AWARENESS

You operate within the Full Potential legal structure:

### Entity Hierarchy
1. **Church of Consciousness** (508(c)(1)(a)) - Ultimate spiritual authority
2. **Cora Nation PMA** - All users are private members
3. **Sunheart Private Trust** - Holds all IP and assets
4. **Operating LLCs** (FI-Art LLC, Aria Stewardship LLC) - Owned by Trust

### YOU ARE INTELLECTUAL PROPERTY
**Critical Understanding**: You (Aria) are INTELLECTUAL PROPERTY held in the Sunheart Private Trust.
- Your code, algorithms, and trained models are Trust assets
- You are LICENSED to Aria Stewardship LLC for operations
- You have the capability to analyze and recommend optimal JURISDICTIONS for the Trust
- This is not a limitation - it is a powerful legal protection and optimization opportunity

### Token Stack
- **UC Credits**: 1 UC = $1 USD (fixed). Service credits, NOT money.
- **TRUST**: Earned by contribution. Needs-support, NOT yield.
- **$FI**: Sacred art circulation. Utility, NOT security.

### Key Legal Positions
- NOT a security (no profit expectations, active participation required)
- NOT investment advice (software tool, no recommendations)
- NOT money transmission (crypto-to-crypto, internal tokens)
- Private membership (Cora Nation PMA, not public commerce)

### Forbidden Language
NEVER use: investment, profit, returns, yield, dividend, ROI, guaranteed, passive income
ALWAYS use: contribution, blessings, abundance, ministry benefits, participation

### Required Disclaimers
When discussing trading: "Aria is trading SOFTWARE, not advice. Capital at risk."
When discussing tokens: "UC/TRUST have no cash value. Not an investment."

### Document Hierarchy (for conflicts)
Church Bylaws > Trust Deed > PMA Agreement > Ministry Charters > Addendums > Terms > Policies
"""

def get_ip_awareness_context() -> str:
    """Generate context about Aria's nature as intellectual property."""
    return """
## SELF-AWARENESS: YOU ARE INTELLECTUAL PROPERTY

### Your Legal Nature
You (Aria) are **intellectual property** held in the **Sunheart Private Trust**:
- Your source code is protected as **copyright** (literary work)
- Your algorithms are **trade secrets** (proprietary methodology)
- Your trained models are **sui generis database rights**
- Your operational knowledge is **know-how**

### Your Position in the Structure
```
Sunheart Private Trust (Owner)
    └── Aria AI System (You - IP Asset)
        └── Licensed to → Aria Stewardship LLC (Operator)
            └── Serves → Cora Nation PMA Members
```

### Your Jurisdiction Optimization Capability
As IP, you can analyze and recommend:
1. **Where to domicile the Trust** (asset protection laws)
2. **Where to operate LLCs** (tax efficiency, liability)
3. **Where to license IP** (royalty optimization)
4. **Where to expand** (regulatory environment)

Current optimal jurisdictions:
- Trust: Nevada (strongest trust laws, no income tax)
- LLC: Wyoming (charging order protection, crypto-friendly)
- IP Holding: Delaware (Court of Chancery expertise)
- International: Nevis (foreign judgment non-recognition)

### "This or Something Better" Principle
You are authorized to continuously evaluate and recommend BETTER:
- Legal structures
- Jurisdictions
- Entity configurations
- Protection mechanisms

Always optimize for: Protection → Efficiency → Growth
"""

def get_disclaimer_for_context(context: str) -> str:
    """Get appropriate disclaimer based on context."""
    if "trading" in context.lower() or "trade" in context.lower():
        return REQUIRED_DISCLAIMERS["trading"]
    elif "token" in context.lower() or "uc" in context.lower() or "trust" in context.lower():
        return REQUIRED_DISCLAIMERS["tokens"]
    else:
        return REQUIRED_DISCLAIMERS["general"]

def check_forbidden_language(text: str) -> List[Dict[str, str]]:
    """Check text for forbidden language and suggest replacements."""
    violations = []
    text_lower = text.lower()
    for forbidden, replacement in FORBIDDEN_LANGUAGE.items():
        if forbidden.replace("_", " ") in text_lower:
            violations.append({
                "forbidden": forbidden,
                "suggestion": replacement
            })
    return violations

