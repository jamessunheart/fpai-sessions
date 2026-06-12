"""
Recruiting Hub router.

Admin-oriented API and dashboard for the gated Rung 4 role-spec pipeline.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
import logging
import os
import secrets

from app.services import recruiting_hub


logger = logging.getLogger(__name__)
router = APIRouter()

templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

ADMIN_KEY = os.getenv("RECRUITING_HUB_ADMIN_KEY") or os.getenv("JOBS_ADMIN_KEY")
AUTH_COOKIE = "recruiting_hub_admin"
LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


class RoleSpecCreate(BaseModel):
    seat_name: str
    rung: int = 4
    mission: str
    outcomes: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    must_have_traits: List[str] = Field(default_factory=list)
    strong_signals: List[str] = Field(default_factory=list)
    disqualifiers: List[str] = Field(default_factory=list)
    access_level: str = "restricted"
    compensation_guardrail: Optional[str] = None
    time_commitment: str = "TBD"


class CandidateCreate(BaseModel):
    role_spec_id: str
    name: str
    source: str = "manual"
    contact_channel: Optional[str] = None
    consent_status: str = "unknown"
    public_links: List[str] = Field(default_factory=list)
    background: str = ""
    why_role: str = ""
    discretion_example: str = ""
    ai_collaboration_example: str = ""
    writing_sample: str = ""
    availability: str = ""
    compensation_expectations: str = ""
    materials: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class ContactApprovalRequest(BaseModel):
    approved_by_james: bool = True
    approved_channel: str
    approved_message: str
    approved_sender: str
    approved_timing: str


class HiringDecisionRequest(BaseModel):
    actor: str = "james"
    decision: str
    rationale: str = ""


class CandidateStatusUpdate(BaseModel):
    status: str
    note: str = ""
    actor: str = "james"


def _model_dump(model: BaseModel) -> Dict:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _is_local_request(request: Request) -> bool:
    host = request.client.host if request.client else ""
    forwarded_host = request.headers.get("host", "").split(":")[0]
    return host in LOCAL_HOSTS or forwarded_host in LOCAL_HOSTS


def _candidate_key(request: Request) -> Optional[str]:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    return (
        request.headers.get("x-admin-key")
        or request.cookies.get(AUTH_COOKIE)
        or request.query_params.get("admin_key")
    )


def _has_admin_access(request: Request) -> bool:
    if ADMIN_KEY:
        candidate = _candidate_key(request)
        return bool(candidate and secrets.compare_digest(candidate, ADMIN_KEY))
    return _is_local_request(request)


def require_recruiting_admin(request: Request) -> None:
    if _has_admin_access(request):
        return
    if ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Recruiting hub admin key required")
    raise HTTPException(
        status_code=503,
        detail="Set RECRUITING_HUB_ADMIN_KEY before exposing the recruiting hub outside localhost",
    )


@router.get("/recruiting/login", response_class=HTMLResponse)
async def recruiting_login_page(request: Request):
    """Admin login page for the recruiting hub."""
    return templates.TemplateResponse(
        "recruiting_login.html",
        {
            "request": request,
            "auth_configured": bool(ADMIN_KEY),
            "local_dev": _is_local_request(request),
            "error": None,
        },
    )


@router.post("/recruiting/login", response_class=HTMLResponse)
async def recruiting_login(request: Request, admin_key: str = Form(...)):
    """Set a short-lived admin cookie after key verification."""
    if not ADMIN_KEY:
        if _is_local_request(request):
            return RedirectResponse(url="/recruiting", status_code=303)
        return templates.TemplateResponse(
            "recruiting_login.html",
            {
                "request": request,
                "auth_configured": False,
                "local_dev": False,
                "error": "Recruiting hub auth is not configured. Set RECRUITING_HUB_ADMIN_KEY.",
            },
            status_code=503,
        )

    if not secrets.compare_digest(admin_key, ADMIN_KEY):
        return templates.TemplateResponse(
            "recruiting_login.html",
            {
                "request": request,
                "auth_configured": True,
                "local_dev": _is_local_request(request),
                "error": "Invalid admin key.",
            },
            status_code=401,
        )

    redirect = RedirectResponse(url="/recruiting", status_code=303)
    redirect.set_cookie(
        AUTH_COOKIE,
        admin_key,
        max_age=60 * 60 * 12,
        httponly=True,
        secure=False,
        samesite="lax",
    )
    return redirect


@router.post("/recruiting/logout")
async def recruiting_logout():
    redirect = RedirectResponse(url="/recruiting/login", status_code=303)
    redirect.delete_cookie(AUTH_COOKIE)
    return redirect


@router.get("/recruiting", response_class=HTMLResponse)
async def recruiting_dashboard(request: Request):
    """Recruiting hub dashboard."""
    if not _has_admin_access(request):
        return RedirectResponse(url="/recruiting/login", status_code=303)

    try:
        roles = recruiting_hub.list_roles()
        candidates = recruiting_hub.list_candidates()
        review_queue = recruiting_hub.review_queue()
        audits = recruiting_hub.audit_log(limit=30)
        return templates.TemplateResponse(
            "recruiting_hub.html",
            {
                "request": request,
                "roles": roles,
                "candidates": candidates,
                "review_queue": review_queue,
                "audits": audits,
                "auth_configured": bool(ADMIN_KEY),
                "local_dev": _is_local_request(request),
            },
        )
    except Exception as exc:
        logger.error("Error loading recruiting dashboard: %s", exc)
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error": "Failed to load recruiting hub",
            },
        )


@router.get("/api/recruiting/roles", dependencies=[Depends(require_recruiting_admin)])
async def list_roles() -> Dict:
    return {"status": "success", "roles": recruiting_hub.list_roles()}


@router.post("/api/recruiting/roles", dependencies=[Depends(require_recruiting_admin)])
async def create_role(role: RoleSpecCreate) -> Dict:
    created = recruiting_hub.create_role(_model_dump(role), actor="james")
    return {"status": "success", "role": created}


@router.get("/api/recruiting/roles/{role_id}", dependencies=[Depends(require_recruiting_admin)])
async def get_role(role_id: str) -> Dict:
    role = recruiting_hub.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return {"status": "success", "role": role}


@router.post("/api/recruiting/roles/{role_id}/approve", dependencies=[Depends(require_recruiting_admin)])
async def approve_role(role_id: str) -> Dict:
    try:
        role = recruiting_hub.approve_role(role_id, actor="james")
        return {"status": "success", "role": role}
    except KeyError:
        raise HTTPException(status_code=404, detail="Role not found")


@router.get("/api/recruiting/candidates", dependencies=[Depends(require_recruiting_admin)])
async def list_candidates(role_spec_id: Optional[str] = None) -> Dict:
    return {
        "status": "success",
        "candidates": recruiting_hub.list_candidates(role_spec_id=role_spec_id),
    }


@router.get("/api/recruiting/review-queue", dependencies=[Depends(require_recruiting_admin)])
async def get_review_queue(role_spec_id: Optional[str] = None, include_archived: bool = False) -> Dict:
    return {
        "status": "success",
        "review_queue": recruiting_hub.review_queue(
            role_spec_id=role_spec_id,
            include_archived=include_archived,
        ),
    }


@router.post("/api/recruiting/candidates", dependencies=[Depends(require_recruiting_admin)])
async def create_candidate(candidate: CandidateCreate) -> Dict:
    try:
        created = recruiting_hub.create_candidate(_model_dump(candidate), actor="james")
        return {"status": "success", "candidate": created}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/recruiting/candidates/{candidate_id}/status", dependencies=[Depends(require_recruiting_admin)])
async def update_candidate_status(candidate_id: str, update: CandidateStatusUpdate) -> Dict:
    payload = _model_dump(update)
    actor = payload.pop("actor", "james")
    try:
        candidate = recruiting_hub.update_candidate_status(candidate_id, actor=actor, **payload)
        return {"status": "success", "candidate": candidate}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/recruiting/candidates/{candidate_id}/screen", dependencies=[Depends(require_recruiting_admin)])
async def screen_candidate(candidate_id: str) -> Dict:
    try:
        candidate = recruiting_hub.screen_candidate(candidate_id)
        return {"status": "success", "candidate": candidate}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/api/recruiting/candidates/{candidate_id}/contact-approval", dependencies=[Depends(require_recruiting_admin)])
async def approve_contact(candidate_id: str, approval: ContactApprovalRequest) -> Dict:
    try:
        candidate = recruiting_hub.approve_contact(candidate_id, _model_dump(approval), actor="james")
        return {"status": "success", "candidate": candidate}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/api/recruiting/candidates/{candidate_id}/decision", dependencies=[Depends(require_recruiting_admin)])
async def record_decision(candidate_id: str, decision: HiringDecisionRequest) -> Dict:
    payload = _model_dump(decision)
    actor = payload.pop("actor", "james")
    try:
        candidate = recruiting_hub.record_decision(candidate_id, payload, actor=actor)
        return {"status": "success", "candidate": candidate}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/api/recruiting/roles/{role_id}/shortlist", dependencies=[Depends(require_recruiting_admin)])
async def get_shortlist(role_id: str) -> Dict:
    try:
        packet = recruiting_hub.shortlist(role_id)
        return {"status": "success", "shortlist": packet}
    except KeyError:
        raise HTTPException(status_code=404, detail="Role not found")


@router.get("/api/recruiting/roles/{role_id}/launch-packet", dependencies=[Depends(require_recruiting_admin)])
async def get_launch_packet(role_id: str) -> Dict:
    try:
        packet = recruiting_hub.launch_packet(role_id)
        return {"status": "success", "launch_packet": packet}
    except KeyError:
        raise HTTPException(status_code=404, detail="Role not found")


@router.get("/api/recruiting/candidates/{candidate_id}/evidence-map", dependencies=[Depends(require_recruiting_admin)])
async def get_candidate_evidence_map(candidate_id: str) -> Dict:
    try:
        evidence_map = recruiting_hub.candidate_evidence_map(candidate_id)
        return {"status": "success", "evidence_map": evidence_map}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/api/recruiting/audit-log", dependencies=[Depends(require_recruiting_admin)])
async def get_audit_log(limit: int = 100) -> Dict:
    return {"status": "success", "audit_log": recruiting_hub.audit_log(limit=limit)}
