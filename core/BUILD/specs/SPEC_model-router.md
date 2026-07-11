# SPEC — Model Router: match each build job to its best-value model

**Why (James 2026-07-10):** The July-2026 independent benchmark scorecard proves there is **no universal winner — match the benchmark to the job**. Our build loop currently pins one model path (claude -p + codex). That leaves both quality and cost on the table: hard reasoning wants Claude, autonomous coding wants GPT-5.6 Sol, and trivial mechanical builds can run **free** on 162's local coder models. Reality tested 2026-07-10: 162 (12 CPU / 31GB / **no GPU**) cannot host the DeepSeek V4 Pro **champion**, but qwen2.5-coder:7b returned correct code in ~19s CPU-only at $0. So the champion, GPT, and Claude all route through the already-stored **OpenRouter** key; 162 serves the free lane.

## The lanes (grounded in the scorecard + the 162 test)

| Lane | Job class | Model | Route | Cost |
|---|---|---|---|---|
| 1 · Reason | Architecture, spec authoring, hard bugs, independent review | Claude (Fable 5 / Opus) | OpenRouter `anthropic/*` | paid |
| 2 · Agent | Autonomous multi-step coding, terminal loops, the build runner | GPT-5.6 Sol | OpenRouter `openai/*` | paid (~⅓ Fable/task) |
| 3 · Bulk | Trivial/mechanical SPECs, boilerplate, high-volume | qwen2.5-coder:7b (deepseek-coder 6.7b fallback) | local Ollama on 162 | **$0** |
| 3c · Bulk-cloud (optional) | Cheap coding when 162 is busy/quality too low | DeepSeek V4 Pro | OpenRouter `deepseek/*` | cheap |

## Build

1. **`tools/build_loop/model_router.py`** — pure function `route(spec) -> {lane, model, endpoint}`. Classifies a SPEC by declared job class (front-matter `lane:` if present) OR heuristics: LOC estimate, "review"/"architecture"/"reasoning" keywords → Lane 1; "autonomous"/"multi-step"/"agent" → Lane 2; "boilerplate"/"mechanical"/small-diff → Lane 3. Default = Lane 2 (safe, capable). Deterministic, unit-tested, no network.
2. **`tools/build_loop/llm_client.py`** — thin adapter with two backends: `openrouter` (POST `https://openrouter.ai/api/v1/chat/completions`, key from `~/.config/fpai/openrouter/api.token`) and `ollama_162` (POST `http://162.0.208.88:11434/api/generate` or ssh `ollama run`). Same interface, so the loop is backend-agnostic.
3. **Wire into the build loop** — the runner asks `model_router.route()` before dispatch, then calls `llm_client` with the chosen lane. Log `{spec, lane, model, tokens, cost_est, elapsed}` to `~/.config/fpai/model_router/routing_ledger.jsonl`.
4. **Cost guardrail** — every paid call checks the $20/day cap ledger BEFORE dispatch; over cap → downgrade to Lane 3 (free) or defer. Lane 3 is always free.

## Guardrails

- **Reversible:** new files + one call site; the old single-model path stays as `lane: 1` default if the router is disabled (`MODEL_ROUTER_DISABLE=1`).
- **No quality regression:** Lane 3 only receives SPECs explicitly classified trivial; anything ambiguous escalates up, never down.
- **Secret hygiene:** OpenRouter key read at runtime from config, never logged, never committed. 162 Ollama endpoint bound local/VPN only — do not expose 11434 publicly.
- **Honest ceiling:** the DeepSeek V4 Pro *champion* is cloud-only for us (no GPU on 162). The spec does NOT claim champion-tier self-hosting.

## Done / Proof (reality, not merge)

1. Unit: `route()` sorts a reasoning SPEC → Lane 1, an autonomous-agent SPEC → Lane 2, a boilerplate SPEC → Lane 3 (deterministic).
2. **Live dogfood:** run one real trivial SPEC through Lane 3 on 162 end-to-end (dispatch → code → committed diff) at $0, logged in `routing_ledger.jsonl` with elapsed time.
3. **Live cloud:** run one Lane 1 review through OpenRouter Claude; ledger shows model + token cost; $20/day cap respected.
4. One week of `routing_ledger.jsonl` shows real lane distribution + $ saved vs all-Lane-1 baseline.

## Contract

Follow docs/codex/SESSION_CONTRACT.md. Branch off feat/headless-build (never main). Register in core/BUILD/REGISTRY.json. Tests required. Do NOT push or merge. $0 to draft/test the local lane; paid lanes gated by the existing $20/day cap.
