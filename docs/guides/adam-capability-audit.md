# Adam Capability Audit — March 2026

## What Adam Has

### Shell Tools (57 tools in workspace/tools/)

| Category | Tools | Status |
|----------|-------|--------|
| **Communication** | email.sh, overflow.sh, twilio.sh, discord.sh | Working |
| **Lead Gen** | leads.sh, facebook.sh, advertising.sh | Working (FB token needs refresh) |
| **Research** | websearch.sh, webfetch.sh, deepresearch.sh, daily-scout.sh, perplexity.sh, news.sh | Working |
| **Infrastructure** | servers.sh, cloudflare.sh, health.sh, cost-audit.sh, cost-optimize.sh, ai-router.sh | Working |
| **Trading** | coinglass.sh, whaletrack.sh, trade.sh, trading.sh, market.sh, stripe.sh | Working (trading dormant) |
| **Bot Management** | baas.sh, spawn_bot.sh, instant_spawn.sh, bot_registry.sh, relay.sh, token_pool.sh | Working |
| **Memory/Brain** | mem0.sh, memory.sh, remember.sh, shared-brain.sh | Working |
| **Content** | chart.sh, chart_demo.sh, browser.sh | Working |
| **Ops** | morning-briefing.sh, ot-tracker.sh, stall_detector.sh, unblock.sh, activity.sh | Working |
| **Other** | cloud.sh, sparket.sh, hub.sh, approval.sh, ask_human.sh, autonomous.sh, collect-apis.sh, marketplace.sh | Mixed |

### Skills (70+ skill definitions)
Full library of behavioral patterns including: cold-email, professional-email-drafting, structured-research-workflow, task-decomposition, debug-systematically, etc.

### Exec Capabilities
Adam has **full root shell access** via OpenClaw's `exec` tool:
- bash, python3, curl, git, docker, npm, pip
- systemctl (start/stop/restart services)
- File read/write/edit anywhere on the server
- Network access (API calls, web requests)
- Cron management

### Services He Can Reach
- LeadCapture API (port 8191)
- Kai Bridge (port 8192)
- Shared Brain (port 8770)
- MetaClaw/LLM proxy (port 30000)
- All local FPAI services

### Scheduled Jobs
- Daily scout (8am UTC)
- Morning briefing (7am UTC)
- Primary server monitor (every 5min)
- Shared brain pending check (every 5min)
- CORA cycle backup (5 times/day)

---

## What Adam Can Handle That Currently Requires Ori

| Task | Can Adam Do It? | Notes |
|------|----------------|-------|
| Edit config files on server | **YES** | Has exec + file write |
| Restart services (systemctl) | **YES** | Has root |
| Deploy simple Python scripts | **YES** | Can write files + restart |
| Update CORA/Operator prompts | **YES** | Direct file write |
| Update nginx configs | **YES** | Write + nginx -t + reload |
| Update cron jobs | **YES** | crontab access |
| Install pip packages | **YES** | pip install access |
| Create new bash tools | **YES** | Write to tools/ dir |
| Modify memory/seed files | **YES** | JSON file operations |
| Run database queries | **YES** | sqlite3, python3 |
| Debug service failures | **YES** | journalctl, logs, ps |
| Update .env files | **YES** | File write |
| Clean up files/logs | **YES** | rm, find |
| Git operations | **YES** | Full git access |

## What Still Requires Ori (Cursor Session)

| Task | Why Ori? |
|------|----------|
| Multi-file system architecture | Complex planning + many coordinated file creates |
| New Python service development | IDE advantages for multi-file projects |
| Complex debugging across systems | Needs broader context than a single agent message |
| Conversation with user about tradeoffs | Cursor's interactive flow |
| Writing specs/documentation | Cursor's editing flow for long docs |
| Deploying from local machine | scp, local file creation |
| Browser-based testing | Cursor MCP browser tools |

## Recommendation

**70% of Ori's server-side build tasks could be handled by Adam** if given clear, specific directives. The key constraint isn't capability — it's context window and instruction precision.

Adam should handle:
- All config changes, service restarts, file edits
- Simple tool creation (single bash/python files)
- Database operations, cron updates
- Routine debugging and log analysis

Ori should handle:
- Multi-service architecture (like the CORA loop build)
- Complex Python services (like the Kai bridge)
- Anything requiring sustained multi-file context
- Spec writing and design decisions

**Action:** Give CORA explicit permission to direct Adam to do server maintenance tasks. Currently CORA generates directives but doesn't specify "Adam, edit this file." It should.
