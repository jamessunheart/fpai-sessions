"""
Labor Displacement Intelligence Module — v5.2
==============================================

Tracks the gap between AI capability (what AI CAN do) and
actual labor displacement (what AI IS doing to human work).

The gap is the product:
  - Large gap, closing fast → disruption imminent
  - Large gap, stable → regulatory/adoption bottleneck
  - Small gap → transition well underway
  - Negative gap → non-AI factors at play

Three revenue streams from one dataset:
  1. Career intelligence (consumer, free/freemium)
  2. Investment signals (professional, premium)
  3. Corporate workforce intel (enterprise)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models.database import JobCategoryRow, async_session

logger = logging.getLogger("fp_index.displacement")

# ─── 25 Initial Categories ──────────────────────────────────────────────────

INITIAL_CATEGORIES = [
    # LEGAL
    {"id": "legal_doc_review", "name": "Legal document review", "sector": "Legal",
     "bls": "23-2011", "cap": 82, "disp": 28,
     "rationale": "AI reads, summarizes, flags issues in contracts at near-human accuracy. Adoption accelerating at law firms."},
    {"id": "legal_research", "name": "Legal research", "sector": "Legal",
     "bls": "23-2011", "cap": 68, "disp": 18,
     "rationale": "Strong at case law search, weaker at novel legal argument construction."},

    # SOFTWARE
    {"id": "code_generation", "name": "Software engineering (code generation)", "sector": "Technology",
     "bls": "15-1252", "cap": 65, "disp": 12,
     "rationale": "Copilot-class tools handle boilerplate, struggle with architecture. Massive gap."},
    {"id": "qa_testing", "name": "QA and software testing", "sector": "Technology",
     "bls": "15-1253", "cap": 76, "disp": 22,
     "rationale": "Automated testing, bug detection, test generation well within AI capability."},
    {"id": "it_support", "name": "IT help desk / support", "sector": "Technology",
     "bls": "15-1232", "cap": 81, "disp": 35,
     "rationale": "Chatbots handle Tier 1-2 support. Displacement already visible in large orgs."},

    # CUSTOMER SERVICE
    {"id": "customer_service_basic", "name": "Customer service (basic inquiries)", "sector": "Customer Service",
     "bls": "43-4051", "cap": 88, "disp": 42,
     "rationale": "Chatbots and voice AI handle routine queries. Gap closing fastest here."},
    {"id": "call_center", "name": "Call center operations", "sector": "Customer Service",
     "bls": "43-4051", "cap": 79, "disp": 31,
     "rationale": "Voice AI improving rapidly. Accent handling, emotional intelligence gaps remain."},

    # FINANCE
    {"id": "financial_analysis", "name": "Financial analysis (routine)", "sector": "Finance",
     "bls": "13-2051", "cap": 71, "disp": 15,
     "rationale": "Spreadsheet analysis, report generation — AI handles well. Displacement lagging."},
    {"id": "bookkeeping", "name": "Bookkeeping and accounting (routine)", "sector": "Finance",
     "bls": "43-3031", "cap": 85, "disp": 38,
     "rationale": "Transaction categorization, reconciliation highly automatable. Active displacement."},
    {"id": "tax_preparation", "name": "Tax preparation (individual)", "sector": "Finance",
     "bls": "13-2082", "cap": 78, "disp": 30,
     "rationale": "Standard returns near-fully automatable. Complex/business returns still need humans."},

    # HEALTHCARE
    {"id": "radiology", "name": "Radiology (image interpretation)", "sector": "Healthcare",
     "bls": "29-1224", "cap": 71, "disp": 8,
     "rationale": "AI matches/exceeds human accuracy on many imaging tasks. Regulatory bottleneck."},
    {"id": "medical_coding", "name": "Medical coding and billing", "sector": "Healthcare",
     "bls": "29-2072", "cap": 83, "disp": 25,
     "rationale": "Pattern-based, rule-heavy — high accuracy AI achievable. Active displacement."},
    {"id": "medical_transcription", "name": "Medical transcription", "sector": "Healthcare",
     "bls": "31-9094", "cap": 92, "disp": 65,
     "rationale": "Whisper-class models + medical vocabulary = near-complete automation. Most displaced category."},

    # CREATIVE
    {"id": "copywriting", "name": "Copywriting and content writing", "sector": "Creative",
     "bls": "27-3043", "cap": 79, "disp": 40,
     "rationale": "Blog posts, product descriptions, social copy — AI handles most of it. Freelance rates crashing."},
    {"id": "graphic_design_basic", "name": "Graphic design (basic/template)", "sector": "Creative",
     "bls": "27-1024", "cap": 72, "disp": 28,
     "rationale": "Social media graphics, basic layouts — AI tools capable. High-end design safe."},
    {"id": "translation", "name": "Translation and interpretation", "sector": "Creative",
     "bls": "27-3091", "cap": 74, "disp": 35,
     "rationale": "Common language pairs very strong. Rare languages, cultural nuance lagging."},

    # ADMINISTRATIVE
    {"id": "data_entry", "name": "Data entry", "sector": "Administrative",
     "bls": "43-9021", "cap": 91, "disp": 55,
     "rationale": "OCR + LLM extraction nearly eliminates manual data entry need."},
    {"id": "scheduling", "name": "Scheduling and calendar management", "sector": "Administrative",
     "bls": "43-6014", "cap": 84, "disp": 30,
     "rationale": "AI scheduling assistants handle most coordination."},
    {"id": "executive_assistant", "name": "Executive assistant (general)", "sector": "Administrative",
     "bls": "43-6011", "cap": 58, "disp": 12,
     "rationale": "AI handles scheduling, drafting, research. Relationship management still human."},

    # EDUCATION
    {"id": "tutoring", "name": "Tutoring (standard subjects)", "sector": "Education",
     "bls": "25-3041", "cap": 73, "disp": 18,
     "rationale": "Khan Academy + GPT-class models effective for math, science, test prep."},
    {"id": "grading", "name": "Essay grading and feedback", "sector": "Education",
     "bls": "25-1000", "cap": 68, "disp": 15,
     "rationale": "Rubric-based grading automatable. Nuanced creative feedback still weak."},

    # LOGISTICS
    {"id": "warehouse_picking", "name": "Warehouse picking and sorting", "sector": "Logistics",
     "bls": "53-7065", "cap": 67, "disp": 20,
     "rationale": "Robotics + vision improving but not yet cost-effective at most warehouses."},
    {"id": "truck_driving", "name": "Truck driving (long-haul)", "sector": "Transportation",
     "bls": "53-3032", "cap": 41, "disp": 3,
     "rationale": "Autonomous trucks tested but regulatory and edge-case barriers remain high."},

    # RESEARCH
    {"id": "literature_review", "name": "Academic literature review", "sector": "Research",
     "bls": "19-0000", "cap": 77, "disp": 15,
     "rationale": "AI excels at finding, summarizing, synthesizing papers. Critical evaluation still human."},
    {"id": "market_research", "name": "Market research and analysis", "sector": "Business Services",
     "bls": "13-1161", "cap": 69, "disp": 20,
     "rationale": "Data gathering, survey analysis, trend identification strong. Strategic insight weaker."},
]


async def seed_categories():
    """Seed the 25 initial job categories if they don't exist."""
    async with async_session() as session:
        existing = (await session.execute(
            select(JobCategoryRow.id)
        )).scalars().all()
        existing_ids = set(existing)

        added = 0
        for cat in INITIAL_CATEGORIES:
            if cat["id"] in existing_ids:
                continue
            gap = cat["cap"] - cat["disp"]
            if gap > 50:
                timeline = "long_term"
            elif gap > 30:
                timeline = "medium_term"
            elif gap > 15:
                timeline = "near_term"
            else:
                timeline = "imminent"

            row = JobCategoryRow(
                id=cat["id"],
                name=cat["name"],
                parent_sector=cat["sector"],
                bls_code=cat["bls"],
                capability_score=cat["cap"],
                displacement_score=cat["disp"],
                gap=gap,
                gap_velocity=0.0,
                automation_timeline=timeline,
                rationale=cat["rationale"],
            )
            session.add(row)
            added += 1
        await session.commit()
        if added:
            logger.info(f"Seeded {added} job categories")
        return added


async def get_all_categories() -> list[dict]:
    """Return all 25 categories with current scores."""
    async with async_session() as session:
        rows = (await session.execute(
            select(JobCategoryRow).order_by(JobCategoryRow.gap.desc())
        )).scalars().all()
        return [_cat_to_dict(r) for r in rows]


async def get_category(category_id: str) -> Optional[dict]:
    async with async_session() as session:
        row = await session.get(JobCategoryRow, category_id)
        if not row:
            return None
        return _cat_to_dict(row)


async def get_sectors_summary() -> list[dict]:
    """Group categories by sector and compute sector-level averages."""
    cats = await get_all_categories()
    sectors: dict[str, list] = {}
    for c in cats:
        sectors.setdefault(c["parent_sector"], []).append(c)

    result = []
    for sector, items in sorted(sectors.items()):
        avg_cap = sum(c["capability_score"] for c in items) / len(items)
        avg_disp = sum(c["displacement_score"] for c in items) / len(items)
        result.append({
            "sector": sector,
            "categories": len(items),
            "avg_capability": round(avg_cap, 1),
            "avg_displacement": round(avg_disp, 1),
            "avg_gap": round(avg_cap - avg_disp, 1),
        })
    return sorted(result, key=lambda s: s["avg_gap"], reverse=True)


async def get_fastest_closing() -> list[dict]:
    """Categories where the gap is closing fastest (highest displacement relative to capability)."""
    cats = await get_all_categories()
    return sorted(cats, key=lambda c: c["displacement_score"] / max(1, c["capability_score"]), reverse=True)[:5]


async def get_largest_gaps() -> list[dict]:
    """Categories with largest untapped capability gap."""
    cats = await get_all_categories()
    return sorted(cats, key=lambda c: c["gap"], reverse=True)[:5]


async def compute_labor_dimension_score() -> float:
    """Compute the labor displacement dimension score for the FP Line.

    Higher score = more displacement activity detected.
    Weighted by: average displacement across all categories,
    velocity of gap closing, and number of categories in active transition.
    """
    cats = await get_all_categories()
    if not cats:
        return 50.0

    avg_displacement = sum(c["displacement_score"] for c in cats) / len(cats)
    active_transition = sum(1 for c in cats if c["gap"] < 30)
    transition_ratio = active_transition / len(cats) * 100

    score = (avg_displacement * 0.6) + (transition_ratio * 0.4)
    return min(100.0, round(score, 1))


def _cat_to_dict(row: JobCategoryRow) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "parent_sector": row.parent_sector,
        "bls_code": row.bls_code,
        "capability_score": row.capability_score,
        "displacement_score": row.displacement_score,
        "gap": row.gap,
        "gap_velocity": row.gap_velocity,
        "automation_timeline": row.automation_timeline,
        "rationale": row.rationale,
        "total_us_employment": row.total_us_employment,
        "median_salary": row.median_salary,
        "short_signal": row.short_signal,
        "long_signal": row.long_signal,
        "last_updated": row.last_updated.isoformat() if row.last_updated else None,
    }


DISCLAIMER = (
    "The Full Potential Index provides intelligence signals based on AI capability "
    "assessment and labor market data analysis. These signals are informational only "
    "and do not constitute financial, investment, legal, or career advice. Past "
    "displacement patterns do not predict future outcomes. Consult qualified "
    "professionals before making investment or career decisions based on this data."
)
