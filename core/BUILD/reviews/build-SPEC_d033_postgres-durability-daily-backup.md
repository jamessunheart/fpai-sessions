# AI Review — build/SPEC_d033_postgres-durability-daily-backup

**Verdict:** APPROVE · **Risk:** low

**Summary:** Well-scoped defensive brain_index backup (pg_dump/offsite/verify/recovery); reads existing host creds, no secrets committed, branches off feat/headless-build not main.

## Findings
- No security issues: backup script refuses repo-local dirs (no secrets in commits), chmod 600 on dumps + 700 on dir, recovery playbook uses placeholder creds only, systemd reads existing /etc/sh-brain/curator.env on host. No main-branch or treasury exposure; pg_dump is read-only against the brain.
- WATCH (live-loop interaction): health_check.sh now fail()s on missing/stale /opt/fpai-backup. Until the timer is installed on 162 and produces a file, every health_check run will report 'brain backup missing or stale' — expected per spec but will surface as a failure immediately on merge before host setup is done.
- Minor: offsite scp/rclone failure trips the ERR trap and logs backup_failed + TG alert even though the local dump succeeded and pruning ran — a transient offsite hiccup reads as a full backup failure.
- Minor robustness: health_check age comparison swallows errors — if the inner python gets an empty/invalid age it exits non-zero and the staleness check silently passes rather than failing loud.
- Scope: visual-digest backup card + backup_status.py go slightly beyond the spec's 'morning digest' wiring, but are non-invasive and test-covered; morning-digest hookup ships as an uninstalled drop-in artifact (good — no silent service rewrite).
- Disclosed gap (not a blocker): tests use fake pg_dump/pg_restore/scp; no live Postgres/offsite/timer/Telegram exercised, and the automated independent review failed (ConnectionRefused) — manual restore-proof on 162 still required before relying on it.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
