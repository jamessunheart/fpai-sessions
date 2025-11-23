# 🌐 Namecheap DNS Setup Guide

**Domain:** fullpotential.com
**Goal:** Get all subdomains working with wildcard or individual records

---

## 🎯 Quick Option: Manual Setup (5 minutes)

### Step 1: Login to Namecheap

1. Go to: https://ap.www.namecheap.com/
2. Navigate to: **Domain List** → **fullpotential.com** → **Manage**
3. Click: **Advanced DNS**

### Step 2: Verify/Fix Wildcard

Look for a record with:
- **Type:** A Record
- **Host:** `*`
- **Value:** `198.54.123.234`
- **TTL:** 300 (or Automatic)

**If it exists:** ✅ Good! Just wait for propagation (30-120 min)

**If it's missing:** Add it:
1. Click "Add New Record"
2. Type: A Record
3. Host: `*` (just the asterisk)
4. Value: `198.54.123.234`
5. TTL: 300
6. Save

### Step 3: Check for Conflicts

**IMPORTANT:** Specific records override wildcard!

Look for these and **DELETE** them if they exist:
- api.fullpotential.com
- match.fullpotential.com
- membership.fullpotential.com
- jobs.fullpotential.com
- registry.fullpotential.com

**Keep these:**
- @ (main domain)
- www
- dashboard (if it exists)

### Step 4: Lower TTL (Optional but Recommended)

For faster updates:
1. Edit each record
2. Change TTL to **300** (5 minutes)
3. Save

---

## 🤖 Automated Option: Use Namecheap API

### Setup (One-Time, 10 minutes)

#### 1. Enable API Access

1. Go to: https://ap.www.namecheap.com/settings/tools/apiaccess/
2. Click **Enable**
3. Accept terms
4. **Copy your API key** (you'll only see it once!)

#### 2. Whitelist Your IP

**CRITICAL:** Namecheap requires IP whitelisting

1. On same page, click "Edit" next to Whitelisted IPs
2. Add your current IP:
   ```bash
   curl https://api.ipify.org
   ```
3. Also add server IP: `198.54.123.234`
4. Save

#### 3. Configure Environment

```bash
# Add to your ~/.zshrc or ~/.bashrc
export NAMECHEAP_API_USER="your-username"
export NAMECHEAP_API_KEY="your-api-key-here"

# Reload
source ~/.zshrc
```

### Usage

```bash
# Make script executable
chmod +x namecheap-dns-automation.sh

# Add all subdomains at once
./namecheap-dns-automation.sh all

# Or add one at a time
./namecheap-dns-automation.sh add api
./namecheap-dns-automation.sh add match

# List current records
./namecheap-dns-automation.sh list
```

---

## ⏱️ Namecheap DNS Propagation Timeline

**Typical:** 30-120 minutes
**Worst case:** Up to 48 hours
**Best case:** 15-30 minutes (with TTL=300)

**Why slower than Cloudflare?**
- Namecheap doesn't control all nameservers
- TTL caching at ISP level
- Distributed nameserver updates

---

## 🔍 Verify Setup

### Check Wildcard in Namecheap

Your Advanced DNS should look like:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A Record | @ | 198.54.123.234 | Automatic |
| A Record | www | 198.54.123.234 | Automatic |
| A Record | * | 198.54.123.234 | 300 |
| A Record | dashboard | 198.54.123.234 | Automatic |

**Delete any other A records!** They'll block the wildcard.

### Test Propagation

```bash
# From your machine
./check-dns-wildcard.sh

# Or manually
dig api.fullpotential.com
# Should return: 198.54.123.234
```

### Check Propagation Globally

Visit: https://dnschecker.org
Search: `api.fullpotential.com`

Green checkmarks = propagated ✅

---

## 🚨 Common Namecheap Issues

### Issue 1: Wildcard Not Working

**Symptoms:** Specific subdomains return NXDOMAIN

**Causes:**
1. Wildcard record missing
2. Specific subdomain records blocking wildcard
3. Wrong nameservers

**Fix:**
1. Verify wildcard exists: `*` → `198.54.123.234`
2. Delete specific subdomain A records
3. Check nameservers are Namecheap's:
   ```
   dns1.registrar-servers.com
   dns2.registrar-servers.com
   ```

### Issue 2: Slow Propagation

**Fix:**
1. Lower TTL to 300 on all records
2. Wait 30-120 minutes
3. Clear your DNS cache:
   ```bash
   # Mac
   sudo dscacheutil -flushcache

   # Linux
   sudo systemd-resolve --flush-caches
   ```

### Issue 3: API Access Denied

**Error:** "Invalid request IP"

**Fix:**
1. Whitelist your current IP in Namecheap dashboard
2. Check IP with: `curl https://api.ipify.org`
3. Add to API Access page

### Issue 4: Changes Not Saving

**Fix:**
1. Make sure you're on "Advanced DNS" tab (not "Basic DNS")
2. Click green checkmark to save each record
3. Click "Save All Changes" at bottom

---

## 🎯 Recommended: Just Use Wildcard

**Simplest approach for you:**

1. ✅ Add/verify wildcard: `*` → `198.54.123.234`
2. ❌ Delete any specific subdomain records (except dashboard)
3. ⏱️ Lower TTL to 300
4. ⏳ Wait 30-60 minutes
5. ✅ Run `./check-dns-wildcard.sh`
6. ✅ When DNS works, run `./get-ssl-certs.sh`

**This eliminates ALL manual DNS updates forever!**

---

## 📊 Current vs Target Setup

### Current (Partially Working)

```
fullpotential.com          → 198.54.123.234  ✅
www.fullpotential.com      → 198.54.123.234  ✅
dashboard.fullpotential.com → 198.54.123.234  ✅
*.fullpotential.com        → Not propagated  ❌
```

### Target (All Working)

```
fullpotential.com          → 198.54.123.234  ✅
www.fullpotential.com      → 198.54.123.234  ✅
*.fullpotential.com        → 198.54.123.234  ✅
  → api.fullpotential.com  (via wildcard)
  → match.fullpotential.com (via wildcard)
  → membership.fullpotential.com (via wildcard)
  → jobs.fullpotential.com (via wildcard)
  → registry.fullpotential.com (via wildcard)
  → ANY subdomain works automatically!
```

---

## 🔥 Fastest Path to Working (Choose One)

### Option A: Fix Wildcard (Recommended)
- **Time:** 5 min setup + 30-60 min propagation
- **Future:** Zero manual DNS updates
- **Method:** Manual in Namecheap dashboard

### Option B: Add Individual Records
- **Time:** 10 min setup + 30-60 min propagation
- **Future:** Manual updates needed for new services
- **Method:** Manual or API script

### Option C: Switch to Cloudflare (Ultimate)
- **Time:** 15 min setup + 5 min propagation
- **Future:** Instant DNS updates, free SSL, DDoS protection
- **Method:** Change nameservers to Cloudflare (free tier)

---

## 🚀 Next Steps

**Right Now:**

1. **Login to Namecheap:** https://ap.www.namecheap.com/
2. **Go to Advanced DNS** for fullpotential.com
3. **Verify wildcard exists:** `*` → `198.54.123.234`
4. **Delete conflicting records** (api, match, etc.)
5. **Lower TTL to 300** on all records
6. **Save changes**

**Then:**

7. ⏳ Wait 30-60 minutes
8. ✅ Run: `./check-dns-wildcard.sh`
9. ✅ When DNS works: `./get-ssl-certs.sh`
10. 🎉 All domains live with HTTPS!

---

**Need help?** Take a screenshot of your Namecheap Advanced DNS page and I'll tell you exactly what to fix!

---

## 📞 Quick Reference

**Namecheap Dashboard:** https://ap.www.namecheap.com/
**Advanced DNS:** Domain List → fullpotential.com → Advanced DNS
**API Access:** Account → Tools → API Access

**Wildcard Syntax:** `*` (just asterisk)
**Server IP:** `198.54.123.234`
**TTL:** 300 (5 minutes)

**Check DNS:** `./check-dns-wildcard.sh`
**Get SSL:** `./get-ssl-certs.sh`
**Test Site:** https://fullpotential.com ✅

---

🌐 With wildcard DNS, you'll never manually add DNS records again!
