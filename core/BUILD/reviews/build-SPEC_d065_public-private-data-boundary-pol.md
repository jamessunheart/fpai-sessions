# AI Review — build/SPEC_d065_public-private-data-boundary-pol

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds a public/private data boundary policy + reusable fail-closed classifier/sanitizer and wires the visual digest public feed to it; defensive privacy build, branches off feat/headless-build, no money/secrets/prod/identity/main touched — safe and net-stricter.

## Findings
- Non-blocking: old regexes (CREDENTIAL_RE/MONEY_RE/WALLET_RE/etc.) remain defined in visual_digest.py but are now dead code after the rewrite — harmless, worth a later cleanup.
- Non-blocking: public_bot_link() rejection narrowed from (credential|correction) to sensitive-lane-only, but the t.me/@-prefix format whitelist still gates output, so no leak path opens.
- Confirmed: default_lane=private and classify-after-sanitize make the pipeline fail-closed; the two earlier review blockers (unmatched-text-public, phones) are fixed with regressions. Wired surface (visual_digest, runs in live digest) is now strictly more conservative than before.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
