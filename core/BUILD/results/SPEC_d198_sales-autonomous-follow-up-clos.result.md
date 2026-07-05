# SPEC_d198_sales-autonomous-follow-up-clos Result

## Status
Done in working tree. Awaiting review and merge. No push, PR, deploy, live send, or payment action performed.

## Files Changed
- `tools/growth/sales_followup.py`
- `tools/growth/test_sales_followup.py`
- `tools/growth/process_leads.py`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d198_sales-autonomous-follow-up-clos.result.md`
- `docs/codex/HANDOFF.md`

## Summary
Added a guarded per-lead sales follow-up agent for post-assessment leads.

The agent:
- reads the lead plus Allocation Score deliverable, stated bottleneck, weakest dimension, and opportunities;
- drafts a 4-touch James + AI sequence: value follow-up, soft booking CTA, Blueprint offer, and objection handling;
- reads reply fixtures/output from the inbox layer and drafts context-aware responses;
- tracks engagement events and stage (`delivered -> engaged -> booked -> proposed -> won/lost`) in local state and optionally `brain_index.sales_followups`;
- writes a review lane, touch JSONL ledger, and Human Edge approval gates for every send by default;
- supports standing approval only when `SALES_AUTOSEND=1` and `--live` are both present, with rate limiting and a kill switch;
- explicitly escalates close/payment territory to James with a dedicated `sales-close-<lead>` Human Edge gate.

`tools/growth/process_leads.py` now stages the follow-up plan after a successful assessment delivery. The hook does not block or resend the assessment if follow-up staging fails.

## Guardrails
- Default mode never sends to a real prospect.
- Public send requires either Human Edge approval or `SALES_AUTOSEND=1` standing approval.
- `SALES_AUTOSEND=1` still cannot auto-charge or auto-close.
- Kill switch: `/opt/fpai-build/.sales_followup_disabled`.
- Rate limit: `SALES_FOLLOWUP_MIN_SECONDS` defaults to 3600.
- Every touch includes compliance copy and the required James + AI signature.

## Tests
- `python3 -B -m unittest tools.growth.test_sales_followup` — 6 OK
- `python3 -B -m unittest tools.growth.test_process_leads tools.growth.test_score_assessment tools.growth.test_sales_followup` — 19 OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/growth/sales_followup.py tools/growth/test_sales_followup.py tools/growth/process_leads.py tools/growth/test_process_leads.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d198-registry-building.json`
- `git diff --check`

## Risks
- Live inbox reading remains delegated to the existing inbox/champion-sign path; this module consumes reply JSON/fixtures or caller-provided replies.
- Live Brevo send proof was not run in this sandbox.
- Optional `brain_index` tracking only writes when `BRAIN_INDEX_DSN` or `DATABASE_URL` is configured and `psycopg2` is available.

## Rollback
Revert this branch. Runtime mitigation without rollback: leave `SALES_AUTOSEND` unset, or touch `/opt/fpai-build/.sales_followup_disabled`.

## Intent Solved
Assessment delivery can now advance into a guarded autonomous sales follow-up lane instead of stopping at the first email.

## Downstream Intent Unlocked
With James approval or `SALES_AUTOSEND=1`, the funnel can run end-to-end through follow-up and reply drafting while preserving the public-send and payment/close walls.
