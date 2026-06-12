"""
Recruiting Hub service.

Implements a gated role-spec recruiting pipeline where AI-generated screening
is advisory, candidate contact is explicitly approved, and hiring decisions are
recorded only as James-owned decisions.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import os
import re
import uuid


DATA_PATH = Path(os.getenv("DATA_PATH", str(Path(__file__).parent.parent.parent / "data")))
ROLE_SPECS_FILE = DATA_PATH / "role_specs.json"
CANDIDATES_FILE = DATA_PATH / "candidates.json"
AUDIT_LOG_FILE = DATA_PATH / "recruiting_audit_log.json"
CONTACT_ALLOWED_CONSENT = {"candidate_submitted", "james_authorized", "contacted"}
PIPELINE_STATUSES = {
    "new",
    "needs_screening",
    "screened",
    "needs_james_review",
    "contact_approved",
    "interviewing",
    "decision_needed",
    "archived",
    "advance",
    "hold",
    "pass",
    "offer",
    "hired",
}
REVIEW_PRIORITY = {
    "needs_james_review": 10,
    "decision_needed": 20,
    "new": 30,
    "needs_screening": 40,
    "screened": 50,
    "interviewing": 60,
    "contact_approved": 70,
    "hold": 80,
    "offer": 90,
    "advance": 100,
    "pass": 900,
    "archived": 950,
    "hired": 1000,
}
BLOCKED_PRIVATE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:api[_ -]?key|secret[_ -]?key|access[_ -]?token|password)\s*[:=]", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
]


def utc_now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _read_json(path: Path, default: Any) -> Any:
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(default, indent=2))
        return default
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, data: Any) -> None:
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or str(uuid.uuid4())


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9+-]*", value.lower())
        if len(token) > 2
    }


def _privacy_violations(values: List[str]) -> List[str]:
    text = "\n".join(value for value in values if value)
    violations = []
    for pattern in BLOCKED_PRIVATE_PATTERNS:
        if pattern.search(text):
            violations.append(pattern.pattern)
    return violations


def seed_human_context_steward_role() -> Dict[str, Any]:
    """Create the first Rung 4 seat if role storage is empty."""
    roles = _read_json(ROLE_SPECS_FILE, [])
    existing = next((role for role in roles if role.get("id") == "human-context-steward"), None)
    if existing:
        return existing

    role = {
        "id": "human-context-steward",
        "seat_name": "Human Context Steward",
        "rung": 4,
        "mission": (
            "Protect the living context around James, FPAI, collaborators, "
            "candidates, projects, and decisions."
        ),
        "outcomes": [
            "James gets clearer continuity across active work, relationships, and decisions.",
            "Candidate and collaborator context is handled with discretion.",
            "AI-generated summaries are checked for tone, missing nuance, and false certainty.",
            "Memory hygiene improves without becoming invasive.",
        ],
        "responsibilities": [
            "Maintain concise context briefs for active people, projects, and decisions.",
            "Review AI summaries for accuracy, consent boundaries, and relational tone.",
            "Flag sensitive context that should not be broadly distributed to agents.",
            "Prepare high-context handoffs before meetings, calls, hiring decisions, and negotiations.",
            "Keep candidate-facing communication warm, honest, and appropriately scoped.",
        ],
        "must_have_traits": [
            "High discretion and trustworthiness.",
            "Excellent written judgment.",
            "Comfort working beside AI without outsourcing human judgment.",
            "Ability to preserve nuance under time pressure.",
            "Strong boundary sense around privacy, consent, and sensitive context.",
        ],
        "strong_signals": [
            "Executive assistance, people ops, recruiting coordination, community stewardship, editorial work, chief-of-staff support, or founder support.",
            "Writes clearly without sounding corporate.",
            "Can summarize complex human situations without becoming reductive.",
            "Notices when an AI answer is plausible but socially wrong.",
        ],
        "disqualifiers": [
            "Treats candidate or collaborator context as raw data to exploit.",
            "Over-indexes on automation at the expense of consent.",
            "Cannot keep confidential information compartmentalized.",
            "Uses AI outputs without review.",
            "Pushes decisions past James without explicit authorization.",
        ],
        "access_level": "restricted",
        "compensation_guardrail": None,
        "time_commitment": "TBD",
        "status": "draft",
        "approved_by_james": False,
        "approved_at": None,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    roles.append(role)
    _write_json(ROLE_SPECS_FILE, roles)
    audit("role_seeded", "role_spec", role["id"], "system", {"seat_name": role["seat_name"]})
    return role


def audit(event: str, entity_type: str, entity_id: str, actor: str, details: Optional[Dict[str, Any]] = None) -> None:
    entries = _read_json(AUDIT_LOG_FILE, [])
    entries.append(
        {
            "id": str(uuid.uuid4()),
            "event": event,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "actor": actor,
            "details": details or {},
            "created_at": utc_now(),
        }
    )
    _write_json(AUDIT_LOG_FILE, entries)


def list_roles() -> List[Dict[str, Any]]:
    seed_human_context_steward_role()
    roles = _read_json(ROLE_SPECS_FILE, [])
    return sorted(roles, key=lambda role: role.get("created_at", ""), reverse=True)


def get_role(role_id: str) -> Optional[Dict[str, Any]]:
    return next((role for role in list_roles() if role.get("id") == role_id), None)


def create_role(payload: Dict[str, Any], actor: str = "james") -> Dict[str, Any]:
    roles = list_roles()
    seat_name = payload["seat_name"].strip()
    role_id = payload.get("id") or _slugify(seat_name)
    if any(role.get("id") == role_id for role in roles):
        role_id = f"{role_id}-{uuid.uuid4().hex[:8]}"

    role = {
        "id": role_id,
        "seat_name": seat_name,
        "rung": int(payload.get("rung", 4)),
        "mission": payload.get("mission", "").strip(),
        "outcomes": payload.get("outcomes", []),
        "responsibilities": payload.get("responsibilities", []),
        "must_have_traits": payload.get("must_have_traits", []),
        "strong_signals": payload.get("strong_signals", []),
        "disqualifiers": payload.get("disqualifiers", []),
        "access_level": payload.get("access_level", "restricted"),
        "compensation_guardrail": payload.get("compensation_guardrail"),
        "time_commitment": payload.get("time_commitment", "TBD"),
        "status": "draft",
        "approved_by_james": False,
        "approved_at": None,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    roles.append(role)
    _write_json(ROLE_SPECS_FILE, roles)
    audit("role_created", "role_spec", role_id, actor, {"seat_name": seat_name})
    return role


def approve_role(role_id: str, actor: str = "james") -> Dict[str, Any]:
    roles = list_roles()
    for role in roles:
        if role.get("id") == role_id:
            role["approved_by_james"] = True
            role["approved_at"] = utc_now()
            role["status"] = "approved"
            role["updated_at"] = utc_now()
            _write_json(ROLE_SPECS_FILE, roles)
            audit("role_approved", "role_spec", role_id, actor)
            return role
    raise KeyError("Role not found")


def list_candidates(role_spec_id: Optional[str] = None) -> List[Dict[str, Any]]:
    candidates = _read_json(CANDIDATES_FILE, [])
    if role_spec_id:
        candidates = [candidate for candidate in candidates if candidate.get("role_spec_id") == role_spec_id]
    return sorted(candidates, key=lambda candidate: candidate.get("created_at", ""), reverse=True)


def get_candidate(candidate_id: str) -> Optional[Dict[str, Any]]:
    return next((candidate for candidate in list_candidates() if candidate.get("id") == candidate_id), None)


def create_candidate(payload: Dict[str, Any], actor: str = "james") -> Dict[str, Any]:
    role = get_role(payload["role_spec_id"])
    if not role:
        raise KeyError("Role not found")

    privacy_violations = _privacy_violations(
        payload.get("materials", [])
        + payload.get("notes", [])
        + payload.get("public_links", [])
        + [
            payload.get("background", ""),
            payload.get("why_role", ""),
            payload.get("discretion_example", ""),
            payload.get("ai_collaboration_example", ""),
            payload.get("writing_sample", ""),
            payload.get("availability", ""),
            payload.get("compensation_expectations", ""),
        ]
    )
    if privacy_violations:
        raise ValueError(
            "Candidate materials appear to include secrets or highly sensitive identifiers. "
            "Remove them before storing candidate context."
        )

    candidates = list_candidates()
    candidate_id = str(uuid.uuid4())
    candidate = {
        "id": candidate_id,
        "role_spec_id": payload["role_spec_id"],
        "name": payload["name"].strip(),
        "source": payload.get("source", "manual").strip(),
        "contact_channel": payload.get("contact_channel"),
        "consent_status": payload.get("consent_status", "unknown"),
        "public_links": payload.get("public_links", []),
        "background": payload.get("background", ""),
        "why_role": payload.get("why_role", ""),
        "discretion_example": payload.get("discretion_example", ""),
        "ai_collaboration_example": payload.get("ai_collaboration_example", ""),
        "writing_sample": payload.get("writing_sample", ""),
        "availability": payload.get("availability", ""),
        "compensation_expectations": payload.get("compensation_expectations", ""),
        "materials": payload.get("materials", []),
        "notes": payload.get("notes", []),
        "pipeline_status": "new",
        "screening": None,
        "contact_approval": None,
        "hiring_decision": {
            "decided_by_james": False,
            "decision": "no_decision",
            "rationale": "",
            "decided_at": None,
        },
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    candidates.append(candidate)
    _write_json(CANDIDATES_FILE, candidates)
    audit("candidate_created", "candidate", candidate_id, actor, {"role_spec_id": payload["role_spec_id"]})
    return candidate


def screen_candidate(candidate_id: str, actor: str = "ai_screener") -> Dict[str, Any]:
    candidates = list_candidates()
    candidate = next((item for item in candidates if item.get("id") == candidate_id), None)
    if not candidate:
        raise KeyError("Candidate not found")

    role = get_role(candidate["role_spec_id"])
    if not role:
        raise KeyError("Role not found")
    if not role.get("approved_by_james"):
        raise PermissionError("Role must be approved by James before screening")

    corpus = " ".join(
        [
            candidate.get("source", ""),
            " ".join(candidate.get("public_links", [])),
            candidate.get("background", ""),
            candidate.get("why_role", ""),
            candidate.get("discretion_example", ""),
            candidate.get("ai_collaboration_example", ""),
            candidate.get("writing_sample", ""),
            candidate.get("availability", ""),
            candidate.get("compensation_expectations", ""),
            " ".join(candidate.get("materials", [])),
            " ".join(candidate.get("notes", [])),
        ]
    )
    corpus_tokens = _tokens(corpus)

    criteria = (
        role.get("must_have_traits", [])
        + role.get("strong_signals", [])
        + role.get("responsibilities", [])
        + role.get("outcomes", [])
    )
    scored_items = []
    matched = []
    unknowns = []
    for criterion in criteria:
        criterion_tokens = _tokens(criterion)
        overlap = sorted(corpus_tokens.intersection(criterion_tokens))
        if overlap:
            matched.append(f"{criterion} (matched: {', '.join(overlap[:5])})")
            scored_items.append(1)
        else:
            unknowns.append(criterion)
            scored_items.append(0)

    disqualifier_hits = []
    for disqualifier in role.get("disqualifiers", []):
        overlap = sorted(corpus_tokens.intersection(_tokens(disqualifier)))
        if len(overlap) >= 2:
            disqualifier_hits.append(f"Inspect possible disqualifier: {disqualifier}")

    raw_score = int((sum(scored_items) / max(len(scored_items), 1)) * 100)
    score = max(0, raw_score - (len(disqualifier_hits) * 15))
    if score >= 70:
        recommendation = "strong_shortlist"
    elif score >= 45:
        recommendation = "possible"
    elif score >= 25:
        recommendation = "hold"
    else:
        recommendation = "not_recommended"

    screening = {
        "fit_score": score,
        "recommendation": recommendation,
        "evidence": matched[:8] or ["No strong evidence found in candidate materials yet."],
        "risks": disqualifier_hits or ["No disqualifier evidence detected by deterministic screening."],
        "unknowns": unknowns[:8],
        "bias_notes": [
            "Deterministic screening can miss non-keyword evidence.",
            "Scores are advisory and must not replace human judgment.",
        ],
        "confidence": "medium" if matched else "low",
        "screened_at": utc_now(),
        "screened_by": actor,
    }

    candidate["screening"] = screening
    candidate["pipeline_status"] = "needs_james_review" if recommendation in {"strong_shortlist", "possible"} else "screened"
    candidate["updated_at"] = utc_now()
    _write_json(CANDIDATES_FILE, candidates)
    audit("candidate_screened", "candidate", candidate_id, actor, screening)
    return candidate


def approve_contact(candidate_id: str, payload: Dict[str, Any], actor: str = "james") -> Dict[str, Any]:
    candidates = list_candidates()
    candidate = next((item for item in candidates if item.get("id") == candidate_id), None)
    if not candidate:
        raise KeyError("Candidate not found")
    if candidate.get("consent_status") not in CONTACT_ALLOWED_CONSENT:
        raise PermissionError(
            "Candidate contact requires consent_status candidate_submitted, james_authorized, or contacted"
        )

    required_fields = ["approved_channel", "approved_message", "approved_sender", "approved_timing"]
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        raise ValueError(f"Missing contact gate fields: {', '.join(missing)}")

    approval = {
        "approved_by_james": bool(payload.get("approved_by_james", True)),
        "approved_channel": payload["approved_channel"],
        "approved_message": payload["approved_message"],
        "approved_sender": payload["approved_sender"],
        "approved_timing": payload["approved_timing"],
        "approved_at": utc_now(),
    }
    if not approval["approved_by_james"]:
        raise PermissionError("Contact approval must be explicitly approved by James")

    candidate["contact_approval"] = approval
    candidate["pipeline_status"] = "contact_approved"
    candidate["updated_at"] = utc_now()
    _write_json(CANDIDATES_FILE, candidates)
    audit("contact_approved", "candidate", candidate_id, actor, approval)
    return candidate


def update_candidate_status(candidate_id: str, status: str, note: str = "", actor: str = "james") -> Dict[str, Any]:
    if status not in PIPELINE_STATUSES:
        raise ValueError(f"Status must be one of: {', '.join(sorted(PIPELINE_STATUSES))}")

    candidates = list_candidates()
    candidate = next((item for item in candidates if item.get("id") == candidate_id), None)
    if not candidate:
        raise KeyError("Candidate not found")

    previous_status = candidate.get("pipeline_status")
    candidate["pipeline_status"] = status
    candidate["updated_at"] = utc_now()
    if note:
        candidate.setdefault("notes", []).append(f"{utc_now()} status note: {note}")
    _write_json(CANDIDATES_FILE, candidates)
    audit(
        "candidate_status_updated",
        "candidate",
        candidate_id,
        actor,
        {"from": previous_status, "to": status, "note": note},
    )
    return candidate


def review_queue(role_spec_id: Optional[str] = None, include_archived: bool = False) -> List[Dict[str, Any]]:
    queue = []
    for candidate in list_candidates(role_spec_id=role_spec_id):
        status = candidate.get("pipeline_status", "new")
        if not include_archived and status in {"archived", "pass", "hired"}:
            continue

        if status == "new":
            next_action = "Review intake and decide whether to screen."
        elif status == "needs_screening":
            next_action = "Run screening against the approved rubric."
        elif status == "screened":
            next_action = "Inspect evidence map and decide whether James review is needed."
        elif status == "needs_james_review":
            next_action = "James reviews evidence map, then approves contact, holds, archives, or moves to interview."
        elif status == "contact_approved":
            next_action = "Contact may be sent through the approved channel/message/timing."
        elif status == "interviewing":
            next_action = "Complete interview and add notes; then mark decision needed."
        elif status == "decision_needed":
            next_action = "James records final advance/hold/pass/offer/hire decision."
        elif status == "offer":
            next_action = "James confirms offer terms before any commitment is made."
        else:
            next_action = "No immediate action."

        queue.append(
            {
                "candidate": candidate,
                "status": status,
                "priority": REVIEW_PRIORITY.get(status, 500),
                "next_action": next_action,
                "screening_score": (candidate.get("screening") or {}).get("fit_score"),
                "recommendation": (candidate.get("screening") or {}).get("recommendation"),
            }
        )

    queue.sort(key=lambda item: (item["priority"], item["candidate"].get("updated_at", "")))
    return queue


def record_decision(candidate_id: str, payload: Dict[str, Any], actor: str = "james") -> Dict[str, Any]:
    candidates = list_candidates()
    candidate = next((item for item in candidates if item.get("id") == candidate_id), None)
    if not candidate:
        raise KeyError("Candidate not found")
    if actor.lower() != "james":
        raise PermissionError("Hiring decisions can only be recorded by James")

    decision = payload.get("decision", "no_decision")
    allowed = {"no_decision", "advance", "hold", "pass", "offer", "hire"}
    if decision not in allowed:
        raise ValueError(f"Decision must be one of: {', '.join(sorted(allowed))}")

    candidate["hiring_decision"] = {
        "decided_by_james": True,
        "decision": decision,
        "rationale": payload.get("rationale", ""),
        "decided_at": utc_now(),
    }
    candidate["pipeline_status"] = "hired" if decision == "hire" else decision
    candidate["updated_at"] = utc_now()
    _write_json(CANDIDATES_FILE, candidates)
    audit("hiring_decision_recorded", "candidate", candidate_id, actor, candidate["hiring_decision"])
    return candidate


def shortlist(role_spec_id: str) -> Dict[str, Any]:
    role = get_role(role_spec_id)
    if not role:
        raise KeyError("Role not found")
    candidates = [
        candidate
        for candidate in list_candidates(role_spec_id)
        if candidate.get("screening")
    ]
    candidates.sort(key=lambda item: item["screening"].get("fit_score", 0), reverse=True)
    return {
        "role": role,
        "candidates": candidates,
        "generated_at": utc_now(),
        "decision_boundary": "AI ranking is advisory. James approves contact and owns final hire decisions.",
    }


def launch_packet(role_spec_id: str) -> Dict[str, Any]:
    role = get_role(role_spec_id)
    if not role:
        raise KeyError("Role not found")

    seat_name = role["seat_name"]
    compensation = role.get("compensation_guardrail") or "TBD with James before outreach"
    time_commitment = role.get("time_commitment") or "TBD"
    responsibilities = role.get("responsibilities", [])
    outcomes = role.get("outcomes", [])
    must_haves = role.get("must_have_traits", [])
    strong_signals = role.get("strong_signals", [])
    disqualifiers = role.get("disqualifiers", [])

    public_role_post = {
        "title": seat_name,
        "summary": role.get("mission", ""),
        "why_this_matters": (
            "This is a high-trust support role for a founder-led AI operating system. "
            "The work is less about moving tasks quickly and more about preserving context, "
            "discretion, tone, and human judgment while AI handles more operational load."
        ),
        "outcomes": outcomes,
        "responsibilities": responsibilities,
        "must_have_traits": must_haves,
        "strong_signals": strong_signals,
        "compensation": compensation,
        "time_commitment": time_commitment,
        "how_to_apply": "Send a concise note, relevant background, and 1-2 examples of context-sensitive work.",
    }

    rubric = [
        {
            "criterion": "Discretion and trustworthiness",
            "weight": 25,
            "look_for": [
                "Clear boundary sense around private information.",
                "History of trusted support roles or sensitive editorial/context work.",
                "Avoids oversharing and does not dramatize confidential context.",
            ],
            "red_flags": [
                "Treats people-context as raw material.",
                "Casual handling of secrets or sensitive personal information.",
            ],
        },
        {
            "criterion": "Written judgment",
            "weight": 20,
            "look_for": [
                "Can compress nuance without sounding corporate or reductive.",
                "Writes warmly, plainly, and precisely.",
            ],
            "red_flags": [
                "Over-polished generic voice.",
                "Summaries that erase uncertainty or emotional texture.",
            ],
        },
        {
            "criterion": "AI collaboration maturity",
            "weight": 15,
            "look_for": [
                "Uses AI as a thinking and drafting partner, not an authority.",
                "Can identify plausible-but-socially-wrong AI outputs.",
            ],
            "red_flags": [
                "Wants AI to make human decisions.",
                "Trusts model output without inspection.",
            ],
        },
        {
            "criterion": "Context stewardship",
            "weight": 20,
            "look_for": [
                "Keeps threads, people, decisions, and commitments coherent over time.",
                "Can distinguish what should be remembered from what should be forgotten.",
            ],
            "red_flags": [
                "Creates sprawling notes without prioritization.",
                "Cannot compartmentalize access or sensitivity.",
            ],
        },
        {
            "criterion": "Operational reliability",
            "weight": 20,
            "look_for": [
                "Follows through calmly.",
                "Can handle founder-paced ambiguity without inventing certainty.",
            ],
            "red_flags": [
                "Needs perfectly defined tasks before moving.",
                "Pushes decisions past James without explicit approval.",
            ],
        },
    ]

    sourcing_queries = [
        '"executive assistant" "AI" "founder" "confidential"',
        '"chief of staff" "context" "founder support"',
        '"people operations" "community" "editorial" "AI"',
        '"recruiting coordinator" "executive assistant" "discretion"',
        '"community steward" "operations" "founder"',
        '"editorial assistant" "confidential" "context"',
    ]

    outreach_drafts = [
        {
            "name": "Warm referral",
            "message": (
                "Hi {name}, I am exploring a high-trust Human Context Steward role around founder support, "
                "AI-assisted operations, and careful context management. {referrer} thought you might have "
                "the right mix of discretion and judgment. Would you be open to a short conversation?"
            ),
        },
        {
            "name": "Direct candidate",
            "message": (
                "Hi {name}, your background stood out for a role I am shaping called Human Context Steward. "
                "It involves preserving context, privacy, tone, and continuity around a founder-led AI system. "
                "No pressure, but would you be open to learning more?"
            ),
        },
        {
            "name": "Application follow-up",
            "message": (
                "Hi {name}, thank you for your note. I am reviewing candidates slowly because this is a trust-heavy role. "
                "The next step would be a short conversation about discretion, context handling, AI collaboration, "
                "and working rhythm."
            ),
        },
    ]

    interview_plan = [
        {
            "stage": "Context and trust screen",
            "questions": [
                "Tell me about a time you handled sensitive context for someone else.",
                "What kinds of information should not be written down, even if it would be convenient?",
                "How do you decide what to remember, summarize, or let fade?",
            ],
        },
        {
            "stage": "AI collaboration screen",
            "questions": [
                "Show me how you would review an AI-generated summary of a sensitive conversation.",
                "What would make you distrust a plausible AI answer?",
                "Where should AI help, and where should it stay out of the decision?",
            ],
        },
        {
            "stage": "Writing and judgment exercise",
            "questions": [
                "Rewrite a messy project update into a clear, humane handoff.",
                "Mark what is known, inferred, sensitive, and unknown.",
                "Draft a candidate message that is warm but not overpromising.",
            ],
        },
    ]

    decision_packet_template = {
        "candidate": "",
        "known_evidence": [],
        "unverified_inferences": [],
        "unknowns_to_resolve": [],
        "privacy_or_trust_risks": [],
        "rubric_scores": [
            {"criterion": item["criterion"], "score": None, "notes": ""}
            for item in rubric
        ],
        "ai_recommendation": "advisory_only",
        "james_decision": "no_decision",
        "decision_rationale": "",
    }

    return {
        "role": role,
        "generated_at": utc_now(),
        "decision_boundary": "Launch materials are drafts. James approves role, contact, and final decision.",
        "public_role_post": public_role_post,
        "private_rubric": rubric,
        "sourcing_queries": sourcing_queries,
        "outreach_drafts": outreach_drafts,
        "interview_plan": interview_plan,
        "decision_packet_template": decision_packet_template,
    }


def candidate_evidence_map(candidate_id: str) -> Dict[str, Any]:
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise KeyError("Candidate not found")
    role = get_role(candidate["role_spec_id"])
    if not role:
        raise KeyError("Role not found")

    screening = candidate.get("screening") or {}
    materials = candidate.get("materials", [])
    notes = candidate.get("notes", [])
    public_links = candidate.get("public_links", [])

    known = []
    if candidate.get("source"):
        known.append(f"Source: {candidate['source']}")
    if candidate.get("consent_status"):
        known.append(f"Consent/source state: {candidate['consent_status']}")
    known.extend(materials[:5])
    known.extend(notes[:5])
    structured_fields = [
        ("Background", candidate.get("background")),
        ("Why this role", candidate.get("why_role")),
        ("Discretion example", candidate.get("discretion_example")),
        ("AI collaboration example", candidate.get("ai_collaboration_example")),
        ("Writing/context sample", candidate.get("writing_sample")),
        ("Availability", candidate.get("availability")),
        ("Compensation expectations", candidate.get("compensation_expectations")),
    ]
    known.extend(f"{label}: {value}" for label, value in structured_fields if value)

    unknowns = screening.get("unknowns") or role.get("must_have_traits", [])
    next_questions = [
        "What sensitive context have they handled before, and under what boundaries?",
        "Can they show a writing sample that preserves nuance without overexplaining?",
        "How do they use AI today, and when do they override it?",
        "What availability, compensation, and access level would be appropriate?",
    ]

    return {
        "candidate": candidate,
        "role": role,
        "known_evidence": known,
        "public_links": public_links,
        "ai_inferences": screening.get("evidence", []),
        "risks": screening.get("risks", []),
        "unknowns": unknowns,
        "next_questions": next_questions,
        "confidence": screening.get("confidence", "unscreened"),
        "decision_boundary": "Evidence maps organize review. They do not authorize contact or hiring.",
        "generated_at": utc_now(),
    }


def audit_log(limit: int = 100) -> List[Dict[str, Any]]:
    entries = _read_json(AUDIT_LOG_FILE, [])
    return list(reversed(entries[-limit:]))
