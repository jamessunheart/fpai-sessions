"""Budget calculation and management."""
import httpx
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from .config import settings, CATEGORIES
from .models import CategoryBudget, BudgetResponse
from .db_models import MonthlyBudget

logger = logging.getLogger(__name__)


async def get_trust_policy() -> Dict[str, Any]:
    """Get current Trust Index policy from trust-index service (best-effort)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.TRUST_INDEX_URL}/api/trust-index/policy")
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Failed to get Trust Index policy: {e}")
    
    # Return mock data
    return {
        "trust_index": 0.50,
        "posture": "balanced",
        "parameters": {"safety_buffer": 1.5},
        "source": "fallback"
    }


async def get_commons_reserve_uc() -> float:
    """
    Get commons reserve value (UC) used for monthly budgeting.

    Source order:
    1) NEEDS_COMMONS_RESERVE_UC_OVERRIDE (if set)
    2) Credits Gateway /api/treasury/allocations → NEEDS_COMMONS_RESERVE_ACCOUNT
    """
    if settings.COMMONS_RESERVE_UC_OVERRIDE is not None:
        try:
            return float(settings.COMMONS_RESERVE_UC_OVERRIDE)
        except Exception:
            return 0.0

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.CREDITS_GATEWAY_URL}/api/treasury/allocations")
            if resp.status_code == 200:
                data = resp.json()
                allocations = data.get("allocations", {}) or {}
                return float(allocations.get(settings.COMMONS_RESERVE_ACCOUNT, 0.0))
    except Exception as e:
        logger.warning(f"Failed to fetch commons reserve from credits gateway: {e}")

    return 0.0


def calculate_monthly_budget(
    trust_index: float,
    posture: str,
    commons_reserve: float,
    safety_buffer: float
) -> float:
    """Calculate monthly budget based on policy posture, Trust Index, and reserve."""
    p = (posture or "balanced").lower().strip()

    # Emergency posture or low trust → freeze (minimize harm)
    if p == "emergency" or trust_index <= settings.EMERGENCY_FREEZE_TRUST_INDEX:
        return 0.0
    
    # Base rate depends on posture
    if p == "generous" or trust_index > 0.7:
        base_rate = 0.05  # Generous: 5% of reserve
    elif p == "conservative" or trust_index <= 0.3:
        base_rate = 0.01  # Conservative: 1%
    else:
        base_rate = 0.03  # Balanced: 3%
    
    # Apply safety reserve (always keep 20%) + policy safety buffer (reduce spend rate)
    safety_reserve = commons_reserve * 0.20
    available = max(0.0, commons_reserve - safety_reserve)
    
    sb = max(1.0, float(safety_buffer or 1.5))
    return (available * base_rate) / sb


async def get_current_budget(db: Optional[AsyncSession] = None) -> BudgetResponse:
    """Get current budget allocation."""
    
    # Get Trust Index policy snapshot
    policy = await get_trust_policy()
    trust_index_raw = policy.get("trust_index", 0.5)
    trust_index = float(trust_index_raw) if trust_index_raw is not None else 0.5
    posture = policy.get("posture") or policy.get("policy_posture") or "balanced"
    safety_buffer = (policy.get("parameters") or {}).get("safety_buffer", 1.5)
    
    # Get Commons Reserve value (UC)
    commons_reserve = await get_commons_reserve_uc()

    # Calculate monthly budget
    monthly_budget = calculate_monthly_budget(trust_index, posture, commons_reserve, safety_buffer)
    
    # Get current period
    now = datetime.utcnow()
    period = f"{now.year}-{now.month:02d}"
    next_month = datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)
    
    # Load actual usage from database (MonthlyBudget) when available.
    usage = {k: 0.0 for k in CATEGORIES.keys()}
    if db is not None:
        result = await db.execute(select(MonthlyBudget).where(MonthlyBudget.id == period))
        mb = result.scalar_one_or_none()
        if mb is None:
            mb = MonthlyBudget(
                id=period,
                total_budget=monthly_budget,
                survival_used=0.0,
                stability_used=0.0,
                growth_used=0.0,
                contribution_used=0.0,
                infrastructure_used=0.0
            )
            db.add(mb)
            # No commit here; router/session manager will commit
        else:
            # Keep total_budget updated for audit/visibility
            mb.total_budget = monthly_budget

        usage = {
            "survival": float(mb.survival_used or 0.0),
            "stability": float(mb.stability_used or 0.0),
            "growth": float(mb.growth_used or 0.0),
            "contribution": float(mb.contribution_used or 0.0),
            "infrastructure": float(mb.infrastructure_used or 0.0)
        }
    
    categories = {}
    for cat, config in CATEGORIES.items():
        allocation = config["allocation"]
        budget = monthly_budget * allocation
        used = usage.get(cat, 0)
        
        categories[cat] = CategoryBudget(
            budget=round(budget, 2),
            used=used,
            available=round(max(0, budget - used), 2),
            allocation_percent=allocation
        )
    
    logger.info(
        f"[BUDGET] posture={posture} trust_index={trust_index:.3f} "
        f"reserve_uc={commons_reserve:.2f} monthly_budget_uc={monthly_budget:.2f}"
    )

    return BudgetResponse(
        trust_index=trust_index,
        posture=posture,
        monthly_budget_uc=round(monthly_budget, 2),
        categories=categories,
        period=period,
        resets=next_month
    )


def check_budget_available(category: str, amount: float, budget: BudgetResponse) -> bool:
    """Check if budget is available for an allocation."""
    
    cat_budget = budget.categories.get(category)
    if not cat_budget:
        return False
    
    return cat_budget.available >= amount




