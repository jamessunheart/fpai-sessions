# Legal Verification Agent - SPECS

**Droplet ID:** TBD
**Service Name:** legal-verification-agent
**Port:** 8010
**Status:** 📋 SPECS Phase
**Created:** 2025-11-15
**Purpose:** AI-assisted legal verification and attorney delegation system

---

## 1. Purpose

The Legal Verification Agent is an **AI-powered compliance verification system** that:

1. **Reviews content** from other services (starting with church-guidance-ministry)
2. **Identifies legal risks** and compliance issues automatically
3. **Generates compliance reports** with specific findings
4. **Flags items for attorney review** when AI cannot determine safety
5. **Delegates to attorneys** through a structured task interface
6. **Tracks attorney feedback** and incorporates into future checks

**CRITICAL BOUNDARY:** This system does NOT provide legal advice. It:
- Performs preliminary AI risk assessment
- Identifies areas requiring attorney review
- Facilitates attorney delegation
- Documents attorney decisions for consistency

The AI acts as a **first-pass filter**, not a replacement for attorneys.

---

## 2. Functional Requirements

### FR-1: Content Analysis
- Accept content for review (text, HTML, templates, documents)
- Analyze for legal/educational boundary violations
- Check for unauthorized practice of law indicators
- Identify missing disclaimers or insufficient warnings
- Detect overly specific advice that resembles legal counsel

### FR-2: Risk Scoring
- Assign risk levels: LOW, MEDIUM, HIGH, CRITICAL
- Provide confidence scores (0-100%)
- Identify specific phrases/sections causing concern
- Explain reasoning for each flag

### FR-3: Compliance Reporting
- Generate structured compliance reports
- List all findings with severity levels
- Provide recommendations for fixes
- Include attorney escalation items
- Track report history and changes over time

### FR-4: Attorney Delegation Interface
- Create attorney review tasks with context
- Specify urgency and type of review needed
- Attach relevant content sections
- Track task status (pending/in-review/completed)
- Store attorney decisions as precedents

### FR-5: Multi-Session Coordination
- Work within existing coordination system
- Send compliance alerts to relevant sessions
- Allow attorneys to respond through system
- Broadcast compliance updates

### FR-6: Learning System
- Store attorney decisions
- Use past decisions to inform future checks
- Build compliance knowledge base
- Reduce false positives over time

---

## 3. Non-Functional Requirements

### NFR-1: Performance
- Content analysis: < 10 seconds for standard page
- Batch analysis: < 60 seconds for full site scan
- Report generation: < 5 seconds

### NFR-2: Security
- Secure API endpoints with authentication
- Encrypt attorney communications
- Audit log all legal reviews
- No storage of sensitive client data

### NFR-3: Reliability
- 99.9% uptime target
- Graceful degradation if AI API unavailable
- Queue system for async processing
- Retry logic for failed analyses

---

## 4. API Endpoints

### 4.1 Verification Endpoints

**POST /verify/content**
- **Purpose:** Analyze content for legal compliance
- **Input:**
  ```json
  {
    "content_type": "html|text|document",
    "content": "string",
    "source_service": "church-guidance-ministry",
    "context": "landing_page|disclaimer|template|etc"
  }
  ```
- **Output:**
  ```json
  {
    "verification_id": "uuid",
    "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
    "confidence": 0.95,
    "findings": [
      {
        "type": "unauthorized_practice_of_law|missing_disclaimer|overly_specific|etc",
        "severity": "LOW|MEDIUM|HIGH|CRITICAL",
        "location": "line 42, section 'services'",
        "excerpt": "problematic text snippet",
        "explanation": "why this is concerning",
        "recommendation": "how to fix it",
        "requires_attorney": true
      }
    ],
    "overall_assessment": "summary of compliance status",
    "attorney_escalation_needed": true,
    "timestamp": "2025-11-15T19:00:00Z"
  }
  ```

**POST /verify/batch**
- **Purpose:** Analyze multiple pieces of content
- **Input:** Array of content items
- **Output:** Array of verification results + summary report

**GET /verify/{verification_id}**
- **Purpose:** Retrieve specific verification result
- **Output:** Verification result object

### 4.2 Attorney Delegation Endpoints

**POST /attorney/task**
- **Purpose:** Create attorney review task
- **Input:**
  ```json
  {
    "verification_id": "uuid",
    "urgency": "low|medium|high|critical",
    "review_type": "content_review|legal_opinion|risk_assessment",
    "description": "what needs attorney review",
    "content_sections": ["section 1", "section 2"],
    "specific_questions": ["question 1", "question 2"],
    "deadline": "2025-11-20T00:00:00Z"
  }
  ```
- **Output:**
  ```json
  {
    "task_id": "uuid",
    "status": "pending",
    "created_at": "timestamp",
    "attorney_assigned": null,
    "estimated_review_time": "2-4 hours"
  }
  ```

**GET /attorney/tasks**
- **Purpose:** List all attorney tasks
- **Query Params:** status, urgency, date_range
- **Output:** Array of tasks

**POST /attorney/tasks/{task_id}/respond**
- **Purpose:** Attorney provides response/decision
- **Input:**
  ```json
  {
    "attorney_name": "string",
    "attorney_bar_number": "string",
    "decision": "approved|rejected|needs_revision",
    "comments": "detailed attorney feedback",
    "specific_changes_required": ["change 1", "change 2"],
    "precedent_note": "can be used for future similar cases"
  }
  ```
- **Output:** Updated task with attorney decision

### 4.3 Reporting Endpoints

**GET /reports/compliance/{service_name}**
- **Purpose:** Get compliance report for a service
- **Output:** Comprehensive compliance status

**GET /reports/history**
- **Purpose:** View verification history over time
- **Output:** Timeline of verifications and changes

**GET /reports/attorney-precedents**
- **Purpose:** View attorney decisions for consistency
- **Output:** Searchable precedent database

### 4.4 Integration Endpoints

**POST /integrate/church-guidance**
- **Purpose:** Trigger verification of church-guidance-ministry
- **Output:** Verification results for entire service

**GET /health**
- **Purpose:** Health check
- **Output:** Service status

**GET /capabilities**
- **Purpose:** UDC compliance
- **Output:** Service capabilities

---

## 5. Technical Specifications

### 5.1 Technology Stack
- **Framework:** FastAPI (Python)
- **AI Model:** Claude 3.5 Sonnet (via Anthropic API)
- **Database:** SQLite (for verification history, attorney decisions)
- **Queue:** In-memory for MVP, Redis for production
- **Integration:** REST API + coordination system

### 5.2 AI Prompt Engineering
- **System Prompt:** Specialized legal risk assessment instructions
- **Context:** Legal compliance boundaries, educational vs advice
- **Few-shot Examples:** Include attorney-approved/rejected samples
- **Chain of Thought:** Require AI to explain reasoning

### 5.3 Data Models

**Verification**
- id, timestamp, content_type, source_service
- risk_level, confidence, findings (JSON)
- attorney_escalation_needed, attorney_task_id

**Finding**
- id, verification_id, type, severity
- location, excerpt, explanation, recommendation
- requires_attorney, attorney_reviewed

**AttorneyTask**
- id, verification_id, urgency, review_type
- description, content_sections, questions
- status, attorney_name, attorney_response
- created_at, completed_at

**Precedent**
- id, task_id, scenario_description
- attorney_decision, reasoning
- reusable, tags

---

## 6. Success Criteria

1. ✅ **Accurate Risk Detection**
   - Catches 95%+ of clear violations (missing disclaimers, etc.)
   - False positive rate < 20%
   - Explains reasoning clearly

2. ✅ **Attorney Delegation Works**
   - Tasks created with complete context
   - Attorney can respond through system
   - Responses stored and reusable

3. ✅ **Integration with Church Guidance**
   - Can verify all church-guidance-ministry pages
   - Identifies known compliance items (disclaimers)
   - Flags areas needing attorney review

4. ✅ **Learning Over Time**
   - Incorporates attorney decisions
   - Reduces repeat escalations for same issues
   - Builds precedent database

5. ✅ **Performance**
   - Single page analysis < 10 seconds
   - Batch analysis reasonable time
   - No blocking delays

6. ✅ **User Experience**
   - Clear, actionable reports
   - Explains findings in plain language
   - Easy to understand severity levels

7. ✅ **Multi-Session Support**
   - Works with coordination system
   - Sessions can request verifications
   - Broadcasts compliance updates

8. ✅ **Attorney Interface Usable**
   - Attorney can access without technical knowledge
   - Clear review tasks with context
   - Simple response mechanism

---

## 7. Compliance Notes

### Legal Boundaries

**This System Does NOT:**
- Provide legal advice
- Replace attorney review
- Make final legal determinations
- Create attorney-client relationships
- Guarantee compliance or accuracy

**This System DOES:**
- Perform preliminary AI analysis
- Identify potential risk areas
- Facilitate attorney delegation
- Document attorney decisions
- Improve consistency over time

**All AI findings must include:**
- Clear statement this is AI analysis, not legal advice
- Recommendation to consult attorney for final determination
- Confidence scores to indicate uncertainty
- Escalation path to actual attorney

### Attorney Role

The attorney delegation system:
- Provides structured way to request attorney review
- Does NOT replace traditional attorney consultation
- Facilitates efficient use of attorney time
- Documents decisions for organizational consistency
- Attorneys have final say on all legal matters

---

## 8. Future Enhancements

- **Phase 2:** Real-time verification during content creation
- **Phase 3:** Integration with more services beyond church guidance
- **Phase 4:** Multi-attorney workflow (specialist routing)
- **Phase 5:** Automated fix suggestions with attorney approval
- **Phase 6:** Public API for other organizations

---

## 9. Dependencies

- Anthropic API (Claude 3.5 Sonnet)
- FastAPI framework
- Coordination system (for multi-session)
- Church Guidance Ministry service (first integration)

---

## 10. Risk Assessment

**High Risks:**
- AI giving advice instead of analysis → Mitigate with careful prompting
- Users relying on AI vs attorney → Mitigate with strong disclaimers
- False sense of security → Mitigate with confidence scores

**Medium Risks:**
- Attorney tasks ignored/delayed → Mitigate with urgency tracking
- Integration complexity → Mitigate with clear APIs

**Low Risks:**
- Performance issues → Mitigate with async processing
- Data storage → Mitigate with minimal PII storage

---

**Assembly Line Status:** SPECS ✅ → BUILD ⏳ → README ⏳ → PRODUCTION ⏳

**Next Step:** BUILD phase - Implement the verification agent
