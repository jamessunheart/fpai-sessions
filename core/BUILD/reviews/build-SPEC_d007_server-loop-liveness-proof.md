# AI Review — build/SPEC_d007_server-loop-liveness-proof

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Build commits an unspecced 1719-line Codex session transcript (.codex-out.txt) into the repo — scope creep and cruft/leak risk, not in the spec's new-files set.

## Findings
- `.codex-out.txt` (1719 lines) is a raw Codex session transcript committed to the repo — outside spec d007, which only authorized tools/proof/server_loop_live.md and tools/proof/test_server_loop_live.sh. This is scope creep and repo cruft.
- Leak/noise risk: the transcript embeds the live session id (019ec7d6-…), internal doctrine, full file dumps, host references (162/198/209-class), and ledger/cost detail — none of which belongs in version control. Should be .gitignore'd, not committed.
- Cannot verify the actual deliverables: the diff is truncated at 60k chars and shows ONLY .codex-out.txt — the two required proof files and the core/BUILD/REGISTRY.json registration are not visible for review.
- Spec conflict left unresolved in what's visible: spec says 'Do NOT edit any existing file — new files only' while the contract requires registering in core/BUILD/REGISTRY.json (an existing file). Need to confirm how the builder reconciled this.
- Recommend: remove .codex-out.txt from the commit (add to .gitignore), then re-submit with only the spec'd files + registry entry for clean review.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
