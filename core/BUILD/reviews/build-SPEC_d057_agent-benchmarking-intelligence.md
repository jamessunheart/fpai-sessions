# AI Review — build/SPEC_d057_agent-benchmarking-intelligence

**Verdict:** APPROVE · **Risk:** low

**Summary:** Advisory agent-benchmarking layer (d057): read-only repo scoring + fixed-allowlist public benchmark fetch into a JSONL ledger; correctly branched off feat/headless-build, no push/merge, advisory-only with hard gates against routing/spend/training/deploy, cost-capped, systemd units not auto-installed — safe.

## Findings
- Non-blocking: the shipped .service runs `--live-public-sources --append-ledger` and writes the git-tracked files core/BUILD/signals/agent_benchmark_intelligence.json + agent_scoring_ledger.jsonl every 6h. If Ember installs the timer on 162, it creates continuous uncommitted churn in a repo where parallel sessions commit — the documented collision-bug surface. Recommend the timer write to an out-of-tree path (e.g. /opt/fpai-build/) or gitignore the signal outputs before install.
- Non-blocking: fetch_public_source pulls untrusted live web page text, strips HTML, and embeds a 700-char snippet into the signal JSON that Ember reads. Used only for keyword dimension-weighting (no exec), so low prompt-injection risk, but the snippet is human-surfaced — keep treating it strictly as data.
- Provider command path (_run_provider via --provider-cmd / AGENT_BENCHMARK_PROVIDER_CMD env) executes an operator-supplied command; correctly uses shlex.split + shell=False and is not used by the default service. Keep it review-gated and never wire it to untrusted input.

*Reviewer: claude-opus-4-8 (independent of the Codex builder).*
