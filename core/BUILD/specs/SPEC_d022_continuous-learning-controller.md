# d022 — continuous learning controller
Auto-generated from standing intent: continuous learning controller (agreed on repeatedly, never yet queued).
## Build
Continuous learning controller — closes the loop between captured corrections and actual model preference updates. Three files, advisory/shadow only, $0, reversible, NEW FILES ONLY.

1. **tools/learn/learning_controller.py** — the controller. Reads `brain_index.corrections` (already live) + `memory/feedback_*.md` files + merge-outcome verdicts from `ops_ledger.jsonl`. Assembles incremental preference pairs (preferred vs rejected) since the last controller run. Writes new pairs to `tools/learn/data/preference_incremental.jsonl` (append-only, never overwrites). Stamps a `last_run` watermark to `tools/learn/.controller_state.json` so each run is idempotent (only processes new signal). Prints a one-line summary: `[d022] +N pairs this run, M total`.

2. **tools/learn/reward_signal.py** — signal extractor. Three sources with explicit weights: corrections (James's live taste, weight=1.0), merge-outcome reversals (weight=0.8), AI-verdict overrides (weight=0.5). Returns structured `RewardSignal` dataclass. Exported for use by the controller and future L3/L4 stages.

3. **tools/learn/test_controller.py** — tests assert: controller produces pairs from fixture corrections, watermark advances (idempotent on re-run), reward_signal weights are applied correctly, empty-signal run produces zero pairs without error.

NO model training in this build (L2 LoRA is deferred until 500+ pairs accumulate — the controller measures that threshold and logs when crossed). NO prod writes. NO self-grant. Output files only.
## Context
- Question: continuous learning controller — closes the loop between live corrections and preference signal
- Answer: standing intent, agreed on across multiple sessions, now queued
- Proof expected: independent-AI-reviewed branch, ready for your merge
## Contract
Follow docs/codex/SESSION_CONTRACT.md. Branch off feat/headless-build (never main).
Register in core/BUILD/REGISTRY.json. Tests required. Do NOT push or merge.
