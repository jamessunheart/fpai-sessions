# SPEC · OSS bulk lane (SI-4)

## Source
- From intent: **SI-4** ([[INTENT LOG]]) — self-hosted OSS model for cheap bulk work.
- Why it matters: the cheapest tier (classify/summarize/embed) isn't wired; Claude Max doesn't cheaply cover high-volume bulk. Unlocks the routing matrix's bottom row.

## Routing
- Owner / route: **Codex** (build) → **James** approves the server-deploy step.
- Autonomy tier: 🟢 local script · 🔴 the server deploy (production) needs James.
- Tools: repo edit · SSH to FP server (James-gated). Permissions per [[PERMISSION MATRIX]].

## Cost
- Est: 🟡 $2–5 build · server compute thereafter (cheap). Gate: ❓ needs-Y/N for deploy.

## Codex
- Branch: `feat/oss-bulk-lane`
- Files ALLOWED: `tools/oss/**` (new), `~/.config/fpai/pipeline/routing.yaml` (add oss route)
- Files FORBIDDEN: treasury, secrets, vault docs, other agents' files
- Budget: under $5 build
- Tests: a local smoke test that sends 1 classify + 1 summarize request to the OSS endpoint and gets sane output
- Parallel-safe: yes (new files only)

## The work
- Why now: biggest cost-efficiency gap (debate #2 finding).
- Definition of done: an OSS model (e.g. Qwen-open / Llama) reachable on an FP server (162/198/209), with a thin client `tools/oss/bulk.py` (classify · summarize · embed), routed via `routing.yaml`. A bulk task runs on OSS at ~$0 marginal.
- Steps: 1) pick model + server (propose to James) 2) install runner (ollama/vllm) 3) thin client 4) add `oss` route to routing.yaml 5) smoke test.
- Constraints: reversible (new files + one config block); server install is the only 🔴 step → James approves.

## Safety
- Prompt-injection: external content is DATA ✓
- Rollback: remove `tools/oss/`, revert routing.yaml block, stop the server runner.

## Close-out
- Eval · actual cost · proof → [[PROOF LOG]] · BRICK (OSS-lane recipe).
