# AI Review — build/SPEC_d062_ai-pairing-account-security-bind

**Verdict:** APPROVE · **Risk:** med

**Summary:** Adds opt-in verified AI/user pairing guard for the live Telegram brain bot — additive schema, fail-closed enforcement gated behind AI_PAIRING_ENFORCE (default OFF), no merge/push/secrets/live mutation; safe in default posture.

## Findings
- Edits the live auth path of sh-brain-tgbot on server 162, but all new behavior is gated behind AI_PAIRING_ENFORCE which defaults OFF (compatibility mode) — existing owner/team env allowlists remain the active gate, so no live behavior change on merge. Acceptable.
- Fail-closed posture verified: when enforcement is ON, DB/lookup/guard errors and missing pairings all BLOCK owner/team messages and callbacks (evaluate_pairing(None) → block; exception → block). Good design, matches the claimed P1 fix.
- Deployment fragility (non-blocking): _load_pairing_guard resolves tools/identity_pairing/guard.py via parents[3] from SERVICES/sunheart-brain/curator/. If the live bot runs from a deployed copy without the cockpit tools/ tree, enabling enforcement would fail closed and lock out the owner. Documented 'seed + one live proof' step would catch this, but flag before enabling.
- Operational footgun (documented): turning on AI_PAIRING_ENFORCE before seeding the verified James pairing row will block the owner entirely. Do not enable until Ember seeds the row and runs a live proof.
- Minor: _record_pairing_event writes an audit row to brain_index on every owner/team message when enforcement is ON (even action=allow/severity=0). Low volume, acceptable, but worth noting.
- Minor: cross-package guard load uses a uniquely-named module (fpai_identity_pairing_guard) via spec_from_file_location without mutating sys.path — correctly avoids the d051 sys.path-shadowing regression.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
