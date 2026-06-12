# Helper Management - Droplet #26

**Autonomous Hiring, Payment, and Task Management**

## Overview

The Helper Management system automates contractor hiring and management. It posts jobs, screens candidates with AI, grants scoped access to credentials, processes payments in crypto or fiat, and tracks task completion.

## Features

- **Automated Job Posting** - Post to Upwork, Fiverr, crypto job boards
- **AI Screening** - Claude-powered candidate evaluation
- **Scoped Access** - Grant helpers limited credential access via Credentials Manager
- **Multi-Currency Payments** - Crypto (USDC, BTC, ETH), Upwork, PayPal
- **Task Tracking** - From posting → hiring → completion → payment
- **Performance Analytics** - Helper ratings, completion times, success rates

## Workflow

```
1. Create Task
   ↓
2. Post to Job Platforms (Upwork, crypto boards)
   ↓
3. Receive Applications
   ↓
4. AI Screens Candidates
   ↓
5. Hire Best Candidate
   ↓
6. Grant Scoped Credential Access
   ↓
7. Helper Completes Task
   ↓
8. Verify Completion
   ↓
9. Process Payment (Crypto/Fiat)
   ↓
10. Revoke Access
```

## Usage Examples

### Example: Hire Someone to Setup SendGrid

**From One Interface (Claude Code):**

```
You: "Setup SendGrid API for email outreach"

AI:
1. ✅ Creates task:
   Title: "Setup SendGrid API"
   Budget: $50
   Duration: 24 hours
   Credentials: SendGrid billing (ID: 5)

2. ✅ Posts to platforms:
   - Upwork: "$50 - Configure SendGrid API"
   - Crypto board: "0.001 BTC - SendGrid setup"

3. ✅ Receives 8 applications

4. ✅ AI screens candidates:
   - contractor_john: 0.92 score ✅
   - contractor_mary: 0.85 score ✅
   - contractor_spam: 0.15 score ❌

5. ✅ Hires contractor_john

6. ✅ Grants 24-hour access to SendGrid billing

7. ✅ John sets up API, tests it

8. ✅ Verifies API works

9. ✅ Pays $50 in USDC to John's wallet

10. ✅ Revokes access

Result: "SendGrid ready. API key stored in Credentials Manager."
```

### API Usage

**Create Task:**
```bash
curl -X POST http://localhost:8026/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Setup SendGrid API",
    "description": "Configure SendGrid for email campaigns. Need API key setup and testing.",
    "requirements": {
      "skills": ["api_integration", "sendgrid"],
      "experience_years": 1
    },
    "budget": 50.0,
    "payment_method": "crypto",
    "duration_hours": 24,
    "credential_ids": [5]
  }'

# Response:
{
  "id": 1,
  "title": "Setup SendGrid API",
  "budget": 50.0,
  "status": "draft",
  "created_at": "2025-01-14T10:00:00Z"
}
```

**Post Task to Platforms:**
```bash
curl -X POST http://localhost:8026/tasks/1/post
```

**View Applications:**
```bash
curl http://localhost:8026/applications?task_id=1

# Response:
[
  {
    "id": 1,
    "task_id": 1,
    "helper_name": "contractor_john",
    "platform": "upwork",
    "ai_score": 0.92,
    "ai_reasoning": "Strong SendGrid experience, realistic timeline, competitive rate",
    "status": "pending"
  }
]
```

**Hire Helper:**
```bash
curl -X POST http://localhost:8026/hire \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": 1,
    "application_id": 1
  }'

# Response:
{
  "status": "hired",
  "helper_id": 1,
  "helper_name": "contractor_john",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "message": "Helper hired and access granted"
}
```

**Pay Helper:**
```bash
curl -X POST http://localhost:8026/payments \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": 1,
    "amount": 50.0,
    "payment_method": "crypto"
  }'

# Response:
{
  "status": "paid",
  "transaction_id": "0xabc123...",
  "amount": 50.0,
  "total": 50.50
}
```

## Integration with Business OS

### Credentials Manager Integration

```python
# Helper Management grants access
POST /hire
→ Calls Credentials Manager: POST /tokens
→ Returns scoped token to helper
→ Helper can access only SendGrid billing

# After task completion
POST /payments
→ Processes payment
→ Calls Credentials Manager: DELETE /tokens/{id}
→ Access revoked
```

### Payment Processing

**Crypto Payments (Preferred):**
- USDC on Ethereum
- Bitcoin
- ETH
- Fee: ~$0.50 gas
- Settlement: 10-30 seconds

**Fiat Payments:**
- Upwork (3% fee, 2-3 day settlement)
- PayPal (2.9% + $0.30 fee)

## AI Screening

Uses Claude to evaluate candidates:

```
Input:
- Task description
- Requirements (skills, experience)
- Candidate application (cover letter, rate, timeline)

Claude Analyzes:
- Qualifications match
- Red flags (spam, unrealistic)
- Rate reasonableness
- Timeline feasibility

Output:
{
  "score": 0.92,
  "reasoning": "Strong experience, realistic timeline",
  "recommendation": "hire",
  "red_flags": [],
  "strengths": ["5+ years experience", "good reviews"]
}

Auto-Decision:
- Score >= 0.8: Auto-accept
- Score < 0.3: Auto-reject
- Score 0.3-0.8: Manual review
```

## Cost Optimization

### Helper Costs by Region

```
Philippines:    $5-15/hour  (English, skilled)
India:          $3-10/hour  (Technical work)
Eastern Europe: $15-30/hour (Development)
Latin America:  $10-25/hour (Customer support)
USA:            $30-100/hour (Specialized)
```

### Payment Method Comparison

```
Crypto (USDC):
- Fee: $0.50 flat
- Settlement: Instant
- Global: Yes
- Reversible: No

Upwork:
- Fee: 3% ($1.50 on $50)
- Settlement: 2-3 days
- Escrow: Yes
- Dispute resolution: Yes

PayPal:
- Fee: 2.9% + $0.30 ($1.75 on $50)
- Settlement: Instant
- Reversible: Yes (chargebacks)
```

### When to Use Each

**Crypto:**
- Small tasks ($10-100)
- International helpers
- Speed critical
- No disputes expected

**Upwork:**
- Large tasks (>$100)
- Need escrow protection
- Dispute risk
- Helper prefers fiat

## Setup

```bash
cd /Users/jamessunheart/Development/agents/services/helper-management

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys

# Setup database
createdb helpers

# Start service
uvicorn app.main:app --port 8026
```

## Files

```
helper-management/
├── app/
│   ├── __init__.py              # Service metadata
│   ├── config.py                # Configuration
│   ├── models.py                # Data models
│   ├── database.py              # Database connection
│   ├── ai_screening.py          # Claude-powered screening
│   ├── payment_processor.py     # Crypto/fiat payments
│   ├── credentials_client.py    # Credentials Manager client
│   └── main.py                  # FastAPI application
├── requirements.txt             # Dependencies
├── .env.example                 # Configuration template
└── README.md                    # This file
```

---

**Status:** Ready for deployment
**Version:** 1.0.0
**Droplet ID:** 26
**Port:** 8026

🤝 Autonomous Workforce Management
