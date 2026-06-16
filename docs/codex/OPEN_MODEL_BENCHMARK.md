# Open Model Benchmark Scaffold

`tools/open_model_benchmark/benchmark.py` creates a repo-local benchmark pack for
Qwen, Mistral, Llama, and Gemma candidates on James's corpus. It measures:

- corpus classification accuracy;
- few-shot learning gain from baseline to one-shot/two-shot rounds;
- latency when response rows include `latency_ms`;
- evidence and calibration signals for reviewer specialization.

The scaffold is advisory-only. It does not download models, train models, spend
money, deploy, send outreach, or change routing authority. Live execution is
opt-in with local Ollama only.

## Commands

Build a task pack:

```bash
python3 -B -m tools.open_model_benchmark.benchmark --json --max-sources 8
```

Score existing response JSONL:

```bash
python3 -B -m tools.open_model_benchmark.benchmark \
  --responses /tmp/open-model-responses.jsonl \
  --output /tmp/open-model-benchmark.json
```

Run a small local Ollama smoke, only if models are already installed:

```bash
python3 -B -m tools.open_model_benchmark.benchmark \
  --run-ollama \
  --max-tasks 3 \
  --output /tmp/open-model-benchmark.json
```

## Response JSONL

Each row should be:

```json
{"model":"qwen","task_id":"omb-example","response":"{\"label\":\"buildstream\",\"evidence\":\"branch/register/tests\",\"confidence\":0.9}","latency_ms":1200}
```

Model ids should be one of `qwen`, `mistral`, `llama`, or `gemma` unless an
operator intentionally adds another candidate for comparison.

## Cooperative Setup

The report emits `cooperative_setup`:

- `builder`: highest weighted task accuracy, learning gain, and speed score;
- `reviewer`: strongest non-builder evidence/calibration score;
- `specialists`: all candidates with advisory roles;
- `cross_checks`: builder/reviewer pairings where the reviewer must cite corpus
  evidence and veto unsupported claims.

No assignment expands model authority. The output is a reviewed input to later
local-model replacement specs.

