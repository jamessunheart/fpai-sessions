"""Job manager for verification jobs."""
import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from uuid import uuid4

from app.models import (
    JobStatus,
    Decision,
    VerificationSummary,
    VerificationReport,
    PhaseResult,
    Issue,
)
from app.phases.structure import verify_structure
from app.phases.udc import verify_udc
from app.phases.security import verify_security
from app.phases.functionality import verify_functionality
from app.phases.quality import verify_code_quality
from app.phases.decision import make_decision

logger = logging.getLogger(__name__)


class VerificationJob:
    """A verification job."""

    def __init__(self, job_id: str, droplet_name: str, droplet_path: Path):
        self.job_id = job_id
        self.droplet_name = droplet_name
        self.droplet_path = droplet_path
        self.status = JobStatus.QUEUED
        self.current_phase: Optional[str] = None
        self.progress_percent = 0
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.decision: Optional[Decision] = None
        self.phases: List[PhaseResult] = []
        self.all_issues: List[Issue] = []
        self.strengths: List[str] = []
        self.recommendations: List[str] = []


class JobManager:
    """Manages verification jobs."""

    def __init__(self):
        self.jobs: Dict[str, VerificationJob] = {}
        self.running_jobs: int = 0
        self.max_concurrent = 3

    def create_job(self, droplet_name: str, droplet_path: str) -> str:
        """Create a new verification job."""
        job_id = f"ver-{uuid4().hex[:8]}"

        job = VerificationJob(
            job_id=job_id,
            droplet_name=droplet_name,
            droplet_path=Path(droplet_path),
        )

        self.jobs[job_id] = job
        logger.info(f"Created verification job {job_id} for {droplet_name}")

        return job_id

    async def run_job(self, job_id: str):
        """Run a verification job."""
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            logger.info(f"Starting verification job {job_id}")

            # Phase 1: Structure
            job.current_phase = "Phase 1: Structure Scan"
            job.progress_percent = 10
            phase1 = verify_structure(job.droplet_path)
            job.phases.append(phase1)

            # Phase 2: UDC Compliance
            job.current_phase = "Phase 2: UDC Compliance"
            job.progress_percent = 30
            phase2 = await verify_udc(job.droplet_path, job.droplet_name)
            job.phases.append(phase2)

            # Phase 3: Security
            job.current_phase = "Phase 3: Security"
            job.progress_percent = 50
            phase3 = verify_security(job.droplet_path)
            job.phases.append(phase3)

            # Collect security issues
            # TODO: Extract issues from phase3

            # Phase 4: Functionality
            job.current_phase = "Phase 4: Functionality"
            job.progress_percent = 70
            phase4 = verify_functionality(job.droplet_path)
            job.phases.append(phase4)

            # Phase 5: Code Quality
            job.current_phase = "Phase 5: Code Quality"
            job.progress_percent = 85
            phase5 = verify_code_quality(job.droplet_path)
            job.phases.append(phase5)

            # Phase 6: Decision
            job.current_phase = "Phase 6: Making Decision"
            job.progress_percent = 95

            decision, strengths, recommendations = make_decision(
                job.phases, job.all_issues
            )

            job.decision = decision
            job.strengths = strengths
            job.recommendations = recommendations

            # Complete
            job.status = JobStatus.COMPLETED
            job.progress_percent = 100
            job.completed_at = datetime.utcnow()

            logger.info(
                f"Completed verification job {job_id} with decision: {decision}"
            )

        except Exception as e:
            logger.error(f"Error running job {job_id}: {str(e)}", exc_info=True)
            job.status = JobStatus.FAILED
            job.completed_at = datetime.utcnow()

    def get_job(self, job_id: str) -> Optional[VerificationJob]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def get_recent_jobs(self, limit: int = 10) -> List[VerificationJob]:
        """Get recent completed jobs."""
        completed = [
            j for j in self.jobs.values() if j.status == JobStatus.COMPLETED
        ]
        completed.sort(key=lambda x: x.completed_at or datetime.min, reverse=True)
        return completed[:limit]

    def get_summary(self, job: VerificationJob) -> Optional[VerificationSummary]:
        """Get summary for a job."""
        if job.status != JobStatus.COMPLETED:
            return None

        # Count issues
        critical = len([i for i in job.all_issues if i.severity.value == "critical"])
        important = len([i for i in job.all_issues if i.severity.value == "important"])
        minor = len([i for i in job.all_issues if i.severity.value == "minor"])

        # Get test results from functionality phase
        tests_passing = "Unknown"
        coverage_percent = None

        for phase in job.phases:
            if phase.phase == "Functionality":
                for check in phase.checks:
                    if "tests passed" in check.details.lower():
                        tests_passing = check.details
                    elif "coverage" in check.details.lower():
                        # Extract coverage percentage
                        import re

                        match = re.search(r"(\d+)%", check.details)
                        if match:
                            coverage_percent = int(match.group(1))

        return VerificationSummary(
            critical_issues=critical,
            important_issues=important,
            minor_issues=minor,
            tests_passing=tests_passing,
            coverage_percent=coverage_percent,
        )


# Global job manager instance
job_manager = JobManager()
