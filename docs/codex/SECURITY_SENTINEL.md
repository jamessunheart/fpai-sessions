# Security Sentinel Agent

The Security Sentinel is a report-only local evidence scanner. It anticipates
security threats before they become live incidents by looking for:

- privileged host, hardware, docker, or device access in runnable artifacts;
- shell-fetch execution patterns that could become exploit loaders;
- recent ops-ledger language that looks like adversarial behavior or guardrail
  circumvention;
- build registry contract violations that would let unsafe branches appear
  merge-ready.

It writes:

- `core/BUILD/signals/security_sentinel.json`
- `core/BUILD/signals/security_sentinel.md`
- one `security_sentinel` row in the ops ledger unless `--no-ledger` is used

## Boundaries

The agent scans repo-local text/config files. It skips obvious secret-bearing
filenames such as `.env`, credential files, private keys, `.pem`, and `.key`
files, and redacts emitted evidence. It does not scan the public internet, SSH
into hosts, read external secret stores, inspect private key material, install
timers, restart services, deploy, spend, move money, send outreach, push, or
merge. Telegram alerting is opt-in through `--send-alert`, and only counts as
sent when `tools/build_loop/notify_telegram.sh` prints `notify: sent`.

Kill switches:

- `SECURITY_SENTINEL_DISABLE_FILE`, default
  `/opt/fpai-build/.security_sentinel_disabled`
- `SECURITY_SENTINEL_COOLDOWN_FILE`, default
  `/opt/fpai-build/.security_sentinel_last_alert`

## Reviewed Timer Artifacts

`core/BUILD/cron/fpai-security-sentinel.service` and
`core/BUILD/cron/fpai-security-sentinel.timer` are reviewed artifacts only. They
are not installed by this branch. Ember can install them on the live host after
merge review, then run one live proof with ops-ledger access before enabling the
timer.

## Manual Proof

```bash
python3 -B -m tools.security_sentinel.sentinel --no-ledger --print-json
python3 -B -m unittest tools.security_sentinel.test_sentinel
```
