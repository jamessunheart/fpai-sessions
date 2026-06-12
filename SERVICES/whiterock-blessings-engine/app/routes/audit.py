"""
WhiteRock Blessings Engine - Audit & Compliance Endpoints
Compliance export, integrity checks, and audit logs.
"""

import io
import zipfile
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.database import get_db
from app.models import Member, Tithe, BlessingRequest, AuditLog
from app.schemas import IntegrityCheckResponse, AuditLogEntry
from app.auth import require_auditor
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/compliance-export")
async def export_compliance_data(
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    auditor: Member = Depends(require_auditor),
    db: AsyncSession = Depends(get_db)
):
    """
    Export compliance data as ZIP file.
    Contains disclosure acknowledgments linked to tithes.
    Auditor only.
    """
    if not start_date:
        start_date = datetime(datetime.utcnow().year, 1, 1)
    if not end_date:
        end_date = datetime.utcnow()
    
    # Get tithes with disclosure data
    result = await db.execute(
        select(Tithe, Member).join(Member).where(
            Tithe.created_at >= start_date,
            Tithe.created_at <= end_date
        ).order_by(Tithe.created_at.asc())
    )
    
    # Prepare CSV
    csv_lines = ["tithe_id,member_id,member_email,amount_cents,disclosure_version,disclosure_acknowledged,scrolled_confirmed,timestamp,disclosure_text_hash"]
    disclosure_texts = {}
    
    for tithe, member in result:
        text_hash = hashlib.sha256(tithe.disclosure_text.encode()).hexdigest()[:16]
        disclosure_texts[text_hash] = tithe.disclosure_text
        
        csv_lines.append(
            f"{tithe.id},{member.id},{member.email},{tithe.amount_cents},"
            f"{tithe.disclosure_version},{tithe.disclosure_acknowledged},"
            f"{tithe.disclosure_scrolled_confirmed},{tithe.created_at.isoformat()},{text_hash}"
        )
    
    # Create ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add CSV
        zf.writestr("disclosures.csv", "\n".join(csv_lines))
        
        # Add disclosure texts
        for text_hash, text_content in disclosure_texts.items():
            zf.writestr(f"disclosure_texts/{text_hash}.txt", text_content)
        
        # Add export metadata
        metadata = f"""WhiteRock Compliance Export
Generated: {datetime.utcnow().isoformat()}
Date Range: {start_date.isoformat()} to {end_date.isoformat()}
Exported By: {auditor.email}
Total Records: {len(csv_lines) - 1}
"""
        zf.writestr("export_metadata.txt", metadata)
    
    zip_buffer.seek(0)
    
    filename = f"compliance-export-{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}.zip"
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/integrity-check", response_model=IntegrityCheckResponse)
async def run_integrity_check(
    auditor: Member = Depends(require_auditor),
    db: AsyncSession = Depends(get_db)
):
    """
    Run integrity check for compliance verification.
    Verifies zero treasury links and data consistency.
    Auditor only.
    """
    issues = []
    
    # Check 1: Foreign key violations (orphaned records)
    fk_violations = 0
    orphaned = 0
    
    # Check tithes without members
    result = await db.execute(text("""
        SELECT COUNT(*) FROM tithes t 
        LEFT JOIN members m ON t.member_id = m.id 
        WHERE m.id IS NULL
    """))
    count = result.scalar_one()
    if count > 0:
        orphaned += count
        issues.append(f"Found {count} orphaned tithe records")
    
    # Check blessings without members
    result = await db.execute(text("""
        SELECT COUNT(*) FROM blessing_requests b 
        LEFT JOIN members m ON b.member_id = m.id 
        WHERE m.id IS NULL
    """))
    count = result.scalar_one()
    if count > 0:
        orphaned += count
        issues.append(f"Found {count} orphaned blessing request records")
    
    # Check 2: Treasury links (CRITICAL - should NEVER find any)
    treasury_links = False
    
    # Check for any tables with treasury/trade references
    treasury_keywords = ['trade', 'position', 'market', 'treasury', 'portfolio', 'order']
    result = await db.execute(text("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public'
    """))
    tables = [row[0] for row in result]
    
    for table in tables:
        for keyword in treasury_keywords:
            if keyword in table.lower():
                treasury_links = True
                issues.append(f"CRITICAL: Found treasury-related table: {table}")
    
    # Check for columns with treasury references
    result = await db.execute(text("""
        SELECT table_name, column_name FROM information_schema.columns 
        WHERE table_schema = 'public' AND (
            column_name LIKE '%trade%' OR 
            column_name LIKE '%position%' OR
            column_name LIKE '%market%' OR
            column_name LIKE '%treasury%'
        )
    """))
    for row in result:
        treasury_links = True
        issues.append(f"CRITICAL: Found treasury-related column: {row[0]}.{row[1]}")
    
    # Check 3: Invalid blessing state transitions
    invalid_transitions = 0
    result = await db.execute(
        select(BlessingRequest).where(BlessingRequest.state_transition_log.isnot(None))
    )
    
    valid_transitions = {
        "draft": ["pending"],
        "pending": ["committee_review"],
        "committee_review": ["info_requested", "approved", "denied"],
        "info_requested": ["committee_review"],
        "approved": ["disbursed"],
        "disbursed": ["closed"],
        "denied": ["closed"],
        "closed": []
    }
    
    for blessing in result.scalars():
        log = blessing.state_transition_log or []
        for i, entry in enumerate(log):
            if i > 0:
                prev_state = log[i-1].get("to")
                curr_from = entry.get("from")
                curr_to = entry.get("to")
                
                if curr_from != prev_state:
                    invalid_transitions += 1
                    issues.append(f"Blessing {blessing.id}: State mismatch at transition {i}")
                
                if curr_to not in valid_transitions.get(curr_from, []):
                    invalid_transitions += 1
                    issues.append(f"Blessing {blessing.id}: Invalid transition {curr_from} → {curr_to}")
    
    # Check 4: Compliance flag violations
    compliance_violations = 0
    result = await db.execute(
        select(BlessingRequest).where(
            BlessingRequest.status.in_(["approved", "disbursed", "closed"]),
            BlessingRequest.amount_approved_cents > 0,
            BlessingRequest.compliance_flag == False
        )
    )
    violations = result.scalars().all()
    compliance_violations = len(violations)
    if compliance_violations > 0:
        issues.append(f"Found {compliance_violations} approvals without compliance flag")
    
    # Determine overall status
    is_pass = (
        not treasury_links and 
        fk_violations == 0 and 
        orphaned == 0 and 
        invalid_transitions == 0 and
        compliance_violations == 0
    )
    
    return IntegrityCheckResponse(
        check_timestamp=datetime.utcnow(),
        foreign_key_violations=fk_violations,
        orphaned_records=orphaned,
        treasury_links_found=treasury_links,
        invalid_state_transitions=invalid_transitions,
        compliance_flag_violations=compliance_violations,
        status="PASS" if is_pass else "FAIL",
        issues=issues
    )


@router.get("/log")
async def get_audit_log(
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    entity_type: str = Query(None),
    severity: str = Query(None),
    actor_id: int = Query(None),
    limit: int = Query(100, le=1000),
    auditor: Member = Depends(require_auditor),
    db: AsyncSession = Depends(get_db)
):
    """
    Query audit log with filters.
    Auditor only.
    """
    audit_service = AuditService(db)
    
    logs = await audit_service.get_logs(
        entity_type=entity_type,
        actor_id=actor_id,
        severity=severity,
        start_date=start_date,
        end_date=end_date,
        limit=limit
    )
    
    return {
        "entries": [
            AuditLogEntry(
                id=log.id,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                actor_id=log.actor_id,
                actor_role=log.actor_role,
                old_values=log.old_values,
                new_values=log.new_values,
                severity=log.severity,
                created_at=log.created_at
            )
            for log in logs
        ],
        "count": len(logs),
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "entity_type": entity_type,
            "severity": severity,
            "actor_id": actor_id
        }
    }



