# 🚀 BRICK 2: AI Marketing Engine - Master Specification

**Service Name:** `brick2-marketing-engine`
**Type:** GHL-Centered Hybrid Marketing Automation Platform
**Priority:** CRITICAL - Revenue Generator
**UBIC Version:** v1.5 Compliant (BRICK 1 Integration Ready)
**Build Time:** 18 hours (6 milestones)
**Revenue Target:** $25K+ in first 4 weeks

---

## 🎯 Mission

Build a next-generation AI marketing automation platform that:
1. Consolidates 15+ marketing tools into 6 core systems
2. Uses GoHighLevel as the central hub
3. Integrates premium AI services for competitive advantage
4. Provides UBIC v1.5 compliance for BRICK 1 AI orchestration
5. Generates measurable revenue from Day 1

---

## 💰 Business Impact

### Revenue Targets (4-Week Ramp)
| Week | Target | Cumulative | Strategy |
|:----:|:------:|:----------:|:---------|
| 1 | $5K+ | $5K | GHL funnels operational |
| 2 | $10K+ | $15K | AI-enhanced outreach |
| 3 | $15K+ | $30K | Scaling winning campaigns |
| 4 | $25K+ | $55K | Full system operational |

### Efficiency Gains
- **Tool Reduction:** 15+ tools → 6 core systems (60% reduction)
- **Cost Savings:** 60% reduction in monthly tool costs
- **Time Efficiency:** Single GHL interface for 80% of tasks
- **Setup Speed:** 50% faster campaign deployment
- **Lead Generation:** 300-500% increase through automation
- **Conversion Rates:** 25-40% improvement via AI optimization

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        BRICK 2: AI MARKETING ENGINE                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     BRICK 1 INTEGRATION LAYER (UBIC v1.5)                │   │
│  │  • /health  • /capabilities  • /state  • /message  • /emergency-stop   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│  ┌───────────────────────────────────┼───────────────────────────────────┐     │
│  │                          AI ORCHESTRATION LAYER                        │     │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │     │
│  │  │ Claude 4 │ │Perplexity│ │ Gemini   │ │Midjourney│ │  OpenAI  │    │     │
│  │  │ Sonnet   │ │   Pro    │ │   Pro    │ │    v6    │ │  Latest  │    │     │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘    │     │
│  │       │            │            │            │            │          │     │
│  │       └────────────┴────────────┼────────────┴────────────┘          │     │
│  │                                 │                                     │     │
│  │  ┌──────────────────────────────┴──────────────────────────────┐     │     │
│  │  │               UNIFIED AI CLIENT (ai_gateway.py)              │     │     │
│  │  └──────────────────────────────┬──────────────────────────────┘     │     │
│  └─────────────────────────────────┼─────────────────────────────────────┘     │
│                                    │                                            │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐     │
│  │                    GOHIGHLEVEL CENTRAL HUB                             │     │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐         │     │
│  │  │    CRM     │ │  Funnels   │ │   Email    │ │  Calendar  │         │     │
│  │  │ + Pipeline │ │ + Landing  │ │ + SMS Auto │ │ + Booking  │         │     │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘         │     │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐         │     │
│  │  │  Social    │ │  Payments  │ │ Analytics  │ │   Chat     │         │     │
│  │  │  Planner   │ │  Stripe    │ │ Dashboard  │ │  Widget    │         │     │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘         │     │
│  └───────────────────────────────────────────────────────────────────────┘     │
│                                    │                                            │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐     │
│  │                      PREMIUM TOOL INTEGRATIONS                         │     │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │     │
│  │  │  Apollo.io   │  │ Instantly.ai │  │    GA4       │                 │     │
│  │  │  Prospecting │  │  Cold Email  │  │ Attribution  │                 │     │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │     │
│  └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐     │
│  │                          MODULE SYSTEM                                 │     │
│  │                                                                        │     │
│  │  M1: GHL Hub    M2: AI Tools    M3: Lead Gen    M4: Revenue Track     │     │
│  │  M5: AI Chat    M6: BRICK 1 Integration                               │     │
│  └───────────────────────────────────────────────────────────────────────┘     │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Module Breakdown

### Module 1: GHL Foundation Hub (4 hours)
**Replaces:** HubSpot, Buffer, Calendly, Mailchimp, Stripe integration, 3+ landing page tools

| Component | GHL Feature | Status |
|:----------|:------------|:-------|
| CRM + Lead Scoring | GHL CRM | 🔵 Pending |
| Sales Pipeline | GHL Opportunities | 🔵 Pending |
| Landing Pages | GHL Funnel Builder | 🔵 Pending |
| Email Automation | GHL Workflows | 🔵 Pending |
| SMS Marketing | GHL SMS | 🔵 Pending |
| Social Scheduling | GHL Social Planner | 🔵 Pending |
| Calendar/Booking | GHL Calendar | 🔵 Pending |
| Payment Processing | GHL Payments | 🔵 Pending |

### Module 2: AI Integration Layer (3 hours)
**Premium AI Services:**

| Provider | Use Case | Monthly Cost |
|:---------|:---------|:-------------|
| Claude 4 Sonnet | Strategic content, complex reasoning | $20 |
| Perplexity Pro | Real-time research, market intel | $20 |
| Gemini Pro | Multimodal content, data analysis | $20 |
| Midjourney v6 | Visual generation | $30 |
| OpenAI Latest | Conversational AI, function calling | $50 |
| **Total** | | **$140/month** |

### Module 3: Lead Generation Engine (3 hours)
**Components:**
- Apollo.io prospect research automation
- Instantly.ai cold email deliverability
- Multi-channel outreach sequences
- Behavioral lead scoring (0-100)
- Response tracking + auto follow-up

**Target:** 50+ qualified prospects daily

### Module 4: Revenue Attribution (2 hours)
**Components:**
- GA4 integration for full journey tracking
- End-to-end attribution pipeline
- ROI calculation automation
- 30-60-90 day revenue forecasting

### Module 5: AI Conversation System (2 hours)
**Components:**
- ChatGPT-powered lead qualification
- Emotional intelligence integration
- Real-time objection handling
- Human handoff protocols (<30 seconds)

**Target:** >80% qualification accuracy

### Module 6: BRICK 1 Integration (4 hours)
**UBIC v1.5 Compliance:**

```python
REQUIRED_ENDPOINTS = [
    "GET  /health",           # System status
    "GET  /capabilities",     # Available features
    "GET  /state",            # Current campaign state
    "GET  /dependencies",     # Tool API status
    "POST /message",          # Strategic guidance receiver
    "POST /send",             # Performance reports
    "POST /reload-config",    # Settings update
    "POST /shutdown",         # Graceful pause
    "POST /emergency-stop"    # Immediate halt (<1 second)
]
```

---

## 🛠️ Tech Stack

### Core
```yaml
Backend: FastAPI 0.104+
Database: PostgreSQL 15+
Cache: Redis 7+
Queue: Celery 5.3+
Container: Docker + Docker Compose
```

### GHL Integration
```yaml
GHL API: REST + Webhooks
Auth: OAuth 2.0
Sync: Real-time + Batch
```

### AI Services
```python
anthropic>=0.18.0      # Claude 4 Sonnet
openai>=1.12.0         # GPT-4, Function Calling
google-generativeai    # Gemini Pro
httpx                  # Perplexity, Midjourney APIs
```

### Premium Tools
```yaml
Apollo.io: REST API
Instantly.ai: REST API
GA4: Data API v1
Stripe: Payments API
```

---

## 📁 Project Structure

```
brick2-marketing-engine/
├── SPEC.md                          # This file
├── README.md                        # Quick start guide
├── docker-compose.yml               # Full deployment
├── requirements.txt                 # Python dependencies
│
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Settings + env vars
│   │
│   ├── core/                        # Shared utilities
│   │   ├── __init__.py
│   │   ├── database.py              # DB connection
│   │   ├── redis.py                 # Cache layer
│   │   └── security.py              # JWT + auth
│   │
│   ├── ai/                          # AI Integration Layer (M2)
│   │   ├── __init__.py
│   │   ├── gateway.py               # Unified AI client
│   │   ├── providers/
│   │   │   ├── claude.py            # Claude 4 Sonnet
│   │   │   ├── openai.py            # GPT-4 + functions
│   │   │   ├── perplexity.py        # Real-time research
│   │   │   ├── gemini.py            # Multimodal
│   │   │   └── midjourney.py        # Visual generation
│   │   └── prompts/                 # Prompt templates
│   │       ├── content.py
│   │       ├── research.py
│   │       └── qualification.py
│   │
│   ├── ghl/                         # GHL Hub (M1)
│   │   ├── __init__.py
│   │   ├── client.py                # GHL API client
│   │   ├── crm.py                   # Contact/Lead management
│   │   ├── pipelines.py             # Opportunities
│   │   ├── funnels.py               # Landing pages
│   │   ├── workflows.py             # Automation triggers
│   │   ├── calendar.py              # Booking system
│   │   ├── social.py                # Social planner
│   │   └── payments.py              # Stripe via GHL
│   │
│   ├── leads/                       # Lead Gen Engine (M3)
│   │   ├── __init__.py
│   │   ├── apollo.py                # Apollo.io integration
│   │   ├── instantly.py             # Cold email
│   │   ├── scoring.py               # Lead scoring (0-100)
│   │   ├── sequencer.py             # Multi-channel outreach
│   │   └── tracker.py               # Response tracking
│   │
│   ├── revenue/                     # Attribution (M4)
│   │   ├── __init__.py
│   │   ├── ga4.py                   # Google Analytics 4
│   │   ├── attribution.py           # Journey tracking
│   │   ├── roi.py                   # ROI calculations
│   │   └── forecasting.py           # Predictive models
│   │
│   ├── chat/                        # AI Conversation (M5)
│   │   ├── __init__.py
│   │   ├── qualification.py         # AI qualifier
│   │   ├── handoff.py               # Human escalation
│   │   └── analytics.py             # Conversation scoring
│   │
│   ├── brick1/                      # BRICK 1 Integration (M6)
│   │   ├── __init__.py
│   │   ├── ubic.py                  # UBIC v1.5 endpoints
│   │   ├── messages.py              # Message handlers
│   │   ├── feature_flags.py         # Capability negotiation
│   │   └── mode_toggle.py           # Human/AI switching
│   │
│   ├── api/                         # REST API routes
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── campaigns.py
│   │   │   ├── leads.py
│   │   │   ├── analytics.py
│   │   │   └── ai.py
│   │   └── ubic/                    # BRICK 1 endpoints
│   │       └── endpoints.py
│   │
│   └── models/                      # Database models
│       ├── __init__.py
│       ├── campaign.py
│       ├── lead.py
│       ├── conversation.py
│       └── attribution.py
│
├── tests/
│   ├── test_ghl.py
│   ├── test_ai.py
│   ├── test_leads.py
│   └── test_ubic.py
│
├── scripts/
│   ├── setup_ghl.py                 # Initial GHL config
│   ├── seed_prompts.py              # Load AI prompts
│   └── migrate.py                   # DB migrations
│
└── infra/
    ├── Dockerfile
    ├── nginx.conf
    └── deploy.sh
```

---

## 🔌 API Endpoints

### Campaign Management
```http
POST   /api/v1/campaigns              # Create campaign
GET    /api/v1/campaigns              # List campaigns
GET    /api/v1/campaigns/{id}         # Get campaign
PUT    /api/v1/campaigns/{id}         # Update campaign
DELETE /api/v1/campaigns/{id}         # Delete campaign
POST   /api/v1/campaigns/{id}/launch  # Launch campaign
POST   /api/v1/campaigns/{id}/pause   # Pause campaign
```

### Lead Generation
```http
POST   /api/v1/leads/research         # Apollo.io research
POST   /api/v1/leads/score            # Score leads
POST   /api/v1/leads/sequence         # Start outreach
GET    /api/v1/leads/pipeline         # Pipeline view
```

### AI Services
```http
POST   /api/v1/ai/generate/content    # Generate content
POST   /api/v1/ai/research            # Perplexity research
POST   /api/v1/ai/qualify             # Qualify lead
POST   /api/v1/ai/visual              # Generate visuals
```

### UBIC v1.5 (BRICK 1)
```http
GET    /health                        # System health
GET    /capabilities                  # Feature flags
GET    /state                         # Current state
GET    /dependencies                  # Tool status
POST   /message                       # Receive directive
POST   /send                          # Send report
POST   /reload-config                 # Reload settings
POST   /shutdown                      # Graceful stop
POST   /emergency-stop                # Immediate halt
```

---

## ⚙️ Environment Variables

```bash
# Core
DATABASE_URL=postgresql://user:pass@localhost:5432/brick2
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key

# GHL
GHL_API_KEY=your-ghl-api-key
GHL_LOCATION_ID=your-location-id
GHL_AGENCY_ID=your-agency-id

# AI Services
ANTHROPIC_API_KEY=your-claude-key
OPENAI_API_KEY=your-openai-key
PERPLEXITY_API_KEY=your-perplexity-key
GOOGLE_AI_API_KEY=your-gemini-key
MIDJOURNEY_API_KEY=your-midjourney-key

# Premium Tools
APOLLO_API_KEY=your-apollo-key
INSTANTLY_API_KEY=your-instantly-key
GA4_PROPERTY_ID=your-ga4-property

# Payments
STRIPE_SECRET_KEY=your-stripe-key

# BRICK 1
BRICK1_ENDPOINT=http://brick1.fullpotential.ai
BRICK1_JWT_SECRET=shared-secret
```

---

## 📊 Success Metrics

### Module 1: GHL Foundation
- [ ] All 8 GHL components operational
- [ ] Response time <2 seconds
- [ ] Test transactions successful

### Module 2: AI Integration
- [ ] All 5 AI providers connected
- [ ] Unified gateway operational
- [ ] Content generation <10 seconds

### Module 3: Lead Generation
- [ ] 50+ qualified prospects/day
- [ ] Lead scoring 0-100 operational
- [ ] Multi-channel sequences running

### Module 4: Revenue Attribution
- [ ] End-to-end tracking operational
- [ ] ROI calculations accurate
- [ ] 30-60-90 forecasts generating

### Module 5: AI Conversation
- [ ] >80% qualification accuracy
- [ ] Human handoff <30 seconds
- [ ] Concurrent conversations supported

### Module 6: BRICK 1 Integration
- [ ] All 9 UBIC endpoints working
- [ ] Strategic guidance processing
- [ ] Emergency stop <1 second

---

## 🚀 Deployment

### Development
```bash
# Clone and setup
cd SERVICES/brick2-marketing-engine
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run locally
uvicorn app.main:app --reload --port 8700
```

### Production
```bash
# Deploy to server
docker-compose up -d

# Health check
curl http://localhost:8700/health
```

### Port Assignment
**Port 8700** - BRICK 2 Marketing Engine

---

## 🔗 Integration Points

### With Existing Services
- **Registry (8000):** Auto-register on startup
- **Orchestrator (8001):** Report campaign status
- **Dashboard (8002):** Display marketing metrics
- **Strategic Intel (8500):** Receive market insights

### With BRICK 1 (Future)
- Strategic guidance receiver
- Performance report sender
- Capability negotiation
- Emergency controls

---

## 📅 Development Timeline

| Milestone | Hours | Focus | Deliverable |
|:---------:|:-----:|:------|:------------|
| M1 | 4 | GHL Foundation | Central hub operational |
| M2 | 3 | AI Integration | 5 AI providers connected |
| M3 | 3 | Lead Generation | 50+ prospects/day system |
| M4 | 2 | Revenue Tracking | Full attribution pipeline |
| M5 | 2 | AI Conversation | Qualification chat live |
| M6 | 4 | BRICK 1 Integration | UBIC v1.5 compliance |
| **Total** | **18** | | **Production ready** |

---

## 🧪 Testing Strategy

### Unit Tests
```bash
pytest tests/ -v --cov=app --cov-report=html
```

### Integration Tests
```bash
pytest tests/integration/ -v
```

### Load Tests
```bash
locust -f tests/load/locustfile.py --host=http://localhost:8700
```

---

**Status:** 🔵 Spec Complete - Ready for Build
**Priority:** CRITICAL (Revenue Generator)
**ROI:** $25K+ in 4 weeks

---

*"One marketing engine to rule them all."*

