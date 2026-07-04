# Spec: Replace bot LLM with claude -p subprocess (subscription-tier, $0)

## Problem
curator/llm.py uses metered Anthropic API ($$$) or Ollama (low quality).
The right carrier is `claude -p` via subprocess — Claude Max subscription, $0 marginal, same quality as sessions.

## Build
Add `claude-cli` provider to /opt/sh-brain-src/curator/llm.py:
- New async function `_claude_cli(system, user, max_tokens, ...)` 
- Uses subprocess to call `claude -p "{system}\n\n{user}"` with timeout=60s
- Falls back to ollama if claude CLI not found or exits nonzero
- Set CURATOR_LLM_PROVIDER=claude-cli in /etc/sh-brain/curator.env
- Restart sh-brain-tgbot

## Proof
journalctl -u sh-brain-tgbot | grep -v "api.anthropic.com" for 30min after deploy

## Contract
SAFE-AUTO. Reversible: revert CURATOR_LLM_PROVIDER=ollama instantly.
No new files needed beyond llm.py edit + curator.env change.
