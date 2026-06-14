# 🚀 Church Guidance Funnel - Deployment Guide

**100% AI-Automated Church Formation Guidance Service**

---

## 📦 What's Included

### Core Files:
- `index.html` - Landing page with pricing tiers
- `questionnaire.html` - User intake form
- `app.py` - Flask web application (main server)
- `document_generator.py` - AI document generation engine
- `generate_guide.py` - Free guide generator
- `email_sequence.md` - 5-email nurture sequence
- `setup_stripe_products.py` - Stripe product creation
- `requirements.txt` - Python dependencies

### Generated Files:
- `church_formation_guide.md` - Free PDF guide (14,934 characters)
- `stripe_products.txt` - Stripe product IDs and payment links
- `generated_docs/` - Folder for customer documents

---

## ⚡ QUICK START (5 Minutes)

### Step 1: Install Dependencies
```bash
cd /Users/jamessunheart/Development/church-guidance-funnel
pip3 install -r requirements.txt
```

### Step 2: Set Environment Variables
```bash
# Anthropic API Key (for AI document generation)
export ANTHROPIC_API_KEY="your_anthropic_api_key_here"

# Stripe API Key (for payments)
export STRIPE_API_KEY="your_stripe_api_key_here"
```

### Step 3: Run the Application
```bash
python3 app.py
```

Visit: `http://localhost:5000`

---

## 🛒 STRIPE PAYMENT LINKS

All products are created and ready to accept payments:

### **Tier 2a: AI Assistant - Monthly**
- **Price:** $97/month recurring
- **Link:** https://buy.stripe.com/fZu00i3O16ND5oV22x9R604
- **Product ID:** prod_TQgIArw6eqrTUZ

### **Tier 2b: AI Assistant - Lifetime**
- **Price:** $297 one-time
- **Link:** https://buy.stripe.com/9B63cuesF8VL4kR5eJ9R605
- **Product ID:** prod_TQgI9RjNs4WFEs

### **Tier 3: Premium Package**
- **Price:** $997 one-time
- **Link:** https://buy.stripe.com/bJeaEW5W95Jz9Fb9uZ9R606
- **Product ID:** prod_TQgIAmL7w448CV
- **Includes:** Multi-state compliance, automated updates, 12-month tracking

### **Tier 4: VIP Package**
- **Price:** $2,997 one-time
- **Link:** https://buy.stripe.com/14AfZg2JXgod9Fb4aF9R607
- **Product ID:** prod_TQgIy9k7i4Ferh
- **Includes:** Everything in Premium + optional human assistance

---

## 🌐 PRODUCTION DEPLOYMENT

### Option 1: Deploy to Existing Server (198.54.123.234)

```bash
# 1. Copy files to server
scp -r /Users/jamessunheart/Development/church-guidance-funnel root@198.54.123.234:/var/www/

# 2. SSH into server
ssh root@198.54.123.234

# 3. Install dependencies
cd /var/www/church-guidance-funnel
pip3 install -r requirements.txt

# 4. Set environment variables
export ANTHROPIC_API_KEY="sk-ant-api03-..."
export STRIPE_API_KEY="sk_live_..."

# 5. Run with Gunicorn (production server)
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:8003 app:app
```

### Option 2: Nginx Configuration

Create `/etc/nginx/sites-available/churchguidance`:

```nginx
server {
    listen 80;
    server_name churchguidance.com www.churchguidance.com;

    location / {
        proxy_pass http://127.0.0.1:8003;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /var/www/church-guidance-funnel/static;
    }
}
```

Enable and restart:
```bash
ln -s /etc/nginx/sites-available/churchguidance /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

### Option 3: Systemd Service (Auto-start)

Create `/etc/systemd/system/churchguidance.service`:

```ini
[Unit]
Description=Church Guidance Funnel Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/church-guidance-funnel
Environment="ANTHROPIC_API_KEY=sk-ant-api03-..."
Environment="STRIPE_API_KEY=sk_live_..."
ExecStart=/usr/bin/gunicorn -w 4 -b 0.0.0.0:8003 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl daemon-reload
systemctl enable churchguidance
systemctl start churchguidance
systemctl status churchguidance
```

---

## 📧 EMAIL AUTOMATION SETUP

The email sequence is documented in `email_sequence.md`. To implement:

### Option 1: ConvertKit (Recommended)
1. Create account: https://convertkit.com
2. Create 5 emails using content from `email_sequence.md`
3. Set up automation sequence:
   - Email 1: Immediate (trigger: form signup)
   - Email 2: 24 hours after signup
   - Email 3: 72 hours after signup
   - Email 4: 120 hours after signup
   - Email 5: 168 hours after signup (with 50% discount code)

4. Create Stripe discount code:
```bash
stripe coupons create --percent-off 50 --duration once --name "50OFF-CHURCH"
```

5. Embed discount link in Email 5

### Option 2: Mailchimp
- Similar setup process
- Use automation workflows
- Embed Stripe payment links with discount parameter

### Option 3: Custom SMTP (app.py)
- Uncomment email sending code in `app.py` (line 145+)
- Configure SMTP credentials
- Or use SendGrid/Mailgun API

---

## 🔒 SECURITY & LIABILITY

### Critical Disclaimers Are Included:
✅ Landing page (index.html)
✅ Questionnaire page (questionnaire.html)
✅ Every generated document (via document_generator.py)
✅ Success page (app.py)

### What You're Selling:
✅ Educational information
✅ Software tools (AI document generator)
✅ Templates and resources

### What You're NOT Selling:
❌ Legal services
❌ Church formation services
❌ Legal advice

**Legal Structure:** Software/Education product (protected), NOT regulated legal services

---

## 📊 ANALYTICS & TRACKING

### Recommended Tracking:
1. **Google Analytics** - Track landing page visits, conversions
2. **Stripe Dashboard** - Monitor revenue, customer count
3. **ConvertKit/Mailchimp** - Email open rates, click-through rates

### Key Metrics to Track:
- Landing page visitors
- Free guide signups
- Email open rates (aim: 40-50%)
- Conversion rate (free → paid, aim: 10-15%)
- Average revenue per customer
- Monthly recurring revenue (MRR)
- Lifetime value (LTV)

---

## 🚀 LAUNCH CHECKLIST

- [x] Landing page created (index.html)
- [x] Free guide generated (church_formation_guide.md)
- [x] Email sequence documented (email_sequence.md)
- [x] AI chat assistant built (questionnaire.html + document_generator.py)
- [x] Stripe products created (4 tiers)
- [x] Payment links live
- [ ] Email automation configured (ConvertKit/Mailchimp)
- [ ] Domain purchased (e.g., churchguidance.com)
- [ ] DNS configured
- [ ] SSL certificate installed
- [ ] Server deployed
- [ ] Test complete user flow
- [ ] Launch ads ($100/day Facebook/Google)

---

## 💰 REVENUE PROJECTIONS

### Conservative (Month 1):
- 500 free signups
- 10% convert to paid = 50 customers
  - 25 monthly ($97) = $2,425/month recurring
  - 25 one-time ($297) = $7,425
- 4% to Premium ($997) = 20 customers = $19,940
- 1% to VIP ($2,997) = 5 customers = $14,985

**Month 1 Total: $44,775**

### Aggressive (Month 3+):
- 1,500 free signups/month
- 15% conversion
- **Monthly: $56,900+**

---

## 🛠️ MAINTENANCE

### Weekly:
- Check server logs
- Monitor Stripe for new customers
- Review email automation performance
- Respond to customer questions

### Monthly:
- Review analytics
- Update content based on performance
- Test document generation
- Check for legal/compliance changes

### As Needed:
- Update AI prompts if documents need improvement
- Add new document types based on customer requests
- Scale server if traffic increases

---

## 📞 SUPPORT

### For Technical Issues:
- Check server logs: `journalctl -u churchguidance`
- Check Flask logs: `tail -f /var/log/churchguidance.log`
- Test AI generation: `python3 document_generator.py`

### For Customer Support:
- Questions about documents: "These are educational templates. Please consult an attorney."
- Payment issues: Check Stripe dashboard
- Can't access documents: Check email delivery, resend from generated_docs folder

---

## 🎯 NEXT STEPS

1. **Configure email automation** (ConvertKit/Mailchimp) - 1 hour
2. **Purchase domain** (churchguidance.com) - 10 minutes
3. **Deploy to server** - 30 minutes
4. **Test complete flow** - 30 minutes
5. **Launch ads** - $100/day budget

**Total time to live: 2-3 hours**

---

## 📈 SCALING STRATEGY

### Month 1: Prove Concept
- $100/day ads
- 50-100 customers
- Validate automation
- Collect testimonials

### Month 2: Scale Traffic
- $300/day ads
- Add SEO content
- YouTube videos (AI-generated scripts)
- 1,000+ free signups

### Month 3: Add Upsells
- Annual compliance ($997/year)
- Multi-church package ($4,997)
- Cross-sell to White Rock Ministry

### Month 6: Exit or Scale
- 5,000+ free users
- 500+ paying customers
- $50K+/month recurring
- **Option:** Sell for 3-5x annual revenue ($600K-1M)

---

**Built with Claude AI in 4 hours**
**100% automated, 95%+ margin, infinite scale** 🚀
