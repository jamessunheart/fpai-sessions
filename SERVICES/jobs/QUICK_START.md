# Jobs Service - Quick Start Guide

## For Autonomous Executor Integration

### 1. Post a Job Automatically

```python
import requests

# Example: Autonomous executor posts a job
job = {
    "title": "Frontend Developer for AI Dashboard",
    "description": "Build React components for real-time AI system monitoring",
    "requirements": [
        "3+ years React experience",
        "TypeScript proficiency",
        "Real-time data visualization"
    ],
    "responsibilities": [
        "Build responsive UI components",
        "Integrate with FastAPI backend",
        "Implement WebSocket updates"
    ],
    "budget": 1500,
    "duration": "2 weeks",
    "skills": ["React", "TypeScript", "WebSockets", "CSS"],
    "remote": True,
    "delegation_id": "auto-exec-12345"  # Links to delegation system
}

response = requests.post(
    "http://198.54.123.234:8008/api/jobs/post",
    json=job
)

result = response.json()
print(f"Job posted: {result['url']}")
print(f"Job ID: {result['job_id']}")
```

### 2. Check Applications

```python
import requests

job_id = "your-job-id-here"

response = requests.get(
    f"http://198.54.123.234:8008/api/jobs/{job_id}/applications"
)

apps = response.json()
print(f"Received {apps['count']} applications")

for app in apps['applications']:
    print(f"\n{app['name']} ({app['email']})")
    print(f"  Experience: {app['experience_years']} years")
    print(f"  Skills: {', '.join(app['relevant_skills'])}")
    print(f"  Status: {app['status']}")
    if 'ai_screening' in app:
        print(f"  AI Score: {app['ai_screening']['overall_score']}")
        print(f"  Recommendation: {app['ai_screening']['recommendation']}")
```

### 3. Test Manually via cURL

#### Post a Job
```bash
curl -X POST http://198.54.123.234:8008/api/jobs/post \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Job",
    "description": "Testing the system",
    "requirements": ["Skill 1", "Skill 2"],
    "responsibilities": ["Task 1", "Task 2"],
    "budget": 1000,
    "duration": "1 week",
    "skills": ["Python", "FastAPI"],
    "remote": true
  }'
```

#### List Jobs
```bash
curl http://198.54.123.234:8008/api/jobs/list | python3 -m json.tool
```

#### View Public Board
```bash
curl http://198.54.123.234:8008/jobs
```

## Service Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/jobs` | GET | Public job board (HTML) |
| `/jobs/{id}` | GET | Job detail + apply form (HTML) |
| `/api/jobs/post` | POST | Create new job |
| `/api/jobs/list` | GET | Get all jobs (JSON) |
| `/api/jobs/{id}` | GET | Get single job (JSON) |
| `/api/jobs/{id}/applications` | GET | Get applications |
| `/api/jobs/apply` | POST | Submit application |

## Recruiting Hub Rung 4

The gated recruiting hub lives inside this service at:

```bash
http://localhost:8008/recruiting
```

It seeds the first role spec, `Human Context Steward`, from the Rung 4 recruiting spec and stores data in the service `data/` directory:

- `role_specs.json`
- `candidates.json`
- `recruiting_audit_log.json`

### Recruiting Hub Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/recruiting` | GET | Admin recruiting dashboard |
| `/api/recruiting/roles` | GET | List role specs |
| `/api/recruiting/roles` | POST | Create draft role spec |
| `/api/recruiting/roles/{id}/approve` | POST | James approves role before screening |
| `/api/recruiting/candidates` | GET | List candidates |
| `/api/recruiting/review-queue` | GET | List candidates ordered by next review action |
| `/api/recruiting/candidates` | POST | Add candidate without contact |
| `/api/recruiting/candidates/{id}/status` | POST | Move candidate through inbox states |
| `/api/recruiting/candidates/{id}/screen` | POST | AI/deterministic screening against approved rubric |
| `/api/recruiting/candidates/{id}/contact-approval` | POST | Record James-gated contact approval |
| `/api/recruiting/candidates/{id}/decision` | POST | Record James-only decision |
| `/api/recruiting/roles/{id}/shortlist` | GET | Generate advisory shortlist packet |
| `/api/recruiting/roles/{id}/launch-packet` | GET | Generate role post, rubric, sourcing, outreach, interview plan |
| `/api/recruiting/candidates/{id}/evidence-map` | GET | Generate candidate evidence, inference, risk, unknowns, and next questions |
| `/api/recruiting/audit-log` | GET | View approval and decision audit log |

### Gate Rules

- Role must be approved by James before candidate screening.
- Candidate contact approval records channel, message, sender, and timing.
- The hub records contact approval; it does not send outreach.
- Final decisions require `actor: "james"`.
- Screening scores are advisory and cannot mark a candidate hired.
- Candidate contact approval requires `consent_status` of `candidate_submitted`, `james_authorized`, or `contacted`.
- Candidate materials reject obvious secrets and highly sensitive identifiers such as private keys, password/API-key fields, and SSN-shaped values.
- Launch packets and evidence maps are advisory review artifacts; they do not authorize contact or hiring.

### Review Inbox States

The candidate inbox uses explicit states so James sees what needs attention first:

- `new`
- `needs_screening`
- `screened`
- `needs_james_review`
- `contact_approved`
- `interviewing`
- `decision_needed`
- `archived`

Final decision states are also allowed: `advance`, `hold`, `pass`, `offer`, and `hired`.

The review queue prioritizes candidates that need James review or decisions above passive/archive states.

### Human Context Steward Intake Fields

The candidate intake form captures role-specific context:

- Background
- Why this role
- Discretion example
- AI collaboration example
- Writing/context sample
- Availability
- Compensation expectations

### Human Context Steward Launch Packet

Use the dashboard `Launch Packet` button or call:

```bash
curl -H "X-Admin-Key: $RECRUITING_HUB_ADMIN_KEY" \
  http://localhost:8008/api/recruiting/roles/human-context-steward/launch-packet
```

The generated packet includes:

- Public role post
- Private scoring rubric
- Sourcing queries
- Outreach drafts
- Interview plan
- Decision packet template

Candidate evidence maps separate known evidence, AI inferences, risks, unknowns, and next questions so screening does not pretend to know more than the candidate materials support.

### Admin Access

Set an admin key before exposing the service beyond localhost:

```bash
export RECRUITING_HUB_ADMIN_KEY="use-a-long-random-value"
```

Browser users can sign in at `/recruiting/login`. API callers can pass the same key with either:

```bash
curl -H "X-Admin-Key: $RECRUITING_HUB_ADMIN_KEY" http://localhost:8008/api/recruiting/roles
```

or:

```bash
curl -H "Authorization: Bearer $RECRUITING_HUB_ADMIN_KEY" http://localhost:8008/api/recruiting/roles
```

When no admin key is configured, the hub allows localhost development access and blocks non-local access.

### Privacy Boundary

Store only role-relevant candidate materials, consent/source state, and operational notes. Do not store secrets, private medical/legal/financial details, intimate relationship context, or sensitive third-party context in the recruiting hub.

### CORS

By default, CORS is limited to:

- `http://localhost:8008`
- `http://127.0.0.1:8008`

Override only when needed:

```bash
export CORS_ALLOW_ORIGINS="https://your-admin-domain.example"
```

## Configuration

### Enable AI Screening

To enable full Claude-powered screening, add API key to container:

```bash
# On server (198.54.123.234)
echo "ANTHROPIC_API_KEY=sk-ant-..." > /root/SERVICES/jobs/.env

# Restart container
docker stop fpai-jobs
docker rm fpai-jobs
cd /root/SERVICES/jobs
docker run -d --name fpai-jobs -p 8008:8008 \
  -v /root/SERVICES/jobs/data:/app/data \
  --env-file .env \
  --restart unless-stopped \
  jobs:latest
```

### View Logs

```bash
# Real-time logs
docker logs -f fpai-jobs

# Last 50 lines
docker logs fpai-jobs --tail 50
```

### Check Data Files

```bash
# Jobs
cat /root/SERVICES/jobs/data/jobs.json | python3 -m json.tool

# Applications
cat /root/SERVICES/jobs/data/applications.json | python3 -m json.tool
```

## Integration with Other Services

### Link to Delegation System
Every job includes a `delegation_id` field:
```python
job = {
    # ... other fields
    "delegation_id": "delegation-uuid-here"
}
```

This enables tracking:
- Which autonomous system posted the job
- Link to milestone verification
- Connect to payment authorization
- Full audit trail

### Link to Coordination System
When an application looks good:
1. Jobs service flags it for review
2. Coordination system receives notification
3. Human approves hire
4. Treasury system processes payment

### Link to Verifier
After hiring:
1. Job becomes a delegation
2. Work is completed
3. Verifier checks 7 quality criteria
4. If passed, payment authorized

## Testing Workflow

### 1. Autonomous Posts Job
```python
# autonomous_executor.py
executor.post_job_to_jobs_service(delegation)
```

### 2. Public Discovers Job
- Google indexes `/jobs` page
- Candidates find and apply
- Applications stored automatically

### 3. AI Screens Applications
- Claude analyzes each application
- Scores skills match, experience, cover letter
- Provides hire/maybe/pass recommendation

### 4. Human Reviews Top Candidates
```python
# Get applications sorted by AI score
apps = get_applications(job_id)
top_candidates = [a for a in apps if a['ai_screening']['recommendation'] == 'hire']
```

### 5. System Sends Offer
- Coordination system approves
- Treasury generates payment address
- Onboarding materials sent

## Data Models

### Job Post
```python
{
    "title": str,
    "description": str,
    "requirements": List[str],
    "responsibilities": List[str],
    "budget": float,
    "duration": str,
    "skills": List[str],
    "remote": bool,
    "delegation_id": Optional[str]
}
```

### Application
```python
{
    "job_id": str,
    "name": str,
    "email": str,
    "portfolio_url": Optional[str],
    "cover_letter": str,
    "experience_years": int,
    "relevant_skills": List[str],
    "availability": str
}
```

### AI Screening Result
```python
{
    "skills_match": int,  # 0-100
    "cover_letter_quality": int,  # 0-100
    "experience_fit": int,  # 0-100
    "overall_score": int,  # 0-100
    "recommendation": str,  # "hire" | "maybe" | "pass"
    "strengths": List[str],
    "concerns": List[str],
    "reasoning": str
}
```

## Production Checklist

- [x] Service deployed and running
- [x] Health endpoint responding
- [x] Data persistence configured
- [x] Public board accessible
- [x] API endpoints tested
- [x] Application flow working
- [ ] ANTHROPIC_API_KEY configured (optional)
- [ ] Domain name configured (optional)
- [ ] SSL certificate (optional)
- [ ] Email notifications (future)
- [ ] Admin dashboard (future)

## Troubleshooting

### Service Not Responding
```bash
# Check if container is running
docker ps | grep fpai-jobs

# Check logs
docker logs fpai-jobs --tail 50

# Restart
docker restart fpai-jobs
```

### Data Not Persisting
```bash
# Check volume mount
docker inspect fpai-jobs | grep Mounts -A 10

# Check file permissions
ls -la /root/SERVICES/jobs/data/
```

### AI Screening Not Working
```bash
# Check if API key is set
docker exec fpai-jobs env | grep ANTHROPIC

# If empty, add to .env and restart (see Configuration above)
```

## Next Steps

1. **Connect Autonomous Executor**
   - Import jobs service client
   - Post test job from executor
   - Verify end-to-end flow

2. **Monitor Applications**
   - Check `/api/jobs/{id}/applications` daily
   - Review AI screening results
   - Approve top candidates

3. **Expand Channels**
   - When Upwork approves: syndicate jobs
   - Add Braintrust integration
   - Post to LinkedIn jobs

4. **Enhance System**
   - Add email notifications
   - Build admin dashboard
   - Implement interview scheduling
   - Add video screening

---

**Status**: OPERATIONAL ✅
**Ready for**: Autonomous recruitment
**Deployed**: 2025-11-15

🚀 Let's recruit!
