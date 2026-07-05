# SPEC_d203_funnel-chat-based-assessment-re Result

## Status

Done in working tree. Awaiting review, merge, and guarded activation on server 198.

## Files Changed

- `SERVICES/champion-sign/main.py`
- `sites/fullpotential-com/audit.html`
- `tools/growth/score_assessment.py`
- `tools/growth/test_score_assessment.py`
- `tools/growth/life_assessment/test_champion_life_lead.py`
- `core/BUILD/activate/SPEC_d203_funnel-chat-based-assessment-re.sh`
- `core/BUILD/specs/SPEC_d203_funnel-chat-based-assessment-re.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d203_funnel-chat-based-assessment-re.result.md`
- `docs/codex/HANDOFF.md`

## Summary

Replaced `/assessment` form-primary UX with an embedded public chat assessment. The chat greets as `James Sunheart + AI`, asks one question at a time, captures name/email mid-conversation, writes the lead row immediately, queues the Meta CAPI `Lead` event on email capture, then calls the existing Allocation Score engine to reveal the score and top three opportunities live in-chat.

The original form remains available in a fallback `<details>` panel for A/B measurement and recovery. The chat endpoint is public-mode only: it uses only visitor-submitted state and `tools/growth/score_assessment.py`, returns `private_context_used=false`, and does not load the James-private curator answer path.

## Tests

- `python3 -B -m unittest tools.growth.test_score_assessment tools.growth.life_assessment.test_champion_life_lead` (14 OK)
- `python3 -B -m unittest tools.growth.test_process_leads tools.growth.test_score_assessment tools.growth.life_assessment.test_champion_life_lead tools.leads.test_mail_leads` (24 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/champion-sign/main.py tools/growth/score_assessment.py tools/growth/test_score_assessment.py tools/growth/life_assessment/test_champion_life_lead.py`
- `awk ... sites/fullpotential-com/audit.html > /tmp/d203-audit-app.js && node --check /tmp/d203-audit-app.js`
- `bash -n core/BUILD/activate/SPEC_d203_funnel-chat-based-assessment-re.sh`
- `python3 tools/build_loop/activation_policy.py --repo-root . --spec-id SPEC_d203_funnel-chat-based-assessment-re --base-ref feat/headless-build --head-ref HEAD`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d203-registry-check.json`
- `git diff --check`

## Risks

- Live `claude -p` scoring, live Meta CAPI proof, and public `/assessment` browser proof were not run in this sandbox.
- Chat result quality depends on the existing Allocation Score model prompt; the endpoint limits rate and scoring happens only after required fields are present.
- Final James voice/booking CTA remains reserved. The chat uses a guarded reserved next-step line; existing email delivery still holds draft CTA sends until approved copy/URL are configured.

## Rollback

Revert this branch. If activated live, restore the prior `SERVICES/champion-sign/main.py` and `audit.html` through the d182 live-service guard backup, restart `champion-sign.service`, and confirm `/lead/assessment-chat` is no longer referenced by the page.

## Intent Solved

The 81-click/0-completion form bottleneck now has a lower-friction chat assessment that demonstrates Allocation Intelligence directly.

## Downstream Intent Unlocked

Server 198 can measure chat-based assessment conversion against the preserved form fallback, with proof from lead rows, Meta Lead events, and in-conversation score completion.

## Questions For Ember/James

After merge on server 198, run the guarded activation and submit one controlled cold-visitor chat. Confirm: chat reaches score in-page, `/var/lib/full-potential/leads/*.md` has `status: chat_scored`, Meta Events Manager receives a server `Lead` event, and the fallback form remains reachable.
