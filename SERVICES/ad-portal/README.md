# Ad Portal

Unified advertising management system for coaching offers with Meta Ads integration, conversion tracking, and profit analytics.

## Features

- **Offer Management**: Create and manage coaching packages
- **Campaign Management**: Launch and control Meta (Facebook/Instagram) ad campaigns
- **Creative Studio**: AI-powered ad copy generation
- **Conversion Tracking**: Stripe webhooks + UC Credits integration
- **Profit Analytics**: Real-time ROAS, CPA, and profit calculations
- **AI Optimization**: Automated recommendations for scaling/pausing campaigns

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Meta Business Account with Marketing API access
- Stripe account

### Backend Setup

```bash
cd SERVICES/ad-portal

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run migrations (if using alembic)
alembic upgrade head

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8800 --reload
```

### Frontend Setup

```bash
cd SERVICES/ad-portal/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Docker Deployment

```bash
cd SERVICES/ad-portal

# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

## API Endpoints

### Offers
- `GET /api/offers` - List all offers
- `POST /api/offers` - Create offer
- `GET /api/offers/{id}` - Get offer
- `PUT /api/offers/{id}` - Update offer
- `DELETE /api/offers/{id}` - Delete offer

### Campaigns
- `GET /api/campaigns` - List campaigns
- `POST /api/campaigns` - Create campaign
- `GET /api/campaigns/{id}` - Get campaign
- `PUT /api/campaigns/{id}` - Update campaign
- `POST /api/campaigns/{id}/launch` - Launch to Meta
- `POST /api/campaigns/{id}/pause` - Pause campaign
- `POST /api/campaigns/{id}/resume` - Resume campaign

### Creatives
- `GET /api/creatives` - List creatives
- `POST /api/creatives` - Create creative
- `POST /api/creatives/generate` - AI generate creatives

### Analytics
- `GET /api/analytics/overview` - Dashboard stats
- `GET /api/analytics/campaigns` - Campaign performance
- `GET /api/analytics/daily` - Daily metrics

### Webhooks
- `POST /api/webhooks/stripe` - Stripe payment events
- `POST /api/webhooks/uc` - UC Credits transactions

## Architecture

```
ad-portal/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings
│   ├── database.py          # Database connection
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── api/                 # API routes
│   ├── integrations/        # External APIs (Meta, Stripe, UC)
│   └── services/            # Business logic
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   └── hooks/           # React Query hooks
│   └── package.json
├── docker-compose.yml
└── requirements.txt
```

## Integration Setup

### Meta Ads API

1. Create a Meta Business Account
2. Set up a Developer App at developers.facebook.com
3. Get Marketing API access
4. Generate a long-lived access token
5. Note your Ad Account ID (format: act_XXXXX)
6. Create a Meta Pixel for conversion tracking

### Stripe Webhooks

1. In Stripe Dashboard, go to Developers > Webhooks
2. Add endpoint: `https://yourdomain.com/api/webhooks/stripe`
3. Select events: `payment_intent.succeeded`, `charge.refunded`
4. Copy the webhook secret to your .env

## Profit Tracking Flow

```
1. User clicks ad → Landing page with fbclid
2. User purchases → Stripe/UC payment
3. Webhook fires → Record conversion with attribution
4. Server sends to Meta CAPI → Improves ad optimization
5. Hourly sync → Pull latest spend from Meta
6. Daily rollup → Calculate profit reports
```

## Port Assignment

- **Backend API**: 8800
- **Frontend**: 8801
- **Database**: 5433 (host) → 5432 (container)

## Support

Part of the Full Potential AI ecosystem.
Service Registry: `docs/coordination/SERVICE_REGISTRY.md`


