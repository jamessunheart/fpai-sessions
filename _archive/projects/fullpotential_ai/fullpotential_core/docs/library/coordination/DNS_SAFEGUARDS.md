# 🛡️ DNS & Configuration Safeguards

**Purpose**: Prevent accidental DNS record deletion and configuration overwrites

**Created**: 2025-11-19 after fullpotential.com DNS wipeout incident

---

## ⚠️ CRITICAL RULES FOR CLAUDE CODE SESSIONS

### Rule 1: NEVER Use Namecheap setHosts Without Getting ALL Records First

**WRONG**:
```bash
# This DELETES all other records!
curl "...&Command=namecheap.domains.dns.setHosts&HostName1=api&RecordType1=A&Address1=1.2.3.4"
```

**CORRECT**:
```bash
# 1. First GET all existing records
curl "...&Command=namecheap.domains.dns.getHosts&SLD=domain&TLD=com"

# 2. Parse ALL existing records into variables

# 3. Include ALL records in setHosts (not just the new one)
curl "...&Command=namecheap.domains.dns.setHosts&HostName1=@&RecordType1=A&Address1=existing&HostName2=api&RecordType2=A&Address2=new..."
```

### Rule 2: Backup DNS Before ANY Changes

Before modifying DNS via API:
```bash
# Save current DNS to file with timestamp
DATE=$(date +%Y%m%d_%H%M%S)
curl "...getHosts..." > "/Users/jamessunheart/Development/docs/coordination/dns_backups/${DOMAIN}_${DATE}.xml"
```

### Rule 3: Never Overwrite Without Asking User First

When making changes that could break things:
- DNS changes
- Email forwarding changes
- Server configuration changes

**Always ask**: "This will change [X]. Current setup: [Y]. Proceed? (yes/no)"

### Rule 4: Document Current State Before Changes

Create a file showing what exists before changing:
```markdown
# BEFORE: domain.com DNS
- @ A 1.2.3.4 (website)
- @ MX mail.domain.com (email)
- www CNAME domain.com

# CHANGE: Adding api.domain.com

# AFTER: domain.com DNS
- @ A 1.2.3.4 (website)
- @ MX mail.domain.com (email)
- www CNAME domain.com
- api A 5.6.7.8 (NEW)
```

---

## 📋 DNS Backup System

### Automatic Backup Before Changes

Create backup directory:
```bash
mkdir -p /Users/jamessunheart/Development/docs/coordination/dns_backups
```

### Backup Script Template

```bash
#!/bin/bash
# backup-dns.sh - Backup DNS before changes

DOMAIN=$1
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/Users/jamessunheart/Development/docs/coordination/dns_backups"

# Get current DNS
ssh root@198.54.123.234 "curl -s 'https://api.namecheap.com/xml.response?ApiUser=globalskypower&ApiKey=1970bffd68144b08a4bea27acbac0854&UserName=globalskypower&Command=namecheap.domains.dns.getHosts&ClientIp=198.54.123.234&SLD=${DOMAIN%.*}&TLD=${DOMAIN##*.}'" > "$BACKUP_DIR/${DOMAIN}_${DATE}.xml"

echo "✅ Backed up $DOMAIN to $BACKUP_DIR/${DOMAIN}_${DATE}.xml"
```

---

## 🔒 Protected Domains List

**These domains have critical DNS - extra care required:**

### Production Email Domains
- fullpotential.com (main email, website)
- coravida.com (email forwarding)
- globalsky.com (website + email forwarding)
- jamesrick.com (email forwarding)

### Current DNS Configuration (As of 2025-11-19)

#### fullpotential.com
```
@ A 198.54.123.234
www CNAME fullpotential.com
mail A 198.54.123.234
@ MX 10 mail.fullpotential.com
@ TXT v=spf1 mx ~all
* A 198.54.123.234
dashboard A 198.54.123.234
```

#### coravida.com
```
@ A 198.54.123.234
www CNAME coravida.com
mail A 198.54.123.234
@ MX 10 mail.fullpotential.com
@ TXT v=spf1 mx ~all
```

#### globalsky.com
```
@ A 141.193.213.20 (old server - call center website)
www CNAME globalsky.com
mail A 198.54.123.234
@ MX 10 mail.fullpotential.com
@ TXT v=spf1 mx ~all
```

#### jamesrick.com
```
@ A 209.74.93.72 (old server - website content)
www CNAME jamesrick.com
mail A 198.54.123.234
@ MX 10 mail.fullpotential.com
@ TXT v=spf1 mx ~all
```

---

## 🚨 What Went Wrong (Incident Log)

### Date: 2025-11-19
**Problem**: fullpotential.com DNS records completely wiped

**Root Cause**:
- Script `agents/services/namecheap-dns-automation.sh` used `setHosts` API
- Only sent 1 record (subdomain to add)
- Namecheap API **replaces all records** when using setHosts
- Result: All MX, A, TXT records deleted

**Impact**:
- ❌ Website down (no A record)
- ❌ Email broken (no MX records)
- ❌ All subdomains stopped working

**Fix Applied**:
- Restored all DNS records via API
- Added proper record structure (@ A, MX, TXT, wildcard)
- Deleted buggy script
- Created this safeguard document

**Prevention**:
- Always fetch existing records first
- Include ALL records in setHosts calls
- Backup before changes
- Add `EmailType=MX` parameter to ensure MX records are included

---

## ✅ Safe DNS Change Checklist

Before ANY DNS modification:

- [ ] Backup current DNS records to file
- [ ] Document what currently exists
- [ ] Fetch ALL existing records via getHosts
- [ ] Include ALL existing records + new record in setHosts
- [ ] Verify the API response shows all records
- [ ] Wait 5 minutes and verify DNS propagated correctly
- [ ] If broken, restore from backup immediately

---

## 🔧 Recovery Procedures

### If DNS Gets Wiped Again

1. **Don't panic** - we have backups and know the configuration

2. **Check latest backup**:
```bash
ls -lt /Users/jamessunheart/Development/docs/coordination/dns_backups/ | head -5
```

3. **Restore from this document** (see "Current DNS Configuration" above)

4. **Use the working restore script**:
```bash
/Users/jamessunheart/Development/restore-dns-fullpotential.sh
```

5. **For other domains**, use the configurations documented above

### Emergency Contacts

- Namecheap Support: https://www.namecheap.com/support/
- Server: root@198.54.123.234
- API Credentials: In `setup-email-dns.sh`

---

## 📝 Change Log Template

When making DNS changes, document them here:

```markdown
### 2025-11-19 - Added API subdomain
**Domain**: fullpotential.com
**Changed by**: Session X
**Change**: Added api.fullpotential.com A record
**Before**: [paste backup]
**After**: [paste new config]
**Verified**: Yes/No
```

---

## 🎯 Best Practices

1. **Read-only first**: Always use `getHosts` to see current state
2. **Backup everything**: One backup per domain per change
3. **Test on non-critical domain first**: Use a test domain to verify scripts
4. **Verify immediately**: Check DNS propagated correctly within 5 minutes
5. **Document changes**: Update this file with what you changed
6. **Keep MX records**: Email is critical - never delete MX records
7. **Preserve A records**: Websites depend on these
8. **Keep SPF/TXT**: Email authentication requires these

---

## 🛠️ Safe Script Template

```bash
#!/bin/bash
# safe-dns-update.sh - Safely update DNS records

DOMAIN="$1"
NEW_SUBDOMAIN="$2"
NEW_IP="$3"

# 1. Backup current DNS
DATE=$(date +%Y%m%d_%H%M%S)
echo "Backing up $DOMAIN..."
ssh root@198.54.123.234 "curl -s '..getHosts..' > dns_backup_${DOMAIN}_${DATE}.xml"

# 2. Get current records
CURRENT=$(ssh root@198.54.123.234 "curl -s '..getHosts..'")

# 3. Parse existing records (implement parser here)

# 4. Build setHosts with ALL records + new one
# (Include all parsed records + new subdomain)

# 5. Apply changes

# 6. Verify
sleep 10
dig $DOMAIN +short
dig $NEW_SUBDOMAIN.$DOMAIN +short

echo "✅ DNS update complete and verified"
```

---

## 🚫 Banned Scripts/Commands

**NEVER run these without user approval:**

- Any `setHosts` call with less than 5 records for production domains
- Any command that deletes DNS records
- Any command that changes nameservers
- Any command that modifies MX records without backup

---

**This document should be reviewed before ANY DNS changes**

**Last Updated**: 2025-11-19
**Next Review**: Before next DNS change
