# SPEC_d100_fpos-frontier-node-public-contri Result

Status: done in working tree / awaiting merge review

## Files Changed

- `tools/forge/`
- `core/STATE/FRONTIER_LOG.md`
- `core/STATE/FRONTIER_LOG.public.md`
- `core/STATE/UPSTREAM_CONTRIBUTIONS.md`
- `benchmarks/`
- `fpos-template/`
- `core/BUILD/specs/SPEC_d100_fpos-frontier-node-public-contri.md`
- `core/BUILD/results/SPEC_d100_fpos-frontier-node-public-contri.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added the FPOS public contribution layer as additive, dry-run-first repo infrastructure. The new Forge helpers sanitize and prepare the public FRONTIER_LOG export, publish only with `--execute` plus `FRONTIER_PUBLISH_APPROVED=1`, track `CONTRIBUTE:` opportunities into `UPSTREAM_CONTRIBUTIONS.md`, draft council-gated upstream PR descriptions, and generate public benchmark leaderboard snapshots only after at least 3 data points per agent. Seeded the public frontier log, public export, upstream contribution tracker, benchmark docs/results, and a canonical non-personal `fpos-template/`.

## Tests

- `python3 -B -m unittest tools.forge.test_frontier_node tools.benchmarks.test_benchmarks`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/forge/__init__.py tools/forge/security_gate.py tools/forge/publish_frontier_log.py tools/forge/track_upstream.py tools/forge/public_benchmarks.py tools/forge/test_frontier_node.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d100-registry.json`
- `python3 -m tools.forge.publish_frontier_log --json`
- `python3 -m tools.forge.public_benchmarks --json`
- `python3 -m tools.forge.track_upstream --input core/STATE/FRONTIER_LOG.md --json`

## Risks

- The public security gate is conservative and pattern-based; it blocks known private-layer patterns but is not a substitute for human review before public releases.
- `publish_frontier_log.py` can call `gh release create` only when explicitly executed and approved by env; this sandbox did not publish anything.
- Upstream PR descriptions are drafts only. Actual external PR submission remains a James/Council gate.
- The seeded benchmark leaderboard currently publishes no agents because the public gate requires at least 3 scored data points.

## Rollback

Revert the d100 files listed above. No live release, external PR, timer, service, deploy, secret access, outreach, or money action was performed.

## Intent

Intent solved: FPOS now has a repo-local public contribution layer that turns frontier scans, benchmark proof, template patterns, and upstream gaps into sanitized public artifacts without making live external moves.

Downstream intent unlocked: Forge can run weekly public-node proofs and James/Ember can choose when to publish a release, template repo, or upstream PR from already sanitized draft artifacts.

