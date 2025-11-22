# Marketing API Setup - Quick Reference

## What You Need From Upwork Freelancer

### 5 Platforms to Set Up

| Platform | Plan | Purpose | Priority |
|----------|------|---------|----------|
| **Apollo.io** | Professional | Find prospects (275M contacts) | ⭐ CRITICAL |
| **Instantly.ai** | Hypergrowth | Send cold emails at scale | ⭐ CRITICAL |
| **HubSpot** | Free CRM | Manage leads & deals | ⭐ CRITICAL |
| **Calendly** | Essentials | Book meetings | ✅ Important |
| **Stripe** | Pay-as-you-go | Process payments | ✅ Important |

---

## Credentials You'll Receive

The freelancer should deliver this JSON file:

```json
{
  "apollo": {
    "api_key": "...",
    "account_email": "james@fullpotential.com",
    "plan": "Professional",
    "credits_available": 24000
  },
  "instantly": {
    "api_key": "...",
    "sending_email": "...",
    "plan": "Hypergrowth"
  },
  "hubspot": {
    "access_token": "...",
    "account_id": "...",
    "plan": "Free CRM"
  },
  "calendly": {
    "api_key": "...",
    "scheduling_link": "https://calendly.com/...",
    "plan": "Essentials"
  },
  "stripe": {
    "publishable_key": "pk_live_...",
    "secret_key": "sk_live_...",
    "products": {
      "ai_employee": "prod_...",
      "ai_team": "prod_...",
      "ai_department": "prod_..."
    }
  }
}
```

---

## How to Add Credentials to Your System

Once you receive the credentials JSON file:

### Step 1: Add to Credential Vault

```bash
cd /Users/jamessunheart/Development/docs/coordination/scripts

# Apollo
./session-set-credential.sh apollo_api_key "PASTE_KEY_HERE" api_key apollo

# Instantly
./session-set-credential.sh instantly_api_key "PASTE_KEY_HERE" api_key instantly
./session-set-credential.sh instantly_email "your@email.com" email instantly

# HubSpot
./session-set-credential.sh hubspot_token "PASTE_TOKEN_HERE" access_token hubspot
./session-set-credential.sh hubspot_account_id "PASTE_ID_HERE" account_id hubspot

# Calendly
./session-set-credential.sh calendly_api_key "PASTE_KEY_HERE" api_key calendly
./session-set-credential.sh calendly_link "https://calendly.com/..." url calendly

# Stripe
./session-set-credential.sh stripe_publishable_key "pk_live_..." api_key stripe
./session-set-credential.sh stripe_secret_key "sk_live_..." secret_key stripe
./session-set-credential.sh stripe_product_employee "prod_..." product_id stripe
./session-set-credential.sh stripe_product_team "prod_..." product_id stripe
./session-set-credential.sh stripe_product_department "prod_..." product_id stripe
```

### Step 2: Test Credentials

```bash
cd /Users/jamessunheart/Development/agents/services/ai-automation

# Test Apollo
curl "https://api.apollo.io/v1/auth/health?api_key=$(cat /path/to/apollo_key)"

# Should see: {"status": "ok"}
```

### Step 3: Deploy

```bash
export FPAI_CREDENTIALS_KEY="0090050b4ac419b69bfd0b7763d861fd11619255f672b4122c34b97abe12d63f"
./deploy-with-credentials.sh
```

---

## What the Freelancer Will Do

### 1. Apollo.io Setup (30 min)
- [x] Create account at apollo.io
- [x] Subscribe to Professional plan ($99/mo)
- [x] Generate API key
- [x] Test API key works
- [x] Screenshot dashboard showing 24K credits

### 2. Instantly.ai Setup (45 min)
- [x] Create account at instantly.ai
- [x] Subscribe to Hypergrowth plan ($97/mo)
- [x] Set up sending email address
- [x] Configure email warm-up (optional but recommended)
- [x] Generate API key
- [x] Test API key works

### 3. HubSpot Setup (30 min)
- [x] Create FREE CRM account
- [x] Complete onboarding
- [x] Create private app with correct scopes:
  - crm.objects.contacts (read/write)
  - crm.objects.deals (read/write)
  - crm.objects.companies (read/write)
- [x] Generate access token
- [x] Note account ID
- [x] Test API token works

### 4. Calendly Setup (15 min)
- [x] Create account at calendly.com
- [x] Subscribe to Essentials plan ($10/mo)
- [x] Create at least one event type (30-min meeting)
- [x] Generate API key
- [x] Get scheduling link
- [x] Test API key works

### 5. Stripe Setup (45 min)
- [x] Create account at stripe.com
- [x] Complete business verification
- [x] Create 3 subscription products:
  - AI Employee: $3,000/month
  - AI Team: $7,000/month
  - AI Department: $15,000/month
- [x] Get API keys (publishable + secret)
- [x] Get product IDs
- [x] Test API keys work

---

## Verification Checklist

Before you accept delivery, verify:

### Apollo
- [ ] API key starts with correct format
- [ ] Test curl command returns `{"status": "ok"}`
- [ ] Can see 24,000 credits available
- [ ] Account email is james@fullpotential.com

### Instantly
- [ ] API key works in test command
- [ ] Sending email is configured
- [ ] Can see campaign dashboard
- [ ] Account email is james@fullpotential.com

### HubSpot
- [ ] Access token works in test command
- [ ] Account ID is provided
- [ ] Can access CRM dashboard
- [ ] Account email is james@fullpotential.com

### Calendly
- [ ] API key works in test command
- [ ] Scheduling link is live and accessible
- [ ] At least one event type exists
- [ ] Account email is james@fullpotential.com

### Stripe
- [ ] Both API keys (publishable + secret) work
- [ ] All 3 products created with correct prices
- [ ] Product IDs provided
- [ ] Account email is james@fullpotential.com

---

## What Happens After Setup

### Immediate (Day 1)
1. Add all credentials to vault ✅
2. Deploy with new credentials ✅
3. Test each integration ✅

### Week 1
1. Search first 100 prospects (Apollo) ✅
2. Create first email campaign (Instantly) ✅
3. Import prospects to HubSpot ✅
4. Set up meeting booking flow (Calendly) ✅

### Week 2
1. Send first 50 emails/day ✅
2. Track all responses in HubSpot ✅
3. Book first demo call ✅

### Week 3-4
1. Scale to 100 emails/day ✅
2. Close first deal ✅
3. Process first payment (Stripe) ✅
4. **First customer = $3K-7K MRR** 🎉

---

## Expected Impact

### Timeline to Value
- Month 1: First customer acquired
- Month 3: 6+ customers
- Month 6: 17+ customers scaling to target revenue

### Key Milestones
- **First customer validates the entire system**
- Multi-channel outreach capability
- Automated lead management and follow-up

---

## Support After Delivery

Request from freelancer:
- [ ] 7-day support window included
- [ ] Available for quick Zoom call if needed
- [ ] Help with any credential issues
- [ ] Willing to fix any setup problems

---

## Bonus Deliverables (Worth Extra $50)

If freelancer includes these, it's worth the bonus:

### Instantly.ai Advanced Setup
- [x] Email warm-up schedule configured
  - Day 1-7: 10 emails/day
  - Day 8-14: 25 emails/day
  - Day 15+: 50 emails/day
- [x] SPF/DKIM/DMARC records configured (if using custom domain)

### HubSpot CRM Setup
- [x] Deal pipeline created with stages:
  - Lead → Qualified → Demo → Proposal → Closed Won/Lost
- [x] Custom properties for AI automation tracking
- [x] Email templates ready

### Calendly Advanced Setup
- [x] Round-robin scheduling (if multiple team members)
- [x] Custom questions for lead qualification
- [x] Automated reminder emails

---

## Emergency Contacts

If something doesn't work:

**Your Setup (already built):**
- Dashboard: https://fullpotential.com/dashboard/marketing
- API Docs: Check APOLLO_INTEGRATION_COMPLETE.md
- Deploy Script: ./deploy-with-credentials.sh

**Platform Support:**
- Apollo: support@apollo.io
- Instantly: support@instantly.ai
- HubSpot: HubSpot Support Chat
- Calendly: help.calendly.com
- Stripe: Stripe Support Chat

---

## Timeline

**Upwork Job:** Post today
**Hire:** Within 24 hours
**Setup:** 24-48 hours from hire
**Testing:** 4-6 hours after delivery
**Launch:** Within 1 week

**Your first campaign could be live in 7-10 days!**

---

## Quick Start After Credentials Received

```bash
# 1. Add credentials to vault (10 min)
./add-all-credentials.sh credentials.json

# 2. Deploy (2 min)
./deploy-with-credentials.sh

# 3. Test API (5 min)
curl https://fullpotential.com/api/prospects/credits
curl https://fullpotential.com/api/prospects/search/saved

# 4. Import first prospects (30 min)
curl -X POST https://fullpotential.com/api/prospects/import-to-campaign \
  -d '{"campaign_id": "test_001", "job_titles": ["CEO"], "limit": 25}'

# 5. You're live! 🚀
```

---

**Ready to post on Upwork? The job description is in `UPWORK_API_SETUP_JOB.md`**
