# SPEC_d136_surface-constitution-in-chat Result

- Status: done in working tree / awaiting independent AI review + merge
- Branch: `build/SPEC_d136_surface-constitution-in-chat`
- Base branch: `feat/headless-build`

## Files changed

- `tools/constitution/__init__.py`
- `tools/constitution/surface.py`
- `tools/constitution/test_surface.py`
- `SERVICES/sunheart-brain/curator/tgbot.py`
- `SERVICES/sunheart-brain/curator/test_tgbot_constitution.py`
- `core/BUILD/activate/SPEC_d136_surface-constitution-in-chat.sh`
- `core/BUILD/specs/SPEC_d136_surface-constitution-in-chat.md`
- `core/BUILD/results/SPEC_d136_surface-constitution-in-chat.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

## Summary

Added a repo-local constitution surfacer that resolves the current constitution source from the server repo, formats it as Telegram-safe HTML chunks, and can send it to James's Telegram chat only when explicitly run with `--send`. The default source is `core/INTENT/AGREEMENTS/CONSTITUTION_v1.md`, falling back to `core/knowledge/CONSTITUTION.md`, with `FPAI_CONSTITUTION_PATH` or `--source` available for future governance-source changes.

Wired `/constitution` into the private owner Telegram bot so James can request the live repo constitution inside chat. Added an idempotent post-merge activation script that sends the constitution once on server 162 and records a marker at `/var/lib/fpai-build/d136_constitution_sent`.

## Tests

- `python3 -B -m unittest tools.constitution.test_surface`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -t SERVICES/sunheart-brain -p 'test_tgbot_constitution.py'`
- `python3 -B -m unittest discover -s SERVICES/sunheart-brain/curator -t SERVICES/sunheart-brain -p 'test_tgbot_correction_wiring.py'`
- `python3 -B -m tools.constitution.surface --repo-root . >/tmp/d136-constitution-dryrun.txt`
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile tools/constitution/__init__.py tools/constitution/surface.py tools/constitution/test_surface.py SERVICES/sunheart-brain/curator/tgbot.py SERVICES/sunheart-brain/curator/test_tgbot_constitution.py`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d136-registry.json`
- `bash -n core/BUILD/activate/SPEC_d136_surface-constitution-in-chat.sh`
- `LC_ALL=C rg -n "[^\\x00-\\x7F]" tools/constitution core/BUILD/activate/SPEC_d136_surface-constitution-in-chat.sh SERVICES/sunheart-brain/curator/test_tgbot_constitution.py || true`
- `git diff --check`

Dry-run proof rendered `core/INTENT/AGREEMENTS/CONSTITUTION_v1.md` as two Telegram messages.

## Independent review

Attempted local independent AI review with `claude -p` over the d136 diff. It failed with `API Error: Unable to connect to API (ConnectionRefused)`. Independent AI review remains a pre-merge gate.

## Risks

- No live Telegram send was performed in this sandbox.
- The post-merge activation script sends to James's owner chat once if Telegram credentials are available on server 162. It is guarded by a state marker to avoid repeated sends on reruns.
- Source choice defaults to the published Mirror Constitution because it is the first current constitution artifact in the repo. Future governance source changes can be handled by setting `FPAI_CONSTITUTION_PATH`.

## Rollback

Revert the listed files. If activation has already run, remove `/var/lib/fpai-build/d136_constitution_sent` only if a future resend is desired; otherwise no persistent service/timer is installed.

## Intent solved

James can read the live repo constitution directly in Telegram without leaving chat.

## Downstream intent unlocked

Governance/constitution references can now be surfaced through the owner chat path, reducing context-switching and making future governance-source updates readable from the same conversation.
