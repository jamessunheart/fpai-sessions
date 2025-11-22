# legal-verification-agent - SPECS

**Created:** 2025-11-15
**Status:** BUILD COMPLETE (Port 8010)

---

## Purpose

AI-assisted legal compliance verification and attorney delegation system. Performs preliminary AI analysis of content to identify potential legal compliance issues, facilitates attorney review, and maintains precedent database for consistency. DOES NOT provide legal advice - AI-powered risk assessment only.

---

## Requirements

### Functional Requirements
- [ ] Analyze content for legal compliance using Claude AI
- [ ] Identify unauthorized practice of law risks
- [ ] Check for proper disclaimers
- [ ] Detect overly specific advice
- [ ] Provide confidence scores and reasoning
- [ ] Create structured attorney review tasks
- [ ] Track attorney task status and urgency
- [ ] Store attorney decisions as precedents
- [ ] Build precedent database for consistency
- [ ] Batch verification support
- [ ] Service-level compliance reports
- [ ] Verification history tracking
- [ ] Risk distribution analysis

### Non-Functional Requirements
- [ ] Performance: Verification < 10 seconds per content piece
- [ ] Reliability: Graceful fallback if Claude API unavailable
- [ ] Clarity: All findings clearly labeled as AI analysis, not legal advice
- [ ] Escalation: High-risk items flagged for attorney review
- [ ] Consistency: Use precedents to reduce false positives over time

---

## API Specs

### Endpoints

**POST /verify/content**
- **Purpose:** Analyze content for compliance
- **Input:** content_type (html/text/markdown), content, source_service, context
- **Output:** verification_id, compliance_score, risk_level, issues, attorney_escalation_needed
- **Success:** 201 Created
- **Errors:** 400 if invalid input, 500 if AI fails

**POST /verify/batch**
- **Purpose:** Batch verification of multiple content pieces
- **Input:** Array of content items
- **Output:** Array of verification results
- **Success:** 201 Created
- **Errors:** 400 if invalid input

**GET /verify/{id}**
- **Purpose:** Get specific verification result
- **Input:** verification ID
- **Output:** Full verification details
- **Success:** 200 OK
- **Errors:** 404 if not found

**POST /attorney/task**
- **Purpose:** Create attorney review task
- **Input:** verification_id, urgency, review_type, description, specific_questions
- **Output:** task_id, status, created_at
- **Success:** 201 Created
- **Errors:** 400 if invalid input, 404 if verification not found

**GET /attorney/tasks**
- **Purpose:** List attorney tasks
- **Input:** Optional filters (status, urgency, service)
- **Output:** Array of attorney tasks
- **Success:** 200 OK
- **Errors:** 500 if query fails

**POST /attorney/tasks/{id}/respond**
- **Purpose:** Attorney provides response to task
- **Input:** task_id, attorney_name, attorney_bar_number, decision, comments, precedent_note
- **Output:** Updated task with decision
- **Success:** 200 OK
- **Errors:** 404 if not found

**GET /attorney/precedents**
- **Purpose:** View attorney decision precedents
- **Input:** Optional filters (service, decision_type)
- **Output:** Array of precedent decisions
- **Success:** 200 OK
- **Errors:** 500 if query fails

**GET /reports/compliance/{service}**
- **Purpose:** Compliance report for a service
- **Input:** service name
- **Output:** Verification summary, risk distribution, common issues
- **Success:** 200 OK
- **Errors:** 404 if service not found

**GET /reports/history**
- **Purpose:** Verification history
- **Input:** Optional filters (date_range, service, risk_level)
- **Output:** Array of verification records
- **Success:** 200 OK
- **Errors:** 500 if query fails

**GET /health**
- **Purpose:** UDC health check
- **Input:** None
- **Output:** {"status": "healthy", "service": "legal-verification-agent", "ai_status": "connected"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

**GET /capabilities**
- **Purpose:** UDC capabilities endpoint
- **Input:** None
- **Output:** Supported content types, risk levels, features
- **Success:** 200 OK
- **Errors:** 500 if unavailable

### Data Models

```python
class VerificationRequest:
    content_type: str  # "html", "text", "markdown"
    content: str
    source_service: str  # "church-guidance-ministry", etc.
    context: str  # "landing_page", "email", "documentation"

class VerificationResult:
    verification_id: str
    content_type: str
    source_service: str
    context: str
    compliance_score: float  # 0-1
    risk_level: str  # "low", "medium", "high"
    issues: List[ComplianceIssue]
    recommendations: List[str]
    attorney_escalation_needed: bool
    confidence: float  # 0-1
    reasoning: str
    verified_at: datetime

class ComplianceIssue:
    issue_type: str  # "unauthorized_practice", "missing_disclaimer", "overly_specific"
    severity: str  # "critical", "important", "minor"
    description: str
    location: Optional[str]
    suggested_fix: str
    precedent_reference: Optional[str]

class AttorneyTask:
    task_id: str
    verification_id: str
    urgency: str  # "low", "medium", "high"
    review_type: str  # "content_review", "precedent_setting", "emergency"
    description: str
    specific_questions: List[str]
    status: str  # "pending", "in_progress", "completed"
    assigned_to: Optional[str]
    created_at: datetime
    due_date: datetime
    completed_at: Optional[datetime]

class AttorneyResponse:
    task_id: str
    attorney_name: str
    attorney_bar_number: str
    decision: str  # "approved", "revise", "reject"
    comments: str
    precedent_note: Optional[str]
    responded_at: datetime

class Precedent:
    precedent_id: str
    service: str
    content_type: str
    issue_type: str
    attorney_decision: str
    reasoning: str
    applicable_contexts: List[str]
    created_at: datetime
    created_by: str
```

---

## Dependencies

### External Services
- Claude API (Anthropic): AI content analysis

### APIs Required
- Anthropic Claude API: Content verification

### Data Sources
- Content from various services (church-guidance-ministry, etc.)
- Attorney precedent database

---

## Success Criteria

How do we know this works?

- [ ] AI verification identifies common compliance issues
- [ ] High-risk content flagged for attorney review
- [ ] Attorney tasks created with all necessary context
- [ ] Attorney responses stored as precedents
- [ ] Precedents used to improve future verifications
- [ ] Compliance reports generated accurately
- [ ] All findings clearly labeled as AI analysis, not legal advice
- [ ] At least 80% of low-risk content passes AI verification
- [ ] At least 1 complete workflow: verify → escalate → attorney review → precedent

---

## Legal Boundaries

### What This System DOES
- AI-powered preliminary risk assessment
- Identifies areas requiring attorney review
- Facilitates attorney delegation
- Documents attorney decisions
- Maintains consistency via precedents

### What This System DOES NOT Do
- Provide legal advice
- Replace attorney review
- Make final legal determinations
- Create attorney-client relationships
- Guarantee compliance or accuracy

**All AI findings include:**
- Clear statement this is AI analysis, not legal advice
- Recommendation to consult attorney
- Confidence scores indicating uncertainty
- Escalation path to actual attorney

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8010
- **Resource limits:**
  - Memory: 256MB max
  - CPU: 0.5 cores
  - Storage: 500MB for database
- **Response time:** < 10 seconds per verification
- **Claude API:** Uses claude-sonnet-4-5-20250929
- **Database:** SQLite (dev) or PostgreSQL (prod)

---

## Integration Example

**Church Guidance Ministry Integration:**
```python
import httpx

# Verify landing page content
response = httpx.post(
    "http://legal-verification-agent:8010/verify/content",
    json={
        "content_type": "html",
        "content": landing_page_html,
        "source_service": "church-guidance-ministry",
        "context": "landing_page"
    }
)

verification = response.json()

if verification["attorney_escalation_needed"]:
    # Create attorney task
    httpx.post(
        "http://legal-verification-agent:8010/attorney/task",
        json={
            "verification_id": verification["verification_id"],
            "urgency": "high",
            "review_type": "content_review",
            "description": "High risk content needs attorney review"
        }
    )
```

---

**Next Step:** Integrate with church-guidance-ministry, set up attorney notification workflow
