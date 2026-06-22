# AI Review — build/SPEC_d116_retroactive-liveness-audit-scan

**Verdict:** APPROVE · **Risk:** med

**Summary:** One-time retroactive liveness audit of merged d001-d092; conservative (unknown-not-dead), branched off feat/headless-build, no push/merge, gated DB/TG side-effects, tests pass — safe with caveats.

## Findings
- Live run (without --no-seed) writes new dNNN-activate rows to brain_index.decisions on server 162, which feeds the autonomous build/merge loop. This is spec-authorized and idempotent (ON CONFLICT DO NOTHING), but heuristic false-'dead' classifications could auto-queue spurious builds. Mitigated by conservative seeded spec text + downstream review gates; reviewer should eyeball the dead set (d023/d049/d053/d077/d078/d092) before a live seed run.
- SQL injection surface is properly defended: _check_table validates the table name via _safe_identifier (regex allowlist) before f-string interpolation, and to_regclass guards existence. Good.
- Hardcoded default DB credential in source: DB_URL falls back to 'postgres://brain_index:changeme@127.0.0.1:25432/appflowy'. Localhost + env-overridable so low risk, but a placeholder password in source is poor hygiene — prefer requiring the env var and failing loudly if unset.
- External endpoint probing is correctly disabled by default (--allow-external-endpoints required), so prod hosts/external URLs are not hit during the audit — good conservative default.
- classify() marks a whole decision 'dead' if ANY single heuristically-inferred artifact is missing; combined with imperfect path/table inference this can over-flag. Acceptable given the unknown-not-dead bias elsewhere, but the seeded follow-ups should be treated as candidates, not confirmed-dead facts.
- Minor: TABLE_RE regex is defined but unused (dead code); harmless.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
