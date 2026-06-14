# Free Trial Pattern 🎁

## The Flywheel

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    FREE TRIAL → FEEDBACK → IMPROVE → CONVERT → TESTIMONIAL │
│         ↑                                          │        │
│         └──────────────────────────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## The Deal

**What users get:**
- Free access to try everything
- Real value, no strings attached
- Direct access to the founder
- Cancel anytime, keep what they learned

**What we ask:**
- ⭐ A testimonial if they love it
- 💡 Honest feedback if we can improve
- That's it. Really.

## Adding a New Service

When creating a new service, add it to the try page:

### 1. Define the Free Trial

| Service Type | Recommended Free Trial | Your Cost |
|-------------|------------------------|-----------|
| API/Requests | 500-1000 requests | ~$0-1 |
| Time-based | 7-30 days | $0 |
| Usage-based | X uses free | Varies |
| Calls/Minutes | 25-50 calls | ~$1-3 |

### 2. Add to Try Page

Edit `/var/www/html/try.html` or `/infra/web/try.html`

Add a new product card:

```html
<!-- New Service -->
<div class="product-card [color-class]">
    <div class="product-icon">[emoji]</div>
    <h3 class="product-name">[Service Name]</h3>
    <p class="product-desc">[One-line description]</p>
    <ul class="product-features">
        <li><span class="check">✓</span> [Feature 1]</li>
        <li><span class="check">✓</span> [Feature 2]</li>
        <li><span class="check">✓</span> [Feature 3]</li>
        <li><span class="check">✓</span> [Feature 4]</li>
    </ul>
    <div class="trial-box">
        <div class="free">[Free Trial Amount]</div>
        <div class="detail">[Value/details]</div>
    </div>
    <div class="price-after">Then <strong>$XX/mo</strong> if you love it</div>
    <a href="#contact" class="try-btn">Try [Service] →</a>
</div>
```

### 3. Color Classes

Available color classes for cards:
- `phone` - Purple
- `whale` - Blue  
- `dashboard` - Cyan
- `wellness` - Green
- `ai` - Orange
- `community` - Pink

### 4. Deploy

```bash
scp /path/to/try.html root@198.54.123.234:/var/www/html/try.html
```

## Feedback Collection

### When trial ends, send:

**If happy (they used it a lot):**
```
Hey [Name]!

Your free trial of [Service] is wrapping up. 

Looks like you've been using it - awesome! 

Quick question: Would you be open to sharing a quick testimonial 
about your experience? Just 2-3 sentences is perfect.

If you want to keep using it, it's $XX/mo. No pressure either way.

Thanks for trying it out!
- James
```

**If unhappy (low usage):**
```
Hey [Name]!

I noticed you tried [Service] but didn't use it much.

No worries at all - but I'd love to learn: 
What would have made it more useful for you?

Your honest feedback helps us build something better.

Thanks!
- James
```

## Tracking Success

### Key Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Trial signups | Growing | Count per week |
| Trial → Active Use | >50% | Users who use 3+ times |
| Active → Paid | >20% | Conversions |
| Paid → Testimonial | >50% | Testimonials collected |

### Feedback → Improvement Loop

1. Collect all feedback in `docs/feedback/[service].md`
2. Weekly: Review feedback, identify patterns
3. Prioritize fixes: Pain points > Nice-to-haves
4. Ship improvements
5. Notify users who gave that feedback
6. Repeat

## Current Services

| Service | Free Trial | Cost | Price | Status |
|---------|-----------|------|-------|--------|
| AI Phone | 25 calls | $1.50 | $99/mo | Live |
| Whale Track | 7 days | $0 | $49/mo | Live |
| Dashboard | 14 days | $0 | $49/mo | Live |
| Wellness | 30 days | $0.30 | $19/mo | Live |
| AI API | 1000 req | $0-1 | $29/mo | Live |
| Community | 30 days | $0 | $9/mo | Live |

## Live Page

**URL:** https://fullpotential.ai/try

---

*Remember: The goal isn't to give away free stuff. The goal is to build trust, collect feedback, and convert happy users into paying customers who become advocates.*













