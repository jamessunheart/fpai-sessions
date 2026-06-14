# 🤖 CLAUDE CODE SESSION STARTUP CHECKLIST

**READ THIS AT THE START OF EVERY SESSION**

---

## CRITICAL PROTECTIONS IN PLACE

### 🛡️ DNS Safeguards
- **Location**: `/Users/jamessunheart/Development/docs/coordination/DNS_SAFEGUARDS.md`
- **Rules file**: `/Users/jamessunheart/Development/docs/coordination/.claud_code_rules`
- **Safe script**: `/Users/jamessunheart/Development/docs/coordination/scripts/safe-dns-update.sh`

### ⚠️ BEFORE ANY DNS CHANGES:

1. **Read the safeguards document**
2. **Run the safe-dns-update.sh script** which:
   - Creates automatic backup
   - Shows current DNS state
   - Requires explicit user "yes" confirmation
   - Documents what will change

3. **NEVER use Namecheap setHosts API directly**
   - Always use the safe wrapper script
   - Always include ALL existing records
   - Always backup first

### 🔒 Protected Domains

These domains have critical email and/or website services:
- **fullpotential.com** - Main email hub, website
- **coravida.com** - Email forwarding
- **globalsky.com** - Call center website + email
- **jamesrick.com** - Email forwarding

**Extra caution required for any changes to these domains**

---

## ENFORCEMENT MECHANISMS

### 1. Safe DNS Update Script
```bash
# Always use this instead of direct API calls:
./docs/coordination/scripts/safe-dns-update.sh <domain> "<description of change>"

# This will:
# - Create timestamped backup
# - Show current DNS records
# - Require user confirmation
# - Prevent accidental overwrites
```

### 2. Rules File
The `.claud_code_rules` file contains:
- Banned commands
- Required procedures
- Protected resources
- Safe practices

### 3. Backup Directory
All DNS changes create backups in:
```
/Users/jamessunheart/Development/docs/coordination/dns_backups/
```

---

## IF YOU NEED TO MODIFY DNS

### ✅ CORRECT Process:

```bash
# 1. Run safe wrapper (creates backup + confirms with user)
./docs/coordination/scripts/safe-dns-update.sh fullpotential.com "Adding new subdomain"

# 2. Get ALL existing records first
ssh root@198.54.123.234 'curl -s "...Command=namecheap.domains.dns.getHosts..."'

# 3. Include ALL records + new record in setHosts call
ssh root@198.54.123.234 'curl -s "...Command=namecheap.domains.dns.setHosts&HostName1=@&...&HostName7=newsubdomain&..."'

# 4. Verify changes
dig domain.com +short
dig newsubdomain.domain.com +short

# 5. Document in DNS_SAFEGUARDS.md change log
```

### ❌ WRONG Process (caused the incident):

```bash
# This DELETES all other records!
ssh root@198.54.123.234 'curl -s "...Command=namecheap.domains.dns.setHosts&HostName1=api&..."'
```

---

## WHAT HAPPENED BEFORE (Learn from this)

**Incident Date**: 2025-11-19

**Problem**: fullpotential.com DNS completely wiped

**Cause**: Script used `setHosts` with only 1 record, deleted everything else

**Impact**:
- Website down
- Email broken
- All subdomains stopped working

**Resolution**:
- Manually restored all DNS records
- Created safeguards to prevent recurrence
- Documented current state
- Created enforcement mechanisms

**Full details**: See DNS_SAFEGUARDS.md incident log

---

## QUICK REFERENCE

### Current Email Setup (as of 2025-11-19):

```
james@fullpotential.com → Gmail via POP3S (port 995, encrypted)
james@coravida.com → forwards to fullpotential.com
james@globalsky.com → forwards to fullpotential.com
james@jamesrick.com → forwards to fullpotential.com
```

### Mail Server Configuration:

- **Server**: 198.54.123.234
- **Postfix config**: /etc/postfix/main.cf, /etc/postfix/virtual
- **Dovecot config**: /etc/dovecot/dovecot.conf
- **User**: james
- **Password**: gmxKnHVwzw/MyHI5DWvbHw==

### DNS Backup Locations:

```bash
# Latest backups
ls -lt /Users/jamessunheart/Development/docs/coordination/dns_backups/ | head -5

# Restore from backup
cat dns_backups/fullpotential.com_TIMESTAMP.xml
```

---

## SESSION START PROTOCOL

When you start a new session, especially if working on:
- DNS changes
- Email configuration
- Domain management
- Server configuration

**You MUST**:

1. ✅ Read this file (CLAUDE_SESSION_START.md)
2. ✅ Review DNS_SAFEGUARDS.md
3. ✅ Check .claud_code_rules
4. ✅ Use safe-dns-update.sh for any DNS changes
5. ✅ Get explicit user approval before breaking changes
6. ✅ Create backups before modifications
7. ✅ Verify changes after applying
8. ✅ Document changes in change log

---

## RED FLAGS 🚩

If you see yourself about to:
- Use `namecheap.domains.dns.setHosts` directly
- Modify DNS without backup
- Change MX records without asking user
- Delete any DNS records
- Modify /etc/postfix or /etc/dovecot without backup

**STOP** ✋ and follow the safe procedures above.

---

## RESOURCES

- **Safeguards doc**: `docs/coordination/DNS_SAFEGUARDS.md`
- **Rules file**: `docs/coordination/.claud_code_rules`
- **Safe script**: `docs/coordination/scripts/safe-dns-update.sh`
- **Backups**: `docs/coordination/dns_backups/`
- **Restore script**: `restore-dns-fullpotential.sh`

---

**This file ensures we never repeat the DNS wipeout incident**

**Last Updated**: 2025-11-19
**Next Review**: Before any DNS/email changes
