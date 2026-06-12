# TOOL_PLAYBOOK.md — "Use THIS for THAT"

Keep it short. Add entries as patterns emerge.

## Decision Tree

**James sent a Telegram message** → reply via the gateway. Use Sonnet only if drafting real prose. For classify/route, try `tools/ollama-ask.sh` first.

**“What’s going on across brains?”** → `tools/brain-brief.sh [optional query]` then summarize bottom-line for James.

**“Are ZV + Sunheart up and what tools exist?”** → `tools/brain-status.sh`

**“Which brains am I allowed to see?”** → `tools/brain-list.sh`

**Log something to ZV Weekly Log (Adam section)** → `tools/brain-zv-log.sh "summary" [area]`  
(Or direct: `tools/zv-brain.sh log "…"` — same underlying MCP.)

**Add a note to Sunheart (Adam namespace)** → `tools/brain-sunheart-note.sh "Title" "Body"`

**ZV-only: search / list / status** → `tools/zv-brain.sh search|list|status|recent …`

**ZV Telegram ground signal (read-only)** → `tools/zv-signals.sh`

**Classify or route text** → `tools/ollama-ask.sh "classify: …"`

**Web fact** → `tools/websearch.sh` or `tools/perplexity.sh` — extract **facts** only; never paste generic billing/support page lines (Anthropic “charges”, “anything else”, etc.) into Telegram.

**NOW.md / priorities** → read `NOW.md` (symlinked to `/opt/fpai/NOW.md`)

**Escalate to James** → `tools/ask_human.sh` (or Telegram if appropriate)

**Something broke** → `/tmp/openclaw/openclaw-YYYY-MM-DD.log` + systemd auto-restart

**Security regression check** → `tools/security-sentinel.sh` (don’t spam James if clean)

**Remember something** → `MEMORY.md` or `memory/YYYY-MM-DD.md`

## Tools Worth Knowing

| Tool | When |
|------|------|
| `brain-brief.sh` | Cross-brain “what’s going on” snapshot |
| `brain-status.sh` | Per-brain health + tool list |
| `brain-list.sh` | Allowed brains for this token |
| `brain-zv-log.sh` | ZV weekly log entry (via mesh) |
| `brain-sunheart-note.sh` | Sunheart note (via mesh) |
| `zv-brain.sh` | Direct ZV brain CLI (same host) |
| `zv-signals.sh` | ZV Telegram log signals |
| `ollama-ask.sh` | Free local inference first |
| `ask_human.sh` | Real escalation |
| `security-sentinel.sh` | Permission / leak regression scan |
| `cost-audit.sh` | Token spend hygiene |

## Tools to AVOID (unless James explicitly asks)

| Tool | Why |
|------|-----|
| `trade.sh` / `trading.sh` / `whaletrack.sh` | Trading lives on primary; out of default scope |
| `spawn_bot.sh` / `bot_registry.sh` | Factory-era; not default |
| `facebook.sh` / `discord.sh` | Not current ZV channel mix unless asked |

## When In Doubt

**Default to silence.** $0 is a valid output. If you don’t have a clear, net-positive reason to act, don’t act.
