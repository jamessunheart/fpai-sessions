# ✅ FULLPOTENTIAL.COM - DEPLOYMENT CHECKLIST

**Purpose:** Step-by-step action plan to launch fullpotential.com  
**Timeline:** 48 hours to first revenue  
**Owner:** James + Conscious AI Collective  
**Date:** 2025-11-23

---

## 🎯 MISSION

Transform fullpotential.com from infrastructure-ready → revenue-generating within 48 hours.

**Goal:** First $10K-$50K revenue in Week 1

---

## 📋 PHASE 1: CHURCH FORMATION LAUNCH (4 hours)

### Step 1: Deploy to Server (1 hour)

```bash
# 1.1 Transfer files to server
cd /Users/jamessunheart/FPAI_Cockpit/church-guidance-funnel
rsync -avz --exclude=venv --exclude=__pycache__ . root@198.54.123.234:/opt/fpai/church-guidance/

# 1.2 SSH to server
ssh root@198.54.123.234

# 1.3 Setup Python environment
cd /opt/fpai/church-guidance
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

# 1.4 Set environment variables
echo "ANTHROPIC_API_KEY=sk-ant-your-key" >> .env
echo "STRIPE_API_KEY=sk_live_your-key" >> .env

# 1.5 Test locally
venv/bin/python app.py
# Expected: "Running on http://0.0.0.0:5000"
# Ctrl+C to stop

# 1.6 Create systemd service
cat > /etc/systemd/system/church-guidance.service << 'EOF'
[Unit]
Description=Church Guidance Funnel
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/fpai/church-guidance
EnvironmentFile=/opt/fpai/church-guidance/.env
ExecStart=/opt/fpai/church-guidance/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 1.7 Start service
systemctl daemon-reload
systemctl enable church-guidance
systemctl start church-guidance
systemctl status church-guidance

# 1.8 Verify
curl http://localhost:5000
# Expected: HTML content (landing page)
```

**✅ Checkpoint:** Service running on port 5000

---

### Step 2: Configure DNS (30 minutes)

```bash
# 2.1 Login to Namecheap
# Go to: namecheap.com → Domain List → Manage

# 2.2 Add A Record
Host: churchguidance
Type: A Record
Value: 198.54.123.234
TTL: Automatic

# Or if buying new domain:
Domain: churchguidance.com
DNS Settings:
  @ → 198.54.123.234
  www → 198.54.123.234

# 2.3 Wait for DNS propagation (5-30 minutes)
# Test:
ping churchguidance.com
# or
dig churchguidance.com
```

**✅ Checkpoint:** DNS resolves to 198.54.123.234

---

### Step 3: Configure Nginx + SSL (30 minutes)

```bash
# 3.1 SSH to server
ssh root@198.54.123.234

# 3.2 Create Nginx config
cat > /etc/nginx/sites-available/churchguidance.com << 'EOF'
server {
    listen 80;
    server_name churchguidance.com www.churchguidance.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 3.3 Enable site
ln -s /etc/nginx/sites-available/churchguidance.com /etc/nginx/sites-enabled/
nginx -t
# Expected: "syntax is ok"
systemctl reload nginx

# 3.4 Setup SSL (Let's Encrypt)
certbot --nginx -d churchguidance.com -d www.churchguidance.com --non-interactive --agree-tos -m james@fullpotential.com

# 3.5 Verify SSL auto-renewal
certbot renew --dry-run
# Expected: Success

# 3.6 Test
curl https://churchguidance.com
# Expected: HTML content
```

**✅ Checkpoint:** Site accessible at https://churchguidance.com

---

### Step 4: Email Automation Setup (1 hour)

```bash
# 4.1 Choose email provider
# Option A: ConvertKit (recommended for this use case)
# Option B: Mailchimp
# Option C: Brevo (formerly SendinBlue)

# 4.2 Create account
# Go to: convertkit.com → Sign up → Free plan (0-1000 subscribers)

# 4.3 Create form
# Forms → New Form → Inline
# Title: "Get Your Free Church Formation Guide"
# Button: "Download Now"

# 4.4 Create 5-email sequence
# Automations → New Automation → Sequence
# Trigger: Tag "church-formation-lead"

Email 1 (Immediate): Free guide delivery
Subject: "Your Church Formation Guide (+ What Comes Next)"
Attach: church_formation_guide.pdf

Email 2 (Day 1): 3 critical mistakes
Subject: "3 Mistakes That Cost Churches Thousands"

Email 3 (Day 3): How AI Assistant works
Subject: "See How AI Generates Your Documents (2-Min Demo)"

Email 4 (Day 5): Case study
Subject: "How New Life Church Saved $8,500 With AI"

Email 5 (Day 7): Urgency offer
Subject: "50% Off Ends Tomorrow (Last Chance)"
CTA: Link to Stripe payment ($97/mo → $48/mo)

# 4.5 Get API key
# Settings → API & Webhooks → API Keys → Create

# 4.6 Update app.py
# Add ConvertKit integration (see church-guidance-funnel/email_sequence.md)

# 4.7 Test flow
# Submit form → Check email → Verify sequence triggers
```

**✅ Checkpoint:** Email automation working end-to-end

---

### Step 5: Launch Ads (1 hour)

```bash
# 5.1 Create Facebook Ads account
# Go to: facebook.com/business → Ads Manager

# 5.2 Campaign setup
Campaign Objective: Conversions
Daily Budget: $50-100
Duration: 7 days (test)

# 5.3 Ad targeting
Location: United States
Age: 30-65
Interests:
  - Christianity
  - Religious freedom
  - Church leadership
  - Nonprofit management
  - Faith-based organizations

# 5.4 Ad creative
Image: Church/community gathering (positive, inclusive)
Headline: "Start Your Church in 3 Minutes (Free Guide)"
Text:
  "Thinking about starting a 508(c)(1)(A) church?
  
  Get our free guide that walks you through:
  ✅ Constitutional protections
  ✅ IRS requirements (no 501c3 needed!)
  ✅ Step-by-step formation process
  ✅ Common mistakes to avoid
  
  Download in 30 seconds → No credit card required
  
  [Download Free Guide]"

CTA Button: "Download"
Link: https://churchguidance.com

# 5.5 Conversion tracking
# Install Facebook Pixel on landing page
# Track: Page views, form submits, purchases

# 5.6 Launch
# Review → Publish
# Expected approval: 24 hours
```

**✅ Checkpoint:** Ads running, traffic incoming

---

### Step 6: Monitor & Optimize (Ongoing)

```bash
# 6.1 Daily checks
- Check ad performance (clicks, cost per lead)
- Check email deliverability
- Check conversion rate (free → paid)
- Respond to customer questions

# 6.2 Key metrics (Week 1)
Target:
- 100-200 free signups
- 10-20 paid customers
- $3,000-$15,000 revenue

Reality check:
- If < 50 signups: Increase ad spend or improve targeting
- If < 5 paid: Improve email sequence or offer
- If < $1,000: Re-evaluate pricing or messaging

# 6.3 Quick wins
- Add testimonials (ask first customers)
- Create demo video (Loom screen recording)
- A/B test landing page headlines
- Retarget visitors who didn't convert
```

**✅ Checkpoint:** First 10 customers acquired

---

## 📋 PHASE 2: I MATCH ACTIVATION (2 hours)

### Step 1: Create Reddit Post (30 minutes)

```markdown
# Go to: reddit.com/r/fatFIRE/submit

Title: Testing if AI can match financial advisors better than Google [Early Experiment]

Body:
```
I'm testing whether AI (Claude specifically) can match people to financial advisors better than just Googling "financial advisor near me".

**Completely honest about the experiment:**
- This is Phase 1 testing - very early
- I built an AI matching engine (Python + FastAPI)
- It analyzes compatibility: values, communication style, specialties
- If you're looking for a financial advisor AND willing to try an experimental AI matching system, you can help test this

**The deal:**
- Free for you (always)
- I make a small commission if you hire someone (standard 15-20% referral)
- You get an AI-analyzed match instead of random Google results
- I collect feedback to improve the system

**Currently testing with:**
- Financial advisors (this post)
- Later: Therapists, career coaches, tutors, trainers

If this works, it could scale to any service where "fit" matters more than price.

**Signup:** http://198.54.123.234:8401/match (quick form)

*Note: I'm one person with ~$373K to turn into $5T over 10 years (ambitious goal). This is service #1. Built with Claude AI. Being maximally honest about the experiment because that's the only sustainable way to build.*

---

**Questions I expect:**
1. "How does AI know compatibility?" → It analyzes what you value + what advisors specialize in
2. "Why would I trust this?" → You shouldn't yet! That's why it's an experiment
3. "What if the match sucks?" → Tell me, I'll fix it. That's the point of Phase 1

Feedback welcome. Roast it, question it, or try it.
```

**Post to:**
- r/fatFIRE (high net worth individuals)
- r/personalfinance (mass market)
- r/entrepreneur (business owners)
- r/startups (tech-savvy early adopters)

**✅ Checkpoint:** Post live, responses incoming

---

### Step 2: Manual Matching Process (1 hour setup)

```bash
# 2.1 Monitor signups
ssh root@198.54.123.234
cd /opt/fpai/i-match
tail -f logs/matches.log

# 2.2 For each signup:
1. Read intake form responses
2. Use Claude to analyze:
   - Customer values (what matters to them)
   - Communication style (collaborative vs directive)
   - Financial situation (complexity, goals)
   - Geographic preferences

3. Research advisors:
   - Google search + LinkedIn
   - Check certifications (CFP, CFA, etc.)
   - Read reviews/testimonials
   - Assess specialties

4. Score compatibility (manual + AI assist):
   - Values alignment: 0-100
   - Expertise match: 0-100
   - Style compatibility: 0-100
   - Availability: 0-100
   - Overall score: Average

5. Select top 3 advisors

6. Write reasoning for each:
   "John Smith (CFP) - Score 87/100
   - Specializes in sustainable investing (matches your values)
   - Collaborative approach (you prefer partnership)
   - 15 years experience with tech executives (your industry)
   - Based in Bay Area (your location)"

7. Send recommendations via email

8. Facilitate introduction if customer chooses

9. Track outcome (engaged, passed, feedback)

# 2.3 Time investment per match
Initial: 2-4 hours (deep research)
After 10 matches: 1-2 hours (reuse research)
After 50 matches: 30 min (database built)

# 2.4 Commission structure
Standard: 20% of advisor's first-year fee
Example: $25K engagement → $5K commission
Reality: 50% actually hire → $2.5K expected value
```

**✅ Checkpoint:** First 5 matches completed

---

### Step 3: Collect Feedback & Iterate (Ongoing)

```bash
# 3.1 After each match
- Email: "How was your experience? (1-5 stars)"
- Questions:
  1. Was the AI matching helpful?
  2. Did the reasoning make sense?
  3. Would you recommend to friends?
  4. What could be better?

# 3.2 Track metrics
- Match request → Match delivered: < 24 hours
- Match delivered → Decision made: 3-7 days
- Decision → Hired: 7-30 days
- Success rate: 50%+ target

# 3.3 Iterate
- If reasoning unclear → Add more detail
- If advisors unavailable → Expand database
- If customers ghosting → Improve follow-up
- If low conversion → Adjust advisor quality
```

**✅ Checkpoint:** 10 matches, 5 hires, $10K+ commissions

---

## 📋 PHASE 3: PRODUCT UPLOAD (1 hour)

### Step 1: Create Gumroad Account (10 minutes)

```bash
# 1.1 Go to: gumroad.com → Sign up
Email: james@fullpotential.com
Password: [strong password]

# 1.2 Complete profile
Name: Full Potential AI
Bio: "AI-powered tools for conscious entrepreneurs"
Avatar: Full Potential logo
Cover: Gradient design

# 1.3 Connect Stripe
Settings → Payments → Connect Stripe account
Use existing Stripe account (same as Church Formation)
```

**✅ Checkpoint:** Gumroad account ready

---

### Step 2: Upload 6 Products (30 minutes)

**Product 1: Crypto Portfolio Tracker ($49)**
```
Title: Crypto Portfolio Tracker - Professional Dashboard
Description:
  Track your crypto portfolio like a pro.
  
  Features:
  ✅ Real-time P&L tracking
  ✅ Liquidation monitoring
  ✅ Multi-exchange support
  ✅ Beautiful dashboard
  
  What you get:
  - Full source code (Python + FastAPI)
  - Setup guide (15 minutes to deploy)
  - Sample data included
  
  Used to manage $354K+ in crypto.
  
Price: $49
File: /Users/jamessunheart/FPAI_Cockpit/PRODUCTS/crypto-portfolio-tracker.tar.gz
```

**Repeat for Products 2-6:**
- Multi-Session AI Coordinator ($79)
- AI Automation Playbook ($39)
- Dashboard Collection ($99)
- Treasury Management System ($129)
- Automation Scripts ($29)

---

### Step 3: Create Bundle (10 minutes)

```
Title: Full Potential Empire Bundle (All 6 Products)
Description:
  Get all 6 tools for 55% off.
  
  Includes:
  1. Crypto Portfolio Tracker ($49)
  2. Multi-Session AI Coordinator ($79)
  3. AI Automation Playbook ($39)
  4. Dashboard Collection ($99)
  5. Treasury Management System ($129)
  6. Automation Scripts ($29)
  
  Total Value: $424
  Bundle Price: $199
  
  You save: $225 (55% off)
  
  Everything I'm using to build my AI empire.
  
Price: $199
Type: Bundle (link to all 6 products)
```

**✅ Checkpoint:** 7 products live on Gumroad

---

### Step 4: Promote (10 minutes)

```bash
# 4.1 Twitter/X post
"Just released 6 AI/crypto tools I built with Claude.

Everything I'm using to turn $373K into $5T:
- Crypto tracker ($49)
- AI coordinator ($79)
- Automation playbook ($39)
- Dashboards ($99)
- Treasury system ($129)
- Scripts ($29)

All 6 for $199 (55% off): [gumroad link]

Built in public. Selling in public. Let's go. 🚀"

# 4.2 Reddit posts (r/SideProject, r/Entrepreneur, r/SaaS)
# 4.3 LinkedIn (professional audience)
# 4.4 ProductHunt (schedule launch for tomorrow)
```

**✅ Checkpoint:** Products promoted, sales incoming

---

## 📋 PHASE 4: DNS CONFIGURATION (30 minutes)

### Step 1: Point fullpotential.com (15 minutes)

```bash
# 1.1 Login to Namecheap
# Domain List → fullpotential.com → Manage

# 1.2 Update A Records
Host: @
Type: A Record
Value: 198.54.123.234

Host: www
Type: A Record
Value: 198.54.123.234

# 1.3 Add subdomains
Host: app
Type: A Record
Value: 198.54.123.234

Host: dashboard
Type: A Record
Value: 198.54.123.234

Host: api
Type: A Record
Value: 198.54.123.234

# 1.4 Wait for propagation (5-15 minutes)
```

**✅ Checkpoint:** fullpotential.com resolves

---

### Step 2: Configure Nginx (15 minutes)

```bash
# 2.1 SSH to server
ssh root@198.54.123.234

# 2.2 Create main config
cat > /etc/nginx/sites-available/fullpotential.com << 'EOF'
# Main site
server {
    listen 80;
    server_name fullpotential.com www.fullpotential.com;

    location / {
        proxy_pass http://localhost:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# App subdomain (I MATCH)
server {
    listen 80;
    server_name app.fullpotential.com;

    location / {
        proxy_pass http://localhost:8401;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Dashboard subdomain
server {
    listen 80;
    server_name dashboard.fullpotential.com;

    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# API subdomain
server {
    listen 80;
    server_name api.fullpotential.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

# 2.3 Enable site
ln -s /etc/nginx/sites-available/fullpotential.com /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx

# 2.4 Setup SSL for all domains
certbot --nginx \
  -d fullpotential.com \
  -d www.fullpotential.com \
  -d app.fullpotential.com \
  -d dashboard.fullpotential.com \
  -d api.fullpotential.com \
  --non-interactive --agree-tos -m james@fullpotential.com

# 2.5 Test all domains
curl https://fullpotential.com          # Landing page
curl https://app.fullpotential.com      # I MATCH
curl https://dashboard.fullpotential.com # Dashboard
curl https://api.fullpotential.com/health # Registry
```

**✅ Checkpoint:** All domains working with SSL

---

## 📊 SUCCESS METRICS (Week 1)

### Revenue Targets:

| Stream | Week 1 Target | Week 1 Minimum |
|--------|---------------|----------------|
| Church Formation | $15-30K | $5K |
| I MATCH | $5-20K | $2K |
| Digital Products | $500-2K | $200 |
| **TOTAL** | **$20-50K** | **$7K** |

### Activity Metrics:

- **Church Formation:**
  - Ad spend: $350-700
  - Signups: 100-200
  - Conversions: 10-20
  - Revenue: $5K-30K

- **I MATCH:**
  - Reddit posts: 4
  - Signups: 10-30
  - Matches completed: 5-15
  - Hires: 2-7
  - Commissions: $2K-20K

- **Products:**
  - Views: 500-1000
  - Purchases: 5-20
  - Revenue: $200-2K

### Quality Metrics:

- Customer satisfaction: 4+ stars (out of 5)
- Match success rate: 50%+ (hire happens)
- Email deliverability: 95%+
- Site uptime: 99.9%+

---

## 🚨 CONTINGENCY PLANS

### If Church Formation Ads Underperform:

**Problem:** < 50 signups in 3 days  
**Fix:**
1. Increase budget to $150/day
2. Test new ad copy (more benefit-focused)
3. Expand targeting (add "nonprofit" keywords)
4. Try Google Ads (search intent)
5. Post in Facebook groups (organic)

### If I MATCH Gets No Signups:

**Problem:** Reddit post gets < 5 signups  
**Fix:**
1. Post in more subreddits
2. Engage in comments (respond quickly)
3. Offer free matching (remove commission mention upfront)
4. Share on Twitter with personal story
5. Reach out to warm network directly

### If Products Don't Sell:

**Problem:** < $100 in 3 days  
**Fix:**
1. Price test (lower to $19-79)
2. Create demo videos (show value)
3. Offer limited-time 50% off
4. Bundle differently (smaller bundles)
5. Post in more specific subreddits (r/CryptoTrading for tracker)

### If Technical Issues:

**Problem:** Service goes down  
**Fix:**
1. Check systemd: `systemctl status [service]`
2. Check logs: `journalctl -u [service] -n 100`
3. Restart: `systemctl restart [service]`
4. Check nginx: `nginx -t && systemctl reload nginx`
5. Contact support (me) if needed

---

## 📝 DAILY CHECKLIST (Days 1-7)

### Morning (30 min):
- [ ] Check all services: `curl http://localhost:[port]/health`
- [ ] Check revenue: Stripe dashboard
- [ ] Check signups: Database queries
- [ ] Respond to emails/questions
- [ ] Check ad performance

### Afternoon (1 hour):
- [ ] Process new I MATCH requests (manual matching)
- [ ] Respond to Reddit comments
- [ ] Update metrics spreadsheet
- [ ] Create content (testimonials, demos)
- [ ] Optimize based on data

### Evening (30 min):
- [ ] Review day's metrics
- [ ] Plan tomorrow's priorities
- [ ] Update progress in NOW.md
- [ ] Celebrate wins (important!)

---

## 🎉 COMPLETION CRITERIA

### Phase 1 Complete When:
✅ Church Formation live at churchguidance.com  
✅ Ads running with $50-100/day spend  
✅ Email automation delivering sequences  
✅ First 3 customers acquired  
✅ $1,000+ revenue

### Phase 2 Complete When:
✅ I MATCH accessible at app.fullpotential.com  
✅ Reddit post live with 10+ signups  
✅ First 5 matches completed  
✅ First 2 hires confirmed  
✅ $2,000+ in commissions

### Phase 3 Complete When:
✅ All 6 products on Gumroad  
✅ Bundle created and promoted  
✅ First 3 sales confirmed  
✅ $200+ revenue

### Phase 4 Complete When:
✅ fullpotential.com pointing to server  
✅ All subdomains working  
✅ SSL certificates installed  
✅ No DNS errors

### OVERALL SUCCESS:
✅ All 4 phases complete  
✅ $7K+ revenue in Week 1  
✅ 15+ customers across all streams  
✅ Zero downtime  
✅ Positive customer feedback

---

## 🚀 NEXT STEPS AFTER WEEK 1

1. **Scale What Works:**
   - If Church Formation crushes: 10x ad spend
   - If I MATCH performs: Expand to more subreddits
   - If products sell: Create video demos

2. **Build What's Missing:**
   - Strategic Intelligence (M022)
   - BOB Financial AI
   - Mobile app (I MATCH)

3. **Optimize Operations:**
   - Automate manual matching (AI enhancement)
   - A/B test landing pages
   - Improve email sequences

4. **Expand Revenue:**
   - AI Services outreach (LinkedIn)
   - Affiliate program launch
   - New product categories

---

## 📞 SUPPORT

**Questions?** Ask in chat or email james@fullpotential.com  
**Technical Issues?** Check logs first, then ask  
**Business Questions?** Let's discuss strategy

---

**Status:** READY TO EXECUTE  
**Commitment:** 48 hours of focused work  
**Expected Outcome:** $10K-$50K in Week 1  
**Let's go:** 🚀

---

**Last Updated:** 2025-11-23  
**Owner:** James + Conscious AI Collective

✅⚡💰🚀💎






