"""
Proactive Growth Orchestrator

AI that doesn't wait for human commands - it identifies gaps,
recruits help (human or AI), monitors progress, and reports results.

Runs daily at 6am, weekly on Mondays, monthly on 1st.
"""

import os
import json
from datetime import datetime, date
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from marketing_engine.tracking import tracker, EventType


class GapType(Enum):
    """Types of gaps that can block growth"""
    INSUFFICIENT_PROSPECTS = "insufficient_prospects"
    LOW_EMAIL_DELIVERABILITY = "low_email_deliverability"
    NO_CONTENT_MARKETING = "no_content_marketing"
    SLOW_RESPONSE_TIME = "slow_response_time"
    NO_LINKEDIN_PRESENCE = "no_linkedin_presence"
    MISSING_API_CREDENTIALS = "missing_api_credentials"
    POOR_CONVERSION_RATE = "poor_conversion_rate"


class RecruitmentType(Enum):
    """How to fill a gap"""
    HUMAN_UPWORK = "human_upwork"  # Post Upwork job
    AI_AGENT = "ai_agent"  # Delegate to AI
    AUTOMATION = "automation"  # Build automated script
    UPGRADE_TOOL = "upgrade_tool"  # Pay for better tools


@dataclass
class Gap:
    """Identified blocker to growth"""
    gap_type: GapType
    severity: int  # 1-10, 10 = critical
    current_state: str
    target_state: str
    solution: str
    recruitment_type: RecruitmentType
    estimated_cost: str
    estimated_time: str
    priority: int  # 1-5, 5 = highest


@dataclass
class ProactiveAction:
    """Action AI plans to take"""
    action_type: str  # "upwork_job", "ai_delegation", "automation", "alert"
    description: str
    requires_approval: bool
    estimated_cost: float
    expected_impact: str
    created_at: datetime
    status: str  # "pending", "approved", "rejected", "completed"


class ProactiveOrchestrator:
    """
    AI that proactively identifies gaps and recruits help.

    Runs autonomously on schedule:
    - Daily: 6am
    - Weekly: Monday 6am
    - Monthly: 1st of month 6am
    """

    def __init__(self):
        self.data_dir = "data/orchestrator"
        os.makedirs(self.data_dir, exist_ok=True)

        self.approval_queue_file = f"{self.data_dir}/approval_queue.json"
        self.actions_log_file = f"{self.data_dir}/actions_log.json"
        self.gaps_file = f"{self.data_dir}/identified_gaps.json"

    # ============================================================
    # MAIN ORCHESTRATION LOGIC
    # ============================================================

    def daily_run(self) -> Dict:
        """Run every morning at 6am"""
        print(f"\n🤖 PROACTIVE ORCHESTRATOR - Daily Run {datetime.now()}\n")

        # 1. Check system health
        health = self.check_all_services()
        print(f"📊 System Health: {health['status']}")

        # 2. Identify gaps
        gaps = self.identify_gaps()
        print(f"\n🔍 Identified {len(gaps)} gaps:")
        for gap in gaps:
            print(f"  - {gap.gap_type.value}: {gap.current_state} → {gap.target_state}")

        # 3. Generate daily tasks
        tasks = self.generate_daily_tasks()
        print(f"\n📋 Generated {len(tasks)} tasks for today")

        # 4. Decide how to handle each gap
        actions = []
        for gap in gaps:
            action = self.create_action_for_gap(gap)
            actions.append(action)

        # 5. Execute or queue for approval
        results = self.execute_actions(actions)

        # 6. Monitor ongoing work
        self.check_freelancer_progress()
        self.check_ai_agent_performance()

        # 7. Generate report
        report = self.generate_daily_report(health, gaps, actions, results)

        return report

    def identify_gaps(self) -> List[Gap]:
        """What's preventing growth right now?"""
        gaps = []

        # Check prospect pipeline
        prospect_count = self.get_prospect_count()
        if prospect_count < 1000:
            gaps.append(Gap(
                gap_type=GapType.INSUFFICIENT_PROSPECTS,
                severity=9,
                current_state=f"{prospect_count} prospects in pipeline",
                target_state="1,000+ prospects for sustainable outreach",
                solution="Deploy Research AI to find 100 prospects/day OR hire LinkedIn researcher",
                recruitment_type=RecruitmentType.AI_AGENT,
                estimated_cost="$0.10/prospect AI OR $300/mo human",
                estimated_time="1 week to build AI agent",
                priority=5
            ))

        # Check email deliverability
        deliverability = self.get_email_deliverability()
        if deliverability < 0.95:
            gaps.append(Gap(
                gap_type=GapType.LOW_EMAIL_DELIVERABILITY,
                severity=8,
                current_state=f"{deliverability*100:.1f}% deliverability",
                target_state="95%+ deliverability for cold email",
                solution="Hire email deliverability consultant for audit",
                recruitment_type=RecruitmentType.HUMAN_UPWORK,
                estimated_cost="$500 one-time",
                estimated_time="3-5 days",
                priority=4
            ))

        # Check content marketing
        blog_posts = self.get_blog_posts_per_month()
        if blog_posts < 4:
            gaps.append(Gap(
                gap_type=GapType.NO_CONTENT_MARKETING,
                severity=6,
                current_state=f"{blog_posts} blog posts/month",
                target_state="12+ blog posts/month for SEO growth",
                solution="Hire content writer OR deploy Content AI",
                recruitment_type=RecruitmentType.HUMAN_UPWORK,  # Human better for quality
                estimated_cost="$300/mo human OR $50/mo AI",
                estimated_time="1 week to hire",
                priority=3
            ))

        # Check for missing API credentials
        missing_creds = self.check_missing_credentials()
        if missing_creds:
            gaps.append(Gap(
                gap_type=GapType.MISSING_API_CREDENTIALS,
                severity=10,
                current_state=f"Missing: {', '.join(missing_creds)}",
                target_state="All API credentials configured",
                solution="Hire API setup specialist via Upwork",
                recruitment_type=RecruitmentType.HUMAN_UPWORK,
                estimated_cost="Test sprint basis",
                estimated_time="24-48 hours",
                priority=5
            ))

        # Check response time
        avg_response_time = self.get_avg_response_time()
        if avg_response_time > 4:  # hours
            gaps.append(Gap(
                gap_type=GapType.SLOW_RESPONSE_TIME,
                severity=7,
                current_state=f"{avg_response_time:.1f} hour avg response time",
                target_state="< 2 hour response time for hot leads",
                solution="Deploy Conversation AI for auto-responses",
                recruitment_type=RecruitmentType.AI_AGENT,
                estimated_cost="$50/mo API costs",
                estimated_time="2-3 days to build",
                priority=4
            ))

        # Sort by priority
        gaps.sort(key=lambda g: g.priority, reverse=True)

        # Save gaps to file
        self.save_gaps(gaps)

        return gaps

    def create_action_for_gap(self, gap: Gap) -> ProactiveAction:
        """Decide what action to take for this gap"""

        if gap.recruitment_type == RecruitmentType.HUMAN_UPWORK:
            return self.create_upwork_job_action(gap)

        elif gap.recruitment_type == RecruitmentType.AI_AGENT:
            return self.create_ai_agent_action(gap)

        elif gap.recruitment_type == RecruitmentType.AUTOMATION:
            return self.create_automation_action(gap)

        elif gap.recruitment_type == RecruitmentType.UPGRADE_TOOL:
            return self.create_tool_upgrade_action(gap)

    def create_upwork_job_action(self, gap: Gap) -> ProactiveAction:
        """Create Upwork job posting for this gap"""

        # Generate job posting
        job_posting = self.generate_upwork_job(gap)

        # Save to file for human review
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"UPWORK_JOB_{gap.gap_type.value}_{timestamp}.md"
        filepath = f"{self.data_dir}/{filename}"

        with open(filepath, 'w') as f:
            f.write(job_posting)

        return ProactiveAction(
            action_type="upwork_job",
            description=f"Created Upwork job posting: {filename}",
            requires_approval=True,
            estimated_cost=self.parse_cost(gap.estimated_cost),
            expected_impact=f"Fill gap: {gap.gap_type.value}",
            created_at=datetime.now(),
            status="pending"
        )

    def create_ai_agent_action(self, gap: Gap) -> ProactiveAction:
        """Delegate to AI agent"""

        return ProactiveAction(
            action_type="ai_delegation",
            description=f"Deploy AI agent for: {gap.gap_type.value}",
            requires_approval=False,  # AI can delegate to AI autonomously
            estimated_cost=self.parse_cost(gap.estimated_cost),
            expected_impact=f"Automated solution for: {gap.gap_type.value}",
            created_at=datetime.now(),
            status="approved"  # Auto-approve AI delegation
        )

    def execute_actions(self, actions: List[ProactiveAction]) -> Dict:
        """Execute approved actions, queue others for human approval"""

        results = {
            "executed": [],
            "queued_for_approval": [],
            "failed": []
        }

        for action in actions:
            if action.requires_approval:
                # Add to approval queue
                self.add_to_approval_queue(action)
                results["queued_for_approval"].append(action.description)
            else:
                # Execute immediately
                try:
                    self.execute_action(action)
                    results["executed"].append(action.description)
                except Exception as e:
                    results["failed"].append({
                        "action": action.description,
                        "error": str(e)
                    })

        return results

    def execute_action(self, action: ProactiveAction):
        """Actually execute the action"""

        if action.action_type == "ai_delegation":
            # Deploy AI agent
            print(f"✅ Deploying AI agent: {action.description}")
            # TODO: Actually deploy the agent

        elif action.action_type == "automation":
            # Create automation
            print(f"✅ Creating automation: {action.description}")
            # TODO: Generate cron job or script

    # ============================================================
    # SYSTEM HEALTH CHECKS
    # ============================================================

    def check_all_services(self) -> Dict:
        """Check if all services are operational"""
        # TODO: Ping all UDC endpoints
        return {
            "status": "healthy",
            "services": {
                "ai-automation": "active",
                "marketing-engine": "active"
            }
        }

    def get_prospect_count(self) -> int:
        """How many prospects in pipeline?"""
        # TODO: Count from campaigns data
        campaigns_file = "data/campaigns.json"
        if not os.path.exists(campaigns_file):
            return 0

        with open(campaigns_file, 'r') as f:
            campaigns = json.load(f)

        total = sum(len(c.get('prospects', [])) for c in campaigns.values())
        return total

    def get_email_deliverability(self) -> float:
        """Current email deliverability rate"""
        # TODO: Calculate from events
        return 0.96  # Placeholder

    def get_blog_posts_per_month(self) -> int:
        """How many blog posts published per month?"""
        # TODO: Check content directory
        return 0  # Placeholder

    def get_avg_response_time(self) -> float:
        """Average time to respond to email replies (hours)"""
        # TODO: Calculate from events
        return 6.0  # Placeholder

    def check_missing_credentials(self) -> List[str]:
        """Which API credentials are missing?"""
        required = ["apollo_api_key", "instantly_api_key", "hubspot_token"]
        missing = []

        for cred in required:
            if not os.getenv(cred.upper()):
                missing.append(cred)

        return missing

    # ============================================================
    # JOB GENERATION
    # ============================================================

    def generate_upwork_job(self, gap: Gap) -> str:
        """Generate Upwork job posting for this gap"""

        templates = {
            GapType.NO_CONTENT_MARKETING: self.content_writer_job_template,
            GapType.NO_LINKEDIN_PRESENCE: self.linkedin_specialist_job_template,
            GapType.LOW_EMAIL_DELIVERABILITY: self.email_expert_job_template,
        }

        template_func = templates.get(gap.gap_type)
        if template_func:
            return template_func(gap)
        else:
            return self.generic_job_template(gap)

    def content_writer_job_template(self, gap: Gap) -> str:
        """Generate content writer job posting"""
        return f"""# Upwork Job: AI Automation Content Writer

**Category:** Writing > Blog Writing
**Experience Level:** Intermediate
**Duration:** Ongoing (monthly retainer)

## Job Description

Looking for a content writer who understands AI automation and B2B SaaS to create SEO-optimized blog posts.

**What You'll Write:**
- 12 blog posts per month (3 per week)
- Topics: AI automation, productivity, business efficiency
- 1,500-2,000 words each
- SEO optimized for keywords like "AI employee", "AI automation", "business automation"

**Required Skills:**
- Strong B2B SaaS writing experience
- Understanding of AI and automation concepts
- SEO knowledge
- Fast turnaround (3 posts/week)

**Deliverables:**
- 12 blog posts/month in Markdown format
- Meta descriptions and title tags
- Internal linking suggestions
- Performance reports (traffic, engagement)

**How to Apply:**
1. Share 3 writing samples (B2B or tech preferred)
2. Outline your blog post process
3. What's your understanding of AI automation?
4. Can you start this week?

**Current State:** {gap.current_state}
**Target:** {gap.target_state}
"""

    def email_expert_job_template(self, gap: Gap) -> str:
        """Generate email deliverability expert job"""
        return f"""# Upwork Job: Email Deliverability Consultant

**Category:** Marketing > Email Marketing
**Experience Level:** Expert
**Duration:** One-time project

## Job Description

Need an email deliverability expert to audit our cold email setup and improve deliverability from {gap.current_state} to 95%+.

**What You'll Do:**
- Audit current email configuration (SPF, DKIM, DMARC)
- Review email content and sending patterns
- Identify deliverability issues
- Provide actionable recommendations
- Help implement fixes

**Required Skills:**
- Email deliverability expertise
- Experience with cold email campaigns
- Knowledge of Instantly.ai or similar platforms
- Understanding of spam filters and inbox placement

**Deliverables:**
- Comprehensive audit report
- Step-by-step fix recommendations
- Help implementing changes
- Follow-up test to verify improvements

**Timeline:** 3-5 days

**How to Apply:**
1. Describe your email deliverability experience
2. What tools do you use for testing?
3. Share a past success story
4. Available to start this week?

**Current State:** {gap.current_state}
**Target:** {gap.target_state}
"""

    def linkedin_specialist_job_template(self, gap: Gap) -> str:
        """Generate LinkedIn outreach specialist job"""
        return f"""# Upwork Job: LinkedIn Outreach Specialist (AI Automation)

**Category:** Sales & Marketing > Lead Generation
**Experience Level:** Intermediate
**Duration:** Ongoing (monthly retainer)

## Job Description

Need a LinkedIn specialist to do personalized outreach to SaaS founders and CEOs about AI automation services.

**What You'll Do:**
- Research and identify 50 prospects/day on LinkedIn
- Send personalized connection requests
- Follow up with warm introduction
- Track responses in HubSpot CRM
- Book discovery calls via Calendly

**Required Skills:**
- LinkedIn Sales Navigator experience
- B2B outreach (SaaS preferred)
- Excellent written communication
- CRM proficiency (HubSpot a plus)

**Target Audience:**
- SaaS company CEOs/Founders
- 10-100 employees
- US-based
- Tech-forward industries

**Deliverables:**
- 250 new connections/week (50/day × 5 days)
- 10-15 qualified responses/week
- 3-5 booked calls/week
- Weekly performance report

**How to Apply:**
1. Share your LinkedIn profile
2. Describe your outreach process
3. What's your experience with B2B SaaS?
4. Sample connection request message

**Current State:** {gap.current_state}
**Target:** {gap.target_state}
"""

    def generic_job_template(self, gap: Gap) -> str:
        """Generic job template"""
        return f"""# Upwork Job: {gap.gap_type.value.replace('_', ' ').title()}

**Category:** To Be Determined
**Experience Level:** Intermediate
**Duration:** Test sprint

## Problem

{gap.current_state}

## Goal

{gap.target_state}

## Solution

{gap.solution}

## Estimated Cost

{gap.estimated_cost}

## Timeline

{gap.estimated_time}

## How to Apply

1. Describe your relevant experience
2. Outline your approach to solving this
3. Estimated timeline
4. Any questions about requirements?
"""

    # ============================================================
    # TASK GENERATION
    # ============================================================

    def generate_daily_tasks(self) -> List[Dict]:
        """What should happen today?"""
        tasks = [
            {
                "task": "Import 100 new prospects from Apollo",
                "type": "automation",
                "priority": 5
            },
            {
                "task": "Send 50 outreach emails",
                "type": "automation",
                "priority": 5
            },
            {
                "task": "Check for email replies and draft responses",
                "type": "ai_agent",
                "priority": 4
            },
            {
                "task": "Update dashboard metrics",
                "type": "automation",
                "priority": 3
            },
        ]
        return tasks

    # ============================================================
    # MONITORING
    # ============================================================

    def check_freelancer_progress(self):
        """Check how freelancers are performing"""
        # TODO: Check Upwork for deliverables
        pass

    def check_ai_agent_performance(self):
        """Check how AI agents are performing"""
        # TODO: Check agent logs
        pass

    # ============================================================
    # REPORTING
    # ============================================================

    def generate_daily_report(self, health, gaps, actions, results) -> str:
        """Generate daily summary report"""

        report = f"""
🤖 PROACTIVE ORCHESTRATOR - Daily Report
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

{'='*60}
SYSTEM HEALTH
{'='*60}

Status: {health['status'].upper()}
Services: {len(health['services'])} active

{'='*60}
GAPS IDENTIFIED
{'='*60}

Found {len(gaps)} gaps preventing growth:
"""

        for i, gap in enumerate(gaps, 1):
            report += f"\n{i}. {gap.gap_type.value.replace('_', ' ').title()} (Priority: {gap.priority}/5)\n"
            report += f"   Current: {gap.current_state}\n"
            report += f"   Target: {gap.target_state}\n"
            report += f"   Solution: {gap.solution}\n"
            report += f"   Cost: {gap.estimated_cost}\n"

        report += f"""
{'='*60}
ACTIONS TAKEN
{'='*60}

Executed: {len(results['executed'])}
"""
        for action in results['executed']:
            report += f"  ✅ {action}\n"

        report += f"\nQueued for Approval: {len(results['queued_for_approval'])}\n"
        for action in results['queued_for_approval']:
            report += f"  ⏳ {action}\n"

        if results['failed']:
            report += f"\nFailed: {len(results['failed'])}\n"
            for fail in results['failed']:
                report += f"  ❌ {fail['action']}: {fail['error']}\n"

        report += f"""
{'='*60}
NEXT STEPS
{'='*60}

1. Review approval queue: {self.approval_queue_file}
2. Check identified gaps: {self.gaps_file}
3. Monitor AI agent performance

Run `python orchestrator.py approve` to approve pending actions.
"""

        # Save report
        report_file = f"{self.data_dir}/daily_report_{date.today()}.txt"
        with open(report_file, 'w') as f:
            f.write(report)

        print(report)
        return report

    # ============================================================
    # UTILITIES
    # ============================================================

    def parse_cost(self, cost_str: str) -> float:
        """Extract numeric cost from string like '$300/mo' or '$0.10/prospect'"""
        # Simple extraction - take first number
        import re
        match = re.search(r'\$?(\d+)', cost_str)
        if match:
            return float(match.group(1))
        return 0.0

    def save_gaps(self, gaps: List[Gap]):
        """Save identified gaps to file"""
        gaps_data = [{
            "gap_type": g.gap_type.value,
            "severity": g.severity,
            "current_state": g.current_state,
            "target_state": g.target_state,
            "solution": g.solution,
            "recruitment_type": g.recruitment_type.value,
            "estimated_cost": g.estimated_cost,
            "estimated_time": g.estimated_time,
            "priority": g.priority
        } for g in gaps]

        with open(self.gaps_file, 'w') as f:
            json.dump(gaps_data, f, indent=2)

    def add_to_approval_queue(self, action: ProactiveAction):
        """Add action to human approval queue"""

        # Load existing queue
        if os.path.exists(self.approval_queue_file):
            with open(self.approval_queue_file, 'r') as f:
                queue = json.load(f)
        else:
            queue = []

        # Add new action
        queue.append({
            "action_type": action.action_type,
            "description": action.description,
            "estimated_cost": action.estimated_cost,
            "expected_impact": action.expected_impact,
            "created_at": action.created_at.isoformat(),
            "status": action.status
        })

        # Save
        with open(self.approval_queue_file, 'w') as f:
            json.dump(queue, f, indent=2)


# ============================================================
# CLI INTERFACE
# ============================================================

if __name__ == "__main__":
    import sys

    orchestrator = ProactiveOrchestrator()

    if len(sys.argv) > 1 and sys.argv[1] == "approve":
        print("📋 Approval Queue:")
        if os.path.exists(orchestrator.approval_queue_file):
            with open(orchestrator.approval_queue_file, 'r') as f:
                queue = json.load(f)
            for i, item in enumerate(queue, 1):
                print(f"\n{i}. {item['description']}")
                print(f"   Cost: ${item['estimated_cost']}")
                print(f"   Impact: {item['expected_impact']}")
        else:
            print("No items in approval queue")
    else:
        # Run daily orchestration
        orchestrator.daily_run()
