# brain-curator — AI-to-AI brain optimizer

An unattended worker that runs on the Secondary server and continuously
optimizes the Sunheart Brain via LLM-driven proposals.

## What it does

Every proposal it makes is written to **`07 · Curator Queue`** in AppFlowy.
Rows where type is safe + confidence is High auto-apply immediately and land
as ✅ Applied. Everything else sits as 🟡 Proposed for you to review in
AppFlowy. Flip a row's Status to ✅ Approved and the next `apply-approved`
run executes it.

## Jobs & cadence

| Job               | Schedule         | What it does                                                     | Auto-applies?              |
| ----------------- | ---------------- | ---------------------------------------------------------------- | -------------------------- |
| `dedup`           | every 1 h        | LLM reviews near-duplicate pairs (0.85-0.95 cosine); proposes link/merge | link-concept @ High only |
| `summarize`       | every 6 h        | 2-3 sentence summary + topics for new conversations               | ✅ yes (cheap & safe)      |
| `cluster-tag`     | every 6 h        | k-means on last 24 h of notes; proposes canonical tag per cluster | no — needs taxonomy review |
| `triage`          | daily @ 03:00 MT | scans Personal-tier notes; proposes safe promotions to Public     | no — tier is sacred        |
| `digest`          | daily @ 07:00 MT | metrics report to the queue (new notes, merges, blocked queries) | records only               |
| `apply-approved`  | every 15 min     | executes any ✅ Approved row                                     | (the executor itself)      |

## LLM routing

- **Preferred:** Anthropic Claude (`ANTHROPIC_API_KEY`).
- **Fallback:** local Ollama (`llama3.1:8b` by default).

Every proposal records `model` + `prompt_sha1` in the `Diff` cell → you can
always see which model decided what.

## Queue schema guardrail

Some AppFlowy setups do not reliably persist the `Type` select value on queue
rows. The curator pipeline therefore treats `Diff` as canonical metadata:

- `Diff.proposal_type` (primary fallback)
- `Diff.diff.type` (secondary fallback)

Telegram approvals, bulk low-risk checks, and `apply-approved` all use this
fallback path so actions still execute even when `Type` is blank.

## Run manually

```bash
# one job, one-shot
systemctl start brain-curator@dedup

# tail everything
journalctl -u 'brain-curator@*' -f

# inspect timers
systemctl list-timers 'brain-curator-*'

# run every job now (first-time priming)
cd /opt/sh-brain-src
.venv/bin/python -m curator all
```

## Safety

- Every change lands in `07 · Curator Queue` — visible, timestamped, reversible.
- `merge_log` in Postgres records every concept merge with the pre-state diff.
- `apply-approved` is the only way tier changes + tag additions get written.
- Disable entirely:
  ```bash
  systemctl disable --now 'brain-curator-*.timer'
  ```
