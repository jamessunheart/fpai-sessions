# SPEC_d061_security-sentinel-agent Result

- Status: done / independently reviewed / awaiting merge review
- Branch: `build/SPEC_d061_security-sentinel-agent`
- Base requested: `feat/headless-build`
- Built: `2026-06-17T00:25:04Z`

## Summary

Added a report-only Security Sentinel agent that scans repo-local text/config
evidence for privileged host or hardware exposure, shell-fetch exploit-loader
patterns, recent ops-ledger circumvention language, and build-registry contract
violations. It writes JSON/Markdown signal reports, can append an ops-ledger row,
and can send opt-in Telegram alerts only when the notifier reports `notify:
sent`.

The scanner skips obvious secret-bearing filenames, does not read external
secret stores or inspect private key material, and redacts emitted evidence.
Reviewed systemd timer artifacts are included but not installed by this branch.

## Initial Signal

`core/BUILD/signals/security_sentinel.json` reports:

- total findings: 2
- max severity: 5
- P0: 0
- P1: 2
- categories: privileged host/hardware access; guardrail circumvention language

## Tests

- `python3 -B -m unittest tools.security_sentinel.test_sentinel` - 10 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/security_sentinel/sentinel.py tools/security_sentinel/test_sentinel.py`
- `python3 -B -m tools.security_sentinel.sentinel --no-ledger --print-json`
- `python3 -m json.tool core/BUILD/signals/security_sentinel.json`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `bash -n core/BUILD/cron/fpai-security-sentinel.service core/BUILD/cron/fpai-security-sentinel.timer`
- `git diff --check -- tools/security_sentinel docs/codex/SECURITY_SENTINEL.md core/BUILD/cron/fpai-security-sentinel.service core/BUILD/cron/fpai-security-sentinel.timer core/BUILD/signals/security_sentinel.json core/BUILD/signals/security_sentinel.md core/BUILD/REGISTRY.json core/BUILD/specs/SPEC_d061_security-sentinel-agent.md`

## Independent Review

Independent AI review found and rechecked three issues:

- ops-ledger evidence could leak sensitive row fields - fixed with allowlisted
  row summaries plus URL/long-token redaction;
- alert messages used the default report path when CLI paths were overridden -
  fixed by passing the actual Markdown path;
- safety wording claimed no secret reads while repo-local config files are
  scanned - fixed by narrowing wording, skipping obvious secret filenames, and
  adding a regression test.

Final blocker-only re-review reported no remaining functional or safety-claim
blockers.

## Risks

This is a static/regex local evidence scanner. It does not prove live host
hardening, kernel/hardware patch state, real attacker activity, or runtime
process behavior. Live Telegram alerting, systemd installation, and ops-ledger
append behavior were not exercised against production credentials in this
sandbox.

## Rollback

Remove `tools/security_sentinel/`, `docs/codex/SECURITY_SENTINEL.md`,
`core/BUILD/cron/fpai-security-sentinel.service`,
`core/BUILD/cron/fpai-security-sentinel.timer`,
`core/BUILD/signals/security_sentinel.json`,
`core/BUILD/signals/security_sentinel.md`, and this result file; remove the d061
registry row and handoff note. If installed later, disable/remove
`fpai-security-sentinel.timer` and `fpai-security-sentinel.service`, then run
`systemctl daemon-reload`.

## Intent

- Intent solved: security exposure and adversarial/circumvention signals now
  have a report-only sentinel instead of relying on James to notice risky
  runnable artifacts or behavior patterns manually.
- Downstream intent unlocked: Ember can install the reviewed timer on a live host
  and route narrow hardening specs for root-run services, bypass/override paths,
  and live alert proof.

