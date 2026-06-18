# SPEC_d112_hot-memory-architecture-5-domain Result

- Status: done in working tree / awaiting merge review
- Branch: `build/SPEC_d112_hot-memory-architecture-5-domain`
- Base: `feat/headless-build`

## Files changed

- `tools/hot_memory/__init__.py`
- `tools/hot_memory/common.py`
- `tools/hot_memory/run_all.py`
- `tools/hot_memory/synthesize.py`
- `tools/hot_memory/scanners/__init__.py`
- `tools/hot_memory/scanners/spec_scanner.py`
- `tools/hot_memory/scanners/identity_scanner.py`
- `tools/hot_memory/scanners/ops_scanner.py`
- `tools/hot_memory/scanners/decision_scanner.py`
- `tools/hot_memory/scanners/signal_scanner.py`
- `tools/hot_memory/test_hot_memory.py`
- `SERVICES/sunheart-brain/curator/build_context.py`
- `SERVICES/sunheart-brain/curator/test_build_context.py`
- `core/STATE/HOT_STATE.md`
- `core/BUILD/cron/fpai-hot-memory-scan.service`
- `core/BUILD/cron/fpai-hot-memory-scan.timer`
- `core/BUILD/cron/fpai-hot-memory-synthesize.service`
- `core/BUILD/cron/fpai-hot-memory-synthesize.timer`
- `core/BUILD/specs/SPEC_d112_hot-memory-architecture-5-domain.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added the d112 hot-memory architecture as a deterministic, side-effect-light repo implementation. Five domain scanners now write bounded scanner JSON reports for spec/build state, identity directives, ops/resource state, recent decisions, and correction/feedback signals. `tools.hot_memory.run_all` runs all scanners, and `tools.hot_memory.synthesize` compresses scanner outputs into a cited `HOT_STATE.md` under the hot-memory directory and mirrors it to `core/STATE/HOT_STATE.md` for repo proof.

The bot context path now checks fresh `HOT_STATE.md` first and uses it as the primary current-memory context. `HOT_MEMORY_DISABLE=1`, missing state, or stale state falls back to the existing patchwork build-context behavior. The generated `HOT_STATE.md` is bounded under 3000 chars and includes the system email, active d112 build, last built d111 spec, bot identity, current directives, and active measurements.

Reviewed systemd timer artifacts are included for a 30-minute scanner cadence and 35-minute synthesis cadence. They are not installed or enabled in this sandbox.

## Tests

- `python3 -B -m unittest tools.hot_memory.test_hot_memory` (3 tests OK)
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -p 'test_build_context.py'` (9 tests OK)
- `python3 -m py_compile tools/hot_memory/common.py tools/hot_memory/run_all.py tools/hot_memory/synthesize.py tools/hot_memory/scanners/spec_scanner.py tools/hot_memory/scanners/identity_scanner.py tools/hot_memory/scanners/ops_scanner.py tools/hot_memory/scanners/decision_scanner.py tools/hot_memory/scanners/signal_scanner.py tools/hot_memory/test_hot_memory.py SERVICES/sunheart-brain/curator/build_context.py SERVICES/sunheart-brain/curator/test_build_context.py`
- `bash -n core/BUILD/cron/fpai-hot-memory-scan.service core/BUILD/cron/fpai-hot-memory-scan.timer core/BUILD/cron/fpai-hot-memory-synthesize.service core/BUILD/cron/fpai-hot-memory-synthesize.timer`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d112-registry.json`
- `python3 -B -m tools.hot_memory.run_all --hot-dir /tmp/d112-hot-memory --json`
- `python3 -B -m tools.hot_memory.synthesize --hot-dir /tmp/d112-hot-memory --output /tmp/d112-hot-memory/HOT_STATE.md --mirror core/STATE/HOT_STATE.md --json`
- `git diff --check`

## Risks

- Live `brain_index` reads were not exercised because this sandbox has no production DB access; decision/signal scanners fail soft to repo mirrors when DB access is unavailable.
- Timers were reviewed as artifacts only; no live systemd install/enable was performed.
- Synthesis is deterministic and local for testability. No Ollama call was made in this sandbox.
- The current bot context reader is `build_context_system_suffix()`, imported by `tgbot.py`; there is no literal `_build_context()` function in this branch.

## Commit status

Local `git add` was attempted and blocked by read-only shared Git metadata: Git could not create `/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d112_hot-memory-architecture-5-domain/index.lock`.

## Rollback

Revert the listed d112 files. If timers are installed later, disable/remove `fpai-hot-memory-scan.timer`, `fpai-hot-memory-scan.service`, `fpai-hot-memory-synthesize.timer`, and `fpai-hot-memory-synthesize.service`. Remove `~/.config/fpai/hot_memory/HOT_STATE.md` and scanner JSONs if live artifacts should be cleared.

## Intent solved

Bot current-memory context now has a single fresh, cited HOT_STATE document instead of assembling six stale-prone sources at query time.

## Downstream intent unlocked

d111 awareness reliability can use HOT_STATE as the ground-truth current-memory surface, making bot awareness probes measure one cited state layer rather than scattered raw sources.
