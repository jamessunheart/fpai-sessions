import httpx
from typing import List
from app.models import CheckResult, VerificationStatus
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ScannerEngine:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.DEFAULT_TIMEOUT)

    async def check_udc_compliance(self, service_url: str) -> List[CheckResult]:
        results = []
        
        # Check /health
        try:
            resp = await self.client.get(f"{service_url}/health")
            if resp.status_code == 200:
                results.append(CheckResult(name="health_endpoint", status=VerificationStatus.PASS, details="200 OK"))
            else:
                results.append(CheckResult(name="health_endpoint", status=VerificationStatus.FAIL, details=f"Status {resp.status_code}"))
        except Exception as e:
            results.append(CheckResult(name="health_endpoint", status=VerificationStatus.ERROR, details=str(e)))

        # Check /capabilities
        try:
            resp = await self.client.get(f"{service_url}/capabilities")
            if resp.status_code == 200:
                results.append(CheckResult(name="capabilities_endpoint", status=VerificationStatus.PASS, details="200 OK"))
            else:
                results.append(CheckResult(name="capabilities_endpoint", status=VerificationStatus.FAIL, details=f"Status {resp.status_code}"))
        except Exception as e:
            results.append(CheckResult(name="capabilities_endpoint", status=VerificationStatus.ERROR, details=str(e)))

        return results

