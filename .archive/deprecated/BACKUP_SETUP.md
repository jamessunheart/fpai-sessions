# Automated Backup Setup

## Overview

All FPAI work is now backed up to GitHub automatically via `backup-to-github.sh`.

## GitHub Repository

**https://github.com/jamessunheart/fpai-sessions**

All code from `/root/SERVICES/` on the server is synced daily to this repo.

## Automatic Backup Script

Location: `/Users/jamessunheart/Development/backup-to-github.sh`

This script:
1. Syncs `/root/SERVICES/` from server to local machine via rsync
2. Commits changes to git
3. Pushes to GitHub
4. Creates local `.tar.gz` archive in `backups/` directory
5. Cleans up archives older than 7 days

## Manual Setup (Required on macOS)

Due to macOS security permissions, the cron job needs manual setup:

### Option 1: Use launchd (Recommended for macOS)

1. Create launchd plist:
```bash
cat > ~/Library/LaunchAgents/com.fpai.backup.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fpai.backup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/jamessunheart/Development/backup-to-github.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>2</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/backup.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/backup.log</string>
</dict>
</plist>
EOF
```

2. Load the launchd job:
```bash
launchctl load ~/Library/LaunchAgents/com.fpai.backup.plist
```

3. Verify it's loaded:
```bash
launchctl list | grep fpai.backup
```

### Option 2: Manual cron setup

1. Grant Terminal Full Disk Access:
   - System Preferences → Security & Privacy → Privacy → Full Disk Access
   - Add Terminal.app

2. Install cron job:
```bash
(crontab -l 2>/dev/null; echo "0 2 * * * /Users/jamessunheart/Development/backup-to-github.sh >> /tmp/backup.log 2>&1") | crontab -
```

## Manual Backup

Run backup manually anytime:
```bash
cd /Users/jamessunheart/Development
./backup-to-github.sh
```

## What Gets Backed Up

### Code (to GitHub):
- All SERVICES (task-automation, webmail, email-dashboard, etc.)
- Excludes: credentials, .env files, logs, databases, .git directories

### Archives (local):
- Full SERVICES directory archived to `backups/`
- Archives kept for 7 days

## What's NOT Backed Up

System-level configurations on the server:
- `/etc/postfix/` (email relay config)
- `/etc/nginx/` (web server config)
- `/etc/letsencrypt/` (SSL certificates)

See `SYSTEM_BACKUP.md` for system-level backup procedures.

## Verification

Check GitHub: https://github.com/jamessunheart/fpai-sessions

Check local archives:
```bash
ls -lh /Users/jamessunheart/Development/backups/
```

Check backup logs:
```bash
tail -f /tmp/backup.log
```

## Current Status

- ✅ Backup script created and tested
- ✅ Git repository initialized
- ✅ Today's work pushed to GitHub (task-automation, webmail, email-dashboard)
- ⏳ Automatic scheduling requires manual permission grant (see above)
