# AI Review — build/SPEC_d107_gepa-library-wire-install-real-m

**Verdict:** APPROVE · **Risk:** low

**Summary:** Wires real MIT gepa package into the d106 prompt-efficiency loop with claude -p reflection, deterministic fallback, kill switch, and human-approval gating for high-impact council prompts; live behavior unchanged and safe.

## Findings
- Spec said 'evals=Ollama' but the adapter's evaluate() is pure deterministic term-matching + token counting (evaluate_text); the Ollama model is metadata-only ('ollama/llama3.1:8b' label) and never actually called. That portion of the spec is labeled, not implemented — the result file is honest about this.
- Council Pragmatist prompt optimization is slightly beyond the minimal spec scope, but it is correctly gated: written only to pending_adoptions, never to active adoptions, and render_council_pragmatist_prompt() returns a baseline template byte-identical to the previously hardcoded prompt — so live council behavior is unchanged. No silent guardrail bypass.
- After activation installs gepa, optimize_template invokes claude_cli_proposer which spawns `claude -p` via subprocess; this is $0 subscription marginal and bounded by max_metric_calls and GEPA_OPTIMIZE_DISABLE=1 kill switch — acceptable. Ensure activate script's `pip install gepa` runs in the build-loop venv, not system python.
- Branch correctly off feat/headless-build (not main); no money/treasury/prod-server/identity/memory/secret writes; fallback paths fail closed and pragmatist_voice wraps the renderer in try/except. Tests included and exercise both gepa and missing-package fallback paths.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
