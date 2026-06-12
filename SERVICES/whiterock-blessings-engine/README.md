# WhiteRock CORA Membership & Community Blessings System

**Version:** 2.1.0  
**Status:** Production-Ready

A member management and community support system for WhiteRock Church Trust that tracks tithing members, manages CORA participation credits with vitality-based decay, and enables discretionary blessing distribution to community members based on need and participation — all under strict 508(c)(1)(A) compliance.

## 🙏 Overview

### What This System Does

- **Member Management**: Registration, profiles, disclosure acknowledgment tracking
- **CORA Vitality Credits**: Non-transferable engagement credits with inactivity decay
- **Tithe Processing**: Stripe integration with full compliance tracking
- **Blessing Requests**: Formal state machine with committee review workflow
- **Vendor-Direct Disbursements**: Payments to landlords, utilities, hospitals (not cash to members)
- **Compliance Audit**: Full audit trail with integrity checks

### Trust Firewall Principle

⚠️ **CRITICAL**: This system maintains ABSOLUTE separation from any treasury/trading systems.

- ❌ No database tables reference trades, positions, or market data
- ❌ No API endpoints expose trading functionality
- ❌ No code imports reference trading/treasury modules
- ❌ CORA has NO transfer or redeem endpoints

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+ (provided in docker-compose)
- Redis (provided in docker-compose)

### Development Setup

```bash
# Clone and navigate
cd SERVICES/whiterock-blessings-engine

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Check health
curl http://localhost:8020/health

# View API docs
open http://localhost:8020/docs
```

### Production Deployment

```bash
# Set production environment variables
export POSTGRES_PASSWORD=your-secure-password
export JWT_SECRET=your-secure-jwt-secret
export STRIPE_API_KEY=sk_live_xxx
export SENDGRID_API_KEY=SG.xxx

# Deploy
docker-compose -f docker-compose.yml up -d

# Initialize database
docker-compose exec app python -c "
from app.database import init_db
import asyncio
asyncio.run(init_db())
"
```

## 📊 API Endpoints

### UDC Standard Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/capabilities` | GET | Feature declaration |
| `/state` | GET | Resource metrics |
| `/dependencies` | GET | Integration status |

### Member Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/members/register` | POST | Public | Register new member |
| `/members/login` | POST | Public | Get access token |
| `/members/me` | GET | JWT | Get profile |
| `/members/me` | PUT | JWT | Update profile |
| `/members/me/acknowledge-disclosure` | POST | JWT | Sign disclosure |

### Tithe Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/tithes` | POST | JWT | Submit tithe |
| `/tithes/me` | GET | JWT | Get tithe history |
| `/tithes/{id}/receipt` | GET | JWT | Download receipt |

### CORA Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/cora/balance` | GET | JWT | Get CORA balance |
| `/cora/tiers` | GET | Public | Get tier definitions |
| `/cora/grant` | POST | Admin | Grant CORA credits |
| `/cora/decay-preview` | GET | Admin | Preview pending decays |

### Blessing Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/blessings/eligibility` | GET | JWT | Check eligibility |
| `/blessings/request` | POST | JWT | Submit request |
| `/blessings/me` | GET | JWT | Get my requests |
| `/blessings/pending` | GET | Committee | Review pending |
| `/blessings/{id}/transition` | PUT | Committee | Change state |
| `/blessings/{id}/disburse` | POST | Admin | Disburse blessing |

### Capacity Endpoint

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/capacity` | GET | JWT | Get community capacity (READ-ONLY) |

### Report Endpoints (Admin)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/reports/community` | GET | Admin | Community metrics |
| `/reports/blessings` | GET | Admin | Blessing report |
| `/reports/cora-health` | GET | Admin | CORA system health |

### Audit Endpoints (Auditor)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/audit/compliance-export` | GET | Auditor | Export disclosures ZIP |
| `/audit/integrity-check` | GET | Auditor | Run integrity check |
| `/audit/log` | GET | Auditor | Query audit log |

## 🔐 CORA Vitality System

CORA (Community Vitality) credits represent a member's standing in the community.

### Key Properties

- **Non-transferable**: No send/trade functions exist
- **Non-redeemable**: Cannot be cashed out
- **Engagement-based**: Earned through tithes and service
- **Decay-prone**: 10% monthly decay after 12 months inactivity

### Tiers

| Tier | Threshold | Cap | Privileges |
|------|-----------|-----|------------|
| Seedling | 0 | 1,000 | Basic access |
| Sprout | 500 | 2,500 | All public events |
| Steward | 2,000 | 5,000 | Full access, voting |
| Elder | 5,000 | 10,000 | Committee eligible |

### Decay Schedule

- Warning email: 30 days before first decay
- Decay starts: After 12 months of no engagement
- Decay rate: 10% of balance per month
- Minimum decay: 1 CORA

## 🙌 Blessing State Machine

Valid state transitions:

```
draft → pending → committee_review → approved → disbursed → closed
                                   → denied → closed
                                   → info_requested ↔ committee_review
```

### Approval Requirements

- ✅ Compliance flag must be TRUE for approval
- ✅ Amount approved must be specified
- ✅ Vendor-direct payment is default
- ⚠️ Cash-to-member requires admin override + audit log

## 📝 Compliance

### 508(c)(1)(A) Requirements

1. **Disclosure Tracking**: Every tithe stores the full disclosure text
2. **Hard Acknowledgment**: Both scroll AND checkbox required
3. **Audit Trail**: All sensitive changes logged with severity
4. **Integrity Check**: `/audit/integrity-check` verifies zero treasury links

### Email Disclaimers

All blessing approval emails include the mandatory footer:

> "This blessing is a one-time discretionary gift from WhiteRock community and does not constitute an ongoing obligation, contract, or entitlement to future support."

## 🔧 Background Tasks

Celery Beat schedules:

| Task | Schedule | Description |
|------|----------|-------------|
| `run_cora_decay` | 1st of month, 3am UTC | Process CORA decay |
| `send_decay_warnings` | Daily, 9am UTC | Send warning emails |
| `health_check` | Daily, midnight UTC | System health check |

## 🌐 Integration

### Internal

- Registry (#1): JWT authentication, service registration
- Orchestrator (#10): Heartbeat, task coordination
- Dashboard (#2): Community metrics display

### External

- **Stripe**: Tithe payment processing
- **SendGrid**: Transactional emails, receipts
- **Redis**: Celery message broker

### NEVER Integrates With

- ❌ Treasury trading systems
- ❌ Position management
- ❌ Market data feeds
- ❌ Any trading-related services

## 📁 Project Structure

```
whiterock-blessings-engine/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── config.py         # Settings
│   ├── database.py       # Async SQLAlchemy
│   ├── models.py         # ORM models
│   ├── schemas.py        # Pydantic schemas
│   ├── auth.py           # JWT authentication
│   ├── state_machine.py  # Blessing states
│   ├── routes/           # API endpoints
│   │   ├── health.py
│   │   ├── members.py
│   │   ├── tithes.py
│   │   ├── cora.py
│   │   ├── service.py
│   │   ├── blessings.py
│   │   ├── reports.py
│   │   ├── audit.py
│   │   └── capacity.py
│   └── services/         # Business logic
│       ├── audit_service.py
│       ├── cora_service.py
│       ├── email_service.py
│       └── stripe_service.py
├── worker/
│   ├── celery_app.py     # Celery configuration
│   └── tasks.py          # Background tasks
├── migrations/
│   └── 001_initial_schema.sql
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🧪 Testing

```bash
# Run tests
docker-compose exec app pytest tests/ -v

# With coverage
docker-compose exec app pytest tests/ --cov=app --cov-report=html
```

## 📞 Support

- **API Docs**: https://whiterock.us/api/docs
- **Ministry**: https://whiterock.us
- **Email**: contact@whiterock.us

---

**WhiteRock Church Trust**  
508(c)(1)(A) Religious Organization  
🙏 Building community through faith and service



