# SPEC_d053_blueprint-weakness-auditor-tool Result

- **Status:** done / awaiting James review + merge review
- **Branch:** `build/SPEC_d053_blueprint-weakness-auditor-tool`
- **Completed:** 2026-06-16T22:35:00Z

## Files changed

- `tools/blueprint_auditor/__init__.py`
- `tools/blueprint_auditor/auditor.py`
- `tools/blueprint_auditor/test_auditor.py`
- `tools/scout/__init__.py`
- `tools/scout/tool_scout.py`
- `tools/scout/test_tool_scout.py`
- `core/BUILD/cron/fpai-blueprint-weakness-auditor.service`
- `core/BUILD/cron/fpai-blueprint-weakness-auditor.timer`
- `core/BUILD/cron/fpai-tool-scout.service`
- `core/BUILD/cron/fpai-tool-scout.timer`
- `core/BUILD/signals/blueprint_weakness_report.md`
- `core/BUILD/signals/blueprint_weakness_proposals.jsonl`
- `core/BUILD/signals/tool_scout_report.md`
- `core/BUILD/signals/tool_scout_proposals.jsonl`
- `core/BUILD/specs/SPEC_d053_blueprint-weakness-auditor-tool.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added two companion scanner agents:

- Blueprint Weakness Auditor: deterministic local audit of `docs/blueprints/*.md` for missing required sections, vague/non-measurable standards, undated verified behavior, aspirational current behavior, incomplete integration maps, weak test coverage, and undated history. It writes a Markdown report plus review-gated JSONL improvement proposals under `core/BUILD/signals/`.
- Tool Scout: ranks GitHub/product/model/tool-drop candidates, validates cost and safety boundaries, writes a report plus adoption proposal JSONL, and supports a scheduled `--live` mode that searches GitHub repository and release endpoints before falling back to local seeds if live sources are unavailable.

Added review-only systemd service/timer artifacts for both agents. No timer was installed in this sandbox, no provider credentials were used, no tools were installed, and no adoption action was taken.

## Initial signal output

- Blueprint audit generated 20 findings across 12 blueprints and 8 review-gated proposals.
- Tool scout generated 3 ranked seed candidates and 2 review-gated adoption proposals.

## Tests

- `python3 -B -m unittest tools.blueprint_auditor.test_auditor tools.scout.test_tool_scout tools.scout.test_scout_run` (14 tests OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/blueprint_auditor/auditor.py tools/blueprint_auditor/test_auditor.py tools/scout/tool_scout.py tools/scout/test_tool_scout.py`
- `python3 -B -m tools.blueprint_auditor.auditor --no-ledger --json`
- `python3 -B -m tools.scout.tool_scout --no-ledger --json`
- `python3 -m json.tool core/BUILD/REGISTRY.json`
- JSONL validation for `core/BUILD/signals/blueprint_weakness_proposals.jsonl` and `core/BUILD/signals/tool_scout_proposals.jsonl`
- `git diff --check -- core/BUILD/REGISTRY.json tools/blueprint_auditor tools/scout core/BUILD/cron core/BUILD/signals core/BUILD/specs/SPEC_d053_blueprint-weakness-auditor-tool.md`

## Independent review

Completed by subagent. It found two blockers:

1. Registry still showed `building` / `tests_passed=false`; fixed during closeout by marking d053 done after tests passed.
2. Tool Scout scheduled path only regenerated static seeds. Fixed by adding `--live`, a built-in GitHub search/release collector, service wiring, and mocked live-source regression coverage.

## Commit status

Blocked in this sandbox. `git commit -m "feat(d053): add blueprint auditor and tool scout"` failed because Git could not create `/opt/fpai-build/FPAI_Cockpit/.git/worktrees/SPEC_d053_blueprint-weakness-auditor-tool/index.lock`: read-only file system. Working-tree changes are intact and unstaged.

## Risks

- Live GitHub/API behavior was not exercised in this restricted sandbox; the live path is covered with mocked API payloads and falls back to seeds if sources fail.
- Tool Scout candidate quality depends on configured search terms and may need tuning after real run evidence.
- Blueprint Auditor audits blueprint files and their contract quality; agents without blueprints are not audited until represented in `docs/blueprints/`.
- The systemd artifacts are review-only until Ember installs them on the live host.

## Rollback

Revert the changed files listed above. If Ember later installs the timers, disable/remove `fpai-blueprint-weakness-auditor.timer` and `fpai-tool-scout.timer`, then run `systemctl daemon-reload`.

## Intent solved

Existing blueprints and adoption candidates now have scanner agents that produce review-gated improvement signals instead of relying on James or Ember to notice weaknesses manually.

## Downstream intent unlocked

The build loop can review concrete blueprint-hardening and tool-adoption proposals from `core/BUILD/signals/` and route the best ones into future specs without installing or adopting anything automatically.
