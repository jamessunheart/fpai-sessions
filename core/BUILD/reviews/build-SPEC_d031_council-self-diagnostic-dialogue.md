# AI Review — build/SPEC_d031_council-self-diagnostic-dialogue

**Verdict:** APPROVE · **Risk:** med

**Summary:** Bounded, in-spec council self-diagnostic with kill switch, parameterized SQL, and list-form subprocess; main risks are live-bot prompt injection surface and autonomous build queuing, but all gated downstream by James's merge.

## Findings
- No SQL injection: all DB reads use parameterized %s; no shell=True and subprocess calls use list form for `dec queue-build` and `claude -p`, so no command injection from Claude/Telegram-derived text.
- Branch correctly bases on feat/headless-build (not main), registers in REGISTRY.json, ships a kill switch (SELF_DIAGNOSTIC_DISABLE=1), 48h cooldown, and rollback notes. Good guardrail discipline.
- SELF-DIRECTED WORK EXPANSION: run_diagnostic_dialogue() auto-queues up to 3 AI-synthesized specs via `dec queue-build`, bypassing the normal council 'surface ONE proposal → James says yes build it' approval gate. In spec, and bounded to once/48h + downstream merge gate, but it lets the system enqueue its own builds without per-build approval — confirm `dec queue-build` does not auto-merge and that James still gates merge.
- PROMPT-INJECTION FLOW: arbitrary tg_messages content (any chat input) flows verbatim into the `claude -p` synthesis prompt, whose JSON output becomes queued build specs. validate_specs() bounds count/length but does not sanitize intent; a crafted message could steer a queued spec. Blast radius contained at the human merge gate, but worth noting for a self-evolving loop.
- LIVE PRODUCTION BOT TOUCHED (server 162): build_context.py/tgbot.py now read the diagnostic context file on every message and prepend a prompt prefix during the window. Degrades safely (missing/expired/malformed file → None → no change), but it modifies live bot system-prompt construction — verify the bot service user can read /opt/fpai-build/ and that the per-message file read is acceptable overhead.
- DATA-AT-REST: .self_diagnostic_context.json persists the last 50 tg_messages (truncated to 500 chars), 'not now' decisions, and rejected builds in plaintext on disk; expiry is only honored by the loader, the file is NOT deleted on expiry, so conversation data lingers until the next run overwrites it. Local to 162 and noted in rollback, but consider unlinking on expiry.
- No secrets logged, no treasury/identity/memory writes, no main-branch action. DSN read from env and never echoed.
- Process note: result.md admits no independent ai_review.py run completed in the sandbox (index.lock read-only + API ConnectionRefused) — this review is that gate; recommend the live post-merge proof checklist the author listed before trusting the loop.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
