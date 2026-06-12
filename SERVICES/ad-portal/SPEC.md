# Ad Portal - Technical Specification

**Service:** ad-portal
**Type:** Revenue Operations Platform
**Priority:** HIGH (Revenue Generation)
**Port:** 8800
**Status:** Development

---

## Mission

One-stop advertising portal for coaching offers: create content, launch Meta campaigns, track conversions, calculate profit, and optimize spend - all in one place.

---

## Business Impact

### Revenue Model
- **Input:** Ad spend on Meta (Facebook/Instagram)
- **Output:** Coaching sales via Stripe + UC Credits
- **Goal:** Positive ROAS (Return on Ad Spend) > 2x

### Success Metrics
| Metric | Target |
|--------|--------|
| Time to first campaign | < 48 hours |
| ROAS | > 2.0x |
| Profit margin | > 30% |
| Campaign launch time | < 10 minutes |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AD PORTAL (Port 8800)                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │    OFFERS    │    │  CAMPAIGNS   │    │  CREATIVES   │          │
│  │   Manager    │───▶│   Manager    │───▶│   Studio     │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│         │                   │                   │                   │
│         ▼                   ▼                   ▼                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    INTEGRATIONS LAYER                        │   │
│  ├─────────────┬─────────────┬─────────────┬─────────────┬─────┤   │
│  │  Meta Ads   │ Meta Pixel  │   Stripe    │ UC Credits  │ AI  │   │
│  │    API      │   CAPI      │  Webhooks   │  Gateway    │Brain│   │
│  └─────────────┴─────────────┴─────────────┴─────────────┴─────┘   │
│         │                   │                   │                   │
│         ▼                   ▼                   ▼                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    ANALYTICS ENGINE                          │   │
│  │    Spend Tracker  │  Revenue Aggregator  │  Profit Calc     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      DASHBOARD (React)                        │  │
│  │   Offers │ Campaigns │ Creatives │ Analytics │ Optimizer     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend
```python
# Core
FastAPI==0.104.1
SQLAlchemy==2.0.23
alembic==1.13.0
asyncpg==0.29.0
pydantic==2.5.0

# Integrations
facebook-business==19.0.0  # Meta Marketing API
stripe==7.0.0
httpx==0.25.0

# Utils
python-dotenv==1.0.0
APScheduler==3.10.4
```

### Frontend
```json
{
  "react": "^18.2.0",
  "vite": "^5.0.0",
  "tailwindcss": "^3.4.0",
  "recharts": "^2.10.0",
  "@tanstack/react-query": "^5.0.0"
}
```

### Database
- PostgreSQL 15 (existing on primary server)
- Schema: `ad_portal`

---

## Data Model

### offers
```sql
CREATE TABLE offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    offer_type VARCHAR(50) DEFAULT 'coaching',
    landing_url TEXT NOT NULL,
    thank_you_url TEXT,
    pixel_id VARCHAR(100),
    stripe_price_id VARCHAR(100),
    uc_price DECIMAL(10,2),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### campaigns
```sql
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES offers(id),
    name VARCHAR(255) NOT NULL,
    meta_campaign_id VARCHAR(100),
    meta_adset_id VARCHAR(100),
    objective VARCHAR(50) DEFAULT 'CONVERSIONS',
    daily_budget DECIMAL(10,2) NOT NULL,
    lifetime_budget DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'draft',  -- draft, active, paused, completed
    start_date DATE,
    end_date DATE,
    targeting JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_campaigns_offer ON campaigns(offer_id);
CREATE INDEX idx_campaigns_status ON campaigns(status);
```

### creatives
```sql
CREATE TABLE creatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id),
    name VARCHAR(255),
    creative_type VARCHAR(50) DEFAULT 'single_image',  -- single_image, carousel, video
    headline VARCHAR(255) NOT NULL,
    primary_text TEXT NOT NULL,
    description TEXT,
    call_to_action VARCHAR(50) DEFAULT 'LEARN_MORE',
    image_url TEXT,
    video_url TEXT,
    meta_ad_id VARCHAR(100),
    variation CHAR(1) DEFAULT 'A',  -- A, B, C for split testing
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_creatives_campaign ON creatives(campaign_id);
```

### ad_metrics
```sql
CREATE TABLE ad_metrics (
    id SERIAL PRIMARY KEY,
    campaign_id UUID REFERENCES campaigns(id),
    creative_id UUID REFERENCES creatives(id),
    date DATE NOT NULL,
    hour INTEGER,  -- 0-23, NULL for daily rollup
    impressions INTEGER DEFAULT 0,
    reach INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    link_clicks INTEGER DEFAULT 0,
    spend DECIMAL(10,2) DEFAULT 0,
    cpm DECIMAL(10,4),  -- cost per 1000 impressions
    cpc DECIMAL(10,4),  -- cost per click
    ctr DECIMAL(6,4),   -- click-through rate
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(campaign_id, creative_id, date, hour)
);

CREATE INDEX idx_metrics_date ON ad_metrics(date);
CREATE INDEX idx_metrics_campaign_date ON ad_metrics(campaign_id, date);
```

### conversions
```sql
CREATE TABLE conversions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id),
    offer_id UUID REFERENCES offers(id),
    source VARCHAR(20) NOT NULL,  -- stripe, uc_credits
    external_id VARCHAR(255),  -- stripe payment_intent_id or uc transaction_id
    amount DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    customer_email VARCHAR(255),
    customer_name VARCHAR(255),
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(100),
    utm_content VARCHAR(100),
    fbclid VARCHAR(255),  -- Facebook click ID for attribution
    converted_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_conversions_campaign ON conversions(campaign_id);
CREATE INDEX idx_conversions_date ON conversions(converted_at);
CREATE INDEX idx_conversions_fbclid ON conversions(fbclid);
```

### profit_reports
```sql
CREATE TABLE profit_reports (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    campaign_id UUID REFERENCES campaigns(id),
    offer_id UUID REFERENCES offers(id),
    total_spend DECIMAL(10,2) DEFAULT 0,
    total_revenue DECIMAL(10,2) DEFAULT 0,
    conversion_count INTEGER DEFAULT 0,
    profit DECIMAL(10,2) GENERATED ALWAYS AS (total_revenue - total_spend) STORED,
    roas DECIMAL(6,2) GENERATED ALWAYS AS (
        CASE WHEN total_spend > 0 THEN total_revenue / total_spend ELSE 0 END
    ) STORED,
    cpa DECIMAL(10,2) GENERATED ALWAYS AS (
        CASE WHEN conversion_count > 0 THEN total_spend / conversion_count ELSE 0 END
    ) STORED,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, campaign_id)
);

CREATE INDEX idx_profit_date ON profit_reports(date);
```

---

## API Endpoints

### Offers
```
GET    /api/offers                    List all offers
POST   /api/offers                    Create offer
GET    /api/offers/{id}               Get offer details
PUT    /api/offers/{id}               Update offer
DELETE /api/offers/{id}               Soft delete offer
```

### Campaigns
```
GET    /api/campaigns                 List campaigns (with filters)
POST   /api/campaigns                 Create campaign
GET    /api/campaigns/{id}            Get campaign with metrics
PUT    /api/campaigns/{id}            Update campaign
POST   /api/campaigns/{id}/launch     Launch to Meta
POST   /api/campaigns/{id}/pause      Pause campaign
POST   /api/campaigns/{id}/resume     Resume campaign
DELETE /api/campaigns/{id}            Archive campaign
```

### Creatives
```
GET    /api/campaigns/{id}/creatives  List creatives for campaign
POST   /api/campaigns/{id}/creatives  Create creative
PUT    /api/creatives/{id}            Update creative
DELETE /api/creatives/{id}            Delete creative
POST   /api/creatives/generate        AI-generate creative copy
```

### Analytics
```
GET    /api/analytics/overview        Dashboard overview stats
GET    /api/analytics/campaigns       Campaign performance comparison
GET    /api/analytics/daily           Daily spend/revenue/profit
GET    /api/analytics/hourly/{date}   Hourly breakdown for date
GET    /api/analytics/creatives       Creative A/B test results
```

### Webhooks
```
POST   /api/webhooks/stripe           Stripe payment webhook
POST   /api/webhooks/meta             Meta Conversions API callback
POST   /api/webhooks/uc               UC Credits transaction hook
```

### Sync
```
POST   /api/sync/meta                 Pull latest metrics from Meta
POST   /api/sync/stripe               Reconcile Stripe payments
```

---

## Integration Details

### Meta Marketing API

**Authentication:**
- App ID + App Secret + Access Token
- Stored in `/opt/fpai/api_keys.json`

**Key Operations:**
```python
# Campaign creation
POST /{ad_account_id}/campaigns
{
    "name": "Coaching Offer - {offer_name}",
    "objective": "OUTCOME_SALES",
    "status": "PAUSED",
    "special_ad_categories": []
}

# Ad Set creation  
POST /{ad_account_id}/adsets
{
    "name": "AdSet - {campaign_name}",
    "campaign_id": "{campaign_id}",
    "daily_budget": budget_cents,
    "billing_event": "IMPRESSIONS",
    "optimization_goal": "OFFSITE_CONVERSIONS",
    "targeting": {...}
}

# Ad creation
POST /{ad_account_id}/ads
{
    "name": "Ad - {creative_name}",
    "adset_id": "{adset_id}",
    "creative": {"creative_id": "{creative_id}"}
}

# Insights (metrics)
GET /{object_id}/insights
    ?fields=impressions,reach,clicks,spend,actions
    &date_preset=last_7d
```

### Meta Conversions API (Server-Side Tracking)

```python
# Send purchase event
POST /v19.0/{pixel_id}/events
{
    "data": [{
        "event_name": "Purchase",
        "event_time": timestamp,
        "action_source": "website",
        "event_source_url": landing_url,
        "user_data": {
            "em": hashed_email,
            "ph": hashed_phone,
            "fbc": fbclid_cookie,
            "fbp": fbp_cookie
        },
        "custom_data": {
            "currency": "USD",
            "value": amount,
            "content_ids": [offer_id],
            "content_type": "product"
        }
    }],
    "access_token": access_token
}
```

### Stripe Webhooks

**Events to handle:**
- `payment_intent.succeeded` - Conversion completed
- `payment_intent.payment_failed` - Track failure
- `charge.refunded` - Adjust revenue

**Webhook payload parsing:**
```python
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    event = stripe.Webhook.construct_event(
        payload, sig_header, STRIPE_WEBHOOK_SECRET
    )
    
    if event["type"] == "payment_intent.succeeded":
        payment = event["data"]["object"]
        # Extract UTM params and fbclid from metadata
        await record_conversion(
            source="stripe",
            amount=payment["amount"] / 100,
            external_id=payment["id"],
            metadata=payment["metadata"]
        )
```

### UC Credits Gateway

**Endpoint:** `http://198.54.123.234:8765/api/transactions`

**Hook into transaction events:**
```python
# Poll or webhook for new transactions
GET /api/transactions?since={timestamp}&type=purchase

# Each transaction contains:
{
    "id": "txn_xxx",
    "amount_uc": 100,
    "amount_usd": 100.00,  # 1 UC = $1
    "product_id": "coaching_offer_id",
    "user_id": "user_xxx",
    "metadata": {"utm_campaign": "...", "fbclid": "..."}
}
```

### AI Brain Integration

**Endpoint:** `http://162.0.208.88:8101/api/generate`

**Creative generation prompt:**
```python
prompt = f"""
Generate Facebook/Instagram ad copy for a coaching offer.

Offer: {offer.name}
Price: ${offer.price}
Description: {offer.description}
Target audience: Entrepreneurs seeking business coaching

Create 3 variations (A, B, C) with:
- Headline (max 40 chars)
- Primary text (max 125 chars) 
- Description (max 30 chars)

Focus on: transformation, results, urgency without pressure.
Tone: Professional, empowering, authentic.

Output as JSON array.
"""
```

---

## Profit Calculation Logic

```python
def calculate_profit(campaign_id: str, date: date) -> ProfitReport:
    # Get spend from ad_metrics
    spend = db.query(
        func.sum(AdMetrics.spend)
    ).filter(
        AdMetrics.campaign_id == campaign_id,
        AdMetrics.date == date
    ).scalar() or 0
    
    # Get revenue from conversions
    revenue = db.query(
        func.sum(Conversion.amount)
    ).filter(
        Conversion.campaign_id == campaign_id,
        func.date(Conversion.converted_at) == date
    ).scalar() or 0
    
    conversion_count = db.query(
        func.count(Conversion.id)
    ).filter(
        Conversion.campaign_id == campaign_id,
        func.date(Conversion.converted_at) == date
    ).scalar() or 0
    
    return ProfitReport(
        date=date,
        campaign_id=campaign_id,
        total_spend=spend,
        total_revenue=revenue,
        conversion_count=conversion_count
        # profit, roas, cpa are auto-calculated columns
    )
```

---

## Scheduler Jobs

```python
# Sync Meta metrics every hour
@scheduler.scheduled_job('cron', minute=5)
async def sync_meta_metrics():
    """Pull latest ad metrics from Meta API"""
    for campaign in get_active_campaigns():
        metrics = await meta_client.get_insights(campaign.meta_campaign_id)
        await save_metrics(campaign.id, metrics)

# Calculate daily profit reports at midnight
@scheduler.scheduled_job('cron', hour=0, minute=30)
async def generate_profit_reports():
    """Roll up daily profit for all campaigns"""
    yesterday = date.today() - timedelta(days=1)
    for campaign in get_all_campaigns():
        report = calculate_profit(campaign.id, yesterday)
        await save_profit_report(report)

# AI optimization recommendations daily
@scheduler.scheduled_job('cron', hour=8)
async def generate_recommendations():
    """AI analyzes performance and suggests optimizations"""
    for campaign in get_active_campaigns():
        if campaign.days_running >= 3:  # Need data
            recommendation = await ai_analyze(campaign)
            await save_recommendation(campaign.id, recommendation)
```

---

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/fpai

# Meta
META_APP_ID=xxx
META_APP_SECRET=xxx
META_ACCESS_TOKEN=xxx
META_AD_ACCOUNT_ID=act_xxx
META_PIXEL_ID=xxx

# Stripe
STRIPE_SECRET_KEY=sk_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# UC Credits Gateway
UC_GATEWAY_URL=http://198.54.123.234:8765

# AI Brain
AI_BRAIN_URL=http://162.0.208.88:8101

# Service
PORT=8800
ENV=production
```

---

## Directory Structure

```
ad-portal/
├── SPEC.md
├── README.md
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── alembic/
│   └── versions/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Settings
│   ├── database.py             # DB connection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── offer.py
│   │   ├── campaign.py
│   │   ├── creative.py
│   │   ├── metrics.py
│   │   └── conversion.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── offer.py
│   │   ├── campaign.py
│   │   └── analytics.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── offers.py
│   │   ├── campaigns.py
│   │   ├── creatives.py
│   │   ├── analytics.py
│   │   └── webhooks.py
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── meta.py             # Meta Marketing API
│   │   ├── meta_pixel.py       # Conversions API
│   │   ├── stripe_hook.py      # Stripe webhooks
│   │   └── uc_credits.py       # UC Gateway
│   └── services/
│       ├── __init__.py
│       ├── creative_ai.py      # AI copy generation
│       ├── profit_calculator.py
│       ├── optimizer.py        # AI recommendations
│       └── scheduler.py        # Background jobs
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── Sidebar.tsx
│       │   ├── OfferCard.tsx
│       │   ├── CampaignCard.tsx
│       │   ├── CreativeEditor.tsx
│       │   ├── MetricsChart.tsx
│       │   └── ProfitGauge.tsx
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── Offers.tsx
│       │   ├── Campaigns.tsx
│       │   ├── Creatives.tsx
│       │   └── Analytics.tsx
│       └── hooks/
│           ├── useOffers.ts
│           ├── useCampaigns.ts
│           └── useAnalytics.ts
└── tests/
    ├── test_offers.py
    ├── test_campaigns.py
    └── test_profit.py
```

---

## Deployment

### Docker Compose
```yaml
version: '3.8'

services:
  ad-portal-api:
    build: .
    ports:
      - "8800:8800"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - META_ACCESS_TOKEN=${META_ACCESS_TOKEN}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
    depends_on:
      - db
    restart: unless-stopped

  ad-portal-frontend:
    build: ./frontend
    ports:
      - "8801:80"
    depends_on:
      - ad-portal-api
    restart: unless-stopped

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=ad_portal
      - POSTGRES_USER=adportal
      - POSTGRES_PASSWORD=${DB_PASSWORD}

volumes:
  postgres_data:
```

### Systemd Service
```ini
[Unit]
Description=Ad Portal API
After=network.target

[Service]
Type=simple
User=fpai
WorkingDirectory=/opt/fpai/services/ad-portal
ExecStart=/opt/fpai/services/ad-portal/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8800
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Success Criteria

### MVP Checklist
- [ ] Create coaching offer with pricing
- [ ] Generate AI ad copy (3 variations)
- [ ] Launch campaign to Meta
- [ ] Track ad spend in real-time
- [ ] Receive Stripe webhook on sale
- [ ] Calculate and display profit/ROAS
- [ ] View analytics dashboard

### Performance Requirements
- API response time < 200ms
- Dashboard load < 2 seconds
- Webhook processing < 500ms
- Metrics sync delay < 1 hour

---

**Built for Full Potential AI - Revenue Operations**
**Port: 8800 | Primary Server: 198.54.123.234**


