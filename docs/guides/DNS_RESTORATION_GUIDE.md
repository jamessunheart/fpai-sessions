# 🚨 DNS RESTORATION GUIDE FOR fullpotential.com

## PROBLEM

A Claude Code session ran the buggy `namecheap-dns-automation.sh` script which **wiped out all DNS records** for fullpotential.com. This broke:

- ❌ **Email**: james@fullpotential.com stopped working (no MX records)
- ❌ **Website**: fullpotential.com stopped loading (no A record)
- ❌ **Subdomains**: All subdomains stopped working

## ROOT CAUSE

The script at `SERVICES/namecheap-dns-automation.sh` has a critical bug on lines 76-82:

```bash
# Add the new subdomain (this is simplified)
url+="&HostName1=${subdomain}"
url+="&RecordType1=A"
url+="&Address1=${SERVER_IP}"
url+="&TTL1=300"
```

**The bug**: Namecheap's `setHosts` command **replaces ALL records**. The script only sent one record, so it deleted everything else including:
- Main domain A record
- MX records for email
- SPF records
- WWW CNAME
- All existing subdomains

## SOLUTION

You need to restore the DNS records. There are two options:

---

## OPTION 1: Manual Restoration (10 minutes, RECOMMENDED)

### Step 1: Login to Namecheap

1. Go to: https://ap.www.namecheap.com/
2. Login with username: `globalskypower`
3. Navigate to: **Domain List** → **fullpotential.com** → **Advanced DNS**

### Step 2: Delete Any Existing Records

Click the trash icon to delete any remaining records (if any exist)

### Step 3: Add These 7 Records

Click "Add New Record" for each:

#### Record 1: Main Domain
- **Type**: A Record
- **Host**: @
- **Value**: 198.54.123.234
- **TTL**: 300 (5 min) or Automatic

#### Record 2: WWW Redirect
- **Type**: CNAME Record
- **Host**: www
- **Value**: fullpotential.com.
- **TTL**: 300 or Automatic

#### Record 3: Mail Server
- **Type**: A Record
- **Host**: mail
- **Value**: 198.54.123.234
- **TTL**: 300 or Automatic

#### Record 4: Email Routing (MX)
- **Type**: MX Record
- **Host**: @
- **Value**: mail.fullpotential.com.
- **Priority**: 10
- **TTL**: 300 or Automatic

#### Record 5: Email Authentication (SPF)
- **Type**: TXT Record
- **Host**: @
- **Value**: v=spf1 mx ~all
- **TTL**: 300 or Automatic

#### Record 6: Wildcard for All Subdomains
- **Type**: A Record
- **Host**: *
- **Value**: 198.54.123.234
- **TTL**: 300 or Automatic

#### Record 7: Dashboard (explicit, in case wildcard has issues)
- **Type**: A Record
- **Host**: dashboard
- **Value**: 198.54.123.234
- **TTL**: 300 or Automatic

### Step 4: Save Changes

Click "Save All Changes" button at the bottom

---

## OPTION 2: API Restoration (Requires IP Whitelisting)

### Prerequisites

1. Whitelist your current IP at Namecheap:
   - Go to: https://ap.www.namecheap.com/settings/tools/apiaccess/
   - Add IP: `64.37.6.153` (your current IP)
   - Or add the server IP: `198.54.123.234`

2. Run the restoration script:
```bash
cd /Users/jamessunheart/Development
./restore-dns-fullpotential.sh
```

---

## VERIFICATION

After adding the records, wait 5-30 minutes for DNS propagation, then verify:

### Check Main Domain
```bash
dig fullpotential.com +short
# Should return: 198.54.123.234
```

### Check Email (MX)
```bash
dig MX fullpotential.com +short
# Should return: 10 mail.fullpotential.com.
```

### Check Mail Server
```bash
dig mail.fullpotential.com +short
# Should return: 198.54.123.234
```

### Check Wildcard Subdomain
```bash
dig api.fullpotential.com +short
# Should return: 198.54.123.234
```

### Check Global Propagation
Visit: https://dnschecker.org and search for `fullpotential.com`

---

## EMAIL TESTING

Once DNS propagates (MX records resolve), test email:

### Send Test Email
Send an email to: james@fullpotential.com

### Check Mail Logs on Server
```bash
ssh root@198.54.123.234 'tail -f /var/log/mail.log'
```

### Check Inbox
```bash
ssh root@198.54.123.234 'mail -u james'
```

Or visit: http://198.54.123.234/inbox

---

## WHAT WILL WORK AFTER RESTORATION

- ✅ **fullpotential.com** → Shows website at 198.54.123.234
- ✅ **www.fullpotential.com** → Redirects to fullpotential.com
- ✅ **james@fullpotential.com** → Email works again
- ✅ **dashboard.fullpotential.com** → Dashboard service
- ✅ **api.fullpotential.com** → API service
- ✅ **match.fullpotential.com** → I MATCH service
- ✅ **ANY.fullpotential.com** → All subdomains work (wildcard)

---

## PREVENTING THIS IN THE FUTURE

### 1. Delete the Buggy Script
```bash
rm /Users/jamessunheart/Development/SERVICES/namecheap-dns-automation.sh
```

### 2. Use the Correct Script Instead
The correct script that preserves existing records is:
```
/Users/jamessunheart/Development/PRODUCTS/automation-scripts/setup-email-dns.sh
```

This script:
- ✅ Fetches existing records first
- ✅ Includes all records in the API call
- ✅ Asks for confirmation before making changes
- ✅ Has proper error handling

### 3. Git Commit to Document This
```bash
git add DNS_RESTORATION_GUIDE.md
git rm SERVICES/namecheap-dns-automation.sh
git commit -m "Remove buggy DNS script that wiped fullpotential.com records

The namecheap-dns-automation.sh script had a critical bug:
it used setHosts API but only sent 1 record, wiping all others.

This caused fullpotential.com to lose:
- Main domain A record
- MX records (email stopped working)
- SPF records
- WWW CNAME
- All subdomains

Added DNS_RESTORATION_GUIDE.md with manual restoration steps.

Use setup-email-dns.sh instead - it properly preserves records.
"
```

---

## TIMELINE

| Step | Time |
|------|------|
| Add DNS records manually | 10 minutes |
| DNS propagation | 5-30 minutes typical |
| Verify all records | 5 minutes |
| **Total** | **20-45 minutes** |

---

## CURRENT STATUS (Before Restoration)

```bash
$ dig fullpotential.com +short
(no response - A record missing)

$ dig MX fullpotential.com +short
(no response - MX record missing)
```

Only the SOA record exists (automatic from registrar).

---

## EXPECTED STATUS (After Restoration)

```bash
$ dig fullpotential.com +short
198.54.123.234

$ dig MX fullpotential.com +short
10 mail.fullpotential.com.

$ dig mail.fullpotential.com +short
198.54.123.234

$ dig api.fullpotential.com +short
198.54.123.234
```

---

## SUPPORT

If you have issues:

1. Check Namecheap's DNS status page
2. Verify your changes saved in Namecheap dashboard
3. Wait longer (DNS can take up to 48 hours in rare cases)
4. Contact Namecheap support if records won't save

---

**Created**: 2025-11-19
**Issue**: DNS records wiped by buggy automation script
**Impact**: Email and website down for fullpotential.com
**Resolution**: Manual DNS restoration (10 minutes)
