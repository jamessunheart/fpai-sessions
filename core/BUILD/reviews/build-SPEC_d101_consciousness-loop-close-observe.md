# AI Review — build/SPEC_d101_consciousness-loop-close-observe

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Closes observer→council→MODEL_DNA loop with careful, well-tested, privacy-respecting non-blocking code, but the council autonomously writes a git-tracked SSOT on the live build server and activation auto-patches live settle hooks — both need hardening before merge.

## Findings
- DRIFT/COLLISION HAZARD: tools/council/debate.py now writes to git-tracked core/STATE/MODEL_DNA.md via maybe_append_from_council on every 5-min cycle on server 162, but never commits. This leaves uncommitted changes in the live build repo that the parallel build loop can sweep into an unrelated build commit or that can block branch checkouts — exactly the parallel-session collision class CLAUDE.md warns about (incident 8b8a64de). MODEL_DNA is not in .claude/hot-files.txt and gets no protection. Fix: commit the MODEL_DNA append atomically, or write directives to an untracked path, before enabling this in the loop.
- ACTIVATION PATCHES LIVE HOOKS: core/BUILD/activate/SPEC_d101...sh edits .claude/hooks/auto-settle.sh and .codex/hooks/auto-settle.sh. With auto-run-activate.sh-post-merge now active (commit 339a858), merging d101 silently rewires every settle on the live host to spawn a background observer. The injected block depends on hook-local vars ($EPISODIC_PATH, $LOG_DIR, $SESSION_ID, log()) that are not verified to exist in those hooks — if absent the backgrounded block fails silently. Confirm intent and verify the variables exist before merge.
- run_observer spawns `claude -p --agent consciousness-observer` on every settle session. Acceptable only if confirmed $0-marginal via Claude Max flat-rate (not metered API) per the cost-cap guardrail; frequency-per-settle vs the prior weekly/on-demand cadence is a behavior change worth an explicit gate/kill-switch (CONSCIOUSNESS_LOOP_DISABLE exists for council but not for the settle-hook observer run).
- Scope: spec text was a bare 'build it', yet the build spans council prompt schema, MODEL_DNA self-modification, digest, and live-hook patching. Aligned with the decision title but broad and self-directing (council writes its own model-development directives) — warrants James's explicit sign-off on the MODEL_DNA self-write before activation.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
