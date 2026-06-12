# ember-substrate-mcp

Thin MCP tool-surface in front of the Ember FastAPI substrate
(`127.0.0.1:8765`). Lets Claude Desktop (and eventually Claude iOS) act as
James's primary work interface without losing the substrate-power Claude Code
has been carrying.

- **Trust-tier:** 4.1 reversible
- **Master kill-switch:** `EMBER_MCP_DISABLE=1`
- **Tools:** 15 read + 5 write = 20 total
- **No subprocess, no Task tool, no agent dispatch** (structural single-depth)

---

## File layout

```
SERVICES/ember-substrate-mcp/
├── server.py         # stdio entrypoint (kill-switch · token preflight · MCP harness)
├── tools.py          # 20 tools + dispatcher + _get_substrate helper
├── permissions.py    # path validation · hot-files.txt loader · structured 403
├── smoke_test.py     # in-process call_tool harness · verifies all 20 + forbidden paths
├── requirements.txt  # mcp>=1.21,<2 · httpx>=0.27
└── README.md         # this file
```

---

## Install (James-side, ~10 min)

### 1. (Optional) confirm Python deps

Both already installed system-wide on the build machine; if you ever rebuild
the Python env:

```sh
python3 -m pip install -r SERVICES/ember-substrate-mcp/requirements.txt
```

### 2. Smoke-test the server in-process

```sh
FPAI_COCKPIT_ROOT=/Users/jamessunheart/FPAI_Cockpit \
EMBER_API_TOKEN_FILE=/Users/jamessunheart/.config/fpai/api.token \
EMBER_API_BASE=http://127.0.0.1:8765 \
EMBER_MEMORY_GLOBAL=/Users/jamessunheart/.claude/memory-global \
EMBER_FPAI_CONFIG=/Users/jamessunheart/.config/fpai \
python3 SERVICES/ember-substrate-mcp/smoke_test.py
```

Expected: `PASS: NN   FAIL: 0` and exit 0.

### 3. Patch Claude Desktop config

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`,
**add** the block under `mcpServers` (alongside sunheart-brain — don't replace):

```json
"ember-substrate": {
  "command": "python3",
  "args": ["/Users/jamessunheart/FPAI_Cockpit/SERVICES/ember-substrate-mcp/server.py"],
  "env": {
    "EMBER_API_TOKEN_FILE": "/Users/jamessunheart/.config/fpai/api.token",
    "EMBER_API_BASE": "http://127.0.0.1:8765",
    "FPAI_COCKPIT_ROOT": "/Users/jamessunheart/FPAI_Cockpit",
    "EMBER_MEMORY_GLOBAL": "/Users/jamessunheart/.claude/memory-global",
    "EMBER_FPAI_CONFIG": "/Users/jamessunheart/.config/fpai"
  }
}
```

Validate JSON before saving:

```sh
python3 -m json.tool < "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

### 4. Cmd+Q Claude Desktop (not just close window), reopen

In a new conversation:

- *"What tools from ember-substrate?"* → should list 20 `ember_*` tools.
- *"What's in my NOW.md?"* → calls `ember_read_now`, returns the file.
- *"Log: testing from Desktop"* → calls `ember_log_message`. Verify in
  terminal: `curl -s -H "Authorization: Bearer $(cat ~/.config/fpai/api.token)" http://127.0.0.1:8765/inbox`
  shows the message with `X-Client: claude-desktop-mcp` traceable.

---

## Tool surface

### Read (15) — always allowed

| Tool | Backing |
|---|---|
| `ember_read_state(layer?)` | `GET /state` or `/state/{layer}` |
| `ember_read_now` | `core/STATE/NOW.md` |
| `ember_read_goals` | `core/STATE/AI_GOALS.md` |
| `ember_read_scene` | `core/STATE/SCENE.md` |
| `ember_read_alignment` | `~/.claude/memory-global/identity/ALIGNMENT.md` |
| `ember_read_story_handoff` | `STORY.md` → "Last session handoff" section |
| `ember_read_next_turn_surface` | `~/.config/fpai/specs/next-turn-surface.md` or `{present:false}` |
| `ember_read_narrator_log(date?)` | `core/INTELLIGENCE/narrator/sessions/<date>.md` |
| `ember_read_events(since_minutes, types?)` | `events.jsonl` tail filtered |
| `ember_read_decisions(since_days)` | `decisions.jsonl` tail |
| `ember_read_memory_search(query, limit)` | grep across `memory-global/*.md` |
| `ember_read_agent(name)` | `.claude/agents/<name>.md` (kebab) |
| `ember_list_agents` | list + first-line description |
| `ember_read_agent_identity(agent)` | `memory-global/agent_identity/<agent>/` |
| `ember_read_mindmap` | `core/STATE/MINDMAP.md` |

### Write (5) — Trust-tier 4.1 (every call runs `check_write` first + fires audit event)

| Tool | Effect |
|---|---|
| `ember_log_message(text, source?, priority?)` | `POST /message` → inbox |
| `ember_log_event(type, payload)` | `POST /event` → `events.jsonl` |
| `ember_queue_forge_work_order(slug, content, priority?)` | `~/.config/fpai/forge/queued/<UTC>_<slug>.md` |
| `ember_queue_canonization(discipline_name, reason, proposed_mechanism)` | append to `~/.config/fpai/standards/canonize_queue.md` |
| `ember_save_memory(filename, content)` | new file under `~/.claude/memory-global/` (no overwrite, no identity, kebab) |

### Forbidden write paths (return structured 403)

```json
{"error": "fatal_zone", "path": "<resolved>", "reason": "<rule>"}
```

- `memory/identity/*`, `core/STATE/identity/*`, `identity/*` under memory-global
- Every line in `.claude/hot-files.txt` (re-read on SIGHUP)
- `.claude/settings.json`, `.claude/settings.local.json`, `CLAUDE.md`
- `.claude/agents/*`, `.claude/hooks/*`
- Anything under `core/STATE/` (writes must go through `/message` or `/event`)
- Anywhere outside FPAI_Cockpit, memory-global, or `~/.config/fpai/`

---

## Troubleshooting

### "ember-substrate server failed to start"

Check stderr in Desktop's MCP log pane. Most common causes:

| Symptom | Fix |
|---|---|
| `EMBER_API_TOKEN_FILE not found` | Token file missing or path wrong. Confirm `ls ~/.config/fpai/api.token`. |
| `EMBER_API_TOKEN_FILE is empty` | Re-issue token + chmod 600. |
| `ConnectError` on first tool call | FastAPI substrate not running. `curl -s http://127.0.0.1:8765/health` should return `{"status":"ok"}`. If not, restart the launchd plist `com.fpai.ember-substrate`. |
| `403 forbidden_zone` on write | Working as intended — target is in the write-protected set. Inspect `reason`. |
| 20 tools missing in Desktop | Did Cmd+Q (not just close window)? Did JSON validate? |

### Disable the server

```sh
# instant — Desktop won't reconnect on next call
export EMBER_MCP_DISABLE=1
# or set it in the Desktop config env block then restart Desktop
```

### Reload `hot-files.txt` without restart

```sh
# server reads hot-files.txt at startup + on SIGHUP
kill -HUP <pid-of-server.py>
```

### Remove entirely

```sh
rm -rf SERVICES/ember-substrate-mcp/
# remove the ember-substrate block from claude_desktop_config.json + restart Desktop
```

No canonical state files were modified — uninstall is byte-clean.

---

## Audit trail

Every write tool fires `ember_log_event(type=mcp_write_attempt, ...)` with:

- `actor`: `claude-desktop-mcp` (configurable via `EMBER_MCP_CLIENT`)
- `tool`: the tool name
- `target`: resolved path or substrate route
- `meta`: tool-specific (slug, priority, bytes, etc.)
- `at`: ISO-8601 UTC

This makes Desktop-originated writes distinguishable from Claude Code writes in
`events.jsonl`, enabling cross-instance triangulation per spec §9.8.

`ember_log_event` itself does NOT recursively audit (would cause infinite
fan-out). All other write tools do.

---

## Reversibility (spec §11)

- `rm -rf SERVICES/ember-substrate-mcp/`
- Remove ember-substrate block from `claude_desktop_config.json`
- `export EMBER_MCP_DISABLE=1` (instant kill-switch)
- No canonical files modified · no git history mutated
