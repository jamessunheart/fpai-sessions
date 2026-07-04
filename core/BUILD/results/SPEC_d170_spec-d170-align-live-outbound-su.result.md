# SPEC_d170_spec-d170-align-live-outbound-su Result

- Status: done in working tree / awaiting review + merge + one-at-a-time live activation
- Branch: `build/SPEC_d170_spec-d170-align-live-outbound-su`
- Files changed: `sites/fullpotential-com/index.html`; `deploy-tools/intake-agent.py`; `tools/public_bot/bot.py`; `tools/public_bot/test_bot.py`; `tools/probe/agent.py`; `tools/probe/test_probe.py`; `tools/hermes/email_adapter.py`; `tools/hermes/test_email_adapter.py`; `tools/discovery/test_outreach_voice.py`; `tools/public_site/test_fullpotential_home.py`; `core/STATE/OUTREACH_VOICE.md`; `core/STATE/archive/bottleneck_session_outreach_templates.md`; `core/BUILD/activate/SPEC_d170_spec-d170-align-live-outbound-su.sh`; `core/BUILD/specs/SPEC_d170_spec-d170-align-live-outbound-su.md`; `core/BUILD/REGISTRY.json`; `core/BUILD/results/SPEC_d170_spec-d170-align-live-outbound-su.result.md`; `docs/codex/HANDOFF.md`

## Summary

Aligned repo-backed outbound surfaces to BBB v1.4:

- `fullpotential.com` root now leads above the fold with Free Full Potential Assessment -> Allocation Score, CTA `Start the Free Assessment ->`, assessment-first metadata, and no first-nav `/game.html` Game item.
- `tools/public_bot/bot.py` no longer loads `core/STATE/OUTREACH_VOICE.md` or `outreach_voice()` into its persona. Public next-step routing now offers `/assessment` before Game/WPA/Character Card/manual outreach/paid call.
- `deploy-tools/intake-agent.py` acknowledgment copy now routes Assessment -> Allocation Score -> Blueprint ($2,500), and booking language is Blueprint-specific.
- Manual first-contact tooling is retired by default: `tools/probe/agent.py` exits the default sender path with `manual_outreach_retired_assessment_funnel_first`, and `tools/hermes/email_adapter.py` refuses sends unless `MANUAL_OUTREACH_LIVE=1` is explicitly set later.
- `core/STATE/OUTREACH_VOICE.md` is marked historical/retired, and `bottleneck_session_outreach_templates.md` moved to `core/STATE/archive/` with a retirement header.
- Added a post-merge activation script that backs up live files, installs the homepage, patches `/opt/fpai/guide/guide_service.py` SYSTEM prompt, installs `/opt/fpai/leads/intake-agent.py`, compiles Python, and restarts only `fp-guide.service` and `intake-agent.service`.

## Tests

- `python3 -B -m unittest tools.public_site.test_fullpotential_home tools.public_bot.test_bot tools.discovery.test_outreach_voice tools.hermes.test_email_adapter tools.probe.test_probe` (39 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile deploy-tools/intake-agent.py tools/public_bot/bot.py tools/public_bot/test_bot.py tools/discovery/test_outreach_voice.py tools/hermes/email_adapter.py tools/hermes/test_email_adapter.py tools/probe/agent.py tools/probe/test_probe.py tools/public_site/test_fullpotential_home.py`
- `bash -n core/BUILD/activate/SPEC_d170_spec-d170-align-live-outbound-su.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d170-registry.json`
- `git diff --check`

## Proof

- Static root proof: focused test confirms the homepage hero contains Allocation Score copy and `/assessment` CTA before the category strip, and the old `What wants to grow today?` hero/Game nav are absent above fold.
- Public-bot proof: focused tests confirm the system prompt/greeting route to the free assessment and Allocation Score, and source grep found no `outreach_voice()` or `OUTREACH_VOICE_PATH` in `tools/public_bot/bot.py`.
- Manual-outreach proof: focused tests confirm default probe sender exits before creating probe sessions/cooldowns and Hermes email returns the retired reason.
- Live-service proof is activation-ready but not executed in this sandbox.

## Risks

- This sandbox did not deploy to host 198, restart `fp-guide.service`, restart `intake-agent.service`, curl live `fullpotential.com`, message the live guide, or trigger a live intake email.
- `/opt/fpai/guide/guide_service.py` is not mirrored in this repo. The activation script expects a top-level triple-quoted `SYSTEM = """..."""` prompt and fails closed if it cannot find one.
- `fullpotential_funnel/architecture_v1.md` was not present under `core`, `docs`, `sites`, `tools`, or `deploy-tools` in this worktree, so there was no file to archive.

## Rollback

- Code rollback: revert this branch.
- Homepage runtime rollback after activation: copy `$BACKUP_DIR/fullpotential-index.html` back to `$FULLPOTENTIAL_SITE_ROOT/index.html`.
- Guide runtime rollback: copy `$BACKUP_DIR/guide_service.py` back to `/opt/fpai/guide/guide_service.py` and restart `fp-guide.service`.
- Intake runtime rollback: copy `$BACKUP_DIR/intake-agent.py` back to `/opt/fpai/leads/intake-agent.py` and restart `intake-agent.service`.
- Manual outreach remains safer by default after rollback unless the reverted code is redeployed and explicit live flags are set.

## Intent

- Intent solved: live outbound surfaces now point first to the BBB v1.4 assessment funnel instead of the pre-BBB game/manual-outreach/session frame.
- Downstream intent unlocked: system-generated demand can hit the public root, guide, and intake acknowledgment without seeing a conflicting offer before the Allocation Score path.
- Next unlocked move: after review/merge, activate one surface at a time and verify: curl root, message guide, trigger a test intake, and confirm public bot has no old outreach persona.
