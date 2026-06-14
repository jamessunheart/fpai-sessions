# SPEC_headless-build

*Phase-2 of the autonomy ladder ([[OPERATING WORKFLOW]]): remove the copy-paste step at ~$0 by invoking a headless FLAT-RATE builder on a spec. Owner: Codex. One spec = one branch.*

## Intent
Today a build needs James to paste a kickoff into Codex. Replace that with a headless invocation that runs on flat plans (`claude -p` on Claude Max, or `codex` CLI) — so voice→spec→build completes with no paste and no metered spend. Pattern already proven by `queue-builder` (`claude -p` headless on Max, ~$0).

## Definition of Done
A `tools/autobuild/run.py` that:
1. takes a spec path (`--spec docs/codex/specs/SPEC_<x>.md`),
2. **cost-guard preflight** (`~/.local/bin/cost-guard autobuild || exit 0`) + kill-switch,
3. invokes a **flat-rate** headless builder on it: prefer `claude -p` (Max) or `codex` CLI; never a metered API unless `--metered` is explicitly passed,
4. captures result → posts to `docs/codex/HANDOFF.md` 📥 (files changed · summary · tests · risks · rollback),
5. does NOT merge / move money / deploy / touch secrets — escalates Reserved work,
6. `--dry-run` prints the command it WOULD run, executes nothing.

## Files allowed
- `tools/autobuild/run.py` · `tools/autobuild/__init__.py`

## Files forbidden
- `tools/router/*` · `tools/index/*` · `tools/selfmodel/*` (other lanes — keep disjoint), SERVICES, secrets, money, deploy.

## Tests
- `python3 -m py_compile tools/autobuild/run.py`
- `--dry-run` prints a flat-rate headless command, runs nothing.
- cost-guard blocks when `.pause-ambient` is set.

## Rollback
- delete `tools/autobuild/`.

## Why now
Turns the manual-paste loop into flat-rate autonomy — the highest-leverage cost-free upgrade; with route-filtering, the router can build `route:auto` specs unattended.
