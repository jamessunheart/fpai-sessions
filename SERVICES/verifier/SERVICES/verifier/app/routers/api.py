from fastapi import APIRouter, HTTPException
from app.models import VerificationReport, VerificationStatus
from app.services.scanner import ScannerEngine
from datetime import datetime
import uuid

router = APIRouter()
scanner = ScannerEngine()

# In-memory report store
reports_db = {}

@router.post("/verify/{service_url:path}", response_model=VerificationReport)
async def verify_service(service_url: str):
    # Normalize URL
    if not service_url.startswith("http"):
        service_url = f"http://{service_url}"
    
    # Run checks
    results = await scanner.check_udc_compliance(service_url)
    
    # Calculate Score
    passed = len([r for r in results if r.status == VerificationStatus.PASS])
    total = len(results)
    score = int((passed / total) * 100) if total > 0 else 0
    
    # Determine Overall Status
    overall_status = VerificationStatus.PASS if score == 100 else VerificationStatus.FAIL

    report = VerificationReport(
        id=str(uuid.uuid4()),
        service_id=service_url,
        status=overall_status,
        score=score,
        results=results,
        created_at=datetime.utcnow()
    )
    
    reports_db[report.id] = report
    return report

@router.get("/reports", response_model=list[VerificationReport])
async def list_reports():
    return list(reports_db.values())

