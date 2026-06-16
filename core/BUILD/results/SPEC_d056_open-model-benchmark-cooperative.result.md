# SPEC_d056_open-model-benchmark-cooperative Result

Status: done / awaiting live independent review + merge review

## Summary

Added an advisory open-model benchmark scaffold for Qwen, Mistral, Llama, and
Gemma on James's repo-local corpus. The scaffold:

- builds deterministic corpus classification tasks across baseline, one-shot,
  and two-shot learning rounds;
- scores supplied response JSONL for accuracy, learning gain, latency, evidence,
  and calibration;
- emits advisory builder/reviewer/specialist role assignments with cross-check
  pairings;
- includes an opt-in local Ollama runner for already-installed models only.

No model download, model training, live API call, production routing, spending,
deployment, outreach, or secret access is performed by default.

## Files Changed

- `tools/open_model_benchmark/__init__.py`
- `tools/open_model_benchmark/benchmark.py`
- `tools/open_model_benchmark/test_benchmark.py`
- `docs/codex/OPEN_MODEL_BENCHMARK.md`
- `tools/learn/README.md`
- `core/BUILD/specs/SPEC_d056_open-model-benchmark-cooperative.md`
- `core/BUILD/REGISTRY.json`
- `core/BUILD/results/SPEC_d056_open-model-benchmark-cooperative.result.md`
- `docs/codex/HANDOFF.md`

## Tests

- `python3 -B -m unittest tools.open_model_benchmark.test_benchmark` — 4 tests OK
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/open_model_benchmark/benchmark.py tools/open_model_benchmark/test_benchmark.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- `python3 -B -m tools.open_model_benchmark.benchmark --max-sources 3 --output /tmp/d056-open-model-benchmark.json`

Dry-run report shape: schema `open-model-benchmark.v1`, 9 tasks, task-pack
mode, model targets `gemma`, `llama`, `mistral`, `qwen`.

## Independent Review

Direct Claude CLI review over the working diff was attempted in this restricted
sandbox. It eventually returned `API Error: Unable to connect to API
(FailedToOpenSocket)`, so no Claude review verdict was obtained here.

Because this worktree has uncommitted edits and the shared git metadata is not
writable in this sandbox, `tools/merge/ai_review.py <branch>` would not review
the working diff correctly. Ember should rerun independent review from a
writable/live host before merge if the merge gate requires it.

## Risks

- This is a scaffold and offline scorer, not proof that any candidate model is
  installed or currently performant on the live host.
- Corpus tasks are deterministic proxies for learning speed; live benchmark
  quality depends on running the generated task pack against actual candidate
  model outputs.
- The optional Ollama runner assumes local models already exist and may fail
  closed if `ollama` is absent or a model tag is unavailable.

## Rollback

Revert the changed files above and remove the d056 entry from
`core/BUILD/REGISTRY.json`.

## Intent Solved

Open-model replacement work now has a concrete benchmark/scoring scaffold for
Qwen, Mistral, Llama, and Gemma on James's corpus instead of relying on generic
provider claims.

## Downstream Intent Unlocked

Ember/James can run one live local-model benchmark pass, compare builder vs
reviewer specialization, and route the first command-compatible local model
replacement spec using measured corpus performance.
