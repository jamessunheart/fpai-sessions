# SPEC_d197_funnel-bridge-free-assessment-p result

- Status: done in working tree / awaiting review + merge + James CTA approval
- Branch: `build/SPEC_d197_funnel-bridge-free-assessment-p`
- Files changed: `tools/growth/score_assessment.py`; `tools/growth/process_leads.py`; `tools/growth/test_score_assessment.py`; `tools/growth/test_process_leads.py`; `core/BUILD/specs/SPEC_d197_funnel-bridge-free-assessment-p.md`; `core/BUILD/REGISTRY.json`; `docs/codex/HANDOFF.md`

## Summary

Added the reserved-copy bridge from the free assessment deliverable to the paid Blueprint/free strategy call next step.

- `score_assessment.py` now includes a required `next_step` schema field.
- The prompt explicitly marks `next_step` as DRAFT-only and reserves final James voice, URL, pricing, scarcity, and guarantees.
- The rendered deliverable now ends with a next-step block.
- Default rendering shows `DRAFT - James approval required` and an `ASSESSMENT_CTA_URL` placeholder link.
- Approved rendering uses `ASSESSMENT_CTA_COPY` plus `ASSESSMENT_CTA_URL` to produce a real `## Your next step` section with a working link.
- `process_leads.py` holds live sends if the deliverable still contains the draft marker, URL placeholder, no approved next-step section, or no real HTTP(S) markdown link.

## Tests

- `python3 -B -m unittest tools.growth.test_score_assessment` — 7 OK
- `python3 -B -m unittest tools.growth.test_process_leads` — 6 OK
- `python3 -B -m unittest tools.growth.test_process_leads tools.growth.test_score_assessment tools.leads.test_mail_leads tools.growth.life_assessment.test_champion_life_lead` — 22 OK; existing Pydantic v1 validator deprecation warnings from `SERVICES/champion-sign/main.py`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/growth/score_assessment.py tools/growth/process_leads.py tools/growth/test_score_assessment.py tools/growth/test_process_leads.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d197-registry-building.json`
- `git diff --check`

## Risks

- James still needs to provide and approve the final invitation copy and booking/Blueprint URL.
- Until `ASSESSMENT_CTA_COPY` and `ASSESSMENT_CTA_URL` are configured, live lead delivery will intentionally hold instead of emailing draft marketing copy.
- Live worker/send proof was not run in this sandbox.
- The fuller G3 nurture sequence after the first deliverable remains a separate follow-on build.

## Rollback

Revert this branch. Runtime mitigation without code rollback is to leave `ASSESSMENT_CTA_COPY` or `ASSESSMENT_CTA_URL` unset, which causes live sends containing the draft CTA to hold.

## Intent

- Intent solved: free assessment leads now have a guarded next-step bridge toward the paid Blueprint/free strategy call without autonomously shipping James-voice marketing copy.
- Downstream intent unlocked: after James approves copy and configures the URL, the first assessment email can carry a working path to book/buy.
- Next unlocked move: James/Ember supplies approved `ASSESSMENT_CTA_COPY` and `ASSESSMENT_CTA_URL`, then observes one controlled lead delivery; follow-on G3 nurture sequence can be specced separately.
