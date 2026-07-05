# SPEC_d196_funnel-fix-meta-lead-attributio Result

- Status: done in working tree / awaiting review + merge + live activation proof
- Branch: `build/SPEC_d196_funnel-fix-meta-lead-attributio`
- Files changed:
  - `tools/growth/process_leads.py`
  - `tools/growth/test_process_leads.py`
  - `core/BUILD/fpai-leads-deliver.service`
  - `core/BUILD/activate/SPEC_d196_funnel-fix-meta-lead-attributio.sh`
  - `core/BUILD/specs/SPEC_d196_funnel-fix-meta-lead-attributio.md`
  - `core/BUILD/results/SPEC_d196_funnel-fix-meta-lead-attributio.result.md`
  - `core/BUILD/REGISTRY.json`
  - `docs/codex/HANDOFF.md`

## Summary

Kept the verified browser pixel untouched. Added a server-side Meta Conversions
API `Lead` event after a real lead is scored and successfully delivered by
`tools/growth/process_leads.py`. The event posts to pixel `110851475615838`,
uses `event_id=<lead filename stem>`, `action_source=website`,
`event_source_url=https://fullpotential.com/assessment`, and SHA-256 normalized
email in `user_data.em` for matching.

The worker reads the Meta token from `META_CONVERSIONS_API_TOKEN`,
`META_CAPI_TOKEN`, `META_ACCESS_TOKEN`, or `/root/.config/fpai/meta.env`.
Missing token is logged as attribution failure but does not resend the delivered
Allocation Score email.

`core/BUILD/fpai-leads-deliver.service` now loads `/root/.config/fpai/meta.env`.
The activation script compiles the worker, installs the updated unit, reloads
systemd, and warns if the Meta env file is absent. It does not trigger a send.

## Tests

- `python3 -B -m unittest tools.growth.test_process_leads` (5 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/growth/process_leads.py tools/growth/test_process_leads.py`
- `bash -n core/BUILD/activate/SPEC_d196_funnel-fix-meta-lead-attributio.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d196-registry-building.json`
- `python3 -B -m unittest tools.growth.test_process_leads tools.growth.test_score_assessment tools.leads.test_mail_leads tools.growth.life_assessment.test_champion_life_lead` (19 OK; existing Pydantic v1 validator deprecation warnings)
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d196_funnel-fix-meta-lead-attributio --base-ref feat/headless-build --head-ref HEAD` (OK: activation script present)
- `git diff --check`

## Risks

- Live Meta CAPI proof was not run in this sandbox; no production deploy, live
  lead processing, or external Meta call was performed.
- If `/root/.config/fpai/meta.env` is absent or lacks a supported token key,
  emails still deliver but attribution logs `missing Meta access token`.
- Browser/server dedup can only use the server `event_id` currently because the
  verified browser page does not know the saved lead filename.

## Rollback

Revert this branch. If already activated, reinstall the prior
`fpai-leads-deliver.service`, run `systemctl daemon-reload`, and leave
`/opt/fpai-build/.leads_worker_disabled` present to stop the worker while
reviewing attribution logs.

## Intent

- Intent solved: delivered assessment leads now emit a server-side Meta Lead
  event instead of relying only on browser pixel delivery.
- Downstream intent unlocked: Meta can count real delivered leads and optimize
  the assessment ad toward leads after live activation/proof.
- Next unlocked move: after merge on server 198/lead-worker host, run the d196
  activation, process one real or controlled non-test lead, then verify Meta
  Events Manager shows a server Lead event and ads status `leads_total`
  increments within the expected reporting window.
