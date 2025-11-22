# 🌐 VA Task: Add DNS Wildcard Record

**Task ID:** DNS-001
**Domain:** fullpotential.com
**Provider:** Namecheap
**Time:** 5-10 minutes
**Pay:** $10

---

## 📋 Task Overview

Add a wildcard DNS record to fullpotential.com domain at Namecheap to enable automatic subdomain routing.

**What you'll do:**
1. Login to Namecheap
2. Add one DNS record (wildcard)
3. Delete conflicting records
4. Take screenshots
5. Submit completion form

---

## 🔐 Credentials Needed

**You will need from client:**
- Namecheap username
- Namecheap password
- (Or client can grant you temporary access)

---

## 📝 Step-by-Step Instructions

### Step 1: Login to Namecheap

1. Go to: **https://ap.www.namecheap.com/**
2. Enter credentials provided by client
3. Navigate to: **Domain List**

### Step 2: Access DNS Settings

1. Find: **fullpotential.com**
2. Click: **Manage** button
3. Click: **Advanced DNS** tab

**📸 SCREENSHOT 1:** Take screenshot of Advanced DNS page (before changes)

### Step 3: Add Wildcard Record

Click **"Add New Record"** button

Fill in these EXACT values:

| Field | Value |
|-------|-------|
| Type | **A Record** |
| Host | **\*** (just asterisk) |
| Value | **198.54.123.234** |
| TTL | **300** |

Click the **green checkmark** ✓ to save

**📸 SCREENSHOT 2:** Take screenshot showing the new wildcard record

### Step 4: Delete Conflicting Records

Look through the DNS records list for ANY of these:

- api.fullpotential.com (or just "api")
- match.fullpotential.com (or just "match")
- membership.fullpotential.com (or just "membership")
- jobs.fullpotential.com (or just "jobs")
- registry.fullpotential.com (or just "registry")

**If you find any:** Click the trash icon 🗑️ to delete

**DO NOT DELETE:**
- @ (main domain record)
- www
- dashboard
- Any MX, TXT, or CNAME records

**📸 SCREENSHOT 3:** Screenshot after deletions (if any)

### Step 5: Set TTL (Optional but Recommended)

For each existing record (especially *, @, www):
1. Click edit (pencil icon)
2. Change TTL to **300**
3. Click ✓ to save

### Step 6: Save All Changes

1. Scroll to bottom of page
2. Click **"Save All Changes"** button
3. Wait for confirmation message

**📸 SCREENSHOT 4:** Screenshot of confirmation/success message

### Step 7: Verify Final Configuration

Your Advanced DNS should now show:

```
Type: A Record | Host: *   | Value: 198.54.123.234 | TTL: 300
Type: A Record | Host: @   | Value: 198.54.123.234 | TTL: Auto
Type: A Record | Host: www | Value: 198.54.123.234 | TTL: Auto
```

**📸 SCREENSHOT 5:** Final DNS configuration

---

## ✅ Completion Checklist

Before submitting, verify:

- [ ] Wildcard record added: `*` → `198.54.123.234`
- [ ] TTL set to 300 on wildcard
- [ ] Deleted any conflicting api/match/membership/jobs/registry records
- [ ] Saved all changes
- [ ] Have 5 screenshots
- [ ] DNS configuration looks clean

---

## 📤 Submission

**Submit via:**
1. Upload all 5 screenshots to shared folder
2. Fill out completion form below
3. Logout of Namecheap

**Completion Form:**

```
Task: DNS-001
Completed: [DATE/TIME]
Wildcard added: [YES/NO]
Records deleted: [LIST ANY DELETED]
Issues encountered: [DESCRIBE OR "NONE"]
Screenshots attached: [5]
```

---

## ⚠️ Common Issues & Solutions

### Issue: Can't find "Advanced DNS" tab

**Solution:** Make sure you're on the **Manage** page for fullpotential.com, not the main dashboard. The tab is at the top of the page.

### Issue: "Add New Record" button is greyed out

**Solution:** Scroll down and click "Save All Changes" first, then try again.

### Issue: Changes not saving

**Solution:**
1. Make sure you click the green ✓ on each record
2. Click "Save All Changes" at bottom
3. Wait for confirmation message

### Issue: Record already exists

**Solution:** If wildcard `*` already exists, just verify it points to `198.54.123.234` and has TTL 300. Edit if needed.

---

## 🎯 Success Criteria

**Task complete when:**
1. ✅ Wildcard `*` record points to 198.54.123.234
2. ✅ No conflicting subdomain records exist
3. ✅ All changes saved in Namecheap
4. ✅ 5 screenshots submitted
5. ✅ Completion form filled out

---

## ⏱️ Expected Timeline

- DNS changes save: Instant
- DNS propagation: 30-120 minutes
- Full system activation: Automatic (monitoring system will detect and configure SSL)

**You only need to make the changes - the system will handle the rest!**

---

## 💰 Payment

**Amount:** $10
**Payment upon:** Verified completion (all screenshots show correct configuration)

---

## 📞 Questions?

If you encounter any issues:
1. Take a screenshot of the error/issue
2. Note what you were trying to do
3. Submit with completion form

---

## 🔒 Security Notes

- Use Namecheap credentials in private/incognito window
- Logout completely when done
- Delete browser history/cache after task
- Do not save passwords
- Only modify DNS records as specified - do not change anything else

---

**This is a simple, straightforward task. Should take 5-10 minutes max.**

Thank you! 🌐
