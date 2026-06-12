# jobs - SPECS

**Created:** 2025-11-15
**Status:** Production (Port 8008)

---

## Purpose

Sovereign job board with autonomous AI-powered recruitment. Handles job posting, AI screening of candidates, AI-conducted interviews, labor coordination, code review, and milestone verification. Reduces hiring time from 20 hours to 1 hour of human involvement.

---

## Requirements

### Functional Requirements
- [ ] Job board UI for posting and browsing jobs
- [ ] Application submission and storage
- [ ] AI screening using Claude (score, reasoning, recommendation)
- [ ] AI interview conductor (generate questions, evaluate responses)
- [ ] Labor coordinator (project kickoff, daily check-ins, code review, blocker assistance)
- [ ] Milestone verification with 7-point quality checklist
- [ ] Social media automation for recruitment (Twitter, LinkedIn, Reddit)
- [ ] Helper onboarding materials generation
- [ ] Performance tracking and analytics
- [ ] Integration with credentials-manager for helper access

### Non-Functional Requirements
- [ ] Performance: AI screening < 10 seconds, interview evaluation < 30 seconds
- [ ] Reliability: All AI operations have fallback to manual review
- [ ] Security: No credential exposure, scoped access only
- [ ] Scalability: Support 100+ concurrent applications
- [ ] User Experience: Simple application flow, clear feedback

---

## API Specs

### Endpoints

**GET /jobs**
- **Purpose:** List all jobs (web UI)
- **Input:** None (optional: filters)
- **Output:** HTML page with job listings
- **Success:** 200 OK
- **Errors:** 500 if template fails

**POST /jobs**
- **Purpose:** Create new job posting
- **Input:** title, description, requirements, compensation, type
- **Output:** Job ID, confirmation
- **Success:** 201 Created
- **Errors:** 400 if validation fails

**POST /applications**
- **Purpose:** Submit application
- **Input:** job_id, name, email, cover_letter, resume, links
- **Output:** Application ID, confirmation
- **Success:** 201 Created
- **Errors:** 400 if validation fails, 404 if job not found

**POST /api/applications/{id}/screen**
- **Purpose:** AI screen application
- **Input:** application ID
- **Output:** AI score, reasoning, recommendation ("hire", "maybe", "pass")
- **Success:** 200 OK
- **Errors:** 404 if not found, 500 if AI fails

**POST /api/interviews**
- **Purpose:** Generate AI interview for candidate
- **Input:** application_id
- **Output:** Interview ID, custom questions (5)
- **Success:** 201 Created
- **Errors:** 404 if not found

**POST /api/interviews/{id}/submit**
- **Purpose:** Submit interview responses
- **Input:** interview ID, answers (array)
- **Output:** Evaluation (scores, overall recommendation, next steps)
- **Success:** 200 OK
- **Errors:** 404 if not found, 400 if invalid responses

**POST /api/labor/kickoff**
- **Purpose:** Start project coordination for hired developer
- **Input:** developer_id, project_details
- **Output:** Welcome message, milestones, first week tasks, check-in schedule
- **Success:** 201 Created
- **Errors:** 404 if not found

**POST /api/labor/checkin**
- **Purpose:** Daily developer check-in
- **Input:** developer_id, update_text
- **Output:** AI feedback (status, praise, suggestions, blockers, next steps)
- **Success:** 200 OK
- **Errors:** 404 if not found

**POST /api/labor/code-review**
- **Purpose:** AI code review
- **Input:** developer_id, code_diff
- **Output:** Review (overall feedback, strengths, issues, suggestions)
- **Success:** 200 OK
- **Errors:** 400 if invalid input

**POST /api/labor/blocker**
- **Purpose:** Help developer with blocker
- **Input:** developer_id, blocker_description
- **Output:** Suggestions, resources, escalation decision
- **Success:** 200 OK
- **Errors:** 404 if not found

**GET /health**
- **Purpose:** Health check
- **Input:** None
- **Output:** {"status": "healthy", "service": "jobs", "ai_screening": "active"}
- **Success:** 200 OK
- **Errors:** 500 if unhealthy

### Data Models

```python
class Job:
    id: int
    title: str
    description: str
    requirements: dict
    compensation: str
    type: str  # "full_time", "contract", "part_time"
    status: str  # "open", "closed"
    created_at: datetime
    posted_by: str

class Application:
    id: int
    job_id: int
    name: str
    email: str
    cover_letter: str
    resume_url: Optional[str]
    portfolio_links: List[str]
    ai_score: Optional[float]
    ai_reasoning: Optional[str]
    ai_recommendation: Optional[str]
    status: str  # "pending", "screened", "interviewing", "hired", "rejected"
    submitted_at: datetime

class Interview:
    id: int
    application_id: int
    questions: List[InterviewQuestion]
    responses: List[InterviewResponse]
    overall_score: Optional[float]
    overall_recommendation: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]

class InterviewQuestion:
    id: int
    category: str  # "technical", "behavioral", "culture_fit"
    question: str
    good_answer: str  # What to look for
    red_flags: List[str]
    scoring_criteria: str

class InterviewResponse:
    question_id: int
    answer: str
    score: float  # 0-10
    strengths: List[str]
    weaknesses: List[str]
    feedback: str

class ProjectKickoff:
    developer_id: int
    welcome_message: str
    milestones: List[Milestone]
    first_week_tasks: List[Task]
    check_in_schedule: dict
    expectations: dict

class DailyCheckin:
    developer_id: int
    update_text: str
    status: str  # "on_track", "at_risk", "blocked"
    feedback: str
    praise: List[str]
    suggestions: List[str]
    blockers_identified: List[str]
    recommended_next_steps: List[str]
    timestamp: datetime

class CodeReview:
    developer_id: int
    code_diff: str
    status: str  # "approved", "approved_with_suggestions", "changes_requested"
    overall_feedback: str
    strengths: List[str]
    issues: List[CodeIssue]
    suggestions: List[str]
    timestamp: datetime

class CodeIssue:
    severity: str  # "critical", "important", "minor"
    category: str  # "security", "performance", "style", "logic"
    description: str
    suggestion: str
    line_numbers: List[int]
```

---

## Dependencies

### External Services
- Claude API (Anthropic): AI screening, interviews, labor coordination
- Credentials Manager (Port 8025): Helper access tokens

### APIs Required
- Anthropic Claude API: All AI operations
- Credentials Manager API: POST /tokens, DELETE /tokens/{id}

### Data Sources
- PostgreSQL: Jobs, applications, interviews, developer coordination

---

## Success Criteria

How do we know this works?

- [ ] Jobs posted and visible on board
- [ ] Applications submitted successfully
- [ ] AI screening provides useful scores
- [ ] AI interviews generate custom questions
- [ ] Interview evaluations provide hire/no-hire recommendations
- [ ] Labor coordinator generates helpful project kickoffs
- [ ] Daily check-ins provide actionable feedback
- [ ] Code reviews catch issues and provide suggestions
- [ ] Blocker assistance helps developers resolve problems
- [ ] At least 1 complete workflow: post → apply → screen → interview → hire → coordinate

---

## AI Workflows

### 1. AI Screening
**Input:** Application (cover letter, resume, job requirements)
**Output:**
```python
{
    "score": 0.92,
    "reasoning": "Strong FastAPI experience, matches requirements",
    "recommendation": "hire",
    "red_flags": [],
    "strengths": ["5+ years", "production experience", "clear communication"]
}
```

### 2. AI Interview
**Generate Questions:**
```python
{
    "questions": [
        {
            "category": "technical",
            "question": "Describe your experience with FastAPI...",
            "good_answer": "Should mention production usage...",
            "red_flags": ["vague", "no production experience"],
            "scoring_criteria": "10 = production + metrics..."
        }
    ]
}
```

**Evaluate Responses:**
```python
{
    "overall_score": 8.4,
    "recommendation": "strong_hire",
    "summary": "Candidate demonstrates strong technical depth...",
    "strengths": ["Production experience", "Works well with AI"],
    "concerns": [],
    "next_steps": ["Extend offer"]
}
```

### 3. Labor Coordination
**Project Kickoff:**
```python
{
    "welcome_message": "Hi Sarah! Excited to work with you...",
    "milestones": [
        {"title": "Foundation", "deliverables": [...], "payment": "$600"}
    ],
    "first_week_tasks": [
        {"task": "Setup FastAPI", "priority": "high", "estimated_hours": 4}
    ],
    "check_in_schedule": {"daily_standup": "9am async via Discord"}
}
```

**Daily Check-in:**
```python
{
    "status": "on_track",
    "feedback": "Great progress! Ahead of schedule.",
    "praise": ["Completed 2 tasks ahead of schedule"],
    "suggestions": ["Use Alembic for migrations"],
    "blockers_identified": [],
    "estimated_completion": "ahead_of_schedule"
}
```

**Code Review:**
```python
{
    "status": "approved_with_suggestions",
    "overall_feedback": "Solid implementation. Minor security suggestions.",
    "strengths": ["Proper password hashing", "Good error handling"],
    "issues": [
        {
            "severity": "important",
            "category": "security",
            "description": "JWT secret hardcoded",
            "suggestion": "Move to environment variable"
        }
    ]
}
```

---

## Technical Constraints

- **Language/Framework:** Python 3.11+ with FastAPI
- **Port:** 8008
- **Database:** PostgreSQL (for production) or SQLite (for dev)
- **Resource limits:**
  - Memory: 512MB max
  - CPU: 1 core
  - Storage: 2GB for database and assets
- **Response time:** AI operations < 30 seconds, page load < 2 seconds
- **Claude API:** Uses claude-sonnet-4-5-20250929

---

## Integration Notes

**With Credentials Manager:**
On hire, grant access to required credentials:
```python
response = httpx.post(
    "http://credentials-manager:8025/tokens",
    json={
        "helper_name": f"developer_{application_id}",
        "credential_ids": project.credential_ids,
        "scope": "read_only",
        "expires_hours": project.duration_hours
    }
)
```

---

## Time Savings

**Before:** 20 hours human time per hire
- Resume screening: 5 hours
- Interviews: 8 hours
- Onboarding: 3 hours
- Daily coordination: 4 hours/week

**After:** 1 hour human time per hire
- AI screening: Auto (seconds)
- AI interviews: Auto (minutes)
- AI onboarding: Auto (minutes)
- AI coordination: Auto (daily)
- Human only: Final approval + spot checks

**Time Savings: 95%**

---

**Next Step:** Test full autonomous hiring workflow with real candidates
