"""
Gap Opportunity Engine — v5.5
===============================

Identifies gaps between AI capability and market adoption,
scores them across 8 dimensions, ranks by build priority,
and produces actionable build assessments.

Three revenue streams from one dataset:
  1. Report on the gap  (subscription revenue)
  2. Invest in the gap  (capital returns)
  3. Fill the gap       (service/product revenue) ← THIS MODULE
"""

import logging
from datetime import datetime, timezone

from .displacement import get_all_categories

logger = logging.getLogger("fp_index.opportunities")

SCORING_DIMENSIONS = {
    "capability_readiness": {
        "weight": 0.20,
        "label": "Capability Readiness",
        "description": "How ready is AI to deliver this?",
    },
    "market_gap_size": {
        "weight": 0.15,
        "label": "Market Gap Size",
        "description": "How large is the unserved demand?",
    },
    "gap_urgency": {
        "weight": 0.15,
        "label": "Gap Urgency",
        "description": "How fast is this gap closing? Faster = more urgent to act.",
    },
    "market_value": {
        "weight": 0.12,
        "label": "Market Value (TAM)",
        "description": "Total money flowing through this category.",
    },
    "willingness_to_pay": {
        "weight": 0.10,
        "label": "Willingness to Pay",
        "description": "Will customers actually pay for this?",
    },
    "competitive_density": {
        "weight": 0.10,
        "label": "Competitive Density",
        "description": "How crowded is this space? Less = better.",
    },
    "delivery_complexity": {
        "weight": 0.10,
        "label": "Delivery Complexity",
        "description": "Can we build this with AI agents + BPO?",
    },
    "recurring_potential": {
        "weight": 0.08,
        "label": "Recurring Revenue Potential",
        "description": "One-time project or ongoing subscription?",
    },
}

COMPLEXITY_MAP = {
    "data_entry": "trivial",
    "medical_transcription": "trivial",
    "scheduling": "trivial",
    "customer_service_basic": "low",
    "copywriting": "low",
    "translation": "low",
    "bookkeeping": "low",
    "grading": "low",
    "literature_review": "low",
    "legal_doc_review": "medium",
    "financial_analysis": "medium",
    "tax_preparation": "medium",
    "market_research": "medium",
    "qa_testing": "medium",
    "it_support": "medium",
    "graphic_design_basic": "medium",
    "tutoring": "medium",
    "call_center": "medium",
    "executive_assistant": "medium",
    "code_generation": "high",
    "legal_research": "high",
    "medical_coding": "high",
    "warehouse_picking": "high",
    "radiology": "extreme",
    "truck_driving": "extreme",
}

COMPLEXITY_SCORES = {"trivial": 95, "low": 80, "medium": 55, "high": 30, "extreme": 10}

HIGH_RECURRING = {
    "customer_service_basic", "call_center", "bookkeeping",
    "data_entry", "scheduling", "medical_transcription",
    "medical_coding", "it_support", "copywriting",
}
MEDIUM_RECURRING = {
    "legal_doc_review", "financial_analysis", "tax_preparation",
    "translation", "market_research", "qa_testing",
    "graphic_design_basic", "executive_assistant",
}
LOW_RECURRING = {
    "legal_research", "code_generation", "tutoring",
    "grading", "literature_review",
}

DELIVERY_MODELS = {
    "api_wrapper": {
        "name": "API wrapper product",
        "description": "Thin layer over existing AI API with custom prompts",
        "build_weeks": 2,
        "team": ["1 developer"],
        "monthly_cost": 200,
        "best_for": {"data_entry", "scheduling", "medical_transcription"},
    },
    "ai_plus_bpo": {
        "name": "AI + BPO hybrid",
        "description": "AI handles 80%+ automatically, BPO team handles exceptions and QA",
        "build_weeks": 4,
        "team": ["1 developer", "2-3 BPO operators"],
        "monthly_cost": 1500,
        "best_for": {
            "customer_service_basic", "bookkeeping", "copywriting",
            "translation", "call_center",
        },
    },
    "custom_pipeline": {
        "name": "Custom AI pipeline",
        "description": "Multiple AI models, custom integrations, BPO operations",
        "build_weeks": 8,
        "team": ["2 developers", "1 AI engineer", "3-5 BPO operators"],
        "monthly_cost": 4000,
        "best_for": {
            "legal_doc_review", "financial_analysis", "tax_preparation",
            "medical_coding", "qa_testing",
        },
    },
    "full_platform": {
        "name": "Full product platform",
        "description": "Standalone product with UI, onboarding, billing, management",
        "build_weeks": 16,
        "team": ["3 developers", "1 designer", "1 PM", "5+ BPO"],
        "monthly_cost": 8000,
        "best_for": {"it_support", "executive_assistant", "market_research"},
    },
}


def _estimate_cost_savings(capability: float) -> float:
    if capability >= 90:
        return 75
    elif capability >= 70:
        return 50
    elif capability >= 50:
        return 30
    return 15


def _select_delivery_model(category_id: str, complexity: str) -> dict:
    for model_id, model in DELIVERY_MODELS.items():
        if category_id in model["best_for"]:
            return {"model_id": model_id, **model}
    fallback = {"trivial": "api_wrapper", "low": "ai_plus_bpo",
                "medium": "custom_pipeline", "high": "full_platform",
                "extreme": "full_platform"}
    model_id = fallback.get(complexity, "custom_pipeline")
    return {"model_id": model_id, **DELIVERY_MODELS[model_id]}


def score_opportunity(cat: dict) -> dict:
    """Score a single category across all 8 dimensions."""
    cap = cat["capability_score"]
    disp = cat["displacement_score"]
    gap = cat["gap"]
    velocity = abs(cat.get("gap_velocity", 0.0))
    employment = cat.get("total_us_employment", 0)
    salary = cat.get("median_salary", 0.0)
    cid = cat["id"]

    scores = {}

    scores["capability_readiness"] = min(100, cap)

    gap_workers = employment * (gap / 100) if employment else gap * 1000
    scores["market_gap_size"] = min(100, (gap_workers / 100000) * 100)

    if velocity > 5:
        scores["gap_urgency"] = 95
    elif velocity > 3:
        scores["gap_urgency"] = 80
    elif velocity > 1:
        scores["gap_urgency"] = 60
    elif velocity > 0.5:
        scores["gap_urgency"] = 40
    else:
        scores["gap_urgency"] = max(20, gap * 0.5)

    tam = employment * salary if employment and salary else 0
    scores["market_value"] = min(100, (tam / 10_000_000_000) * 100) if tam else min(100, cap * 0.4)

    savings = _estimate_cost_savings(cap)
    scores["willingness_to_pay"] = min(100, savings * 1.2)

    scores["competitive_density"] = 60 if gap > 40 else 40

    complexity = COMPLEXITY_MAP.get(cid, "medium")
    scores["delivery_complexity"] = COMPLEXITY_SCORES.get(complexity, 55)

    if cid in HIGH_RECURRING:
        scores["recurring_potential"] = 90
    elif cid in MEDIUM_RECURRING:
        scores["recurring_potential"] = 60
    elif cid in LOW_RECURRING:
        scores["recurring_potential"] = 35
    else:
        scores["recurring_potential"] = 50

    composite = sum(
        scores[dim] * cfg["weight"]
        for dim, cfg in SCORING_DIMENSIONS.items()
    )

    delivery = _select_delivery_model(cid, complexity)

    revenue_projection = {}
    if tam > 0:
        gap_pct = gap / 100
        addressable = tam * gap_pct
        serviceable = addressable * 0.40
        revenue_projection = {
            "total_labor_spend": round(tam),
            "addressable_market": round(addressable),
            "serviceable_market": round(serviceable),
            "conservative_yr1": round(serviceable * 0.001),
            "moderate_yr1": round(serviceable * 0.005),
        }

    margin = 75 if complexity in ("trivial", "low") else 60 if complexity == "medium" else 45

    return {
        "category_id": cid,
        "name": cat["name"],
        "sector": cat["parent_sector"],
        "capability_score": cap,
        "displacement_score": disp,
        "gap": gap,
        "gap_velocity": cat.get("gap_velocity", 0.0),
        "rationale": cat.get("rationale", ""),
        "employment": employment,
        "median_salary": salary,
        "scores": scores,
        "composite_score": round(composite, 1),
        "complexity": complexity,
        "build_weeks": delivery["build_weeks"],
        "delivery_model": delivery["name"],
        "delivery_model_id": delivery["model_id"],
        "team": delivery["team"],
        "estimated_margin_pct": margin,
        "revenue_projection": revenue_projection,
        "recommendation": "BUILD" if composite >= 60 and margin >= 40 and delivery["build_weeks"] <= 8 else "EVALUATE",
        "last_scored": datetime.now(timezone.utc).isoformat(),
    }


async def get_ranked_opportunities() -> list[dict]:
    """Score all 25 categories and return ranked by composite score."""
    categories = await get_all_categories()
    scored = [score_opportunity(cat) for cat in categories]
    scored.sort(key=lambda o: o["composite_score"], reverse=True)
    for i, opp in enumerate(scored):
        opp["rank"] = i + 1
    return scored


async def get_opportunity(category_id: str) -> dict | None:
    """Get detailed opportunity data for a single category."""
    categories = await get_all_categories()
    for cat in categories:
        if cat["id"] == category_id:
            opp = score_opportunity(cat)
            opp["rank"] = 0
            opp["build_plan"] = _generate_build_plan(opp)
            opp["go_to_market"] = _generate_gtm(opp)
            return opp
    return None


async def get_top_opportunities(n: int = 5) -> list[dict]:
    ranked = await get_ranked_opportunities()
    return ranked[:n]


def _generate_build_plan(opp: dict) -> dict:
    model = opp["delivery_model_id"]
    weeks = opp["build_weeks"]

    if model == "api_wrapper":
        return {
            "total_weeks": weeks,
            "phases": [
                {"week": "1", "name": "Build core",
                 "tasks": ["Design prompt chain", "Build API wrapper", "Create web UI/endpoint", "Internal testing"]},
                {"week": "2", "name": "Polish and launch",
                 "tasks": ["QA with real data", "Stripe billing", "Landing page", "Soft launch (5 customers)"]},
            ],
        }
    elif model == "ai_plus_bpo":
        return {
            "total_weeks": weeks,
            "phases": [
                {"week": "1-2", "name": "AI core",
                 "tasks": ["AI pipeline design", "Automated processing engine", "Exception criteria", "BPO docs"]},
                {"week": "2-3", "name": "BPO integration",
                 "tasks": ["Train BPO team", "Build handoff system", "QA layer", "Real data testing"]},
                {"week": "3-4", "name": "Launch",
                 "tasks": ["Onboarding flow", "Billing", "Landing page", "First 5 customers"]},
            ],
        }
    else:
        return {
            "total_weeks": weeks,
            "phases": [
                {"week": "1-3", "name": "Architecture + AI pipeline",
                 "tasks": ["System architecture", "AI processing pipeline", "Multi-model integration"]},
                {"week": "3-5", "name": "Operations layer",
                 "tasks": ["Exception workflows", "QA system", "Documentation"]},
                {"week": "5-7", "name": "Customer product",
                 "tasks": ["UI/UX", "Onboarding", "Billing"]},
                {"week": f"7-{weeks}", "name": "Launch + iterate",
                 "tasks": ["Beta customers", "Feedback loop", "Scale operations"]},
            ],
        }


def _generate_gtm(opp: dict) -> dict:
    savings = _estimate_cost_savings(opp["capability_score"])
    return {
        "positioning": (
            f"AI-powered {opp['name'].lower()} at ~{savings}% less than traditional providers. "
            f"Powered by the same intelligence engine tracking the entire AI frontier."
        ),
        "channels": [
            {"channel": "Full Potential content", "cost": 0,
             "description": "Daily briefing + displacement watch reach the exact audience."},
            {"channel": "Direct outreach", "cost": 500,
             "description": f"Target companies in {opp['name'].lower()} via LinkedIn. Lead with data."},
            {"channel": "Consulting funnel", "cost": 0,
             "description": "Existing diagnostic clients who need this specific capability."},
        ],
        "pricing": f"40% of human labor cost. Customer saves ~{savings}%. Margin ~{opp['estimated_margin_pct']}%.",
    }


OPPORTUNITY_DISCLAIMER = (
    "Gap opportunity rankings are based on the Full Potential Index scoring system "
    "combining AI capability assessment, labor market data, and estimated market conditions. "
    "Revenue projections are hypothetical estimates, not guarantees. Market conditions, "
    "competitive dynamics, and execution quality will affect actual results. These rankings "
    "are intelligence products, not business advice."
)
