# White Rock Ministry Landing Page - Deployment Guide

## 🚀 Quick Deploy to Vercel (5 minutes)

### Step 1: Install Vercel CLI (if needed)
```bash
npm install -g vercel
```

### Step 2: Deploy
```bash
cd /Users/jamessunheart/Development/delegation-system/landing-page
vercel --prod
```

That's it! Vercel will give you a live URL.

---

## 💳 Step 3: Set Up Stripe Payment Links (10 minutes)

### Create Stripe Account:
1. Go to: https://dashboard.stripe.com/register
2. Complete registration
3. Activate account

### Create Products:
1. **Basic Membership**
   - Go to: Products → Create Product
   - Name: "White Rock Ministry - Basic Membership"
   - Price: $2,500
   - Click "Create payment link"
   - Copy link

2. **Premium Membership**  
   - Name: "White Rock Ministry - Premium Membership"
   - Price: $7,500
   - Create payment link
   - Copy link

3. **Platinum Membership**
   - Name: "White Rock Ministry - Platinum Membership"  
   - Price: $15,000
   - Create payment link
   - Copy link

### Add Links to Landing Page:
Edit `index.html` line ~230-250:
```javascript
function selectTier(tier) {
    const links = {
        'basic': 'YOUR_STRIPE_LINK_BASIC',
        'premium': 'YOUR_STRIPE_LINK_PREMIUM',
        'platinum': 'YOUR_STRIPE_LINK_PLATINUM'
    };
    window.location.href = links[tier];
}
```

Redeploy:
```bash
vercel --prod
```

---

## 📅 Step 4: Set Up Calendly (5 minutes)

### Create Calendly Account:
1. Go to: https://calendly.com
2. Sign up (free plan works)
3. Create event: "Financial Sovereignty Consultation"
   - Duration: 90 minutes
   - Set your availability

### Get Booking Link:
1. Copy your Calendly link (e.g., https://calendly.com/yourname/consultation)

### Add to Stripe Success Pages:
1. In Stripe dashboard → Payment links
2. For each link, click "Edit"
3. Under "After payment" → Custom message
4. Add: "Thank you! Schedule your consultation: [YOUR_CALENDLY_LINK]"

---

## 📊 Step 5: Set Up Facebook Pixel (Optional but Recommended)

### Create Facebook Business Account:
1. Go to: https://business.facebook.com
2. Create account
3. Go to Events Manager
4. Create Pixel

### Add Pixel to Landing Page:
Edit `index.html` line ~280:
```html
<script>
!function(f,b,e,v,n,t,s)
{if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', 'YOUR_PIXEL_ID');
fbq('track', 'PageView');
</script>
```

Redeploy with pixel tracking.

---

## 🎯 Step 6: Launch Facebook Ads ($100 Test)

### Create Ad Campaign:
1. Go to Facebook Ads Manager
2. Click "Create"
3. Objective: "Traffic" or "Conversions"

### Ad Set:
- **Daily Budget:** $14.28 ($100/week)
- **Audience:**
  - Age: 30-55
  - Location: United States
  - Interests: Entrepreneurship, Financial Independence, Real Estate Investing, Asset Protection
  - Income: Top 10%

### Create 3 Ads (A/B/C Test):

**Ad A:**
- Headline: "Financial Sovereignty Starts Here"
- Text: "Join 200+ entrepreneurs building wealth through trust structures and professional treasury optimization. 20-30% APY targets. Private membership. Legal & compliant."
- Link: Your Vercel URL
- CTA: Learn More

**Ad B:**
- Headline: "Protect Your Assets. Grow Your Wealth."
- Text: "White Rock Ministry PMA: Trust structure guidance + AI-powered treasury tools. Constitutional protection. Privacy-first. Freedom-focused community."  
- Link: Your Vercel URL
- CTA: Sign Up

**Ad C:**
- Headline: "Stop Paying Unnecessary Taxes"
- Text: "Legitimate trust structures for asset protection and tax optimization. Professional guidance. Proven strategies. Private membership association."
- Link: Your Vercel URL
- CTA: Get Started

### Launch:
- Review ads
- Set to run for 7 days
- Monitor daily

---

## 📈 Step 7: Track Results (Daily)

### Metrics to Monitor:
- **Impressions:** How many people saw your ad
- **Clicks:** How many clicked to landing page
- **CTR:** Click-through rate (clicks/impressions)
- **Landing page visitors:** From Vercel analytics
- **Consultation bookings:** From Calendly
- **Payments:** From Stripe dashboard
- **Cost per booking:** Ad spend / bookings
- **ROI:** (Revenue - Cost) / Cost

### Success Criteria:
- **Minimum:** 1+ consultation booked from $100 = Concept validated
- **Good:** 2-3 consultations = $5-7.5K revenue = 4,900% ROI
- **Excellent:** 5+ consultations = $12.5K+ revenue

---

## 🎉 What Success Looks Like

**Day 1-3:** Ads running, tracking impressions/clicks  
**Day 4-7:** First consultation bookings come in  
**Day 8-14:** Complete consultations, close deals  
**Day 15+:** Analyze data, optimize, scale winners

---

## 🛠️ Tools Needed:
- [ ] Vercel account (free)
- [ ] Stripe account (free, 2.9% + 30¢ per transaction)
- [ ] Calendly account (free)
- [ ] Facebook Business account (free)
- [ ] Facebook Ad Account with payment method ($100)

**Total Cost:** $100 ad spend + ~$75 in Stripe fees if you get 3 bookings

**Potential Revenue:** $7,500 - $45,000 (if 3 bookings convert)

---

## 🚨 Quick Commands

**Deploy:**
```bash
cd /Users/jamessunheart/Development/delegation-system/landing-page
vercel --prod
```

**Update and redeploy:**
```bash
# Edit index.html
vercel --prod
```

**Test locally first:**
```bash
python3 -m http.server 8080
# Visit: http://localhost:8080
```

---

**STATUS:** Landing page ready to deploy  
**NEXT:** Run through steps 1-7 above  
**TIME TO LIVE:** 30 minutes
