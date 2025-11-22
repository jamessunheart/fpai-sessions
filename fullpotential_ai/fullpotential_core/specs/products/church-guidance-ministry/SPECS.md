# church-guidance-ministry - SPECS

**Created:** 2025-11-15
**Status:** Planning

---

## Purpose

Educational ministry providing guidance and resources for individuals interested in forming 508(c)(1)(A) churches. Service focuses on education, documentation support via AI, and clear legal boundaries - NOT legal advice or formation services.

---

## Requirements

### Functional Requirements
- [ ] Landing page with educational content about 508(c)(1)(A) churches
- [ ] Intake form for collecting user information and needs assessment
- [ ] AI-powered compliance documentation generator (educational templates)
- [ ] Clear disclaimer system throughout (educational ministry, not legal service)
- [ ] Payment integration for guidance packages ($2,500 educational package)
- [ ] Document delivery system (email PDF bundles)
- [ ] Follow-up consultation booking (Calendly integration)
- [ ] Upsell pathway for ongoing compliance guidance ($300/month educational support)

### Non-Functional Requirements
- [ ] Performance: Page load < 2 seconds, form submission < 1 second
- [ ] Security: SSL/TLS encryption, secure payment processing (Stripe), no storage of payment data
- [ ] Compliance: Clear educational disclaimers, liability boundaries on every page, attorney review of all user-facing content

---

## API Specs

### Endpoints

**GET /**
- **Purpose:** Landing page - educational content about 508(c)(1)(A) churches
- **Input:** None
- **Output:** HTML page with educational content, CTA for intake form
- **Success:** 200 OK
- **Errors:** 500 if template fails

**GET /intake**
- **Purpose:** Intake form page for needs assessment
- **Input:** None
- **Output:** HTML form
- **Success:** 200 OK
- **Errors:** 500 if template fails

**POST /intake**
- **Purpose:** Submit intake form, trigger AI document generation
- **Input:** Form data (name, email, state, mission, timeline, package selection)
- **Output:** Confirmation page + trigger email with documents
- **Success:** 201 Created, redirect to /thank-you
- **Errors:** 400 if validation fails, 500 if processing fails

**GET /payment/{package_type}**
- **Purpose:** Payment page (Stripe integration)
- **Input:** package_type (guidance-package or ongoing-support)
- **Output:** Stripe checkout session
- **Success:** 302 Redirect to Stripe
- **Errors:** 400 if invalid package, 500 if Stripe fails

**POST /webhook/stripe**
- **Purpose:** Handle Stripe payment confirmations
- **Input:** Stripe webhook event
- **Output:** Process payment, trigger document generation/delivery
- **Success:** 200 OK
- **Errors:** 400 if invalid signature, 500 if processing fails

**GET /health**
- **Purpose:** Health check for monitoring
- **Input:** None
- **Output:** {"status": "healthy", "service": "church-guidance-ministry"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

### Data Models

```python
class IntakeSubmission:
    name: str
    email: str
    state: str  # US state for compliance considerations
    mission: str  # Religious/philosophical mission statement
    timeline: str  # When they want to form
    package: str  # "guidance-package" or "ongoing-support"
    phone: Optional[str]
    submitted_at: datetime

class GuidancePackage:
    package_id: str
    user_email: str
    documents: List[str]  # List of generated document paths
    status: str  # "pending", "generated", "delivered"
    payment_status: str  # "unpaid", "paid"
    created_at: datetime
    delivered_at: Optional[datetime]
```

---

## Dependencies

### External Services
- Stripe: Payment processing for guidance packages
- Calendly: Consultation booking integration
- Email service (SendGrid or similar): Document delivery and communications

### APIs Required
- Anthropic Claude API: AI-powered document generation and compliance assistance
- Stripe API: Payment processing, webhook handling
- Calendly API: Embedded booking widget

### Data Sources
- 508(c)(1)(A) educational templates (pre-reviewed by legal)
- State-specific compliance guidelines database
- Document templates library

---

## Success Criteria

How do we know this droplet works?

- [ ] Landing page loads with educational content and disclaimers visible
- [ ] Intake form accepts and validates submissions
- [ ] AI generates educational documents based on intake (< 2 minutes)
- [ ] Stripe payment flow completes successfully (test mode)
- [ ] Documents delivered via email after payment confirmation
- [ ] All disclaimers present on every page (automated test)
- [ ] Health check endpoint returns 200 OK
- [ ] All tests pass (unit + integration)
- [ ] Deployed and accessible on production server
- [ ] Legal review completed on all user-facing content

---

## Compliance Notes

### Legal Considerations

**Service Type:** Educational ministry providing guidance and resources

**NOT Legal Services:** This service does NOT constitute legal advice, tax advice, or professional services requiring licensure. All content is educational in nature.

**Disclaimers Required on ALL Pages:**
```
EDUCATIONAL MINISTRY DISCLAIMER: This service provides educational
resources and guidance about 508(c)(1)(A) churches. This is NOT legal
advice. We are NOT attorneys. We do NOT form churches on your behalf.
We provide educational templates and guidance only. You are responsible
for ensuring compliance with all applicable laws. Consult with a
licensed attorney for legal advice specific to your situation.
```

**Attorney Review:** All templates, content, and user-facing materials must be reviewed by licensed attorney before production deployment.

**State Considerations:** Service available nationwide, but must include state-specific disclaimer variations where required by law.

### Liability Boundaries

**What This Service DOES Provide:**
- Educational content about 508(c)(1)(A) churches
- Template documents for educational purposes
- AI-assisted guidance for documentation (educational)
- Resources and checklists
- General information about compliance

**What This Service DOES NOT Provide:**
- Legal advice or representation
- Tax advice or tax preparation services
- Guaranteed outcomes or compliance assurance
- Filing services with government agencies
- Attorney-client relationship
- Professional services requiring licensure

**User Responsibility:**
Users acknowledge they are solely responsible for:
- Verifying accuracy of all documents
- Ensuring compliance with all applicable laws
- Consulting appropriate professionals (attorneys, CPAs, etc.)
- Filing any required government forms
- Maintaining ongoing compliance

### AI Compliance Support

**AI Role:** Educational documentation assistant

**How AI Assists:**
- Generates educational document templates based on user inputs
- Provides compliance checklists (educational purposes)
- Customizes generic templates with user-provided information
- Suggests best practices based on educational materials
- Creates drafts for user review and professional consultation

**What AI Does NOT Do:**
- Provide legal advice or opinions
- Replace attorney review
- Guarantee legal compliance
- Make legal determinations
- Establish attorney-client privilege
- Practice law

**Human Oversight:**
- All AI-generated content clearly marked as "AI-assisted educational draft"
- Users prompted to seek professional review
- Templates pre-reviewed by attorneys before AI customization
- AI operates within defined educational parameters only

### Record Keeping

- Maintain records of disclaimer acknowledgments
- Log all user interactions for quality assurance
- Retain copies of delivered educational materials
- Document version control for templates
- Track legal review dates for all content

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8003 (next available in sequence)
- **Resource limits:**
  - Memory: 512MB max
  - CPU: 1 core
  - Storage: 1GB for templates and logs
- **Response time:** < 2 seconds for page loads, < 30 seconds for document generation
- **Concurrent users:** Support 10+ simultaneous users
- **Uptime:** 99.9% target
- **SSL/TLS:** Required for all endpoints (production)
- **Environment:** Docker container deployment

---

## Build Timeline Estimate

- **Phase 1 (SPECS):** ✅ COMPLETE (30 minutes)
- **Phase 2 (BUILD):** 4-6 hours
  - Landing page + templates: 1 hour
  - Intake form + validation: 1 hour
  - AI document generation: 2 hours
  - Stripe integration: 1 hour
  - Email delivery: 1 hour
- **Phase 3 (README):** 30 minutes
- **Phase 4 (PRODUCTION):** 1 hour (deployment + testing)

**Total:** ~6-8 hours to production-ready

---

**Next Step:** ✅ SPECS COMPLETE - Ready for BUILD phase

⚡ Assembly Line: SPECS ✅ → BUILD ⏳ → README → PRODUCTION
