# AI Review — build/SPEC_d124_spec-d124-chat-context-routing-s

**Verdict:** APPROVE · **Risk:** low

**Summary:** Adds a deterministic, env-gated (CURATOR_CONTEXT_ROUTING=1, off by default) chat context router for the Telegram synthesis path; reversible, no deploy/merge/push, no money/secrets/identity touched — safe.

## Findings
- Gate is correctly off by default: when CURATOR_CONTEXT_ROUTING is unset, _classify_context_route returns 'general' and _context_blocks_for_route enables all blocks + brain_search, preserving legacy behavior. Verified.
- importlib loading in _load_context_router uses spec_from_file_location with parents[3] (repo root) and does NOT mutate sys.path — complies with SESSION_CONTRACT Rule 6. Correct path resolution.
- Perf (minor, non-blocking): _load_context_router() re-reads and re-exec's the module on every call, and is called multiple times per message (_classify_context_route, _context_blocks_for_route in both _handle_message and _synthesize_answer). For a chat hot path consider caching the loaded module. Not a correctness bug.
- Behavior risk when gate ENABLED (intended per spec, but flag for the live proof): ops/treasury routes skip brain_search, so treasury/ops answers are synthesized without brain retrieval. This is the owner's own chat, reversible via unsetting the env var, and off by default — acceptable, but the planned single live proof should confirm answer quality before making routing default.
- In routed mode both hot_state and render_build_context system_status may be injected together (the legacy hot_state fast-path early-return is bypassed). Possible minor duplication of system info in the prompt; not a correctness issue.
- Registry/result/handoff are honest: explicitly state independent AI review timed out and reviewer pass remains a pre-merge gate, and that no live chat/restart/deploy/merge/secrets/money occurred. No guardrail bypass; merge gate still applies.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
