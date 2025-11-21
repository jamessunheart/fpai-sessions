# Upwork Job Posting: Marketing API Setup & Configuration

**Job Title:** Set Up 5 Marketing APIs for AI Automation Platform (Apollo, Instantly, HubSpot, etc.)

**Category:** Web Development > API Integration
**Experience Level:** Intermediate
**Duration:** Less than 1 week

---

## Job Description

I need an experienced API integration specialist to set up and configure 5 marketing platform accounts and provide me with the API keys and configuration details.

This is for an AI-powered marketing automation platform that's already built - I just need the accounts created and API keys delivered in a specific format.

**This is NOT a development job** - the code is already written. You'll be:
1. Creating accounts on 5 platforms
2. Configuring each account properly
3. Extracting API keys and credentials
4. Documenting everything in a simple format

---

## Required Platforms & Setup

### 1. Apollo.io (B2B Prospect Database)

**Plan Needed:** Professional plan (24K credits/month)
- Sign up at https://apollo.io
- Choose Professional plan
- Verify email and complete onboarding
- Navigate to Settings → Integrations → API
- Generate API key

**Deliverable:**
- Apollo API key
- Account email used
- Screenshot of credit balance

**Why:** Access to 275M+ verified B2B contacts for prospecting

---

### 2. Instantly.ai (Cold Email Platform)

**Plan Needed:** Hypergrowth plan (unlimited leads)
- Sign up at https://instantly.ai
- Choose Hypergrowth plan
- Complete email warm-up setup
- Navigate to Settings → API
- Generate API key

**Deliverable:**
- Instantly API key
- Default sending email address configured
- Screenshot of campaign dashboard

**Why:** Send cold emails at scale with best-in-class deliverability

---

### 3. HubSpot CRM (Customer Relationship Management)

**Plan Needed:** FREE (Free CRM Forever plan)
- Sign up at https://hubspot.com
- Choose FREE CRM plan (no credit card needed)
- Complete onboarding wizard
- Navigate to Settings → Integrations → API Key
- Generate private app token with these scopes:
  - `crm.objects.contacts.read`
  - `crm.objects.contacts.write`
  - `crm.objects.deals.read`
  - `crm.objects.deals.write`
  - `crm.objects.companies.read`
  - `crm.objects.companies.write`

**Deliverable:**
- HubSpot Private App Access Token
- HubSpot Account ID
- Screenshot of API key settings

**Why:** Industry-standard CRM for managing leads and deals

---

### 4. Calendly (Meeting Scheduling)

**Plan Needed:** Essentials plan (1 seat)
- Sign up at https://calendly.com
- Choose Essentials plan
- Set up at least one event type (30-minute meeting)
- Navigate to Integrations → API & Webhooks
- Generate API key

**Deliverable:**
- Calendly API key
- Your scheduling link (e.g., calendly.com/yourname/30min)
- Screenshot of event types configured

**Why:** Automated meeting booking when prospects reply

---

### 5. Stripe (Payment Processing)

**Plan Needed:** Standard account (pay-as-you-go)
- Sign up at https://stripe.com
- Complete business verification (can use personal info for now)
- Navigate to Developers → API Keys
- Get both:
  - Publishable key (starts with `pk_`)
  - Secret key (starts with `sk_`)
- Create 3 subscription products:
  - AI Employee: $3,000/month
  - AI Team: $7,000/month
  - AI Department: $15,000/month

**Deliverable:**
- Stripe Publishable Key
- Stripe Secret Key
- Product IDs for all 3 subscription products
- Screenshot of products dashboard

**Why:** Accept recurring payments from customers

---

## Deliverable Format

Please provide all credentials in this exact format (JSON):

```json
{
  "apollo": {
    "api_key": "YOUR_APOLLO_API_KEY_HERE",
    "account_email": "email@used.com",
    "plan": "Professional",
    "credits_available": 24000
  },
  "instantly": {
    "api_key": "YOUR_INSTANTLY_API_KEY_HERE",
    "sending_email": "your@email.com",
    "plan": "Hypergrowth"
  },
  "hubspot": {
    "access_token": "YOUR_HUBSPOT_TOKEN_HERE",
    "account_id": "12345678",
    "plan": "Free CRM"
  },
  "calendly": {
    "api_key": "YOUR_CALENDLY_API_KEY_HERE",
    "scheduling_link": "https://calendly.com/yourname/30min",
    "plan": "Essentials"
  },
  "stripe": {
    "publishable_key": "pk_live_...",
    "secret_key": "sk_live_...",
    "products": {
      "ai_employee": "prod_...",
      "ai_team": "prod_...",
      "ai_department": "prod_..."
    },
    "plan": "Pay-as-you-go"
  }
}
```

Also provide:
- Screenshots of each platform's dashboard showing active status
- Login credentials (email/password) for each account
- Any important notes or setup considerations

---

## Important Notes

### Account Ownership
- Create all accounts using my email: `james@fullpotential.com`
- Or if you create with your email, transfer ownership to me after
- I'll need to be able to access all accounts long-term

### Payment Methods
- I'll provide my credit card for paid plans
- Or you can use yours and I'll reimburse

### Security
- Use strong passwords (I'll change them after handover)
- Enable 2FA where available
- Don't share API keys publicly

### Email Configuration (Important!)
For Instantly.ai:
- You'll need to set up a sending domain (I can provide: mail.fullpotential.ai)
- Configure SPF, DKIM, DMARC records (I can provide DNS access)
- OR just set up with a Gmail account for now

---

## Testing & Validation

After setup, please test each API key with a simple curl command:

### Apollo Test
```bash
curl https://api.apollo.io/v1/auth/health?api_key=YOUR_KEY
```
Should return: `{"status": "ok"}`

### Instantly Test
```bash
curl https://api.instantly.ai/api/v1/account \
  -H "Authorization: Bearer YOUR_KEY"
```
Should return account info

### HubSpot Test
```bash
curl https://api.hubapi.com/crm/v3/objects/contacts \
  -H "Authorization: Bearer YOUR_TOKEN"
```
Should return contacts list (empty is fine)

### Calendly Test
```bash
curl https://api.calendly.com/users/me \
  -H "Authorization: Bearer YOUR_KEY"
```
Should return user info

### Stripe Test
```bash
curl https://api.stripe.com/v1/products \
  -u YOUR_SECRET_KEY:
```
Should return products list

---

## Timeline

**Estimated Time:** 2-4 hours
- Apollo setup: 30 min
- Instantly setup: 45 min (including email config)
- HubSpot setup: 30 min
- Calendly setup: 15 min
- Stripe setup: 45 min
- Testing & documentation: 30 min

**Deadline:** 24-48 hours from job start

---

## Optional Advanced Configuration

If you have experience with these platforms, additional configuration would be valuable:
- Set up email warm-up schedule in Instantly (10 emails/day increasing to 50/day over 2 weeks)
- Configure HubSpot deal pipeline with stages: Lead → Qualified → Demo → Proposal → Closed Won/Lost
- Create Calendly routing rules
- Set up Stripe customer portal

---

## Required Skills

- Experience with API key generation and management
- Familiarity with SaaS platform setup
- Basic understanding of marketing automation
- Attention to detail (credentials must be exact)
- Clear communication in English

**Nice to have:**
- Previous experience with Apollo, Instantly, or HubSpot
- Email deliverability knowledge (SPF/DKIM/DMARC)
- Stripe integration experience

---

## Questions to Answer When Applying

1. Have you set up API integrations for Apollo.io, Instantly.ai, or HubSpot before?
2. How long will this take you? (be realistic)
3. Do you have experience with email domain configuration (SPF/DKIM)?
4. What's your approach to securely delivering API keys?
5. Can you start immediately?

---

## What Happens After Setup

Once you deliver the credentials:
1. I'll test each API key to verify it works
2. I'll add them to my secure credential vault
3. The AI marketing automation platform will automatically connect
4. I'll release payment upon verification

This is a straightforward job - no custom development needed. Just need someone detail-oriented who can navigate these platforms and extract the right API keys.

---

## Support After Delivery

Not required, but appreciated:
- 7-day support window for any setup issues
- Quick Zoom call if needed to walk through setup
- Help with any initial troubleshooting

---

## Why This Matters

These APIs will power an AI marketing automation platform that:
- Finds and enriches B2B prospects (Apollo)
- Sends personalized cold emails at scale (Instantly)
- Manages leads and deals (HubSpot)
- Books sales calls automatically (Calendly)
- Processes payments (Stripe)

Your setup work is the foundation that makes this possible!

---

## Ready to Apply?

Include in your proposal:
1. Relevant experience with these platforms
2. Your timeline (be realistic)
3. Any questions about the requirements
4. Confirmation you understand the deliverable format

**Looking forward to working with you!**
