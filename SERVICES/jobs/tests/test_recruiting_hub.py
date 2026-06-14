import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest


SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.main import app  # noqa: E402
from app.routers import recruiting_hub as hub_router  # noqa: E402
from app.services import recruiting_hub as hub_service  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(hub_router, "ADMIN_KEY", "test-secret")
    monkeypatch.setattr(hub_service, "DATA_PATH", tmp_path)
    monkeypatch.setattr(hub_service, "ROLE_SPECS_FILE", tmp_path / "role_specs.json")
    monkeypatch.setattr(hub_service, "CANDIDATES_FILE", tmp_path / "candidates.json")
    monkeypatch.setattr(hub_service, "AUDIT_LOG_FILE", tmp_path / "recruiting_audit_log.json")
    return TestClient(app)


def auth_headers():
    return {"X-Admin-Key": "test-secret"}


def approve_seed_role(client):
    roles = client.get("/api/recruiting/roles", headers=auth_headers()).json()["roles"]
    role_id = roles[0]["id"]
    response = client.post(f"/api/recruiting/roles/{role_id}/approve", headers=auth_headers())
    assert response.status_code == 200
    return role_id


def create_candidate(client, role_id, **overrides):
    payload = {
        "role_spec_id": role_id,
        "name": "Mira Steward",
        "source": "referral",
        "contact_channel": "email",
        "consent_status": "james_authorized",
        "background": "Executive assistant and people ops support for founders.",
        "why_role": "Drawn to preserving context and reducing founder cognitive load.",
        "discretion_example": "Handled confidential notes with compartmentalized access.",
        "ai_collaboration_example": "Uses AI for drafts, then checks tone and social correctness.",
        "writing_sample": "Concise handoff with knowns, unknowns, and sensitivities separated.",
        "availability": "10 hours/week",
        "compensation_expectations": "TBD",
        "materials": ["community stewardship editorial context summaries"],
        "notes": ["Strong written judgment signal"],
    }
    payload.update(overrides)
    response = client.post("/api/recruiting/candidates", headers=auth_headers(), json=payload)
    assert response.status_code == 200, response.text
    return response.json()["candidate"]


def test_recruiting_api_requires_admin_key(client):
    assert client.get("/api/recruiting/roles").status_code == 401
    assert client.get("/api/recruiting/roles", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.get("/api/recruiting/roles", headers=auth_headers()).status_code == 200


def test_candidate_privacy_filter_blocks_secret_like_material(client):
    role_id = approve_seed_role(client)
    response = client.post(
        "/api/recruiting/candidates",
        headers=auth_headers(),
        json={
            "role_spec_id": role_id,
            "name": "Secret Candidate",
            "materials": ["password: abc123"],
        },
    )
    assert response.status_code == 400
    assert "secrets" in response.json()["detail"]


def test_contact_approval_requires_consent_state(client):
    role_id = approve_seed_role(client)
    candidate = create_candidate(client, role_id, consent_status="unknown")

    response = client.post(
        f"/api/recruiting/candidates/{candidate['id']}/contact-approval",
        headers=auth_headers(),
        json={
            "approved_by_james": True,
            "approved_channel": "email",
            "approved_message": "Approved message",
            "approved_sender": "James",
            "approved_timing": "today",
        },
    )

    assert response.status_code == 400
    assert "consent_status" in response.json()["detail"]


def test_hiring_decision_requires_james_actor(client):
    role_id = approve_seed_role(client)
    candidate = create_candidate(client, role_id)

    response = client.post(
        f"/api/recruiting/candidates/{candidate['id']}/decision",
        headers=auth_headers(),
        json={"actor": "ai", "decision": "hire", "rationale": "model score"},
    )

    assert response.status_code == 400
    assert "only be recorded by James" in response.json()["detail"]


def test_review_queue_prioritizes_decision_needed(client):
    role_id = approve_seed_role(client)
    create_candidate(client, role_id, name="New Candidate")
    decision_candidate = create_candidate(client, role_id, name="Decision Candidate")

    response = client.post(
        f"/api/recruiting/candidates/{decision_candidate['id']}/status",
        headers=auth_headers(),
        json={"actor": "james", "status": "decision_needed", "note": "Interview complete"},
    )
    assert response.status_code == 200

    queue = client.get("/api/recruiting/review-queue", headers=auth_headers()).json()["review_queue"]
    assert queue[0]["candidate"]["name"] == "Decision Candidate"
    assert queue[0]["status"] == "decision_needed"


def test_invalid_candidate_status_is_rejected(client):
    role_id = approve_seed_role(client)
    candidate = create_candidate(client, role_id)

    response = client.post(
        f"/api/recruiting/candidates/{candidate['id']}/status",
        headers=auth_headers(),
        json={"actor": "james", "status": "teleported"},
    )

    assert response.status_code == 400
    assert "Status must be one of" in response.json()["detail"]
