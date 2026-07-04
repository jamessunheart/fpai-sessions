# SPEC_d164_spec-growth-stack-master-plan-th Result

- Status: done in working tree / awaiting review + merge
- Branch: `build/SPEC_d164_spec-growth-stack-master-plan-th`
- Date: 2026-07-04

## Summary

Implemented the missing Growth Stack G3/G5 bridge for the master plan:

- `tools/growth/nurture_router.py` routes inbound assessment leads from dimension scores or proxy text to BBB v1.4 buckets, builds a 5-email sequence, emits listmonk/n8n dry-run payloads, and writes each email as a growth-ledger asset with `utm_campaign` attribution preserved.
- `tools/growth/growth_allocator.py` scores assets by Growth CCD, kills assets below channel floors, breeds champion children with exactly one mutated gene, caps the next ad allocation at `$10`, emits a local allocation plan, and distills ledger-proven champions into `core/STATE/WINNING_PATTERNS.md`.
- Proof artifacts under `core/BUILD/results/` show one test lead routed to Blueprint nurture, five email ledger rows emitted, one full kill/breed/allocate cycle completed, two assets killed, two champions bred, and winning patterns updated.

No live email send, Postiz scheduling, Meta API call, spend, deploy, service change, secret read, push, or merge was performed.

## Files Changed

- `tools/growth/nurture_router.py`
- `tools/growth/test_nurture_router.py`
- `tools/growth/growth_allocator.py`
- `tools/growth/test_growth_allocator.py`
- `core/STATE/WINNING_PATTERNS.md`
- `core/BUILD/specs/SPEC_d164_spec-growth-stack-master-plan-th.md`
- `core/BUILD/results/SPEC_d164_lead.fixture.json`
- `core/BUILD/results/SPEC_d164_nurture_packet.json`
- `core/BUILD/results/SPEC_d164_nurture_ledger.jsonl`
- `core/BUILD/results/SPEC_d164_growth_assets.fixture.jsonl`
- `core/BUILD/results/SPEC_d164_growth_allocator_plan.json`
- `core/BUILD/results/SPEC_d164_spec-growth-stack-master-plan-th.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.growth.test_nurture_router tools.growth.test_growth_allocator tools.growth.test_content_engine tools.growth.test_ad_engine tools.growth.test_score_assessment` (14 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/growth/nurture_router.py tools/growth/growth_allocator.py tools/growth/test_nurture_router.py tools/growth/test_growth_allocator.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d164-registry.json`

## Proof

- `SPEC_d164_nurture_packet.json`: `d164-proof-lead` routes by weakest `time` dimension to `blueprint`, list `fpai-blueprint-nurture`, with `utm_campaign=assessment-savings`.
- `SPEC_d164_nurture_ledger.jsonl`: five email assets generated for the matching sequence.
- `SPEC_d164_growth_allocator_plan.json`: killed `d164-ad-exec-loser` and `d164-article-allocation`; championed `d164-ad-savings-winner` and `d164-email-time-winner`; bred two children with one mutated gene each; allocation plan capped ad budget at `$10`.
- `core/STATE/WINNING_PATTERNS.md`: distilled only the two fixture champion assets and includes no invented benchmarks.

## Risks

- This is repo-local orchestration only. It does not configure live n8n/listmonk workflows, activate Postiz, deploy pages, or schedule nightly automation.
- The allocator currently uses simple JSONL asset rows and local Growth CCD scoring; wiring it to the SQLite `tools/growth/ledger.py` store and any future allocation-ledger scorer can be a follow-up.
- The proof cycle uses deterministic fixture outcomes, not live Umami/listmonk/Meta data.

## Rollback

Revert this branch to remove the new router/allocator modules, tests, generated proof artifacts, `WINNING_PATTERNS.md`, registry entry, result artifact, and handoff note. No live runtime state was changed.

## Intent Solved

d164 now has a concrete, reviewable repo implementation for the Growth Stack's lead nurture routing and kill/breed allocation loop, extending the already-built G1/G2/G4 pieces without live sends or spend.

## Downstream Intent Unlocked

After review/merge, the next growth build can wire these dry-run payloads to approved n8n/listmonk activation and feed real Umami/listmonk/Meta outcomes into the allocator cycle.
