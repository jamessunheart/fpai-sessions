# AI Review — build/SPEC_d072_update-outreach-voice-offer-fram

**Verdict:** APPROVE · **Risk:** low

**Summary:** Reframes canonical outreach voice/offer copy and wires email+probe adapters and discovery scoring to read it; doc/template/scoring only, no live sends, on build branch off feat/headless-build, no prod/secrets/identity/main touched.

## Findings
- Minor: default OUTREACH_LINK fallback '@sunheartbrain_bot' renders as 'Ready? -> @sunheartbrain_bot' in email body — not a clickable URL; build correctly flags that OUTREACH_LINK should be set before any live email batch (no live send occurs without OUTREACH_LIVE/DRY_RUN gates, so not a blocker).
- Minor: score_signal() in common.py is still unclamped and the new weights raise the theoretical max from ~1.19 to ~2.0; pre-existing pattern, but confirm no downstream consumer assumes score is normalized to [0,1]. Discovery still gated by MIN_DISCOVERY_SCORE=0.4 and DISCOVERY_DISABLE.
- Note: spec footer says 'New files only' but the build also edits existing adapters (common.py, email_adapter.py, probe/agent.py) and NORTH_STAR.md — these edits are required to make the canonical voice actually take effect and are explicitly described in the spec body (Spark routing, discovery scoring, email), so within intent rather than scope creep.
- Verified guardrails intact: outreach remains behind OUTREACH_LIVE/DRY_RUN/PROBE_DISABLE/OUTREACH_EMAIL_DISABLE/DISCOVERY_DISABLE; no secrets, no new external calls, no push/merge; canonical voice still requires James approval to change.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
