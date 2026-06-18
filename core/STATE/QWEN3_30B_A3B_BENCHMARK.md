# Qwen3-30B-A3B MoE Benchmark

- Generated: `2026-06-18T20:08:57Z`
- Mode: `task-pack`
- Tasks: `8`
- Candidate: `qwen3-30b-a3b` (`qwen3:30b-a3b`, 30B total / 3B active)
- Baseline: `llama3.1-8b` (`llama3.1:8b`, 8B dense)
- Authority: advisory-only; this report does not change routing or deploy models.

## Result

No live responses were scored in this sandbox. The benchmark task pack is ready for server 162 or any local Ollama host with both model tags already installed.

Run live only when approved from the target host:

```bash
python3 -B -m tools.open_model_benchmark.qwen_moe_benchmark --run-ollama --max-tasks 8 --output core/BUILD/signals/qwen3_30b_a3b_benchmark.json --state core/STATE/QWEN3_30B_A3B_BENCHMARK.md
```
