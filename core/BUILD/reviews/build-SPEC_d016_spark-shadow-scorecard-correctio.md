# AI Review — build/SPEC_d016_spark-shadow-scorecard-correctio

**Verdict:** REQUEST_CHANGES · **Risk:** med

**Summary:** Shadow-only build is well-scoped and over-escalates correctly, but the default code path makes an unauthenticated plaintext HTTP call to production host 162 carrying local context (NOW/INBOX/HUMAN_EDGE_QUEUE) with no kill-switch.

## Findings
- Hardcoded production IP DEFAULT_OLLAMA_URL='http://162.0.208.88:11434/...' — plaintext HTTP, no auth header. Spec authorizes llama-on-162, but there is no env var or CLI flag to disable the network call; default route_message/CLI fuzzy-middle path will POST to prod 162 automatically.
- Data-handling: read_live_context() reads core/STATE/NOW.md, HUMAN_EDGE_QUEUE.md and INBOX.json (up to ~2KB each) and _context_prompt sends that content to the 162 endpoint. INBOX/HUMAN_EDGE_QUEUE may contain sensitive/private text being shipped off-box over an unencrypted channel; add a redaction/opt-in gate before default live intake uses real files.
- capture_route_correction appends into the d010 preference dataset (DEFAULT_DATASET) which feeds the self-evolution judge — touches the learning/identity loop. It is CLI-gated and append-only (acceptable), but worth confirming DEFAULT_DATASET is the intended path and not a shared production dataset.
- should_read_llama skips llama for T4/T5 non-stakes tiers (only T1-T3 trigger reads); acceptable but means high-tier-but-no-detected-stakes messages get neither deterministic-stakes treatment nor a model read — confirm intended.
- Positives confirmed: shadow_mode defaults True, no live reroute, stakes force route:james at 0.99 confidence even with low llama confidence and skip the llama call entirely (no sensitive money/public msgs sent to 162), branched off feat/headless-build, registered, tests use injected classifier (no network in tests), no push/merge/secret/treasury write. No live-router or main-branch changes.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
