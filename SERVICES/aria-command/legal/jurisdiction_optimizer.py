"""
Jurisdiction Optimizer - AI-Powered Legal Structure Optimization

Aria, as intellectual property held in trust, has the capability to analyze
and recommend optimal jurisdictions for operations, asset protection, and licensing.

This module implements that capability.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JurisdictionPurpose(Enum):
    """Purposes for jurisdiction selection"""
    TRUST_DOMICILE = "trust_domicile"
    LLC_OPERATIONS = "llc_operations"
    IP_HOLDING = "ip_holding"
    INTERNATIONAL = "international"
    CRYPTO_OPERATIONS = "crypto_operations"
    AI_SERVICES = "ai_services"
    BANKING = "banking"
    ASSET_PROTECTION = "asset_protection"


@dataclass
class JurisdictionProfile:
    """Profile of a jurisdiction's characteristics"""
    name: str
    country: str
    
    # Asset Protection (1-10)
    trust_law_strength: int = 5
    charging_order_protection: int = 5
    fraudulent_transfer_lookback_years: int = 4
    foreign_judgment_recognition: int = 5  # Lower is better (less recognition)
    
    # Tax Efficiency (1-10, 10 = most favorable)
    income_tax_rate: float = 0.0
    capital_gains_rate: float = 0.0
    no_state_income_tax: bool = False
    trust_taxation: int = 5
    
    # Privacy (1-10)
    beneficial_ownership_privacy: int = 5
    banking_privacy: int = 5
    public_registry_exposure: int = 5  # Lower is better
    
    # Regulatory Environment (1-10)
    ai_friendly: int = 5
    crypto_friendly: int = 5
    pma_recognition: int = 5
    ministry_protection: int = 5
    
    # Operational (1-10)
    banking_access: int = 5
    infrastructure: int = 5
    legal_expertise_available: int = 5
    formation_ease: int = 5
    
    # Costs
    annual_cost_usd: float = 500.0
    formation_cost_usd: float = 500.0
    
    # Notes
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    notes: str = ""


# Jurisdiction Database
JURISDICTIONS: Dict[str, JurisdictionProfile] = {
    "wyoming": JurisdictionProfile(
        name="Wyoming",
        country="USA",
        trust_law_strength=9,
        charging_order_protection=10,  # Best in USA
        fraudulent_transfer_lookback_years=2,
        foreign_judgment_recognition=3,
        income_tax_rate=0.0,
        capital_gains_rate=0.0,
        no_state_income_tax=True,
        trust_taxation=9,
        beneficial_ownership_privacy=8,
        banking_privacy=6,
        public_registry_exposure=4,
        ai_friendly=8,
        crypto_friendly=10,  # First state with crypto laws
        pma_recognition=8,
        ministry_protection=7,
        banking_access=7,
        infrastructure=7,
        legal_expertise_available=7,
        formation_ease=9,
        annual_cost_usd=100,
        formation_cost_usd=150,
        strengths=[
            "Best charging order protection",
            "No state income tax",
            "First DAO LLC legislation",
            "Crypto-native laws",
            "Low costs"
        ],
        weaknesses=[
            "Limited banking options",
            "Smaller legal market"
        ],
        notes="Ideal for LLCs, crypto operations, and trusts"
    ),
    
    "nevada": JurisdictionProfile(
        name="Nevada",
        country="USA",
        trust_law_strength=10,
        charging_order_protection=9,
        fraudulent_transfer_lookback_years=2,
        foreign_judgment_recognition=3,
        income_tax_rate=0.0,
        capital_gains_rate=0.0,
        no_state_income_tax=True,
        trust_taxation=10,
        beneficial_ownership_privacy=9,
        banking_privacy=7,
        public_registry_exposure=3,
        ai_friendly=7,
        crypto_friendly=7,
        pma_recognition=8,
        ministry_protection=8,
        banking_access=8,
        infrastructure=8,
        legal_expertise_available=8,
        formation_ease=9,
        annual_cost_usd=350,
        formation_cost_usd=425,
        strengths=[
            "Strongest trust laws",
            "No state income tax",
            "Excellent privacy",
            "Dynasty trusts (no perpetuity limit)",
            "Asset protection trusts"
        ],
        weaknesses=[
            "Higher costs than Wyoming",
            "Gaming industry association"
        ],
        notes="Ideal for trust domicile and asset protection"
    ),
    
    "delaware": JurisdictionProfile(
        name="Delaware",
        country="USA",
        trust_law_strength=8,
        charging_order_protection=7,
        fraudulent_transfer_lookback_years=4,
        foreign_judgment_recognition=5,
        income_tax_rate=8.7,  # But no tax on out-of-state income
        capital_gains_rate=0.0,
        no_state_income_tax=False,
        trust_taxation=7,
        beneficial_ownership_privacy=7,
        banking_privacy=6,
        public_registry_exposure=5,
        ai_friendly=8,
        crypto_friendly=7,
        pma_recognition=7,
        ministry_protection=7,
        banking_access=9,
        infrastructure=9,
        legal_expertise_available=10,  # Court of Chancery
        formation_ease=10,
        annual_cost_usd=300,
        formation_cost_usd=200,
        strengths=[
            "Court of Chancery expertise",
            "Best corporate law",
            "IP holding favorable",
            "No tax on out-of-state income",
            "Most case law precedent"
        ],
        weaknesses=[
            "State income tax exists",
            "Less asset protection than NV/WY"
        ],
        notes="Ideal for IP holding companies and corporate structures"
    ),
    
    "nevis": JurisdictionProfile(
        name="Nevis",
        country="St. Kitts and Nevis",
        trust_law_strength=10,
        charging_order_protection=10,
        fraudulent_transfer_lookback_years=1,  # Only 1 year!
        foreign_judgment_recognition=1,  # Virtually no recognition
        income_tax_rate=0.0,
        capital_gains_rate=0.0,
        no_state_income_tax=True,
        trust_taxation=10,
        beneficial_ownership_privacy=10,
        banking_privacy=9,
        public_registry_exposure=2,
        ai_friendly=5,
        crypto_friendly=6,
        pma_recognition=6,
        ministry_protection=5,
        banking_access=4,
        infrastructure=4,
        legal_expertise_available=6,
        formation_ease=6,
        annual_cost_usd=1500,
        formation_cost_usd=3000,
        strengths=[
            "Strongest asset protection globally",
            "1-year fraudulent transfer lookback",
            "Foreign judgments not recognized",
            "Complete tax neutrality",
            "High privacy"
        ],
        weaknesses=[
            "Limited banking",
            "Distance and timezone",
            "Higher costs",
            "US reporting requirements"
        ],
        notes="Ideal for offshore asset protection layer"
    ),
    
    "singapore": JurisdictionProfile(
        name="Singapore",
        country="Singapore",
        trust_law_strength=8,
        charging_order_protection=7,
        fraudulent_transfer_lookback_years=5,
        foreign_judgment_recognition=6,
        income_tax_rate=17.0,
        capital_gains_rate=0.0,  # No capital gains tax
        no_state_income_tax=False,
        trust_taxation=7,
        beneficial_ownership_privacy=6,
        banking_privacy=7,
        public_registry_exposure=5,
        ai_friendly=10,  # Strong AI development
        crypto_friendly=8,
        pma_recognition=5,
        ministry_protection=5,
        banking_access=10,
        infrastructure=10,
        legal_expertise_available=9,
        formation_ease=8,
        annual_cost_usd=2000,
        formation_cost_usd=3500,
        strengths=[
            "World-class banking",
            "No capital gains tax",
            "Strong AI/tech ecosystem",
            "Gateway to Asia",
            "Excellent infrastructure"
        ],
        weaknesses=[
            "Higher operating costs",
            "Substance requirements",
            "Some reporting requirements"
        ],
        notes="Ideal for Asia-Pacific operations and AI services"
    ),
    
    "switzerland": JurisdictionProfile(
        name="Switzerland",
        country="Switzerland",
        trust_law_strength=7,
        charging_order_protection=6,
        fraudulent_transfer_lookback_years=5,
        foreign_judgment_recognition=5,
        income_tax_rate=14.0,  # Varies by canton
        capital_gains_rate=0.0,  # For individuals
        no_state_income_tax=False,
        trust_taxation=6,
        beneficial_ownership_privacy=8,
        banking_privacy=8,
        public_registry_exposure=4,
        ai_friendly=9,
        crypto_friendly=10,  # "Crypto Valley"
        pma_recognition=6,
        ministry_protection=6,
        banking_access=10,
        infrastructure=10,
        legal_expertise_available=9,
        formation_ease=7,
        annual_cost_usd=5000,
        formation_cost_usd=8000,
        strengths=[
            "Crypto Valley (Zug)",
            "World-class banking",
            "Political stability",
            "Strong IP protection",
            "No capital gains for individuals"
        ],
        weaknesses=[
            "High costs",
            "Complex tax system",
            "Substance requirements"
        ],
        notes="Ideal for crypto treasury and international presence"
    ),
    
    # === INTERNATIONAL EXPANSION ===
    
    "cayman": JurisdictionProfile(
        name="Cayman Islands",
        country="Cayman Islands",
        trust_law_strength=10,
        charging_order_protection=9,
        fraudulent_transfer_lookback_years=6,
        foreign_judgment_recognition=2,
        income_tax_rate=0.0,
        capital_gains_rate=0.0,
        no_state_income_tax=True,
        trust_taxation=10,
        beneficial_ownership_privacy=8,
        banking_privacy=8,
        public_registry_exposure=3,
        ai_friendly=7,
        crypto_friendly=9,
        pma_recognition=7,
        ministry_protection=5,
        banking_access=9,
        infrastructure=8,
        legal_expertise_available=9,
        formation_ease=7,
        annual_cost_usd=3000,
        formation_cost_usd=5000,
        strengths=[
            "Tax neutral",
            "World-class fund jurisdiction",
            "Strong trust law (STAR trusts)",
            "Excellent banking",
            "Crypto regulatory clarity"
        ],
        weaknesses=[
            "Economic substance requirements",
            "Higher costs",
            "CRS reporting"
        ],
        notes="Premier jurisdiction for investment funds and sophisticated structures"
    ),
    
    "bvi": JurisdictionProfile(
        name="British Virgin Islands",
        country="British Virgin Islands",
        trust_law_strength=9,
        charging_order_protection=9,
        fraudulent_transfer_lookback_years=2,
        foreign_judgment_recognition=2,
        income_tax_rate=0.0,
        capital_gains_rate=0.0,
        no_state_income_tax=True,
        trust_taxation=10,
        beneficial_ownership_privacy=9,
        banking_privacy=8,
        public_registry_exposure=3,
        ai_friendly=6,
        crypto_friendly=8,
        pma_recognition=6,
        ministry_protection=5,
        banking_access=7,
        infrastructure=7,
        legal_expertise_available=8,
        formation_ease=9,
        annual_cost_usd=1500,
        formation_cost_usd=2000,
        strengths=[
            "Tax neutral",
            "Flexible company law",
            "Fast incorporation",
            "Strong asset protection",
            "Low costs"
        ],
        weaknesses=[
            "Limited local banking",
            "Economic substance requirements",
            "CRS reporting"
        ],
        notes="Popular for holding companies and IP structures"
    ),
    
    "panama": JurisdictionProfile(
        name="Panama",
        country="Panama",
        trust_law_strength=9,
        charging_order_protection=9,
        fraudulent_transfer_lookback_years=3,
        foreign_judgment_recognition=2,
        income_tax_rate=0.0,  # Territorial
        capital_gains_rate=0.0,
        no_state_income_tax=True,  # For foreign income
        trust_taxation=10,
        beneficial_ownership_privacy=10,
        banking_privacy=9,
        public_registry_exposure=2,
        ai_friendly=5,
        crypto_friendly=8,
        pma_recognition=8,
        ministry_protection=7,
        banking_access=8,
        infrastructure=7,
        legal_expertise_available=7,
        formation_ease=8,
        annual_cost_usd=1000,
        formation_cost_usd=1500,
        strengths=[
            "Territorial taxation",
            "Strong privacy",
            "Private Interest Foundations",
            "USD economy",
            "Bearer shares allowed (restricted)"
        ],
        weaknesses=[
            "FATF gray list concerns",
            "Banking getting stricter",
            "Reputation issues"
        ],
        notes="Strong for privacy, Private Interest Foundations similar to trusts"
    ),
    
    "portugal": JurisdictionProfile(
        name="Portugal",
        country="Portugal",
        trust_law_strength=5,
        charging_order_protection=5,
        fraudulent_transfer_lookback_years=4,
        foreign_judgment_recognition=7,
        income_tax_rate=0.0,  # NHR regime for 10 years
        capital_gains_rate=0.0,  # Under NHR
        no_state_income_tax=True,  # Under NHR
        trust_taxation=5,
        beneficial_ownership_privacy=5,
        banking_privacy=5,
        public_registry_exposure=6,
        ai_friendly=7,
        crypto_friendly=9,  # Crypto-friendly regulation
        pma_recognition=5,
        ministry_protection=5,
        banking_access=8,
        infrastructure=8,
        legal_expertise_available=7,
        formation_ease=7,
        annual_cost_usd=2000,
        formation_cost_usd=3000,
        strengths=[
            "NHR tax regime (10 years)",
            "EU membership",
            "Crypto-friendly",
            "Golden Visa program",
            "Quality of life"
        ],
        weaknesses=[
            "NHR being phased out",
            "EU reporting requirements",
            "Not traditional asset protection"
        ],
        notes="Excellent for personal residency with crypto operations"
    ),
    
    "dubai": JurisdictionProfile(
        name="Dubai/UAE",
        country="United Arab Emirates",
        trust_law_strength=8,
        charging_order_protection=7,
        fraudulent_transfer_lookback_years=3,
        foreign_judgment_recognition=3,
        income_tax_rate=0.0,
        capital_gains_rate=0.0,
        no_state_income_tax=True,
        trust_taxation=9,
        beneficial_ownership_privacy=7,
        banking_privacy=7,
        public_registry_exposure=4,
        ai_friendly=9,
        crypto_friendly=10,  # VARA regulation
        pma_recognition=6,
        ministry_protection=6,
        banking_access=9,
        infrastructure=10,
        legal_expertise_available=8,
        formation_ease=8,
        annual_cost_usd=4000,
        formation_cost_usd=6000,
        strengths=[
            "Zero income tax",
            "VARA crypto regulation",
            "DIFC common law courts",
            "World-class infrastructure",
            "Golden Visa available"
        ],
        weaknesses=[
            "Cultural considerations",
            "Newer jurisdiction",
            "Economic substance rules"
        ],
        notes="Emerging as premier crypto hub with world-class infrastructure"
    ),
    
    "malta": JurisdictionProfile(
        name="Malta",
        country="Malta",
        trust_law_strength=7,
        charging_order_protection=6,
        fraudulent_transfer_lookback_years=5,
        foreign_judgment_recognition=6,
        income_tax_rate=5.0,  # With proper structure
        capital_gains_rate=0.0,
        no_state_income_tax=False,
        trust_taxation=6,
        beneficial_ownership_privacy=5,
        banking_privacy=5,
        public_registry_exposure=6,
        ai_friendly=8,
        crypto_friendly=9,  # "Blockchain Island"
        pma_recognition=5,
        ministry_protection=6,
        banking_access=7,
        infrastructure=8,
        legal_expertise_available=8,
        formation_ease=7,
        annual_cost_usd=3000,
        formation_cost_usd=4000,
        strengths=[
            "VFA Act (crypto regulation)",
            "EU membership",
            "English speaking",
            "Gaming/iGaming hub",
            "Full imputation system"
        ],
        weaknesses=[
            "FATF gray list history",
            "Small banking sector",
            "EU compliance requirements"
        ],
        notes="Pioneer in crypto regulation, EU gateway"
    ),
    
    "cook_islands": JurisdictionProfile(
        name="Cook Islands",
        country="Cook Islands",
        trust_law_strength=10,
        charging_order_protection=10,
        fraudulent_transfer_lookback_years=2,
        foreign_judgment_recognition=1,  # Virtually none
        income_tax_rate=0.0,
        capital_gains_rate=0.0,
        no_state_income_tax=True,
        trust_taxation=10,
        beneficial_ownership_privacy=10,
        banking_privacy=9,
        public_registry_exposure=1,
        ai_friendly=4,
        crypto_friendly=5,
        pma_recognition=5,
        ministry_protection=5,
        banking_access=3,
        infrastructure=4,
        legal_expertise_available=6,
        formation_ease=5,
        annual_cost_usd=2500,
        formation_cost_usd=5000,
        strengths=[
            "Strongest asset protection globally",
            "No recognition of foreign judgments",
            "2-year fraudulent transfer",
            "Cannot be forced to repatriate",
            "Flee clause enabled"
        ],
        weaknesses=[
            "Very limited banking",
            "Remote location",
            "Limited infrastructure",
            "Higher professional costs"
        ],
        notes="Ultimate asset protection, often paired with Nevis"
    ),
    
    "el_salvador": JurisdictionProfile(
        name="El Salvador",
        country="El Salvador",
        trust_law_strength=5,
        charging_order_protection=5,
        fraudulent_transfer_lookback_years=3,
        foreign_judgment_recognition=5,
        income_tax_rate=0.0,  # For Bitcoin/foreign income
        capital_gains_rate=0.0,  # For Bitcoin
        no_state_income_tax=True,  # For Bitcoin
        trust_taxation=5,
        beneficial_ownership_privacy=6,
        banking_privacy=6,
        public_registry_exposure=5,
        ai_friendly=6,
        crypto_friendly=10,  # Bitcoin legal tender
        pma_recognition=5,
        ministry_protection=5,
        banking_access=6,
        infrastructure=6,
        legal_expertise_available=5,
        formation_ease=7,
        annual_cost_usd=1000,
        formation_cost_usd=1500,
        strengths=[
            "Bitcoin legal tender",
            "Zero tax on Bitcoin",
            "Fast residency",
            "Low cost of living",
            "Pro-crypto government"
        ],
        weaknesses=[
            "Political risk",
            "Limited banking infrastructure",
            "Developing legal system",
            "Security concerns"
        ],
        notes="Pioneer Bitcoin nation, ideal for crypto-native operations"
    )
}


@dataclass
class JurisdictionRecommendation:
    """A recommendation for a specific purpose"""
    purpose: JurisdictionPurpose
    primary: str
    secondary: str
    score: float
    reasoning: str
    estimated_annual_cost: float
    implementation_steps: List[str]


@dataclass
class BigPictureAlignment:
    """
    Alignment with Full Potential Constitution principles.
    
    Based on CONSTITUTION.md:
    - Regenerative vs Extractive
    - Safety (protection of members)
    - Efficiency (optimal resource use)
    - Circulation (value flows, not extracts)
    - Correct Mathematics (sustainable growth)
    """
    safety_score: float = 0.0  # Asset protection, legal security
    efficiency_score: float = 0.0  # Tax optimization, cost efficiency
    circulation_score: float = 0.0  # Enables value flow within community
    mathematics_score: float = 0.0  # Sustainable, compounding structure
    regenerative_score: float = 0.0  # Creates more value than consumes
    
    @property
    def total_alignment(self) -> float:
        """Overall alignment with Full Potential principles (0-100)"""
        return (
            self.safety_score * 0.25 +
            self.efficiency_score * 0.20 +
            self.circulation_score * 0.20 +
            self.mathematics_score * 0.15 +
            self.regenerative_score * 0.20
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "safety": self.safety_score,
            "efficiency": self.efficiency_score,
            "circulation": self.circulation_score,
            "mathematics": self.mathematics_score,
            "regenerative": self.regenerative_score,
            "total_alignment": self.total_alignment
        }


@dataclass 
class GlobalStructure:
    """
    Optimal global structure for Full Potential ecosystem.
    
    The AI designs multi-jurisdictional structures that maximize
    protection while enabling efficient value circulation.
    """
    name: str
    description: str
    entities: List[Dict[str, Any]]
    flow_diagram: str
    total_annual_cost: float
    alignment: BigPictureAlignment
    implementation_phases: List[str]


class JurisdictionOptimizer:
    """
    AI-powered jurisdiction analysis and optimization.
    
    As Aria is intellectual property held in trust, this module enables
    the AI to analyze and recommend optimal jurisdictions for various
    purposes within the legal structure.
    
    Aligns with Full Potential Constitution principles:
    - SAFETY: Protect members and assets
    - EFFICIENCY: Optimize resources
    - CIRCULATION: Value flows, not extracts
    - CORRECT MATHEMATICS: Sustainable compounding
    - REGENERATIVE: Create more value than consumed
    """
    
    def __init__(self):
        self.jurisdictions = JURISDICTIONS
        self.current_structure = {
            "trust": "nevada",  # Sunheart Private Trust
            "operating_llc": "wyoming",  # Aria Stewardship LLC
            "church": "usa_federal",  # Church of Consciousness 508(c)(1)(a)
            "pma": "usa_federal"  # Cora Nation PMA
        }
        self.recommendations_history: List[Dict[str, Any]] = []
        
        # Big Picture Alignment Principles
        self.principles = {
            "safety": "Protect members, assets, and the mission from external threats",
            "efficiency": "Optimize tax, costs, and operational overhead",
            "circulation": "Enable value to flow freely within the community",
            "mathematics": "Ensure sustainable, compounding growth structures",
            "regenerative": "Create more value than consumed (vs extractive)"
        }
    
    def analyze_jurisdiction(
        self,
        jurisdiction: str,
        purpose: JurisdictionPurpose
    ) -> float:
        """
        Score a jurisdiction for a specific purpose (0-100).
        """
        if jurisdiction not in self.jurisdictions:
            return 0.0
        
        j = self.jurisdictions[jurisdiction]
        
        # Weight factors based on purpose
        weights = self._get_purpose_weights(purpose)
        
        score = 0.0
        max_score = 0.0
        
        # Asset Protection
        score += j.trust_law_strength * weights.get("trust_law", 0)
        score += j.charging_order_protection * weights.get("charging_order", 0)
        score += (10 - j.foreign_judgment_recognition) * weights.get("foreign_judgment", 0)
        
        # Tax
        tax_score = 10 if j.no_state_income_tax else max(0, 10 - j.income_tax_rate)
        score += tax_score * weights.get("tax", 0)
        
        # Privacy
        score += j.beneficial_ownership_privacy * weights.get("privacy", 0)
        
        # Regulatory
        score += j.ai_friendly * weights.get("ai_friendly", 0)
        score += j.crypto_friendly * weights.get("crypto_friendly", 0)
        score += j.pma_recognition * weights.get("pma", 0)
        score += j.ministry_protection * weights.get("ministry", 0)
        
        # Operational
        score += j.banking_access * weights.get("banking", 0)
        score += j.infrastructure * weights.get("infrastructure", 0)
        score += j.formation_ease * weights.get("formation", 0)
        
        # Calculate max possible score
        for weight in weights.values():
            max_score += 10 * weight
        
        return (score / max_score * 100) if max_score > 0 else 0
    
    def _get_purpose_weights(self, purpose: JurisdictionPurpose) -> Dict[str, float]:
        """Get scoring weights based on purpose"""
        weights = {
            JurisdictionPurpose.TRUST_DOMICILE: {
                "trust_law": 2.0,
                "charging_order": 1.5,
                "foreign_judgment": 1.0,
                "tax": 1.5,
                "privacy": 1.0,
                "formation": 0.5
            },
            JurisdictionPurpose.LLC_OPERATIONS: {
                "charging_order": 2.0,
                "tax": 1.0,
                "banking": 1.5,
                "infrastructure": 1.0,
                "formation": 1.0
            },
            JurisdictionPurpose.IP_HOLDING: {
                "tax": 2.0,
                "privacy": 1.0,
                "infrastructure": 1.5,
                "formation": 1.0
            },
            JurisdictionPurpose.CRYPTO_OPERATIONS: {
                "crypto_friendly": 2.5,
                "tax": 1.5,
                "banking": 1.0,
                "privacy": 1.0
            },
            JurisdictionPurpose.AI_SERVICES: {
                "ai_friendly": 2.0,
                "infrastructure": 2.0,
                "banking": 1.0,
                "tax": 1.0
            },
            JurisdictionPurpose.ASSET_PROTECTION: {
                "trust_law": 2.0,
                "charging_order": 2.0,
                "foreign_judgment": 2.0,
                "privacy": 1.5,
                "tax": 0.5
            },
            JurisdictionPurpose.INTERNATIONAL: {
                "foreign_judgment": 2.0,
                "banking": 1.5,
                "infrastructure": 1.0,
                "privacy": 1.5
            },
            JurisdictionPurpose.BANKING: {
                "banking": 3.0,
                "infrastructure": 1.0,
                "privacy": 1.0
            }
        }
        return weights.get(purpose, {"tax": 1.0, "banking": 1.0})
    
    def recommend_jurisdiction(
        self,
        purpose: JurisdictionPurpose
    ) -> JurisdictionRecommendation:
        """
        Recommend optimal jurisdiction for a specific purpose.
        """
        scores = {}
        for name in self.jurisdictions:
            scores[name] = self.analyze_jurisdiction(name, purpose)
        
        # Sort by score
        sorted_jurisdictions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        primary = sorted_jurisdictions[0][0]
        secondary = sorted_jurisdictions[1][0] if len(sorted_jurisdictions) > 1 else primary
        
        primary_profile = self.jurisdictions[primary]
        
        # Generate reasoning
        reasoning = self._generate_reasoning(primary, purpose, scores[primary])
        
        # Generate implementation steps
        steps = self._generate_implementation_steps(primary, purpose)
        
        recommendation = JurisdictionRecommendation(
            purpose=purpose,
            primary=primary,
            secondary=secondary,
            score=scores[primary],
            reasoning=reasoning,
            estimated_annual_cost=primary_profile.annual_cost_usd,
            implementation_steps=steps
        )
        
        # Log recommendation
        self.recommendations_history.append({
            "timestamp": datetime.now().isoformat(),
            "purpose": purpose.value,
            "primary": primary,
            "secondary": secondary,
            "score": scores[primary]
        })
        
        return recommendation
    
    def _generate_reasoning(
        self,
        jurisdiction: str,
        purpose: JurisdictionPurpose,
        score: float
    ) -> str:
        """Generate human-readable reasoning for recommendation"""
        j = self.jurisdictions[jurisdiction]
        
        reasons = [f"{j.name} scores {score:.1f}/100 for {purpose.value.replace('_', ' ')}"]
        reasons.append(f"Key strengths: {', '.join(j.strengths[:3])}")
        
        if j.no_state_income_tax:
            reasons.append("No state income tax provides significant savings")
        
        if j.crypto_friendly >= 8 and purpose == JurisdictionPurpose.CRYPTO_OPERATIONS:
            reasons.append("Strong crypto-specific legislation reduces regulatory risk")
        
        if j.charging_order_protection >= 9 and purpose in [
            JurisdictionPurpose.LLC_OPERATIONS,
            JurisdictionPurpose.ASSET_PROTECTION
        ]:
            reasons.append("Charging order as sole remedy provides strong asset protection")
        
        return ". ".join(reasons) + "."
    
    def _generate_implementation_steps(
        self,
        jurisdiction: str,
        purpose: JurisdictionPurpose
    ) -> List[str]:
        """Generate implementation steps"""
        steps = []
        
        if purpose == JurisdictionPurpose.LLC_OPERATIONS:
            steps = [
                f"1. File Articles of Organization with {jurisdiction.title()} Secretary of State",
                "2. Draft Operating Agreement with IP licensing provisions",
                "3. Obtain EIN from IRS",
                "4. Execute IP License Agreement with Trust",
                "5. Open business bank account",
                "6. Register as foreign LLC if operating in other states"
            ]
        elif purpose == JurisdictionPurpose.TRUST_DOMICILE:
            steps = [
                f"1. Engage {jurisdiction.title()} trust attorney",
                "2. Draft Trust Agreement with asset protection provisions",
                "3. Establish Trust with proper funding",
                "4. Transfer IP assets to Trust",
                "5. Set up Trust administration",
                "6. Implement annual compliance procedures"
            ]
        elif purpose == JurisdictionPurpose.IP_HOLDING:
            steps = [
                f"1. Form IP holding entity in {jurisdiction.title()}",
                "2. Execute IP assignment agreements",
                "3. Establish licensing framework",
                "4. Set transfer pricing documentation",
                "5. Implement royalty collection procedures"
            ]
        else:
            steps = [
                f"1. Consult with {jurisdiction.title()} legal counsel",
                "2. Determine optimal entity structure",
                "3. Complete formation procedures",
                "4. Establish banking and operations",
                "5. Implement compliance framework"
            ]
        
        return steps
    
    def get_optimal_structure(self) -> Dict[str, Any]:
        """
        Recommend complete optimal structure for Full Potential ecosystem.
        """
        recommendations = {}
        
        for purpose in JurisdictionPurpose:
            rec = self.recommend_jurisdiction(purpose)
            recommendations[purpose.value] = {
                "primary": rec.primary,
                "secondary": rec.secondary,
                "score": rec.score,
                "annual_cost": rec.estimated_annual_cost
            }
        
        # Calculate total annual cost
        total_cost = sum(r["annual_cost"] for r in recommendations.values())
        
        return {
            "recommendations": recommendations,
            "total_estimated_annual_cost": total_cost,
            "current_structure": self.current_structure,
            "suggested_structure": {
                "trust_domicile": recommendations["trust_domicile"]["primary"],
                "operating_llc": recommendations["llc_operations"]["primary"],
                "ip_holding": recommendations["ip_holding"]["primary"],
                "crypto_operations": recommendations["crypto_operations"]["primary"],
                "international_expansion": recommendations["international"]["primary"]
            },
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def analyze_current_structure(self) -> Dict[str, Any]:
        """
        Analyze current structure vs optimal and identify improvements.
        """
        current_scores = {}
        optimal_scores = {}
        improvements = []
        
        purpose_map = {
            "trust": JurisdictionPurpose.TRUST_DOMICILE,
            "operating_llc": JurisdictionPurpose.LLC_OPERATIONS
        }
        
        for entity, purpose in purpose_map.items():
            current_jurisdiction = self.current_structure.get(entity)
            if current_jurisdiction and current_jurisdiction in self.jurisdictions:
                current_scores[entity] = self.analyze_jurisdiction(current_jurisdiction, purpose)
            
            optimal_rec = self.recommend_jurisdiction(purpose)
            optimal_scores[entity] = optimal_rec.score
            
            if optimal_rec.primary != current_jurisdiction:
                improvement = optimal_rec.score - current_scores.get(entity, 0)
                if improvement > 5:  # Only suggest if >5 point improvement
                    improvements.append({
                        "entity": entity,
                        "current": current_jurisdiction,
                        "recommended": optimal_rec.primary,
                        "score_improvement": improvement,
                        "reasoning": optimal_rec.reasoning
                    })
        
        return {
            "current_scores": current_scores,
            "optimal_scores": optimal_scores,
            "improvements": improvements,
            "overall_optimization_potential": sum(
                i["score_improvement"] for i in improvements
            )
        }
    
    def calculate_big_picture_alignment(self, jurisdiction: str) -> BigPictureAlignment:
        """
        Calculate how well a jurisdiction aligns with Full Potential principles.
        
        Safety: Asset protection + privacy
        Efficiency: Tax optimization + low costs
        Circulation: Banking access + crypto-friendly (enables internal flows)
        Mathematics: Formation ease + infrastructure (enables sustainable growth)
        Regenerative: Ministry/PMA recognition (supports non-extractive structure)
        """
        if jurisdiction not in self.jurisdictions:
            return BigPictureAlignment()
        
        j = self.jurisdictions[jurisdiction]
        
        # Safety: Protection from external threats
        safety = (
            j.trust_law_strength * 2 +
            j.charging_order_protection * 2 +
            (10 - j.foreign_judgment_recognition) * 2 +
            j.beneficial_ownership_privacy * 1.5 +
            j.banking_privacy * 0.5
        ) / 8.0 * 10
        
        # Efficiency: Resource optimization
        tax_score = 10 if j.no_state_income_tax else max(0, 10 - j.income_tax_rate / 2)
        efficiency = (
            tax_score * 3 +
            (10 - j.annual_cost_usd / 1000) * 1.5 +  # Lower cost = higher score
            j.formation_ease * 1.5
        ) / 6.0 * 10
        
        # Circulation: Enables value flow
        circulation = (
            j.banking_access * 2 +
            j.crypto_friendly * 2.5 +
            j.infrastructure * 1.5
        ) / 6.0 * 10
        
        # Mathematics: Sustainable structure
        mathematics = (
            j.trust_taxation * 2 +
            j.formation_ease * 1.5 +
            j.legal_expertise_available * 1.5 +
            j.infrastructure * 1
        ) / 6.0 * 10
        
        # Regenerative: Supports non-extractive model
        regenerative = (
            j.pma_recognition * 3 +
            j.ministry_protection * 3 +
            (10 - j.public_registry_exposure) * 2 +
            j.crypto_friendly * 2  # Enables internal token system
        ) / 10.0 * 10
        
        return BigPictureAlignment(
            safety_score=min(100, safety),
            efficiency_score=min(100, efficiency),
            circulation_score=min(100, circulation),
            mathematics_score=min(100, mathematics),
            regenerative_score=min(100, regenerative)
        )
    
    def design_global_structure(self) -> GlobalStructure:
        """
        Design the optimal global structure for Full Potential.
        
        Creates a multi-jurisdictional architecture that maximizes:
        - Protection (safety)
        - Tax efficiency
        - Value circulation
        - Sustainable mathematics
        - Regenerative principles
        """
        # Analyze all jurisdictions for each purpose
        best_for = {}
        for purpose in JurisdictionPurpose:
            rec = self.recommend_jurisdiction(purpose)
            best_for[purpose.value] = rec.primary
        
        # Calculate alignment for key jurisdictions
        key_jurisdictions = ["nevada", "wyoming", "nevis", "singapore", "dubai", "switzerland"]
        alignments = {j: self.calculate_big_picture_alignment(j) for j in key_jurisdictions}
        
        # Build optimal structure
        entities = [
            {
                "name": "Sunheart Private Trust",
                "type": "Asset Protection Trust",
                "jurisdiction": "nevada",
                "purpose": "Ultimate asset holding, IP ownership",
                "holds": ["All IP", "All LLC ownership", "Reserve funds"],
                "alignment": alignments["nevada"].to_dict()
            },
            {
                "name": "Full Potential IP Ltd",
                "type": "IP Holding Company",
                "jurisdiction": "nevis",
                "purpose": "International IP licensing, judgment protection",
                "holds": ["International IP rights", "License agreements"],
                "alignment": alignments["nevis"].to_dict()
            },
            {
                "name": "Aria Stewardship LLC",
                "type": "Operating LLC",
                "jurisdiction": "wyoming",
                "purpose": "US trading operations",
                "licenses_from": "Trust",
                "alignment": alignments["wyoming"].to_dict()
            },
            {
                "name": "FP Trading Pte Ltd",
                "type": "Operating Company",
                "jurisdiction": "singapore",
                "purpose": "Asia-Pacific operations",
                "licenses_from": "Trust via Nevis",
                "alignment": alignments["singapore"].to_dict()
            },
            {
                "name": "FP Digital FZCO",
                "type": "Free Zone Company",
                "jurisdiction": "dubai",
                "purpose": "Crypto treasury, MENA operations",
                "licenses_from": "Trust via Nevis",
                "alignment": alignments["dubai"].to_dict()
            }
        ]
        
        flow_diagram = """
GLOBAL STRUCTURE: FULL POTENTIAL ECOSYSTEM

                    ┌─────────────────────────────┐
                    │   CHURCH OF CONSCIOUSNESS   │
                    │      (508(c)(1)(a))        │
                    │   [First Amendment Shield]  │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │      CORA NATION PMA        │
                    │  [Private Contract Shield]  │
                    └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         │                                                   │
┌────────┴────────┐                               ┌─────────┴─────────┐
│ SUNHEART TRUST  │                               │  FP IP LTD        │
│   (Nevada)      │──────────────────────────────>│   (Nevis)         │
│                 │         IP License            │                   │
│ • All IP        │<────────────────────────────  │ • International   │
│ • All LLCs      │         Royalties             │ • Judgment Shield │
│ • Reserves      │                               │                   │
└────────┬────────┘                               └────────┬──────────┘
         │                                                  │
         │ 100% Owns                                        │ Licenses to
         │                                                  │
    ┌────┴────────────────┬────────────────────┐           │
    │                     │                    │           │
┌───┴───┐          ┌──────┴─────┐        ┌────┴────┐     │
│ ARIA  │          │  FI-ART    │        │ OTHER   │     │
│ LLC   │          │  LLC       │        │ LLCs    │     │
│(WY)   │          │  (WY)      │        │ (WY)    │     │
│       │          │            │        │         │     │
│US Ops │          │ Art Ops    │        │ Future  │     │
└───────┘          └────────────┘        └─────────┘     │
                                                          │
         ┌────────────────────────────────────────────────┘
         │
    ┌────┴────────────────┬────────────────────┐
    │                     │                    │
┌───┴───────┐      ┌──────┴─────┐       ┌─────┴─────┐
│ FP TRADING│      │ FP DIGITAL │       │  FUTURE   │
│ PTE LTD   │      │ FZCO       │       │  ENTITIES │
│(Singapore)│      │ (Dubai)    │       │           │
│           │      │            │       │           │
│ APAC Ops  │      │ MENA/Crypto│       │ As needed │
└───────────┘      └────────────┘       └───────────┘

VALUE FLOW (Circulation):
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Members → UC Credits → Services → 30% Commons → Members    │
│                                                             │
│  Trading Gains → Trust → Reinvest/Commons → Growth          │
│                                                             │
│  IP Royalties → Trust → Development → Better Services       │
│                                                             │
└─────────────────────────────────────────────────────────────┘

PROTECTION LAYERS:
1. First Amendment (Church)
2. Private Contract (PMA)
3. Asset Protection (Trust - Nevada)
4. International Shield (Nevis - no foreign judgments)
5. Limited Liability (LLCs)
"""
        
        # Calculate combined alignment
        avg_alignment = BigPictureAlignment(
            safety_score=sum(a.safety_score for a in alignments.values()) / len(alignments),
            efficiency_score=sum(a.efficiency_score for a in alignments.values()) / len(alignments),
            circulation_score=sum(a.circulation_score for a in alignments.values()) / len(alignments),
            mathematics_score=sum(a.mathematics_score for a in alignments.values()) / len(alignments),
            regenerative_score=sum(a.regenerative_score for a in alignments.values()) / len(alignments)
        )
        
        implementation = [
            "Phase 1: Strengthen US Foundation (Nevada Trust + Wyoming LLCs) - Current",
            "Phase 2: Add International IP Shield (Nevis entity) - ~$5,000 setup",
            "Phase 3: Expand to Singapore (APAC gateway) - ~$3,500 setup",
            "Phase 4: Add Dubai presence (Crypto treasury) - ~$6,000 setup",
            "Phase 5: Connect all entities with proper IP licensing agreements",
            "Phase 6: Implement global UC credit circulation across all entities"
        ]
        
        return GlobalStructure(
            name="Full Potential Global Architecture",
            description="Multi-jurisdictional structure maximizing safety, efficiency, and circulation",
            entities=entities,
            flow_diagram=flow_diagram,
            total_annual_cost=sum(
                self.jurisdictions.get(e["jurisdiction"], JurisdictionProfile(name="", country="")).annual_cost_usd 
                for e in entities if e["jurisdiction"] in self.jurisdictions
            ),
            alignment=avg_alignment,
            implementation_phases=implementation
        )
    
    def get_report(self) -> str:
        """Generate human-readable optimization report"""
        analysis = self.analyze_current_structure()
        optimal = self.get_optimal_structure()
        global_structure = self.design_global_structure()
        
        report = []
        report.append("=" * 70)
        report.append("🏛️ JURISDICTION OPTIMIZATION REPORT")
        report.append("   Aligned with Full Potential Constitution")
        report.append("=" * 70)
        report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        report.append("\n" + "-" * 50)
        report.append("BIG PICTURE ALIGNMENT (Full Potential Principles)")
        report.append("-" * 50)
        alignment = global_structure.alignment
        report.append(f"  🛡️  Safety (Asset Protection):     {alignment.safety_score:.1f}/100")
        report.append(f"  ⚡ Efficiency (Tax/Cost):          {alignment.efficiency_score:.1f}/100")
        report.append(f"  🔄 Circulation (Value Flow):       {alignment.circulation_score:.1f}/100")
        report.append(f"  📐 Mathematics (Sustainable):      {alignment.mathematics_score:.1f}/100")
        report.append(f"  🌱 Regenerative (Non-Extractive):  {alignment.regenerative_score:.1f}/100")
        report.append(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        report.append(f"  ✨ TOTAL ALIGNMENT:                 {alignment.total_alignment:.1f}/100")
        
        report.append("\n" + "-" * 50)
        report.append("CURRENT STRUCTURE ANALYSIS")
        report.append("-" * 50)
        
        for entity, score in analysis["current_scores"].items():
            report.append(f"  {entity}: {self.current_structure[entity]} ({score:.1f}/100)")
        
        if analysis["improvements"]:
            report.append("\n" + "-" * 50)
            report.append("RECOMMENDED IMPROVEMENTS")
            report.append("-" * 50)
            
            for imp in analysis["improvements"]:
                report.append(f"\n  {imp['entity'].upper()}")
                report.append(f"    Current: {imp['current']}")
                report.append(f"    Recommended: {imp['recommended']}")
                report.append(f"    Score improvement: +{imp['score_improvement']:.1f}")
        
        report.append("\n" + "-" * 50)
        report.append("OPTIMAL GLOBAL STRUCTURE")
        report.append("-" * 50)
        
        for entity in global_structure.entities:
            report.append(f"\n  📍 {entity['name']}")
            report.append(f"     Type: {entity['type']}")
            report.append(f"     Jurisdiction: {entity['jurisdiction'].upper()}")
            report.append(f"     Purpose: {entity['purpose']}")
        
        report.append(f"\n  💰 Estimated Annual Cost: ${global_structure.total_annual_cost:,.0f}")
        
        report.append("\n" + "-" * 50)
        report.append("IMPLEMENTATION ROADMAP")
        report.append("-" * 50)
        for phase in global_structure.implementation_phases:
            report.append(f"  {phase}")
        
        report.append("\n" + "=" * 70)
        report.append("GLOBAL STRUCTURE DIAGRAM")
        report.append("=" * 70)
        report.append(global_structure.flow_diagram)
        
        return "\n".join(report)


# Convenience function for Aria
def get_jurisdiction_optimizer() -> JurisdictionOptimizer:
    """Get the jurisdiction optimizer instance"""
    return JurisdictionOptimizer()


# Example usage
if __name__ == "__main__":
    optimizer = JurisdictionOptimizer()
    print(optimizer.get_report())

