# SPEC_d163_spec-replace-bot-llm-with-claude - Result

Status: done in working tree / awaiting review + merge.

Files changed:
- `SERVICES/sunheart-brain/curator/llm.py`
- `SERVICES/sunheart-brain/curator/test_llm.py`
- `core/BUILD/activate/SPEC_d163_spec-replace-bot-llm-with-claude.sh`
- `core/BUILD/specs/SPEC_d163_spec-replace-bot-llm-with-claude.md`
- `core/BUILD/results/SPEC_d163_spec-replace-bot-llm-with-claude.result.md`
- `core/BUILD/REGISTRY.json`
- `docs/codex/HANDOFF.md`

Summary:
- Added explicit `CURATOR_LLM_PROVIDER=claude-cli` support in curator `llm.py`.
- The new provider calls `claude -p "<system>\n\n<user>"` asynchronously with a 60s default timeout.
- Missing `claude`, nonzero CLI exit, and CLI timeout fall back to the existing Ollama provider.
- Added `CURATOR_CLAUDE_CLI_BIN` and `CURATOR_CLAUDE_CLI_TIMEOUT` knobs while keeping `claude` and 60s as defaults.
- Added a post-merge activation script that backs up live `llm.py` and `/etc/sh-brain/curator.env`, installs the reviewed `llm.py`, sets `CURATOR_LLM_PROVIDER=claude-cli`, compiles the live file, and restarts `sh-brain-tgbot.service`.

Tests:
- `python3 -B -m unittest curator.test_llm` (3 OK)
- `env PYTHONPYCACHEPREFIX=/tmp/fpai-pycache python3 -m py_compile SERVICES/sunheart-brain/curator/llm.py SERVICES/sunheart-brain/curator/test_llm.py`
- `bash -n core/BUILD/activate/SPEC_d163_spec-replace-bot-llm-with-claude.sh`
- `python3 -m json.tool core/BUILD/REGISTRY.json >/tmp/d163-registry.json`
- `git diff --check`

Risks:
- This sandbox did not edit `/opt/sh-brain-src`, change `/etc/sh-brain/curator.env`, restart the live bot, or observe 30 minutes of live journal output.
- If the systemd service cannot find or authenticate `claude`, the provider intentionally falls back to Ollama. Set `CURATOR_CLAUDE_CLI_BIN` if the CLI lives outside systemd's default `PATH`.
- Live `llm.py` is a known diverged curator follow-up surface; the activation script backs up before replacing it, but merge review should confirm the repo file is the intended live source for this slice.

Rollback:
- Immediate runtime rollback after activation: restore `CURATOR_LLM_PROVIDER=ollama` in `/etc/sh-brain/curator.env` and restart `sh-brain-tgbot.service`.
- Full activation rollback: copy `llm.py` and `curator.env` from the activation backup directory printed by the script, then restart `sh-brain-tgbot.service`.
- Code rollback: revert this branch.

Intent solved:
- d163 removes the Telegram bot's dependence on metered Anthropic API for primary Claude-quality replies by routing through the Claude subscription CLI.

Downstream intent unlocked:
- The live bot can use subscription-tier Claude quality with $0 marginal token spend, while retaining Ollama as a no-network fallback if the CLI is unavailable.

Proof still needed after merge/activation:
- `journalctl -u sh-brain-tgbot --since '30 minutes ago' --no-pager | grep -F 'api.anthropic.com'` returns no rows.
