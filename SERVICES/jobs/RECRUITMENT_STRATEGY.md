# How to Get Real Candidates - Recruitment Strategy

## Phase 1: Immediate Actions (Today)

### 1. Domain Setup
**Current:** http://198.54.123.234:8008/jobs (IP address)
**Needed:** jobs.fullpotential.com

**Why:**
- SEO requires domain name
- Candidates trust domains over IPs
- Email deliverability
- Professional branding

**Action:**
```bash
# Add DNS A record:
jobs.fullpotential.com → 198.54.123.234

# Add nginx/caddy for HTTPS:
https://jobs.fullpotential.com
```

### 2. SEO Optimization
**Status:** HTML templates are SEO-ready
**Add:**
- Sitemap.xml generation
- robots.txt
- Open Graph meta tags
- JSON-LD structured data

### 3. Post to Free Job Boards
**Immediate channels:**
- LinkedIn Jobs (free posting available)
- AngelList/Wellfound (startup jobs)
- HackerNews "Who's Hiring" monthly thread
- Reddit r/forhire, r/jobbit
- Twitter/X with #hiring hashtag
- Dev.to job board
- Indie Hackers job board

**Action:** Use the job posting API to create a post, then manually share:
```bash
curl http://198.54.123.234:8008/api/jobs/{job_id}
# Share this URL on all platforms
```

### 4. AI-Specific Communities
Since we're building AI infrastructure:
- Discord: AI developer communities
- Anthropic Discord
- OpenAI Developer Forum
- LangChain Discord
- AI startup Slack communities

**Pitch:** "Work on bleeding-edge autonomous AI systems"

---

## Phase 2: Growth (Week 1-2)

### 1. Paid Job Boards
**Budget:** $200-500/post

Top platforms:
- **Upwork** - Post project for $150 budget
  - When API approved, automate via Upwork integration
  - Currently: Manual posting

- **Braintrust** - Crypto-native talent network
  - Perfect for blockchain + AI work
  - Post jobs manually until integration built

- **Toptal** - Premium developers
  - Higher quality, higher cost
  - For critical roles

- **We Work Remotely** - $300/post
  - High visibility in remote work community

### 2. Content Marketing
**Create:**
- Blog post: "How We Built an Autonomous AI Recruitment System"
- Technical deep-dive on the architecture
- Open source parts of the system
- Share on HackerNews

**Result:** Inbound applications from developers interested in the tech

### 3. Referral Program
**Structure:**
- $500 bonus for successful referral
- Paid after referred developer completes first milestone
- Both referrer and referee get bonus

---

## Phase 3: Automation (Week 2-4)

### 1. Multi-Channel Job Syndication
**Build system to auto-post to:**
- Jobs service (sovereign - done ✅)
- Upwork (when approved)
- Braintrust API
- LinkedIn API
- AngelList API

**One API call posts everywhere:**
```python
# Autonomous executor posts once
jobs_service.post_job(delegation)

# Syndicator automatically posts to:
# - jobs.fullpotential.com
# - Upwork
# - Braintrust
# - LinkedIn
# - AngelList
```

### 2. Email Campaign
**Target:**
- Developers who starred AI repos on GitHub
- Newsletter subscribers
- Past applicants

**Automation:**
- Welcome email with onboarding
- Milestone reminders
- Payment confirmations

### 3. AI-Powered Outreach
**Use Claude to:**
- Find relevant developers on GitHub
- Draft personalized outreach messages
- Send via LinkedIn/email
- Follow up automatically

**Example:**
```python
# AI finds developers who:
# - Contributed to FastAPI repos
# - Have Docker experience
# - Interested in AI/ML
# - Open to remote work

# Sends personalized message:
"Hi {name}, noticed your work on {repo}.
We're building autonomous AI infrastructure
and think you'd be perfect for..."
```

---

## Phase 4: Quality & Scale (Month 2+)

### 1. Application Funnel Optimization
**Track:**
- Source (where did they find us?)
- Conversion rate (views → applications)
- Quality score (AI screening results)
- Time to hire

**Optimize:**
- Job descriptions that convert
- Application form that's quick
- Fast response time (AI auto-screens)

### 2. Community Building
**Create:**
- Developer community on Discord
- Regular tech talks/webinars
- Open source contributions
- Case studies of successful projects

**Result:** Pipeline of pre-qualified developers

### 3. Employer Brand
**Build reputation as:**
- Cutting-edge AI company
- Fair payment (USDC escrow, no delays)
- Great developer experience
- Autonomous tools that help (not replace) humans

---

## Current Status: What Works TODAY

### ✅ You Can Post Jobs
```python
import requests

job = {
    "title": "React Developer for AI Dashboard",
    "description": "Build UI for autonomous AI system",
    "requirements": ["3+ years React", "TypeScript"],
    "budget": 1500,
    "duration": "2 weeks",
    "skills": ["React", "TypeScript"],
    "remote": True
}

response = requests.post(
    "http://198.54.123.234:8008/api/jobs/post",
    json=job
)

job_url = response.json()["url"]
print(f"Share this: {job_url}")
```

### ✅ Applications Come In Automatically
- Public form at `/jobs/{id}`
- AI screens them (if API key set)
- Stored in `/root/SERVICES/jobs/data/applications.json`

### ✅ You Review and Hire
```python
# Get applications
response = requests.get(
    f"http://198.54.123.234:8008/api/jobs/{job_id}/applications"
)

apps = response.json()["applications"]

# Sort by AI score (when enabled)
top_candidates = [a for a in apps if a.get('ai_screening', {}).get('recommendation') == 'hire']
```

---

## What You Need to Do MANUALLY (Until Integration Built)

### Hiring Workflow (Manual Steps)

**1. Post the job**
```bash
curl -X POST http://198.54.123.234:8008/api/jobs/post \
  -H "Content-Type: application/json" \
  -d '{...job details...}'
```

**2. Share the URL**
- LinkedIn
- Twitter
- HackerNews
- Discord communities
- Email newsletters

**3. Review applications**
```bash
curl http://198.54.123.234:8008/api/jobs/{job_id}/applications
```

**4. Contact top candidate**
- Email them directly
- Share onboarding materials (auto-generated by autonomous executor)
- Set up in coordination system

**5. Create delegation manually**
```bash
# Call autonomous executor to create delegation
# Send onboarding doc to developer
# Set up milestone tracking
```

**6. Developer submits work**
```bash
curl -X POST http://198.54.123.234:8007/api/coordination/submit-work
```

**7. You approve payment**
```bash
curl -X POST http://198.54.123.234:8007/api/coordination/approve-payment
```

---

## Integration That's MISSING (Needs to Be Built)

### Jobs Service → Coordination Bridge

**File to create:** `/Users/jamessunheart/Development/SERVICES/jobs/app/services/hiring_coordinator.py`

```python
class HiringCoordinator:
    """Bridge between jobs service and coordination system"""

    async def hire_candidate(self, application_id: str, job_id: str):
        """Complete hiring workflow"""

        # 1. Get application and job details
        app = get_application(application_id)
        job = get_job(job_id)

        # 2. Generate onboarding materials
        onboarding = await autonomous_executor.generate_onboarding({
            'title': job['title'],
            'description': job['description'],
            'budget': job['budget'],
            'timeline': job['duration']
        })

        # 3. Create delegation in coordination system
        delegation = await coordination.create_delegation({
            'developer_email': app['email'],
            'developer_name': app['name'],
            'job_id': job_id,
            'budget': job['budget'],
            'milestones': 5
        })

        # 4. Send offer email
        await email_service.send_offer(
            to=app['email'],
            onboarding_doc=onboarding['welcome_doc'],
            technical_brief=onboarding['technical_brief'],
            delegation_id=delegation['id']
        )

        # 5. Update job status
        job['status'] = 'filled'
        job['hired_candidate'] = app['name']

        return {
            'status': 'hired',
            'delegation_id': delegation['id'],
            'onboarding_sent': True
        }
```

**This is the 40% gap that needs to be closed.**

---

## Priority Actions (Next 48 Hours)

### High Priority
1. ✅ **Jobs service is live** - Done!
2. 🔲 **Set up domain:** jobs.fullpotential.com
3. 🔲 **Post first real job:** React Developer role
4. 🔲 **Share on 5 platforms:** LinkedIn, Twitter, HN, Reddit, Discord

### Medium Priority
1. 🔲 **Build hiring coordinator bridge**
2. 🔲 **Set up email notifications**
3. 🔲 **Add ANTHROPIC_API_KEY for AI screening**
4. 🔲 **Create offer letter template**

### Nice to Have
1. 🔲 **Upwork integration** (waiting for approval)
2. 🔲 **LinkedIn API integration**
3. 🔲 **Referral program**
4. 🔲 **Developer community Discord**

---

## Success Metrics

**Week 1 Goals:**
- 50 job views
- 5 applications
- 1 hire

**Month 1 Goals:**
- 500 job views
- 50 applications
- 5 hires
- 3 completed milestones

**Month 3 Goals:**
- Fully automated recruiting
- 10 active developers
- $10k in verified work
- Positive developer reviews

---

## The Vision

**Today:** Manual posting, manual hiring, AI-assisted verification
**Month 2:** Semi-automated posting, AI screening, human approval
**Month 6:** Fully autonomous: AI posts jobs, screens candidates, manages projects, verifies work, releases payments

**Humans in the loop for:**
- Final hiring decisions
- Payment approvals
- Quality spot-checks
- Strategic direction

---

*Ready to recruit real developers TODAY with sovereign infrastructure!*
