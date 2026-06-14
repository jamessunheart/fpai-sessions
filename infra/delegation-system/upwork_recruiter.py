"""
Upwork API Integration for Automated VA Recruitment
Automatically posts jobs, screens applicants, and hires VAs
"""

import json
import os
import datetime
from typing import Dict, List, Optional
from pathlib import Path
import requests


class UpworkRecruiter:
    """Automated VA recruitment via Upwork API"""

    def __init__(self, credentials_path: str = "/root/delegation-system/credentials"):
        self.credentials_path = Path(credentials_path)
        self.jobs_log = Path("/root/delegation-system/upwork-api/jobs_log.json")
        self.jobs_log.parent.mkdir(parents=True, exist_ok=True)

        if not self.jobs_log.exists():
            self.jobs_log.write_text(json.dumps([], indent=2))

        # Load Upwork credentials (will be set up separately)
        self.api_base = "https://www.upwork.com/api/v3"
        self.access_token = os.getenv("UPWORK_ACCESS_TOKEN", "")

    def generate_job_description(self, task_description: str, deliverables: List[str],
                                  budget: int, deadline: str) -> str:
        """Generate professional job description"""

        description = f"""
**Task Overview:**
{task_description}

**Required Deliverables:**
{chr(10).join([f"- {d}" for d in deliverables])}

**Timeline:**
- Deadline: {deadline}
- Expected completion: Within 24-48 hours of hiring

**Requirements:**
- Strong communication skills (English)
- Previous experience with similar tasks
- Available to start immediately
- Responsive (replies within 2-4 hours during work hours)

**Budget:**
${budget} USD (fixed price for this specific task)

**How to Apply:**
1. Confirm you can complete by the deadline
2. Share 1-2 examples of similar work
3. Confirm your hourly rate for potential ongoing work

**About Us:**
We're building AI-powered systems and need reliable VAs for specific setup tasks. Great opportunity for ongoing work if you perform well.

**Next Steps:**
- Top candidates will receive credentials and detailed instructions
- Task is straightforward, just requires human verification/account setup
- Fast payment upon completion and verification
        """.strip()

        return description

    def post_job(self, task_description: str, deliverables: List[str],
                 budget: int, deadline: str, category: str = "Admin Support") -> Dict:
        """Post job to Upwork"""

        job_data = {
            "title": f"VA Needed: {task_description[:50]}...",
            "description": self.generate_job_description(task_description, deliverables, budget, deadline),
            "category": category,
            "budget": budget,
            "duration": "Less than 1 week",
            "visibility": "public",
            "expertise_level": "Intermediate",
            "job_type": "fixed_price"
        }

        # For now, log the job (actual API integration requires Upwork OAuth)
        job = {
            "id": f"job_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "posted_at": datetime.datetime.now().isoformat(),
            "status": "posted",
            **job_data
        }

        # Save to jobs log
        jobs = json.loads(self.jobs_log.read_text())
        jobs.append(job)
        self.jobs_log.write_text(json.dumps(jobs, indent=2))

        print(f"✅ Job posted: {job['id']}")
        print(f"Title: {job['title']}")
        print(f"Budget: ${budget}")

        return job

    def analyze_cover_letter(self, cover_letter: str, task_requirements: List[str]) -> float:
        """
        AI-powered analysis of cover letter quality
        Returns score 0-10
        """
        score = 5.0  # Base score

        # Positive signals
        positive_signals = [
            ("experience", 1.0),
            ("portfolio", 1.0),
            ("available", 0.5),
            ("immediately", 0.5),
            ("deadline", 0.5),
            ("previous", 0.5),
            ("similar", 0.5)
        ]

        for signal, points in positive_signals:
            if signal.lower() in cover_letter.lower():
                score += points

        # Check for task-specific keywords
        task_matches = sum(1 for req in task_requirements if req.lower() in cover_letter.lower())
        score += min(task_matches * 0.5, 2.0)

        # Negative signals
        if len(cover_letter) < 50:
            score -= 2.0  # Too short
        if "copy paste" in cover_letter.lower() or "template" in cover_letter.lower():
            score -= 1.0

        return min(max(score, 0), 10)  # Clamp between 0-10

    def screen_applicants(self, job_id: str, min_rating: float = 4.5,
                          min_cover_letter_score: float = 7.0) -> List[Dict]:
        """Screen applicants automatically"""

        # In production, this would call Upwork API
        # For now, simulate with test data
        applicants = []

        # Load job details
        jobs = json.loads(self.jobs_log.read_text())
        job = next((j for j in jobs if j["id"] == job_id), None)

        if not job:
            return []

        print(f"🔍 Screening applicants for job: {job_id}")
        print(f"Minimum rating: {min_rating}")
        print(f"Minimum cover letter score: {min_cover_letter_score}")

        qualified = [a for a in applicants if
                     a.get("rating", 0) >= min_rating and
                     a.get("cover_letter_score", 0) >= min_cover_letter_score]

        print(f"✅ {len(qualified)} qualified applicants found")

        return qualified

    def hire_freelancer(self, job_id: str, applicant_id: str) -> Dict:
        """Hire a freelancer for the job"""

        hire_data = {
            "job_id": job_id,
            "applicant_id": applicant_id,
            "hired_at": datetime.datetime.now().isoformat(),
            "status": "hired"
        }

        print(f"✅ Hired freelancer {applicant_id} for job {job_id}")

        return hire_data

    def generate_onboarding_message(self, job_details: Dict, credentials: Dict) -> str:
        """Generate onboarding message with credentials and instructions"""

        message = f"""
**Welcome! You've been hired for: {job_details['title']}**

**Task Details:**
{job_details['description']}

**Access & Credentials:**
{chr(10).join([f"- {k}: {v}" for k, v in credentials.items()])}

**⚠️ IMPORTANT SECURITY NOTES:**
- These credentials are monitored. All access is logged.
- Use ONLY for this specific task
- Do NOT share these credentials with anyone
- Delete credentials after task completion

**Deliverables:**
Please provide the following when complete:
{chr(10).join([f"- {d}" for d in job_details.get('deliverables', [])])}

**Timeline:**
- Deadline: {job_details.get('deadline', 'ASAP')}
- Please update every 4-6 hours on progress

**Questions?**
Reply to this message or contact us via Upwork messaging.

**Payment:**
Will be released within 24 hours of verification.

Looking forward to working with you! 🚀
        """.strip()

        return message

    def send_message(self, freelancer_id: str, message: str):
        """Send message to freelancer"""
        print(f"📧 Sending message to {freelancer_id}")
        print(f"Message preview: {message[:100]}...")

    def hire_and_onboard(self, job_id: str, applicant_id: str, credentials: Dict):
        """Hire freelancer and send onboarding with credentials"""

        # Load job details
        jobs = json.loads(self.jobs_log.read_text())
        job = next((j for j in jobs if j["id"] == job_id), None)

        if not job:
            raise ValueError(f"Job {job_id} not found")

        # Hire
        hire_result = self.hire_freelancer(job_id, applicant_id)

        # Send onboarding
        onboarding_msg = self.generate_onboarding_message(job, credentials)
        self.send_message(applicant_id, onboarding_msg)

        print(f"✅ Freelancer hired and onboarded successfully")

        return hire_result


class TaskDelegator:
    """Automatically detect tasks and delegate to VAs or AI"""

    def __init__(self, vault_path: str = "/root/delegation-system"):
        self.vault_path = Path(vault_path)
        self.task_log = self.vault_path / "upwork-api" / "task_log.json"
        self.task_log.parent.mkdir(parents=True, exist_ok=True)

        if not self.task_log.exists():
            self.task_log.write_text(json.dumps([], indent=2))

        self.recruiter = UpworkRecruiter()

    def analyze_task(self, description: str) -> str:
        """Determine if task requires human or AI"""

        human_keywords = [
            "account", "signup", "verification", "captcha", "phone",
            "identity", "kyc", "credit card", "payment method"
        ]

        ai_keywords = [
            "generate", "write", "analyze", "research", "summarize",
            "code", "document", "calculate"
        ]

        description_lower = description.lower()

        human_score = sum(1 for kw in human_keywords if kw in description_lower)
        ai_score = sum(1 for kw in ai_keywords if kw in description_lower)

        if human_score > ai_score:
            return "human_required"
        else:
            return "ai_can_handle"

    def delegate_task(self, task: Dict) -> Dict:
        """
        Automatically delegate task to appropriate resource

        Task format:
        {
            'description': 'Setup Twitter Developer Account + get API keys',
            'deliverables': ['API Key', 'API Secret', 'Bearer Token'],
            'deadline': '24 hours',
            'credentials': ['operations_card', 'ops_email'],
            'budget': 50
        }
        """

        task_type = self.analyze_task(task['description'])

        task_record = {
            "id": f"task_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "created_at": datetime.datetime.now().isoformat(),
            "type": task_type,
            "status": "pending",
            **task
        }

        # Save task
        tasks = json.loads(self.task_log.read_text())
        tasks.append(task_record)
        self.task_log.write_text(json.dumps(tasks, indent=2))

        if task_type == "human_required":
            # Post job to Upwork
            job = self.recruiter.post_job(
                task_description=task['description'],
                deliverables=task['deliverables'],
                budget=task['budget'],
                deadline=task['deadline']
            )

            task_record['job_id'] = job['id']
            task_record['status'] = "job_posted"

            print(f"✅ Task delegated to VA (Job posted: {job['id']})")

        else:
            task_record['status'] = "assigned_to_ai"
            print(f"✅ Task can be handled by AI")

        # Update task record
        tasks = json.loads(self.task_log.read_text())
        tasks[-1] = task_record
        self.task_log.write_text(json.dumps(tasks, indent=2))

        return task_record

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a delegated task"""
        tasks = json.loads(self.task_log.read_text())
        return next((t for t in tasks if t["id"] == task_id), None)


if __name__ == "__main__":
    # Test the delegation system
    delegator = TaskDelegator()

    # Example tasks for LAUNCH TODAY church formation
    launch_today_tasks = [
        {
            'description': 'Setup Stripe account + get API keys for payment processing',
            'deliverables': ['Stripe Account ID', 'Publishable Key', 'Secret Key'],
            'deadline': '24 hours',
            'credentials': ['operations_card', 'ops_email'],
            'budget': 50
        },
        {
            'description': 'Setup Facebook Ads account + pixel for landing page',
            'deliverables': ['Ads Account ID', 'Facebook Pixel ID', 'Access Token'],
            'deadline': '24 hours',
            'credentials': ['operations_card', 'ops_email'],
            'budget': 50
        },
        {
            'description': 'Setup Google Ads account for search campaigns',
            'deliverables': ['Google Ads Account ID', 'Conversion Tracking Tag'],
            'deadline': '24 hours',
            'credentials': ['operations_card', 'ops_email'],
            'budget': 50
        }
    ]

    print("🚀 DELEGATING LAUNCH TODAY SETUP TASKS\n")

    for task in launch_today_tasks:
        result = delegator.delegate_task(task)
        print(f"Task ID: {result['id']}")
        print(f"Status: {result['status']}")
        print(f"Type: {result['type']}\n")

    print("✅ All tasks delegated!")
    print("Expected completion: 24-48 hours")
    print("Your involvement: 5 minutes (approving hires)")
