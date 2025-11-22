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

## Configuration

### Enable AI Screening

To enable full Claude-powered screening, add API key to container:

```bash
# On server (198.54.123.234)
echo "ANTHROPIC_API_KEY=sk-ant-..." > /root/agents/services/jobs/.env

# Restart container
docker stop fpai-jobs
docker rm fpai-jobs
cd /root/agents/services/jobs
docker run -d --name fpai-jobs -p 8008:8008 \
  -v /root/agents/services/jobs/data:/app/data \
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
cat /root/agents/services/jobs/data/jobs.json | python3 -m json.tool

# Applications
cat /root/agents/services/jobs/data/applications.json | python3 -m json.tool
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
ls -la /root/agents/services/jobs/data/
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
