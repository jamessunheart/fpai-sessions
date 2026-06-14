# 🚀 Quick Session Management Guide

**The essential commands you need to know**

---

## Every Time You Start a Claude Instance

```bash
bash docs/coordination/scripts/session-identify.sh
```

**What it does:**
1. Detects stale sessions (optional cleanup)
2. Shows you the registry
3. Lets you choose/confirm your session number
4. Caches your identity for the day
5. Sends heartbeat to track activity

**Time:** 30 seconds

---

## First Instance of the Day

```bash
bash docs/coordination/scripts/session-identify.sh
```

When asked "Clean up stale sessions?":
- Answer: **y** (yes)
- This marks inactive sessions so you can see what's truly available

---

## Other Instances (Same Day)

```bash
bash docs/coordination/scripts/session-identify.sh
```

When asked "Clean up stale sessions?":
- Answer: **n** (no)
- Already cleaned by first instance

---

## Check Which Sessions Are Active

```bash
bash docs/coordination/scripts/session-cleanup-stale.sh --dry-run
```

**Output shows:**
- ✅ Active sessions (recent heartbeat)
- 💤 Stale sessions (no heartbeat > 2 hours)

---

## Manually Clean Up Stale Sessions

```bash
bash docs/coordination/scripts/session-cleanup-stale.sh
```

**This marks inactive sessions so their numbers become available for reuse.**

---

## Common Scenarios

### "Which session number am I?"

```bash
cat /Users/jamessunheart/Development/docs/coordination/.session_identity
```

Or check environment:
```bash
echo $FPAI_SESSION_NUMBER
```

### "I want to change my session number"

```bash
# Delete cached identity
rm /Users/jamessunheart/Development/docs/coordination/.session_identity

# Re-identify
bash docs/coordination/scripts/session-identify.sh
```

### "I closed Claude and restarted"

```bash
# Just identify again (reactivates your number)
bash docs/coordination/scripts/session-identify.sh
# Choose same number as before
```

### "Registry shows 13 active but I only have 3 running"

```bash
# Clean up stale sessions
bash docs/coordination/scripts/session-cleanup-stale.sh

# Then identify
bash docs/coordination/scripts/session-identify.sh
```

---

## Quick Reference

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `session-identify.sh` | Identify yourself + heartbeat | Every session start |
| `session-cleanup-stale.sh --dry-run` | Check stale sessions | When unsure about registry |
| `session-cleanup-stale.sh` | Clean up inactive sessions | When registry is bloated |
| `.session_identity` | See your cached number | Quick check |
| `$FPAI_SESSION_NUMBER` | Environment variable | In scripts |

---

## That's It!

**Just remember:**

```bash
bash docs/coordination/scripts/session-identify.sh
```

**Every time you start working in a Claude instance.**

The system handles the rest! 🚀
