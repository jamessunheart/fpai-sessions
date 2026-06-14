"""Client for spec-verifier service"""

import logging
import httpx
from typing import Dict, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class VerificationClient:
    """Client for communicating with spec-verifier service"""

    def __init__(self):
        self.base_url = settings.spec_verifier_url

    async def verify_spec(self, spec_content: str) -> Dict:
        """
        Verify SPEC content using spec-verifier service

        Args:
            spec_content: SPEC markdown content

        Returns:
            Verification result dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/verify",
                    json={
                        "spec_content": spec_content,
                        "strict_mode": False
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"✅ Verification complete: score={result.get('score', {}).get('overall', 0)}"
                    )
                    return result
                else:
                    logger.error(f"❌ Verification failed: {response.status_code}")
                    return self._error_result(f"HTTP {response.status_code}")

        except httpx.TimeoutException:
            logger.error("❌ Verification timeout")
            return self._error_result("Timeout")
        except Exception as e:
            logger.error(f"❌ Verification error: {e}")
            return self._error_result(str(e))

    async def verify_file(self, file_path: str) -> Dict:
        """
        Verify SPEC file by path using spec-verifier service

        Args:
            file_path: Path to SPEC file

        Returns:
            Verification result dictionary
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/verify-file",
                    json={
                        "file_path": file_path,
                        "strict_mode": False
                    }
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"❌ File verification failed: {response.status_code}")
                    return self._error_result(f"HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"❌ File verification error: {e}")
            return self._error_result(str(e))

    async def check_health(self) -> bool:
        """Check if spec-verifier is available"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except:
            return False

    def _error_result(self, error: str) -> Dict:
        """Generate error result"""
        return {
            "valid": False,
            "score": {
                "completeness": 0,
                "clarity": 0,
                "udc_compliance": 0,
                "build_readiness": 0,
                "overall": 0.0
            },
            "sections": {
                "found": [],
                "missing": [],
                "incomplete": []
            },
            "udc_endpoints": {
                "documented": 0,
                "required": 5,
                "missing": ["/health", "/capabilities", "/state", "/dependencies", "/message"],
                "compliant": False
            },
            "recommendations": [],
            "errors": [f"Verification service error: {error}"],
            "warnings": []
        }
