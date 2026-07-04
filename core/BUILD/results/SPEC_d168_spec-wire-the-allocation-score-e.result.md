# SPEC_d168_spec-wire-the-allocation-score-e Result

- Status: done in working tree / awaiting independent review + merge
- Branch: `build/SPEC_d168_spec-wire-the-allocation-score-e`
- Files changed: `tools/growth/score_assessment.py`; `tools/growth/test_score_assessment.py`; `tools/intelligence/routing.yaml`; `tools/intelligence/test_model_router.py`; `tools/leads/mail_leads.py`; `tools/leads/test_mail_leads.py`; `core/BUILD/specs/SPEC_d168_spec-wire-the-allocation-score-e.md`; `core/BUILD/results/SPEC_d168_spec-wire-the-allocation-score-e.result.md`; `core/BUILD/REGISTRY.json`; `docs/codex/HANDOFF.md`

## Summary

`score_assessment.run_claude()` now calls `tools.intelligence.model_router.call_model(prompt, "assessment-scorer")` before any direct CLI call. The scorer keeps its lenient JSON extraction and retains a direct `claude -p` fallback that loads the loop Claude env file when present. `tools/intelligence/routing.yaml` now has a dedicated `assessment-scorer` route limited to `claude` and `ollama`, so the assessment path cannot fall through to metered API providers before real-client scoped-key approval.

`tools/leads/mail_leads.py` now detects new leads whose `interest == "allocation-audit"`, writes the remote lead body to a temporary local file, runs `score_assessment.py --lead <temp> --out ~/.config/fpai/leads_mailer/allocation_scores/<lead>.allocation-score.md`, and appends the generated markdown deliverable to James's notification email. Ordinary leads keep the existing notification path.

## Tests

- `python3 -B -m unittest tools.growth.test_score_assessment tools.leads.test_mail_leads tools.intelligence.test_model_router` (15 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/growth/score_assessment.py tools/growth/test_score_assessment.py tools/leads/mail_leads.py tools/leads/test_mail_leads.py tools/intelligence/model_router.py tools/intelligence/test_model_router.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d168-registry.json`
- Fake-CLI smoke: `python3 tools/growth/score_assessment.py --demo` with a temporary `claude` shim produced `/tmp/d168-demo.md` containing `Allocation Score: **60/100**`
- `git diff --check`

## Risks

The sandbox did not run a live authenticated `claude -p` call and did not send a live email to James. The first live allocation-audit lead should confirm that server 162's router/Claude auth is present and that the generated markdown is acceptable in the notification body.

Independent review remains a pre-merge gate.

## Rollback

Revert this branch. Runtime cleanup is limited to removing generated local deliverables under `~/.config/fpai/leads_mailer/allocation_scores/` if desired. No live services, deploys, secrets, money movement, or applicant outreach were changed by this build.

## Intent Solved

d168 wires the Allocation Score engine onto the existing $0 subscription router path and surfaces generated deliverables to James for `allocation-audit` leads.

## Downstream Intent Unlocked

After review/merge, the first real allocation-audit lead can produce a forwardable Allocation Score deliverable without James manually running the scorer or exposing the path to metered API spend.
