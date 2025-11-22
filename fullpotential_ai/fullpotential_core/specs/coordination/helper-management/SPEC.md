# helper-management - SPECS

**Created:** 2025-11-15
**Status:** Production Ready (Droplet #26)
**Port:** 8026

---

## Purpose

Autonomous hiring, payment, and task management for contractors. Automates job posting, AI-powered screening, scoped credential access, multi-currency payments, and task tracking from posting through completion.

---

## Requirements

### Functional Requirements
- [ ] Create and post tasks to job platforms (Upwork, Fiverr, crypto boards)
- [ ] Receive and store applications
- [ ] AI-powered candidate screening using Claude
- [ ] Hire candidates and grant scoped credential access
- [ ] Track task status from creation to completion
- [ ] Process payments in crypto (USDC, BTC, ETH) or fiat (Upwork, PayPal)
- [ ] Integrate with credentials-manager for access tokens
- [ ] Auto-revoke credentials after task completion
- [ ] Performance analytics (ratings, completion times, success rates)
- [ ] Helper reputation system

### Non-Functional Requirements
- [ ] Performance: AI screening < 10 seconds per application
- [ ] Security: No direct credential exposure, scoped tokens only
- [ ] Payment processing: < 1 minute for crypto, respect platform SLAs for fiat
- [ ] Reliability: Retry failed payments up to 3 times
- [ ] Scalability: Support 100+ concurrent tasks

---

## API Specs

### Endpoints

**POST /tasks**
- **Purpose:** Create new task
- **Input:** title, description, requirements, budget, payment_method, duration_hours, credential_ids
- **Output:** Task ID, status, created_at
- **Success:** 201 Created
- **Errors:** 400 if validation fails

**POST /tasks/{id}/post**
- **Purpose:** Post task to job platforms
- **Input:** task ID, platforms (array: upwork, fiverr, crypto_boards)
- **Output:** Posting confirmation with platform-specific URLs
- **Success:** 202 Accepted
- **Errors:** 404 if task not found, 400 if already posted

**GET /applications**
- **Purpose:** List applications for tasks
- **Input:** Optional: task_id, status, min_ai_score
- **Output:** Array of applications with AI scores
- **Success:** 200 OK
- **Errors:** 500 if query fails

**POST /applications/{id}/screen**
- **Purpose:** AI screen a single application
- **Input:** application ID
- **Output:** AI score, reasoning, recommendation
- **Success:** 200 OK
- **Errors:** 404 if not found, 500 if AI fails

**POST /hire**
- **Purpose:** Hire helper for a task
- **Input:** task_id, application_id
- **Output:** Helper ID, access_token (from credentials-manager), confirmation
- **Success:** 201 Created
- **Errors:** 404 if not found, 409 if already hired

**POST /tasks/{id}/complete**
- **Purpose:** Mark task as complete and trigger payment
- **Input:** task ID, quality_rating, completion_notes
- **Output:** Payment transaction info
- **Success:** 200 OK
- **Errors:** 404 if not found, 400 if not ready for completion

**POST /payments**
- **Purpose:** Process payment to helper
- **Input:** task_id, amount, payment_method (crypto, upwork, paypal)
- **Output:** Transaction ID, status
- **Success:** 202 Accepted
- **Errors:** 400 if invalid input, 402 if insufficient funds

**GET /helpers/{id}/performance**
- **Purpose:** Get helper performance analytics
- **Input:** helper ID
- **Output:** Ratings, completion rate, average time, skills
- **Success:** 200 OK
- **Errors:** 404 if not found

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "active_tasks": 5, "ai_screening": "active"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

### Data Models

```python
class Task:
    id: int
    title: str
    description: str
    requirements: dict  # skills, experience_years
    budget: float
    payment_method: str  # "crypto", "upwork", "paypal"
    duration_hours: int
    credential_ids: List[int]
    status: str  # "draft", "posted", "hired", "in_progress", "completed", "cancelled"
    created_at: datetime
    posted_at: Optional[datetime]
    completed_at: Optional[datetime]

class Application:
    id: int
    task_id: int
    helper_name: str
    helper_email: str
    platform: str  # "upwork", "fiverr", "crypto_board"
    cover_letter: str
    proposed_rate: float
    proposed_timeline_hours: int
    ai_score: Optional[float]  # 0-1
    ai_reasoning: Optional[str]
    ai_recommendation: Optional[str]  # "hire", "maybe", "pass"
    status: str  # "pending", "screened", "hired", "rejected"
    submitted_at: datetime

class Helper:
    id: int
    name: str
    email: str
    platform: str
    skills: List[str]
    experience_years: int
    rating: float  # Average across all tasks
    tasks_completed: int
    tasks_failed: int
    average_completion_time_hours: float
    total_earned: float
    created_at: datetime

class Payment:
    id: int
    task_id: int
    helper_id: int
    amount: float
    payment_method: str
    transaction_id: str
    status: str  # "pending", "processing", "completed", "failed"
    created_at: datetime
    completed_at: Optional[datetime]
    error: Optional[str]

class AIScreeningResult:
    application_id: int
    score: float  # 0-1
    reasoning: str
    recommendation: str  # "hire", "maybe", "pass"
    red_flags: List[str]
    strengths: List[str]
    screened_at: datetime
```

---

## Dependencies

### External Services
- Credentials Manager (Port 8025): Scoped access token generation and management
- Upwork API: Job posting and fiat payments
- PayPal API: Alternative fiat payments
- Crypto wallet: USDC, BTC, ETH payments
- Claude API (Anthropic): AI candidate screening

### APIs Required
- Credentials Manager API: POST /tokens, DELETE /tokens/{id}
- Claude API: Application screening
- Upwork API: Job posting, escrow, payments
- PayPal API: Payment processing
- Web3 RPC: Crypto payment processing

### Data Sources
- PostgreSQL: Tasks, applications, helpers, payments
- Blockchain: Crypto transaction confirmation

---

## Success Criteria

How do we know this works?

- [ ] Tasks created and posted to job platforms
- [ ] Applications received and stored
- [ ] AI screening provides useful scores and recommendations
- [ ] Hire workflow grants correct credential access
- [ ] Payments process successfully in both crypto and fiat
- [ ] Credentials automatically revoked after task completion
- [ ] Helper performance analytics tracked accurately
- [ ] Auto-decisions (score >= 0.8 hire, < 0.3 pass) work correctly
- [ ] At least 1 complete workflow: post → hire → complete → pay

---

## AI Screening Logic

**Claude evaluates:**
- Qualifications match (experience, skills)
- Red flags (spam, unrealistic claims, poor communication)
- Rate reasonableness (compared to market, budget)
- Timeline feasibility (realistic for task scope)

**Output:**
```python
{
    "score": 0.92,  # 0-1
    "reasoning": "Strong SendGrid experience, realistic timeline, competitive rate",
    "recommendation": "hire",  # "hire", "maybe", "pass"
    "red_flags": [],
    "strengths": ["5+ years experience", "good reviews", "clear communication"]
}
```

**Auto-decisions:**
- Score >= 0.8: Auto-accept (if budget allows)
- Score < 0.3: Auto-reject
- Score 0.3-0.8: Flag for manual review

---

## Payment Processing

### Crypto Payments (Preferred)
**Supported:**
- USDC on Ethereum/Arbitrum
- Bitcoin
- ETH

**Pros:**
- Low fees (~$0.50 gas)
- Instant settlement (10-30 seconds)
- Global, no platform restrictions
- No chargebacks

**Cons:**
- Requires helper crypto wallet
- Price volatility (use stablecoins)

### Fiat Payments

**Upwork:**
- Fee: 3% platform fee
- Settlement: 2-3 days
- Escrow protection
- Dispute resolution

**PayPal:**
- Fee: 2.9% + $0.30
- Settlement: Instant
- Chargeback risk

---

## Cost Optimization

**Helper costs by region:**
- Philippines: $5-15/hour (English, skilled)
- India: $3-10/hour (Technical work)
- Eastern Europe: $15-30/hour (Development)
- Latin America: $10-25/hour (Customer support)
- USA: $30-100/hour (Specialized)

**When to use crypto vs fiat:**
- Small tasks ($10-100): Crypto (better fees)
- Large tasks (>$100): Upwork (escrow protection)
- International: Crypto (no platform restrictions)
- Dispute risk: Upwork (resolution system)

---

## Integration with Credentials Manager

**Grant access on hire:**
```python
# Helper Management calls Credentials Manager
response = httpx.post(
    "http://credentials-manager:8025/tokens",
    headers={"Authorization": f"Bearer {admin_token}"},
    json={
        "helper_name": f"contractor_{task_id}",
        "credential_ids": task.credential_ids,
        "scope": "read_only",
        "expires_hours": task.duration_hours + 24  # Buffer
    }
)

token = response.json()["token"]
# Send token to helper
```

**Revoke access on completion:**
```python
# After payment processed
httpx.delete(
    f"http://credentials-manager:8025/tokens/{token_id}",
    headers={"Authorization": f"Bearer {admin_token}"}
)
```

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8026
- **Database:** PostgreSQL
- **Resource limits:**
  - Memory: 512MB max
  - CPU: 1 core
  - Storage: 2GB for database
- **Response time:** AI screening < 10 seconds, payment processing < 60 seconds
- **Payment retries:** 3 attempts with exponential backoff
- **Token expiration:** Task duration + 24 hour buffer

---

**Next Step:** Deploy to production, post first real task, test full workflow
