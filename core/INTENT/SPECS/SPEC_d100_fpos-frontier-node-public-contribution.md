# SPEC d100 — FPOS Frontier Node: Public Contribution Layer

**Status:** queued | **Stream:** Game + Ventures | **Blast radius:** additive only

## What

Transform FPOS from a frontier consumer into a frontier node. Nodes attract signal. Signal accelerates the compounding loop. This is the credibility, marketing, and funding strategy — executed through the system itself, not through pitching.

## The compounding flywheel

```
Scan frontier → integrate → stack improves
→ novel capability emerges → publish proof
→ community finds us → contributes back
→ better scans → faster integration
→ repeat — each cycle faster than the last
```

## Four outputs that build the node

### 1. Public FRONTIER_LOG (weekly, sanitized)
- `core/STATE/FRONTIER_LOG.md` already designed (d096)
- Publish sanitized version weekly as GitHub release + optional newsletter
- Security gate strips all private layer before publication
- The AI community will cite "FPOS weekly scan" if it's consistently useful
- Cost: $0. Benefit: authority, inbound, citations

### 2. Open benchmark leaderboard
- d073 produces per-agent benchmark scores
- Publish as `benchmarks/` in a public-facing repo: cost-per-task vs GPT-4o, latency p95, sovereign run qualification
- Format: simple markdown table updated each fine-tune cycle
- What gets funded: "self-improving AI OS, measurably cheaper than closed alternatives, sovereign-run qualified"
- This is the proof investors look for without being pitched

### 3. Canonical FPOS template (cell-split seed, public repo)
- The non-personal canonical layer (MODEL_DNA.md + routing rules + council debate pattern + GEPA integration + Dittofeed journey config) published as a standalone repo
- License: MIT or Apache-2.0
- Every fork is a user. Every user's improvement (if they contribute back) feeds the canonical layer
- This IS the product demo — "here's a self-improving AI OS, fork it"
- Template repo: `github.com/sunheartai/fpos-template` (or similar)

### 4. Upstream contributions
- As we integrate Pipecat / Cognee / GEPA / Dittofeed / Postiz, we find gaps
- Forge tracks gaps found during integration → queues PRs to upstream repos
- Each merged PR: we're contributors, not just consumers
- Contributors get noticed. Noticed = inbound interest
- `core/STATE/FRONTIER_LOG.md` gets an `UPSTREAM_PR` section tracking this

## The Forge's expanded mandate

Beyond scanning and integrating, the Forge now:

1. **Identifies contribution opportunities** — while integrating external tools, flags: "this project has a gap we could fix"
2. **Drafts upstream PRs** — writes the PR description + minimal code change
3. **Tracks community reception** — watches GitHub stars/forks/citations of our contributions
4. **Identifies when our benchmark results exceed published baselines** — that's the moment to write the paper or post

Weekly scan output gains a new section:
```
CONTRIBUTE: [project] — [gap we found] — [PR complexity: low/med/high]
```

## The self-reinforcing credibility loop

```
We publish FRONTIER_LOG → community cites it
→ they find FPOS-template → they fork it
→ fork improvements feed canonical layer
→ FPOS-llama benchmarks improve
→ we publish improvement delta
→ OSS investors notice
→ funding unlocks more compute
→ better fine-tune → better benchmarks
→ more credibility → more forks → repeat
```

No pitching. No marketing spend. The system markets itself by being useful and measurable.

## The funding proof (what investors actually need to see)

- ✅ Benchmarks: cost-per-task < GPT-4o API on our task set (d073)
- ✅ Sovereign run: completes without required external API (Ollama)
- ✅ Self-improving: benchmark delta improves each GEPA/fine-tune cycle
- ✅ Community: forks of FPOS-template (even 10 is proof of utility)
- ✅ Real usage: James's corrections table as proof of live signal
- ✅ Upstream contributions: merged PRs in Pipecat/Cognee/GEPA

That's a fundable proof without a pitch deck.

## Deliverables

### `tools/forge/publish_frontier_log.py`
- Reads FRONTIER_LOG.md, runs security gate (strip private layer)
- Publishes sanitized version as GitHub release via gh CLI
- Runs after weekly scan (fpai-forge-weekly.timer)

### `tools/forge/track_upstream.py`
- Tracks contribution opportunities found during integration
- Logs to `core/STATE/UPSTREAM_CONTRIBUTIONS.md`
- Drafts PR descriptions for Forge review

### `benchmarks/` directory (public-facing)
- `README.md` — benchmark methodology
- `results/YYYY-MM-DD.md` — per-cycle results
- `leaderboard.md` — current best scores vs baselines

### `fpos-template/` seed (canonical layer only)
- `MODEL_DNA.md` (canonical layer, personal stripped)
- `council/` — 3-lens debate config
- `routing/` — T0→T5 routing rules
- `learning/` — GEPA integration pattern
- `README.md` — "fork this to start your own self-improving AI OS"

## Gates
- Security gate: every publication runs through `tools/forge/security_gate.py`
- Template repo: personal DNA never included (automated check)
- Benchmarks: only publish when we have ≥3 data points (avoid single-run noise)
- Upstream PRs: council reviews before submission (irreversible — goes to external)

## Why this is the marketing and funding strategy

The community that would fund this is the same community that uses GEPA, Pipecat, Cognee. They find us through our contributions, our frontier log, our benchmarks. They adopt the template. Adoption is the proof. Proof is the pitch.

No separate marketing budget. No separate funding campaign. The system builds its own credibility by being genuinely useful to the frontier it's consuming from.
