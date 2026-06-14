"""Solvency score source - Treasury Health Score from Credits Gateway."""
import httpx
import logging
from typing import Tuple, Dict, Any

from ..config import settings

logger = logging.getLogger(__name__)


async def get_solvency_score() -> Tuple[float, Dict[str, Any]]:
    """
    Get solvency score from Treasury Health Score.
    
    Credits Gateway returns:
    {
        "score": 2.0,  # THS - ratio of assets to liabilities
        "mode": "ABUNDANCE",  # DEFICIT, STABLE, GROWTH, ABUNDANCE
        "assets_usd": 0.0,
        "liabilities_uc": 0,
        ...
    }
    
    Returns:
        Tuple of (score 0-1, details dict)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.CREDITS_GATEWAY_URL}/api/treasury/health"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # THS from Credits Gateway
                ths = data.get("score", 1.0)
                mode = data.get("mode", "STABLE")
                assets = data.get("assets_usd", 0)
                liabilities = data.get("liabilities_uc", 0)
                
                # Normalize THS to 0-1 score
                # THS of 1.5+ = 1.0 (fully healthy)
                # THS of 0 = 0 (insolvent)
                score = min(1.0, max(0, ths / 1.5))
                
                # Map mode to status
                status_map = {
                    "DEFICIT": "critical",
                    "STABLE": "stable", 
                    "GROWTH": "healthy",
                    "ABUNDANCE": "thriving"
                }
                
                logger.info(f"[SOLVENCY] THS={ths:.2f}, Mode={mode}, Score={score:.3f}")
                
                return score, {
                    "raw_ths": ths,
                    "mode": mode,
                    "treasury_assets": assets,
                    "uc_outstanding": liabilities,
                    "status": status_map.get(mode, "unknown"),
                    "assets_breakdown": data.get("assets_breakdown", {}),
                    "policy": data.get("policy", "")
                }
            else:
                logger.warning(f"Treasury health check failed: {response.status_code}")
                return 0.5, {"error": "failed_to_fetch", "status_code": response.status_code}
                
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch THS: {e}")
        # Return moderate score on error to avoid emergency freeze
        return 0.5, {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error fetching THS: {e}")
        return 0.5, {"error": str(e)}


async def get_solvency_score_mock() -> Tuple[float, Dict[str, Any]]:
    """Mock solvency score for testing."""
    return 0.85, {
        "raw_ths": 1.28,
        "mode": "GROWTH",
        "treasury_assets": 150000,
        "uc_outstanding": 117000,
        "status": "healthy",
        "mock": True
    }

