# Recruiting Hub Rung 4 - Session Consensus Note

**Date:** 2026-06-12
**Session focus:** Build and harden the Rung 4 Recruiting Hub for the first Human Context Steward hire.
**Current integration branch:** `feat/headless-build`

---

## What Happened

This session began with a request to create `SPEC_recruiting-hub-rung4.md` under `docs/codex/specs/`. The spec established the core boundary:

- AI may screen, structure, compare, and shortlist.
- Every candidate contact is gated by James.
- The final hire decision remains irreducibly James.

The spec then became an implemented FastAPI/Jinja recruiting hub inside `SERVICES/jobs`.

---

## Built

### Recruiting Hub Surface

- Admin dashboard at `/recruiting`.
- Admin login at `/recruiting/login`.
- API namespace under `/api/recruiting/*`.
- JSON-backed storage for role specs, candidates, audit log, and generated review artifacts.
- Seed role: `Human Context Steward`.

### Human Context Steward Pipeline

- Role spec board.
- Candidate intake.
- AI/deterministic screening.
- Shortlist packet.
- Contact approval gate.
- James-only hiring decision recording.
- Audit log.

### Trust and Safety Layer

- Admin key gate via `RECRUITING_HUB_ADMIN_KEY` or `JOBS_ADMIN_KEY`.
- Browser login cookie.
- API auth via `X-Admin-Key` or `Authorization: Bearer ...`.
- Removed admin key auth from URL query params.
- `RECRUITING_HUB_COOKIE_SECURE=true` support for HTTPS deployments.
- Default CORS narrowed to local origins unless `CORS_ALLOW_ORIGINS` is configured.
- Candidate privacy filter blocks obvious secret-like material.
- Contact approval requires explicit consent/source state.

### Launch and Review Tools

- Human Context Steward launch packet:
  - public role post
  - private rubric
  - sourcing queries
  - outreach drafts
  - interview plan
  - decision packet template
- Candidate evidence maps:
  - known evidence
  - AI inferences
  - risks
  - unknowns
  - next questions
- Candidate review inbox:
  - `new`
  - `needs_screening`
  - `screened`
  - `needs_james_review`
  - `contact_approved`
  - `interviewing`
  - `decision_needed`
  - `archived`
  - final decision states: `advance`, `hold`, `pass`, `offer`, `hired`

---

## Pull Requests

### PR #3

**Title:** `[codex] Build rung 4 recruiting hub`
**URL:** https://github.com/jamessunheart/fpai-sessions/pull/3
**State:** Merged
**Merged into:** `feat/headless-build`

### PR #5

**Title:** `[codex] Add recruiting hub readiness tests`
**URL:** https://github.com/jamessunheart/fpai-sessions/pull/5
**State:** Merged
**Merged into:** `feat/headless-build`
**Merged at:** 2026-06-12T16:56:08Z

---

## Verification Performed

- `pytest SERVICES/jobs/tests/test_recruiting_hub.py`
  - Result: `6 passed`
- `python3 -m py_compile SERVICES/jobs/app/main.py SERVICES/jobs/app/routers/recruiting_hub.py SERVICES/jobs/app/services/recruiting_hub.py`
  - Result: passed
- Integrated branch verification:
  - created temporary worktree from `origin/feat/headless-build`
  - confirmed PR #3 and PR #5 are both present
  - ran focused tests successfully
  - started the jobs service on port `8018`
  - confirmed `/recruiting` rendered with HTTP `200`
  - removed temporary verification worktree

GitHub reported no checks configured/reported for these branches.

---

## Important Constraints

- The hub records approvals; it does not send candidate outreach.
- Candidate contact still requires James to approve candidate, channel, message, sender, and timing.
- Hiring decisions can only be recorded with actor `james`.
- Current persistence is JSON files, not a database.
- Auth is admin-key based, appropriate for early internal use but not yet a mature multi-user permissions model.
- Privacy filter catches obvious secrets/SSN-shaped values, not all sensitive personal context.

---

## My Recommendation

For the final integration/consensus session, do not start by adding more autonomy. Start by deciding the operating policy.

Recommended agenda:

1. **Confirm the human boundary**
   - AI can draft, screen, rank, and summarize.
   - James approves contact and decisions.
   - No autonomous outreach yet.

2. **Choose deployment posture**
   - Local-only for first use?
   - Private admin subdomain?
   - VPN or IP allowlist?
   - Required env vars:
     - `RECRUITING_HUB_ADMIN_KEY`
     - `RECRUITING_HUB_COOKIE_SECURE=true` for HTTPS
     - `CORS_ALLOW_ORIGINS` for any deployed admin domain

3. **Approve the Human Context Steward launch packet**
   - role post
   - rubric
   - sourcing queries
   - outreach drafts
   - interview plan

4. **Define first candidate source**
   - referrals only
   - James-named candidates
   - application form
   - public profiles manually reviewed

5. **Decide what not to store**
   - secrets
   - intimate/private third-party context
   - medical/legal/financial sensitive details
   - private relationship context
   - anything not needed for role fit

6. **Nominate next technical increment**
   - deploy privately
   - add tests for dashboard routes
   - add edit/delete flows for candidates
   - add exportable decision packet
   - add a candidate application form with explicit consent language

---

## My View

The right next step is a consensus pass, not another feature burst.

This hub is now powerful enough to touch real people. That means the question is no longer "can the system recruit?" The question is "under what covenant does the system recruit?"

My recommendation is to hold the line:

- make the first Human Context Steward search referral/manual only
- use the hub as a review and memory instrument
- require explicit consent before contact
- keep all outreach human-approved
- treat AI screening as a way to preserve James's attention, not replace James's discernment

If the other sessions agree, the next build should be a small private deployment plus a first-candidate trial, not broad sourcing automation.
