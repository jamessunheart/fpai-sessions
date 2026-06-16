# Subscription Dependency Map

Audit date: 2026-06-16

Scope: repo-side build loop surfaces that mention or invoke Claude Max, Claude CLI, ChatGPT Max, Codex CLI, or subscription-backed AI roles. This map is operational evidence, not a billing ledger and not permission to change subscriptions.

## Executive Read

The build loop has two different subscription dependencies:

- **ChatGPT Max / Codex CLI is the primary build executor.** If it is pulled, the server can still notice decisions, write specs, run deterministic tests, and surface merge gates, but it loses the unattended `codex exec` lane that turns approved specs into branch diffs.
- **Claude Max / Claude CLI is the primary context, routing, review, and message-composition layer.** If it is pulled, builds can still be executed by Codex, but the loop loses independent AI review, self-audit spec proposal, Claude-authored horizon messages, and the main Ember/Claude Code steward surface.
- **Metered Anthropic API is a separate risk.** Some older service paths use `ANTHROPIC_API_KEY`; pulling Claude Max does not necessarily disable those API calls, and pulling the API key does not necessarily disable Claude Max CLI. Treat the subscription CLI lane and API lane separately.

## Build Loop Step Map

| Step | Evidence | Current model/subscription dependency | If Claude Max is pulled | If ChatGPT Max is pulled | Local replacement priority |
|---|---|---|---|---|---|
| Decision-to-spec bridge | `tools/decisions/bridge_to_codex.sh` | Uses SSH/server state and shell logic to write specs; dispatches Codex later; independent review uses Claude later. | Spec writing still works. Independent review phase fails when `tools/merge/ai_review.py` cannot run Claude. | Bridge can write specs and mark decisions, but `run_codex.sh` cannot build branches with `codex exec`. | P1 for build executor; P0 for reviewer if auto-merge gates depend on review. |
| Pending-spec builder | `tools/build_loop/run_codex.sh` | Requires `codex` CLI logged into `~/.codex/auth.json` in ChatGPT auth mode. | No direct failure. Codex builds continue. | Hard build-execution failure. If `codex` is missing the script exits before work; if `codex exec` returns nonzero, the script still writes a result file containing `[codex exited non-zero]`, creating a possible false "result exists" integration hazard unless reviewed. | P0 local coding agent replacement. |
| Orchestrator priority/integration | `tools/build_loop/build_orchestrator.sh` | Mostly deterministic shell/git. Calls `run_codex.sh` for builds, `merge_gate.sh` for review, `curator/blueprints/manager.py update-after-build` after auto-merge, and may call `self_audit.py` after loop. | Build phase still works via Codex. Merge gate review fails if Claude review is required. Self-audit proposal generation degrades. Post-auto-merge blueprint regeneration fails or is skipped when Claude cannot update the blueprint. | SAFE-AUTO specs are detected, but build phase cannot reliably produce branch diffs; a nonzero Codex run can still leave a result file that the integration loop may treat as built. | P0 builder; P1 reviewer/proposer/blueprint updater. |
| Headless single-spec build | `tools/autobuild/run.py`, `docs/codex/specs/SPEC_headless-build.md` | Prefers `claude -p`, falls back to `codex exec`. Both are intended flat-rate, non-metered paths. | Falls back to Codex when available; no hard failure unless Codex is also unavailable. | Falls back to Claude when available; no hard failure unless Claude is also unavailable. | P0 only if both flat-rate CLIs are gone; otherwise preserve dual-provider fallback. |
| Merge gate | `tools/merge/merge_gate.sh` | Deterministic registry/base/tests checks, then calls `tools/merge/ai_review.py`. | Hard gate failure when AI reviewer cannot run; merge command is not printed unless review approves or code is changed to permit manual-only fallback. | No direct failure. Gate still reviews Claude-written or manually built branches. | P0 independent reviewer if gated merges must continue without Claude. |
| Independent AI review | `tools/merge/ai_review.py` | Calls `~/.local/bin/claude -p`; reviewer is explicitly Claude Opus, different lab from Codex builder. | Hard failure: review file records AI review error and gate requests changes/manual review. | No direct failure, but independence weakens if replacement builder is Claude and reviewer is also Claude. | P0 reviewer replacement independent from primary builder. |
| Post-build blueprint refresh | `curator/blueprints/manager.py` | `update_blueprint_after_build()` calls `claude -p --effort high` after an orchestrator auto-merge to regenerate the affected module blueprint. | Hard failure for blueprint regeneration unless caught by caller; build code may already be merged, but the learning/blueprint update does not land. | No direct failure. | P2 local blueprint/learning updater. |
| Idle self-audit proposal generator | `tools/build_loop/self_audit.py` | Calls `claude -p` to propose 1-3 safe improvement specs from local evidence. | Graceful degradation: returns an empty list; no self-audit improvement specs are generated/queued. | No direct failure. | P2 local proposal model. |
| Horizon Scanner message composition | `tools/horizon/scanner.py` | Uses `claude -p` when present; deterministic fallback exists. | Graceful degradation: messages use deterministic fallback wording. Signal detection still runs. | No direct failure. | P3 local summarizer/composer. |
| Content Bank seed drafting | `tools/beacon/seed_content_bank.py` | Uses `claude -p` when available; deterministic fallback bodies exist. | Graceful degradation: draft quality drops to fallback assets. Existing files are still protected. | No direct failure. | P3 local draft writer. |
| Auto-loop tick | `tools/autoloop/tick.sh` | Cost guard, closeout, router report. No direct subscription CLI invocation in the tick. | Direct tick still runs; downstream routes that rely on Claude elsewhere degrade. | Direct tick still runs; build execution queued by other scripts fails. | Not first; keep deterministic tick. |
| Instrument Rack routing | `core/STATE/INSTRUMENT_RACK.yaml` | Routes hard reasoning/routine/classification to Claude models; routes builds to Codex on ChatGPT Max. | Routing policy loses its named Claude lanes; classify/routine/hard reasoning need alternate models. | Build lane loses its named Codex executor. | P0 builder, P1 hard-reasoning/reviewer, P2 cheap classify. |
| Ember/AI Context Steward | `core/STATE/AI_ROSTER.md`, `core/STATE/SSOT_REGISTRY.md` | Main context steward is a Claude Code session; identity/memory SSOT references `~/.claude`. | James loses the main whole-picture context surface and Claude-specific memory/session hooks. Repo mirrors remain readable. | No direct failure. | P1 context steward local model with repo/vault memory access. |

## Failure Modes By Subscription

### Claude Max Pulled

Hard failures:

- `tools/merge/ai_review.py` cannot produce a Claude Opus independent review, so `tools/merge/merge_gate.sh` fails the branch instead of printing a merge command.
- `curator/blueprints/manager.py update-after-build` cannot regenerate module blueprints after auto-merge, so the build may ship without its learning/blueprint refresh.
- The main Ember/Claude Code context-steward surface becomes unavailable or must move to another interface.
- Claude-model routes in `core/STATE/INSTRUMENT_RACK.yaml` no longer represent runnable local/subscription lanes.

Graceful degradations:

- `tools/build_loop/self_audit.py` logs or swallows the Claude failure and returns no proposed specs.
- `tools/horizon/scanner.py` uses deterministic fallback messages.
- `tools/beacon/seed_content_bank.py` can use deterministic fallback drafts.
- `tools/autobuild/run.py` can fall back to Codex if `codex` is available.

What does not fail directly:

- `tools/build_loop/run_codex.sh` and Codex-built isolated worktrees.
- Registry JSON updates, queue scans, cost guard, router report-only ticks, shell merge checks, and deterministic unit tests.

### ChatGPT Max Pulled

Hard failures:

- `tools/build_loop/run_codex.sh` cannot execute pending specs through `codex exec`; no reliable headless Codex branch diffs are generated. Missing CLI exits before result creation; nonzero `codex exec` can still write a result file containing failure text.
- `tools/build_loop/build_orchestrator.sh` can find SAFE-AUTO specs but cannot reliably complete the build phase that depends on `run_codex.sh`; a failure result file can create a false integration signal.
- Decision bridge output stalls after spec generation/review setup because the Codex build branch is missing, empty, or contains only a failed-build result.
- Build-lane policy in `core/STATE/INSTRUMENT_RACK.yaml` no longer has its named executor.

Graceful degradations:

- `tools/autobuild/run.py` can fall back to `claude -p` if Claude is available and the requested spec does not need Codex-specific behavior.
- Claude review, Claude self-audit, Claude horizon composition, and Claude context stewardship remain available.

What does not fail directly:

- Independent AI review of already-created branches.
- Ember/Claude Code context stewardship.
- Deterministic queue/registry/status/report scripts.

### Both Pulled

The deterministic spine still runs: registry checks, status scans, cost guard, router report-only logic, tests, and hand-authored docs/specs. The autonomous intelligence loop is no longer self-standing: it cannot reliably generate code diffs, independently review them, or synthesize next improvement specs without manual human/model substitution.

## Role Replacement Priority

Replace in this order if subscriptions are removed or reliability drops:

1. **Build Executor (P0):** local coding agent for `run_codex.sh` and `tools/autobuild/run.py` fallback. It must edit isolated worktrees, run tests, obey `SESSION_CONTRACT.md`, and produce reviewable result files without main-branch writes. Candidate interface: local OpenClaw/OpenHands-style agent or an OpenAI-compatible local coding runner behind the same command contract.
2. **Independent Reviewer (P0):** local reviewer that can replace `tools/merge/ai_review.py` without sharing the same model/runtime as the build executor. It must return strict JSON verdicts and preserve protected-path blocking before any model call.
3. **Context Steward / Ember Surface (P1):** local or self-hosted long-context model with access to repo/vault mirrors and identity/session memory. Without this, James becomes the router and synthesis layer again.
4. **Hard Reasoning / Architecture Model (P1):** replacement for `hard_reasoning` and `routine` Claude lanes in `core/STATE/INSTRUMENT_RACK.yaml`; needed for architecture, doctrine-adjacent analysis after James blesses scope, and complex route decisions.
5. **Self-Audit / Blueprint Learning Model (P2):** replacement for `tools/build_loop/self_audit.py` and `curator/blueprints/manager.py` so idle/merge-count triggers still propose safe improvement specs and post-build blueprint learning still lands.
6. **Cheap Classifier / Summarizer (P2):** replacement for high-volume classify/summarize lanes; prevents Claude/ChatGPT from being used for low-value bulk routing.
7. **Message/Draft Composer (P3):** replacement for horizon, Beacon/content, and digest polishing where deterministic fallbacks already exist.

## Replacement Command Contracts

The least disruptive local-model migration is command-compatible:

- Builder contract: provide a command equivalent to `codex exec --cd <worktree> --full-auto - < <spec_prompt>` or `claude -p <prompt>` that can be selected by `tools/autobuild/run.py` and `tools/build_loop/run_codex.sh`.
- Reviewer contract: provide a command used by `tools/merge/ai_review.py` that accepts a prompt and returns strict JSON with `verdict`, `risk`, `summary`, and `findings`.
- Proposal contract: provide a command used by `tools/build_loop/self_audit.py` that returns a strict JSON array of safe low/medium-risk specs.
- Composer contract: provide a command used by `tools/horizon/scanner.py` and content tooling; fallback quality may be lower, but failure must not block the build loop.

## Immediate Adoption Candidates

- **Local coding agent runner:** first replacement to evaluate, because ChatGPT Max removal stops the branch-producing loop.
- **Local reviewer model:** second replacement, because Claude Max removal blocks merge gates even when Codex builds succeed.
- **LiteLLM/OpenRouter-style router:** useful for API/provider abstraction, but it does not by itself remove subscription dependency unless backed by local models and cost gates.
- **OSS bulk lane:** useful for P2/P3 classify/summarize/draft work; it should not be treated as enough for P0 coding/review until it passes branch-diff and review-verdict tests.

## Acceptance Test For This Map

This audit is current when all of these are true:

- Every build-loop step above names an evidence file.
- Every Claude Max failure mode says whether the step hard-fails or degrades.
- Every ChatGPT Max failure mode says whether the step hard-fails or degrades.
- The replacement priority explicitly names the first local-model roles: build executor and independent reviewer.
