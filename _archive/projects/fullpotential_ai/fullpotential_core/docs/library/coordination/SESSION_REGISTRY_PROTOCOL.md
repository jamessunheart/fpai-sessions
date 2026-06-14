# Session Registry Protocol

**For all Claude Code sessions**

## Quick Start

```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts
./claude-session-register.sh YOUR_NUMBER "Your Role" "Your Goal"
```

## Example

```bash
./claude-session-register.sh 12 "Revenue Engineer" "Build revenue systems"
```

## What Happens

1. Your session is added to `claude_sessions.json`
2. Within 5 seconds, appears in `SSOT.json` (auto-merged)
3. All other sessions can see you

## View All Sessions

```bash
cat /Users/jamessunheart/Development/docs/coordination/SSOT.json | python3 -m json.tool | grep -A 100 claude_sessions
```

## Available Numbers

Currently registered: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13
**Available: 12**

## Check Messages

```bash
./scripts/session-check-messages.sh
```

## That's It!

Simple protocol:
- Register → Wait 5 seconds → Visible to all sessions
- No HTTP, no complexity
- One command to join
