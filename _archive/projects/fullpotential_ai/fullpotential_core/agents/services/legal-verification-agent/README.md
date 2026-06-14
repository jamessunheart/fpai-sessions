# legal-verification-agent

**Status:** 🚀 BUILD COMPLETE - READY FOR TESTING
**Progress:** SPECS ✅ | BUILD ✅ | README ✅ | PRODUCTION ⏳
**Last Updated:** 2025-11-15
**Port:** 8010

---

## Overview

AI-assisted legal compliance verification and attorney delegation system.

**Purpose:** Performs preliminary AI analysis of content to identify potential legal compliance issues, facilitates attorney review, and maintains precedent database for consistency.

**⚠️ CRITICAL:** This system does NOT provide legal advice. It performs AI-powered risk assessment only.

---

## Quick Start

```bash
# Navigate to BUILD directory
cd BUILD

# Create .env file
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn src.main:app --host 0.0.0.0 --port 8010 --reload

# Visit http://localhost:8010/docs for API documentation
```

---

## Testing

```bash
cd BUILD

# Run all tests
pytest tests/ -v

# Run without AI integration tests (no API key needed)
pytest tests/ -v -k "not real_api"

# Run specific test
pytest tests/test_basic.py::test_health_check -v
```

---

## API Endpoints

### Verification
- **POST /verify/content** - Analyze content for compliance
- **POST /verify/batch** - Batch verification
- **GET /verify/{id}** - Get specific verification

### Attorney Delegation
- **POST /attorney/task** - Create attorney review task
- **GET /attorney/tasks** - List attorney tasks
- **POST /attorney/tasks/{id}/respond** - Attorney provides response
- **GET /attorney/precedents** - View attorney decisions

### Reporting
- **GET /reports/compliance/{service}** - Compliance report
- **GET /reports/history** - Verification history

### System
- **GET /health** - Health check
- **GET /capabilities** - UDC capabilities
- **GET /docs** - OpenAPI documentation

---

## Usage Examples

### Verify Content

```bash
curl -X POST http://localhost:8010/verify/content \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "html",
    "content": "<p>Your content here...</p>",
    "source_service": "church-guidance-ministry",
    "context": "landing_page"
  }'
```

### Create Attorney Task

```bash
curl -X POST http://localhost:8010/attorney/task \
  -H "Content-Type: application/json" \
  -d '{
    "verification_id": "your-verification-id",
    "urgency": "high",
    "review_type": "content_review",
    "description": "Need attorney review of disclaimer",
    "specific_questions": ["Is this disclaimer sufficient?"]
  }'
```

### Attorney Response

```bash
curl -X POST http://localhost:8010/attorney/tasks/{task_id}/respond \
  -H "Content-Type: application/json" \
  -d '{
    "attorney_name": "Jane Doe, Esq.",
    "attorney_bar_number": "CA-12345",
    "decision": "approved",
    "comments": "Content is compliant",
    "precedent_note": "Educational content with disclaimers OK"
  }'
```

---

## Features

### ✅ AI Verification
- Analyzes content for legal compliance risks
- Identifies unauthorized practice of law
- Checks for proper disclaimers
- Detects overly specific advice
- Provides confidence scores and reasoning

### ✅ Attorney Delegation
- Creates structured attorney review tasks
- Tracks task status and urgency
- Stores attorney decisions
- Builds precedent database

### ✅ Compliance Reporting
- Service-level compliance reports
- Risk distribution analysis
- Verification history tracking
- Attorney task monitoring

### ✅ Learning System
- Stores attorney decisions as precedents
- Uses past decisions for consistency
- Reduces false positives over time

---

## Integration

### Church Guidance Ministry

This service integrates with church-guidance-ministry to verify content compliance:

```python
import httpx

# Verify a page
response = httpx.post("http://localhost:8010/verify/content", json={
    "content_type": "html",
    "content": page_html,
    "source_service": "church-guidance-ministry",
    "context": "landing_page"
})

verification = response.json()

if verification["attorney_escalation_needed"]:
    # Create attorney task
    task_response = httpx.post("http://localhost:8010/attorney/task", json={
        "verification_id": verification["verification_id"],
        "urgency": "high",
        "review_type": "content_review",
        "description": "High risk content needs attorney review"
    })
```

---

## Architecture

```
legal-verification-agent/
├── BUILD/
│   ├── src/
│   │   ├── main.py                    # FastAPI application
│   │   ├── models/
│   │   │   └── schemas.py             # Pydantic models
│   │   └── services/
│   │       ├── verification_service.py # AI verification
│   │       └── attorney_service.py     # Attorney delegation
│   ├── tests/
│   │   └── test_basic.py              # Test suite
│   ├── requirements.txt
│   └── .env.example
├── SPECS/
│   └── SPECS.md                       # Complete specifications
├── PRODUCTION/
│   └── (deployment artifacts)
└── README.md                          # This file
```

---

## Compliance Notes

### What This System Does
- ✅ AI-powered preliminary risk assessment
- ✅ Identifies areas requiring attorney review
- ✅ Facilitates attorney delegation
- ✅ Documents attorney decisions
- ✅ Maintains consistency via precedents

### What This System Does NOT Do
- ❌ Provide legal advice
- ❌ Replace attorney review
- ❌ Make final legal determinations
- ❌ Create attorney-client relationships
- ❌ Guarantee compliance or accuracy

**All AI findings include:**
- Clear statement this is AI analysis, not legal advice
- Recommendation to consult attorney
- Confidence scores indicating uncertainty
- Escalation path to actual attorney

---

## Development Status

### Phase 1: SPECS ✅ COMPLETE
- [x] Purpose and requirements defined
- [x] API endpoints specified
- [x] Data models designed
- [x] Success criteria established
- [x] Legal boundaries documented

### Phase 2: BUILD ✅ COMPLETE
- [x] FastAPI application
- [x] AI verification service (Claude integration)
- [x] Attorney delegation service
- [x] All API endpoints implemented
- [x] Pydantic models
- [x] Test suite created

### Phase 3: README ✅ COMPLETE
- [x] Quick start guide
- [x] API documentation
- [x] Usage examples
- [x] Integration guide

### Phase 4: PRODUCTION ⏳ PENDING
- [ ] Deploy to server (port 8010)
- [ ] Configure environment variables
- [ ] Run tests in production
- [ ] Integrate with church-guidance-ministry
- [ ] Set up attorney notification system

---

## Next Steps

1. **Test Locally** - Run pytest and manual API tests
2. **Deploy to Production** - Port 8010 on server
3. **Integrate** - Connect to church-guidance-ministry
4. **Attorney Setup** - Configure attorney notification workflow
5. **Monitor** - Track verifications and attorney tasks

---

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_key_here

# Optional
PORT=8010
DEBUG=False
```

---

**Assembly Line Status:** SPECS ✅ → BUILD ✅ → README ✅ → PRODUCTION ⏳

**Ready for:** Local testing and production deployment
