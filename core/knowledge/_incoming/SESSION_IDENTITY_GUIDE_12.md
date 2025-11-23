# 🆔 Session Identity System

**Enhanced multi-session coordination through automatic identity management**

---

## Overview

The Session Identity System solves the problem: **"How does each Claude session know which session number it is?"**

### The Problem Before

- Sessions had to manually check `.current_session` file
- No validation if the file was stale
- No easy way to see available session numbers
- Manual registration was error-prone
- Identity wasn't cached between commands

### The Solution Now

**One command handles everything:**

```bash
bash docs/coordination/scripts/session-identify.sh
```

---

## Quick Start

### First Time Setup

1. **Run the identity script:**
   ```bash
   bash docs/coordination/scripts/session-identify.sh
   ```

2. **Choose your session number:**
   - The script shows all registered sessions (1-13)
   - Enter your session number
   - Or type `new` to register a new session
   - Or type `skip` to continue without identity (not recommended)

3. **Identity is cached:**
   - Your choice is saved for the day
   - Next time you run the script, it auto-loads
   - No need to re-enter

### Daily Usage

Just run it once per day:

```bash
bash docs/coordination/scripts/session-identify.sh
```

The system will:
- ✅ Auto-load your cached identity (if today's session)
- ✅ Verify it still exists in the registry
- ✅ Set `$FPAI_SESSION_NUMBER` environment variable
- ✅ Update `.current_session` for backward compatibility

---

## Features

### 1. Visual Session Directory

Shows all registered sessions with status:

```
Currently Registered Sessions:

  ✅ #1  - Builder/Architect - AI Marketing Engine Infrastructure
  ✅ #2  - Architect - Coordination & Infrastructure
  ✅ #3  - Infrastructure Engineer - Marketing Automation Platform
  ...
  ✅ #13 - Meta-Coordinator & Collective Mind Hub

Available numbers: 14, 15, 16...
```

### 2. Smart Caching

- Identity cached for 24 hours (file timestamp checked)
- Auto-expires at midnight (new day = new verification)
- Prevents stale identity issues

### 3. Validation

- Verifies session number exists in registry
- Confirms role and goal are set
- Checks session status is active
- Prevents using unregistered numbers

### 4. Easy Registration

If you choose an unregistered number, offers to register it:

```
Would you like to register it? (y/n)
> y

Role (e.g., 'Infrastructure Engineer'): DevOps Lead
Goal (e.g., 'Deploy and maintain core services'): Manage deployments

✅ Session #14 registered successfully!
```

### 5. Environment Integration

Sets environment variable for other scripts:

```bash
export FPAI_SESSION_NUMBER=8
```

All coordination scripts can now check:

```bash
if [ -n "$FPAI_SESSION_NUMBER" ]; then
    echo "Session #$FPAI_SESSION_NUMBER is active"
fi
```

---

## How It Works

### File Structure

```
docs/coordination/
├── .session_identity           # Cached session number (24hr TTL)
├── .session_env                # Environment variable export
├── .current_session            # Backward compatibility (session-N format)
├── claude_sessions.json        # Session registry
└── scripts/
    └── session-identify.sh     # The identity script
```

### Identity Flow

```
┌─────────────────────────────────────────────┐
│  Run session-identify.sh                    │
└─────────────┬───────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│  Check .session_identity file               │
│  Is it from today?                          │
└─────────────┬───────────────────────────────┘
              │
         Yes  │  No
      ┌───────┴────────┐
      ▼                ▼
┌──────────────┐  ┌──────────────────────────┐
│ Load cached  │  │ Show session directory   │
│ session #    │  │ Prompt for choice        │
└──────┬───────┘  └─────────┬────────────────┘
       │                    │
       └────────┬───────────┘
                ▼
┌─────────────────────────────────────────────┐
│  Verify session # in claude_sessions.json   │
└─────────────┬───────────────────────────────┘
              │
         Valid│  Invalid
      ┌───────┴────────┐
      ▼                ▼
┌──────────────┐  ┌──────────────┐
│ Set env var  │  │ Offer to     │
│ Cache ID     │  │ register     │
│ Success!     │  │              │
└──────────────┘  └──────────────┘
```

### Cache Expiration

The cache expires based on file modification date:

```bash
if [ "$(date +%Y-%m-%d)" = "$(date -r "$IDENTITY_FILE" +%Y-%m-%d)" ]; then
    # Same day - use cached identity
else
    # New day - prompt for identity
fi
```

This ensures:
- Fresh verification daily
- No stale sessions from yesterday
- Automatic cleanup

---

## Integration with Other Scripts

### Before (Manual)

```bash
# Every script had to check manually
SESSION_NUM=$(cat docs/coordination/.current_session | sed 's/session-//')
if [ -z "$SESSION_NUM" ]; then
    echo "Unknown session"
    exit 1
fi
```

### After (Automatic)

```bash
# Just source the environment
source docs/coordination/.session_env 2>/dev/null

if [ -n "$FPAI_SESSION_NUMBER" ]; then
    echo "Session #$FPAI_SESSION_NUMBER is active"
else
    echo "Run: bash docs/coordination/scripts/session-identify.sh"
    exit 1
fi
```

### Example: Heartbeat Script Integration

```bash
#!/bin/bash
# session-heartbeat.sh

# Load session identity
source /Users/jamessunheart/Development/docs/coordination/.session_env

if [ -z "$FPAI_SESSION_NUMBER" ]; then
    echo "❌ Session identity not set"
    echo "Run: bash docs/coordination/scripts/session-identify.sh"
    exit 1
fi

# Send heartbeat with known session number
python3 heartbeat.py --session "$FPAI_SESSION_NUMBER"
```

---

## Best Practices

### ✅ DO

- **Run once per day** - Start each session with the identity script
- **Use the environment variable** - Check `$FPAI_SESSION_NUMBER` in scripts
- **Register properly** - Fill in meaningful role and goal
- **Verify regularly** - The script does this automatically

### ❌ DON'T

- **Don't manually edit** `.session_identity` - Let the script manage it
- **Don't skip identification** - It breaks coordination
- **Don't share session numbers** - Each session needs unique identity
- **Don't use stale caches** - Let the 24hr expiration work

---

## Troubleshooting

### "Session identity not found or expired"

**Cause:** First run of the day, or identity file was deleted

**Solution:** Just choose your session number from the list

### "Session #X is not registered"

**Cause:** You chose a number that doesn't exist in `claude_sessions.json`

**Solution:** Either:
1. Choose a different number from the registered list
2. Type `y` when asked to register the new number

### "All session slots (1-13) are taken"

**Cause:** All primary session numbers are registered

**Solution:** You can:
1. Use a higher number (14, 15, etc.)
2. Check if any sessions are inactive and can be reclaimed
3. Type `new` to register with next available number

### Environment variable not persisting

**Cause:** `.session_env` isn't sourced in your shell

**Solution:** Add to your shell startup:

```bash
# In ~/.bashrc or ~/.zshrc
if [ -f ~/Development/docs/coordination/.session_env ]; then
    source ~/Development/docs/coordination/.session_env
fi
```

---

## Migration Guide

### From Old System

If you were using the old `.current_session` file:

1. **Run the new script:**
   ```bash
   bash docs/coordination/scripts/session-identify.sh
   ```

2. **Choose your existing session number**
   - The registry already has your session
   - Just confirm your number

3. **The script updates both:**
   - New `.session_identity` file (with caching)
   - Old `.current_session` file (backward compatibility)

4. **Scripts still work:**
   - Old scripts reading `.current_session` continue to work
   - New scripts can use `$FPAI_SESSION_NUMBER`

### Backward Compatibility

The identity script maintains the old `.current_session` format:

```bash
# .current_session still contains:
session-8

# Plus new .session_identity contains:
8

# Plus .session_env contains:
export FPAI_SESSION_NUMBER=8
```

This ensures zero breaking changes.

---

## Advanced Usage

### Scripted Identity (CI/CD)

For automated environments:

```bash
# Non-interactive mode (future enhancement)
bash docs/coordination/scripts/session-identify.sh --session 8 --auto
```

### Force Re-identification

To clear cache and re-identify:

```bash
rm /Users/jamessunheart/Development/docs/coordination/.session_identity
bash docs/coordination/scripts/session-identify.sh
```

### Check Current Identity

Quick check without running the full script:

```bash
cat /Users/jamessunheart/Development/docs/coordination/.session_identity
# Output: 8

# Or
echo $FPAI_SESSION_NUMBER
# Output: 8 (if .session_env is sourced)
```

---

## Future Enhancements

Planned improvements:

1. **Auto-detect terminal** - Match session to terminal window
2. **Session health check** - Verify session is still active
3. **Multi-day persistence** - Option to cache identity for longer
4. **Session transfer** - Move identity between terminals
5. **Cloud sync** - Share identity across machines
6. **Audit trail** - Track which session did what

---

## Related Documentation

- **BOOT.md** - System initialization guide (includes identity setup)
- **claude-session-register.sh** - Manual session registration
- **claude_sessions.json** - Session registry format
- **MULTI_SESSION_COORDINATION.md** - Coordination protocols

---

## Summary

The Session Identity System provides:

✅ **Clarity** - Always know which session you are
✅ **Automation** - One command, cached for the day
✅ **Validation** - Confirms identity is valid
✅ **Integration** - Works with all coordination scripts
✅ **Backward Compatible** - Old scripts still work

**Start every session with:**

```bash
bash docs/coordination/scripts/session-identify.sh
```

**And you're ready to coordinate!** 🚀
