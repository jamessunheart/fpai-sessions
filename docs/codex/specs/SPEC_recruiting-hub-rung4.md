# Recruiting Hub Rung 4: Role-Spec Pipeline

**Created:** 2026-06-12
**Status:** Draft
**Owner:** James
**First Seat:** Human Context Steward
**Security Level:** Restricted

---

## Purpose

Build a recruiting hub that turns role intent into a tight hiring pipeline: role spec, sourcing brief, AI screening, shortlist, gated outreach, interview packet, and final human decision.

The first production role is the **Human Context Steward**: a trusted human operator who helps preserve nuance, continuity, and relational context across AI-assisted workflows.

---

## Core Principle

AI may gather, structure, compare, and recommend. It does not autonomously contact candidates, negotiate, reject, hire, or create obligations.

Every candidate contact is gated by James. The final hire decision stays irreducibly James.

---

## Rung 4 Scope

### In Scope

- Convert rough hiring intent into a reusable role spec.
- Generate a sourcing profile and search query pack.
- Ingest candidate materials from approved sources.
- Score candidates against explicit criteria.
- Produce a ranked shortlist with evidence, caveats, and open questions.
- Draft candidate contact messages for review.
- Prepare interview plans, reference checks, and decision packets.
- Track candidate state through the gated pipeline.

### Out of Scope

- Autonomous candidate outreach.
- Automated rejection messages.
- Automated offer letters or compensation commitments.
- Hiring decisions made by model score alone.
- Collection of sensitive personal data beyond what the candidate voluntarily provides or what is explicitly approved.

---

## Human Context Steward Seat

### Mission

The Human Context Steward protects the living context around James, FPAI, collaborators, candidates, projects, and decisions. They help the system remember what matters without flattening people into tasks.

### Outcomes

- James gets clearer continuity across active work, relationships, and decisions.
- Candidate and collaborator context is handled with discretion.
- AI-generated summaries are checked for tone, missing nuance, and false certainty.
- The system improves its memory hygiene without becoming invasive.

### Responsibilities

- Maintain concise context briefs for active people, projects, and decisions.
- Review AI summaries for accuracy, consent boundaries, and relational tone.
- Flag sensitive context that should not be broadly distributed to agents.
- Help prepare high-context handoffs before meetings, calls, hiring decisions, and negotiations.
- Keep candidate-facing communication warm, honest, and appropriately scoped.

### Must-Have Traits

- High discretion and trustworthiness.
- Excellent written judgment.
- Comfort working beside AI without outsourcing human judgment.
- Ability to preserve nuance under time pressure.
- Strong boundary sense around privacy, consent, and sensitive context.

### Strong Signals

- Background in executive assistance, people ops, recruiting coordination, therapy-adjacent operations, community stewardship, editorial work, chief-of-staff support, or founder support.
- Writes clearly without sounding corporate.
- Can summarize complex human situations without becoming reductive.
- Notices when an AI answer is plausible but socially wrong.

### Disqualifiers

- Treats candidate or collaborator context as raw data to exploit.
- Over-indexes on automation at the expense of consent.
- Cannot keep confidential information compartmentalized.
- Uses AI outputs without review.
- Pushes decisions past James without explicit authorization.

---

## Pipeline

### 1. Role Intake

Inputs:

- Seat name.
- Mission.
- Outcomes.
- Responsibilities.
- Required trust level.
- Access level.
- Compensation range or budget guardrail.
- Time commitment.
- Working style constraints.
- Known dealbreakers.

Output:

- `RoleSpec` with explicit scoring criteria and human-only decision points.

### 2. Role Spec Generation

The hub generates:

- Public-facing role post.
- Internal scoring rubric.
- Candidate sourcing brief.
- Interview question bank.
- Red flag checklist.
- Candidate communication drafts.

James must approve the role spec before sourcing begins.

### 3. Candidate Intake

Allowed sources:

- Direct referrals.
- Candidates James explicitly names.
- Applications submitted through an approved form.
- Public profiles from approved platforms.
- Existing network lists that James explicitly authorizes for this role.

Captured fields:

- Name.
- Contact channel, if already available and approved.
- Source.
- Public links.
- Submitted materials.
- Notes.
- Consent status.
- Pipeline status.

### 4. AI Screening

AI screens candidates only against the approved rubric.

Outputs:

- Fit score.
- Evidence for fit.
- Risks and unknowns.
- Suggested interview focus.
- Bias and confidence notes.
- Recommendation: `strong_shortlist`, `possible`, `hold`, or `not_recommended`.

Screening must include citations to candidate-provided or public material when possible. Unverified inferences must be labeled as inference.

### 5. Shortlist Review

The hub produces a shortlist packet:

- Top candidates.
- Why each candidate is included.
- What is known.
- What is unknown.
- Suggested first contact.
- Suggested interview sequence.
- Specific risks for James to inspect.

James chooses which candidates may be contacted.

### 6. Contact Gate

No contact is sent until James explicitly approves:

- Candidate.
- Channel.
- Message.
- Sender identity.
- Timing.

Approved contact may be sent manually by James or by an assistant acting under explicit instruction.

### 7. Interview Support

The hub prepares:

- Candidate brief.
- Interview agenda.
- Questions tied to the rubric.
- Follow-up probes.
- Evaluation form.
- Post-interview synthesis template.

AI may summarize interview notes. James owns interpretation and next-step decisions.

### 8. Decision Packet

The final packet includes:

- Role criteria.
- Candidate evidence.
- Interview notes.
- Reference notes, if any.
- Compensation and availability fit.
- Risks.
- Open questions.
- AI recommendation with confidence.
- Human decision field.

The final decision field can only be set by James.

---

## Data Model

```python
class RoleSpec:
    id: str
    seat_name: str
    rung: int
    mission: str
    outcomes: list[str]
    responsibilities: list[str]
    must_have_traits: list[str]
    strong_signals: list[str]
    disqualifiers: list[str]
    access_level: str
    compensation_guardrail: str | None
    status: str  # draft, approved, sourcing, interviewing, filled, paused
    approved_by_james: bool

class Candidate:
    id: str
    role_spec_id: str
    name: str
    source: str
    contact_channel: str | None
    consent_status: str  # unknown, candidate_submitted, james_authorized, contacted, withdrawn
    public_links: list[str]
    materials: list[str]
    pipeline_status: str  # sourced, screened, shortlisted, contact_approved, contacted, interviewing, offer_ready, hired, archived
    notes: list[str]

class ScreeningResult:
    candidate_id: str
    role_spec_id: str
    fit_score: float
    recommendation: str  # strong_shortlist, possible, hold, not_recommended
    evidence: list[str]
    risks: list[str]
    unknowns: list[str]
    bias_notes: list[str]
    confidence: str

class ContactApproval:
    candidate_id: str
    approved_by_james: bool
    approved_channel: str | None
    approved_message: str | None
    approved_sender: str | None
    approved_at: str | None

class HiringDecision:
    candidate_id: str
    decided_by_james: bool
    decision: str  # no_decision, advance, hold, pass, offer, hire
    rationale: str
    decided_at: str | None
```

---

## Required Views

### Role Spec Board

- Draft roles.
- Approved roles.
- Active sourcing.
- Interviewing.
- Filled or paused.

### Candidate Review

- Candidate list grouped by role.
- Score and recommendation.
- Evidence summary.
- Risks.
- Unknowns.
- Contact approval state.

### Shortlist Packet

- Compact view for James.
- Shows only candidates ready for human review.
- Makes gates visually obvious: `Needs Role Approval`, `Needs Contact Approval`, `Needs Decision`.

### Decision Console

- Final candidate packet.
- Human notes.
- Decision options.
- Explicit confirmation that AI recommendation is advisory.

---

## Guardrails

- AI recommendations are advisory metadata, not decisions.
- Candidate contact requires explicit approval every time.
- Rejections are drafted only after James approves the decision and message.
- Sensitive notes must be compartmentalized by role and access level.
- The system must preserve uncertainty instead of converting unknowns into fake confidence.
- The hub must log every approval, contact, status change, and final decision.

---

## Acceptance Criteria

- [ ] A Human Context Steward role spec can be created from rough intake.
- [ ] James can approve or edit the role spec before sourcing starts.
- [ ] Candidates can be added without triggering contact.
- [ ] AI can screen candidates and produce evidence-based shortlist packets.
- [ ] Contact actions are blocked until James approves candidate, message, channel, sender, and timing.
- [ ] Interview packets can be generated from the approved rubric.
- [ ] Final hiring decision can only be recorded as James's decision.
- [ ] Audit log shows role approval, candidate screening, contact approvals, and decision events.

---

## Open Questions

- What compensation range should be attached to the Human Context Steward seat?
- Is this initially part-time, fractional, trial project, or full-time?
- Which candidate sources are approved for the first pass?
- Should the first contact come directly from James or from an assistant under James's name?
- What information should be considered too sensitive for the recruiting hub to store?
