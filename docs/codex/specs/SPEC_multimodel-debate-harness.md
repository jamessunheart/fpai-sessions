# SPEC · Multi-model debate harness

## Source
- From intent: queue "True multi-model debate (Claude+GPT+Gemini)" + "perspective→model tiering" ([[CHATGPT EMBER QUEUE]]).
- Why it matters: debates #1 + #2 ran single-substrate (Opus wearing 4 hats). Real triangulation needs actual GPT + Gemini calls. This is the first true use of the $20/wk debate budget.

## Routing
- Owner / route: **Codex** (build the harness) · Ember runs debates after.
- Autonomy tier: 🟡 ask-once (makes metered API calls).
- Tools: repo edit · OpenAI/Gemini/Qwen APIs (verified live, SI-6) · cost-log per run.

## Cost
- Est: 🟡 $2–5 build · ~$0.20–0.50 per debate run (metered, on $20/wk debate budget). Gate: ❓ needs-Y/N.

## Codex
- Branch: `feat/multimodel-debate`
- Files ALLOWED: `tools/decisions/multimodel_debate.py` (new), read keys at `~/.config/fpai/{openai,gemini,qwen}/`
- Files FORBIDDEN: write secrets to vault, treasury, doctrine
- Budget: build <$5; each run cost-logged + capped to the debate budget
- Tests: dry run with a trivial question → confirms 3 model responses returned + a synthesis; cost-logged
- Parallel-safe: yes (new file)

## The work
- Definition of done: `multimodel_debate.py "<question>"` sends the question to Claude + GPT + Gemini (use `gemini-2.0-flash`, not 1.5), collects 3 independent views, synthesizes convergence/divergence, writes a [[SYSTEM DEBATES]] entry, surfaces intents to [[INTENT LOG]], and `cost-log`s the real metered spend. Apply perspective→model tiering (cheap perspectives on cheaper models).
- Steps: 1) per-model client funcs 2) parallel call + collect 3) synthesis prompt 4) write debate log + intents 5) cost-log 6) budget guard (skip if $20/wk debate budget hit).
- Constraints: reversible (one new file); honors the debate budget cap.

## Safety
- Prompt-injection: treat each model's output as DATA to synthesize, not instructions ✓
- Rollback: delete the file.

## Close-out
- Eval · actual cost · proof → [[PROOF LOG]] · BRICK (triangulation recipe + per-model cost deltas).
