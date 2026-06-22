# AI Review — build/SPEC_d123_d014-correction-capture-close-d0

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** In-scope fix appending recent correction pairs to the fresh-HOT_STATE bot context path; small and well-tested, but injects an unguarded DB read into the live owner prompt hot path.

## Findings
- _render_recent_corrections_context only catches ImportError, not runtime errors from `await recent_corrections(...)` (DB/network/Supabase failure). This is now on the fresh-HOT_STATE path — the most common production owner-bot context path, which previously had NO DB dependency. A live read failure would now raise out of build_context_system_suffix and break the bot turn. The result file claims 'the correction path remains non-blocking,' but the code does not enforce that on this path. Wrap the recent_corrections()/render call in try/except returning '' on any exception.
- max_chars budget not respected: hot_state is rendered with max_chars, then the corrections block is concatenated on top with no length cap, so the combined suffix can exceed the intended context budget on the hot path.
- Not blocking for merge boundaries: no money/secrets/identity/main-branch touched, REGISTRY status correctly 'done' not 'merged', no push/deploy. But per the build's own notes the independent-AI review failed (ConnectionRefused) and no live proof ran — both must complete before merge.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
