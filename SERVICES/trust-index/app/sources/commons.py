"""Commons health score source - fetches from Credits Gateway ledger + Needs Allocation."""
import httpx
import logging
from typing import Tuple, Dict, Any

from ..config import settings

logger = logging.getLogger(__name__)


async def get_commons_health_score() -> Tuple[float, Dict[str, Any]]:
    """
    Get commons health score from reserve metrics.

    Data sources:
    - Reserve value: Credits Gateway /api/treasury/allocations (ledger) → settings.COMMONS_RESERVE_ACCOUNT
    - Committed needs: Needs Allocation /api/needs/committed

    Components:
    - Reserve ratio (50%): reserve_value / committed_needs
    - Liquidity ratio (30%): liquid_assets / total_reserve
    - Stability (20%): 1 - volatility

    Returns:
        Tuple of (score 0-1, details dict)
    """
    reserve_value = 0.0
    liquid_assets = 0.0
    committed_needs = 1.0  # Default to 1 to avoid division by zero
    volatility = 0.15  # Default low volatility

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Get reserve value from ledger allocations
            try:
                alloc_resp = await client.get(
                    f"{settings.CREDITS_GATEWAY_URL}/api/treasury/allocations"
                )
                if alloc_resp.status_code == 200:
                    alloc_data = alloc_resp.json()
                    allocations = alloc_data.get("allocations", {}) or {}
                    reserve_value = float(allocations.get(settings.COMMONS_RESERVE_ACCOUNT, 0.0))
                    liquid_assets = reserve_value * 0.8  # Assume 80% liquid by default
            except Exception as e:
                logger.warning(f"Failed to fetch treasury allocations: {e}")

            # 2. Get committed needs from needs-allocation
            try:
                needs_resp = await client.get(
                    f"{settings.NEEDS_ALLOCATION_URL}/api/needs/committed"
                )
                if needs_resp.status_code == 200:
                    needs_data = needs_resp.json()
                    # IMPORTANT: committed_needs should represent actual outstanding obligations,
                    # not monthly budget projections (to avoid circular dependencies with Trust Index).
                    committed_needs = max(1.0, float(needs_data.get("total_committed_uc", 0.0)))
            except Exception as e:
                logger.warning(f"Failed to fetch needs data: {e}")

        # Calculate components
        reserve_ratio = reserve_value / committed_needs if committed_needs > 0 else 0
        reserve_score = min(1.0, reserve_ratio / 2.0)  # 2x committed = 1.0

        liquidity_ratio = liquid_assets / reserve_value if reserve_value > 0 else 1.0
        liquidity_score = min(1.0, liquidity_ratio)

        max_volatility = 0.5
        stability_score = max(0, 1 - (volatility / max_volatility))

        # Weighted composite
        score = (
            reserve_score * 0.50 +
            liquidity_score * 0.30 +
            stability_score * 0.20
        )

        logger.info(
            f"[COMMONS] Reserve={reserve_value:.0f} ({settings.COMMONS_RESERVE_ACCOUNT}), "
            f"Committed={committed_needs:.0f}, Score={score:.3f}"
        )

        return score, {
            "reserve_ratio": round(reserve_ratio, 3),
            "liquidity_ratio": round(liquidity_ratio, 3),
            "stability": round(stability_score, 3),
            "reserve_value": reserve_value,
            "committed_needs": committed_needs,
            "liquid_assets": liquid_assets,
            "volatility_30d": volatility,
            "reserve_account": settings.COMMONS_RESERVE_ACCOUNT,
            "source": "credits-gateway-ledger"
        }

    except Exception as e:
        logger.error(f"Error calculating commons health: {e}")
        return 0.5, {"error": str(e)}

