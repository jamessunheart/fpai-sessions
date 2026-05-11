"""Integration client for spec-verifier and spec-optimizer"""

import logging
import httpx
from typing import Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class IntegrationClient:
    """Client for integrating with spec-verifier and spec-optimizer"""

    def __init__(self):
        self.verifier_url = settings.spec_verifier_url
        self.optimizer_url = settings.spec_optimizer_url

    async def verify_spec(self, spec_content: str) -> Dict:
        """Verify SPEC using spec-verifier"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.verifier_url}/verify",
                    json={"spec_content": spec_content, "strict_mode": False}
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Verification: score={result.get('score', {}).get('overall', 0)}")
                    return result
                else:
                    logger.error(f"❌ Verification failed: {response.status_code}")
                    return self._error_result("Verification service error")

        except Exception as e:
            logger.error(f"❌ Verification error: {e}")
            return self._error_result(str(e))

    async def optimize_spec(self, spec_content: str, target_score: int = 90) -> Dict:
        """Optimize SPEC using spec-optimizer"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.optimizer_url}/optimize",
                    json={
                        "spec_content": spec_content,
                        "optimization_level": "standard",
                        "target_score": target_score
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"✅ Optimization: "
                        f"{result.get('verification_before', {}).get('score', {}).get('overall', 0)} → "
                        f"{result.get('verification_after', {}).get('score', {}).get('overall', 0)}"
                    )
                    return result
                else:
                    logger.error(f"❌ Optimization failed: {response.status_code}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            logger.error(f"❌ Optimization error: {e}")
            return {"success": False, "error": str(e)}

    async def check_verifier_health(self) -> bool:
        """Check if spec-verifier is available"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.verifier_url}/health")
                return response.status_code == 200
        except:
            return False

    async def check_optimizer_health(self) -> bool:
        """Check if spec-optimizer is available"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.optimizer_url}/health")
                return response.status_code == 200
        except:
            return False

    def _error_result(self, error: str) -> Dict:
        """Generate error verification result"""
        return {
            "valid": False,
            "score": {"overall": 0.0},
            "errors": [f"Verification error: {error}"],
            "warnings": []
        }
