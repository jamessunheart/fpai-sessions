"""Participation score source."""
import httpx
import logging
from typing import Tuple, Dict, Any

from ..config import settings

logger = logging.getLogger(__name__)


async def get_participation_score() -> Tuple[float, Dict[str, Any]]:
    """
    Get participation score from contribution tracker.
    
    Components:
    - Active ratio (50%): active_contributors / total_members
    - Avg contribution (30%): avg_score / target_score
    - Retention (20%): members_retained / members_start
    
    Returns:
        Tuple of (score 0-1, details dict)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.CONTRIBUTION_TRACKER_URL}/api/contributions/aggregate"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                active_ratio = data.get("active_ratio", 0)
                avg_score = data.get("avg_quarterly_score", 0)
                target_score = 100  # Active tier minimum
                
                # Calculate components
                active_score = min(1.0, active_ratio)
                avg_contribution_score = min(1.0, avg_score / target_score)
                
                # TODO: Add actual retention tracking
                retention_score = 0.85  # Placeholder
                
                # Weighted composite
                score = (
                    active_score * 0.50 +
                    avg_contribution_score * 0.30 +
                    retention_score * 0.20
                )
                
                return score, {
                    "active_ratio": active_ratio,
                    "avg_contribution": avg_contribution_score,
                    "retention": retention_score,
                    "total_members": data.get("total_members", 0),
                    "active_contributors": data.get("active_contributors", 0),
                    "avg_quarterly_score": avg_score
                }
            else:
                logger.warning(f"Contribution tracker check failed: {response.status_code}")
                return 0.5, {"error": "failed_to_fetch"}
                
    except httpx.RequestError as e:
        logger.error(f"Failed to fetch participation data: {e}")
        return 0.5, {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error fetching participation: {e}")
        return 0.5, {"error": str(e)}


async def get_participation_score_mock() -> Tuple[float, Dict[str, Any]]:
    """Mock participation score for testing."""
    return 0.62, {
        "active_ratio": 0.55,
        "avg_contribution": 0.70,
        "retention": 0.85,
        "total_members": 500,
        "active_contributors": 275,
        "avg_quarterly_score": 87,
        "mock": True
    }










