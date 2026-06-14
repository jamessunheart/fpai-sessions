# 📧 Gmail Forwarding Setup Guide

**Goal**: Forward emails from james@globalsky.com and james@jamesrick.com to james@fullpotential.com

**Your Gmail**: james.rick.stinson@gmail.com (where you currently access these emails)

---

## Setup Instructions

Since both james@globalsky.com and james@jamesrick.com are configured with Google Workspace (Gmail), you can easily set up automatic forwarding.

### Option 1: Forward via Gmail Web Interface (Easiest)

#### For james@globalsky.com:

1. **Login to Gmail**
   - Go to: https://mail.google.com
   - Login as: james@globalsky.com (or access via james.rick.stinson@gmail.com if it's delegated)

2. **Open Settings**
   - Click the gear icon (⚙️) in top right
   - Select "See all settings"

3. **Go to Forwarding Tab**
   - Click "Forwarding and POP/IMAP" tab

4. **Add Forwarding Address**
   - Click "Add a forwarding address"
   - Enter: `james@fullpotential.com`
   - Click "Next" → "Proceed" → "OK"

5. **Verify Forwarding**
   - Gmail will send a confirmation email to james@fullpotential.com
   - Check your inbox at: http://198.54.123.234 (webmail for fullpotential.com)
   - Or via SSH: `ssh root@198.54.123.234 'mail -u james'`
   - Click the verification link in the email

6. **Enable Forwarding**
   - Return to Gmail Settings → Forwarding tab
   - Select: "Forward a copy of incoming mail to james@fullpotential.com"
   - Choose what to do with Gmail's copy:
     - "Keep Gmail's copy in the Inbox" (recommended - keeps backup)
     - OR "Archive Gmail's copy"
     - OR "Delete Gmail's copy" (not recommended)
   - Click "Save Changes"

#### For james@jamesrick.com:

**Repeat steps 1-6 above**, but login as james@jamesrick.com instead

---

### Option 2: Access via Delegated Account (If Applicable)

If you access both email accounts through james.rick.stinson@gmail.com using account delegation:

1. **Login to Gmail**: james.rick.stinson@gmail.com
2. **Switch Account**: Click your profile icon → select the delegated account (james@globalsky.com or james@jamesrick.com)
3. **Follow steps 2-6 above** for each account

---

### Option 3: Create Filters for Forwarding (Alternative)

If you can't access the Forwarding settings (some Google Workspace admins disable it):

1. **Login to Gmail** for the account
2. **Settings** → "Filters and Blocked Addresses"
3. **Create a new filter**:
   - "To": (leave blank or enter the account email)
   - Click "Create filter"
4. **Action**:
   - Check "Forward it to"
   - Select or add: james@fullpotential.com
   - Check "Skip the Inbox" if you want
   - Click "Create filter"

---

## Verification

### Test Email Forwarding:

1. **Send test email to**: james@globalsky.com
2. **Wait 1-2 minutes**
3. **Check fullpotential.com inbox**:
   ```bash
   ssh root@198.54.123.234 'tail -f /var/log/mail.log'
   ```
   Or browse to: http://198.54.123.234

4. **Repeat for**: james@jamesrick.com

---

## Troubleshooting

### Can't find Forwarding settings?

- **Cause**: Google Workspace admin may have disabled forwarding
- **Solution**: Contact the workspace admin or use filter method (Option 3)

### Verification email not arriving?

- **Check DNS propagation** (for coravida.com):
  ```bash
  dig MX coravida.com +short
  # Should show: 10 mail.fullpotential.com.
  ```

- **Check mail server logs**:
  ```bash
  ssh root@198.54.123.234 'tail -50 /var/log/mail.log'
  ```

### Forwarding not working?

1. **Check Gmail spam folder** (verification email might be there)
2. **Wait for DNS propagation** (5-30 minutes for coravida.com)
3. **Verify forwarding is enabled** in Gmail Settings

---

## Current Email Status

### ✅ coravida.com - READY!

- **DNS**: Switched to Namecheap DNS ✅
- **MX Record**: Points to mail.fullpotential.com ✅
- **Mail Server**: Configured to accept and forward ✅
- **Status**: james@coravida.com → james@fullpotential.com (automatic)
- **Propagation**: 5-30 minutes

**No action needed** - email will work automatically once DNS propagates!

### 🔧 globalsky.com - NEEDS GMAIL FORWARDING

- **DNS**: External (ns1/ns2.outbounders.com at 209.74.93.72)
- **MX Record**: Points to Google Workspace ✅
- **Current Email**: Works via Gmail
- **Action Needed**: Setup Gmail forwarding (see Option 1 above)

### 🔧 jamesrick.com - NEEDS GMAIL FORWARDING

- **DNS**: External (ns1/ns2.outbounders.com at 209.74.93.72)
- **MX Record**: Points to Google Workspace ✅
- **Current Email**: Works via Gmail
- **Action Needed**: Setup Gmail forwarding (see Option 1 above)

---

## Summary

| Email | Current Status | Forwarding Method | Action Needed |
|-------|---------------|-------------------|---------------|
| james@coravida.com | ✅ Configured | Automatic (mail server) | None - wait for DNS |
| james@globalsky.com | ✅ Working | Manual (Gmail settings) | Setup Gmail forwarding |
| james@jamesrick.com | ✅ Working | Manual (Gmail settings) | Setup Gmail forwarding |

**Time Required**: ~10 minutes total (5 min per Gmail account)

---

## Quick Links

- **Gmail Settings**: https://mail.google.com/mail/u/0/#settings/fwdandpop
- **Check DNS Propagation**: https://dnschecker.org
- **Check coravida.com MX**: `dig MX coravida.com +short`
- **Check fullpotential.com inbox**: http://198.54.123.234

---

**Created**: 2025-11-19
**Next**: Setup Gmail forwarding for globalsky.com and jamesrick.com (10 minutes)
