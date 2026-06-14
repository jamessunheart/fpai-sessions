"""Main Auto-Fix Loop - Coordinates fixing until APPROVED"""

import httpx
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from .config import settings
from .models import FixIteration, Issue, FixJobStatus, FixStatus
from .issue_analyzer import IssueAnalyzer
from .fix_generator import FixGenerator
from .fix_applier import FixApplier


class AutoFixLoop:
    """
    Main auto-fix orchestrator.

    Implements the fix loop:
    1. Get Verifier report
    2. Analyze issues
    3. Generate fixes
    4. Apply fixes
    5. Re-verify
    6. Repeat until APPROVED or max iterations
    """

    def __init__(self):
        """Initialize auto-fix loop"""
        self.analyzer = IssueAnalyzer()
        self.generator = FixGenerator()
        self.applier = FixApplier()

    async def execute_fix_loop(
        self,
        droplet_path: str,
        droplet_name: str,
        initial_verification_job_id: str,
        max_iterations: int = 3
    ) -> FixJobStatus:
        """
        Execute the auto-fix loop.

        Returns final status after all iterations.
        """
        job_status = FixJobStatus(
            fix_job_id=f"fix-{initial_verification_job_id}",
            droplet_name=droplet_name,
            status=FixStatus.IN_PROGRESS,
            current_iteration=0,
            max_iterations=max_iterations,
            iterations=[],
            started_at=datetime.now()
        )

        current_verification_id = initial_verification_job_id

        for iteration_num in range(1, max_iterations + 1):
            print(f"\n🔄 Fix Iteration {iteration_num}/{max_iterations}")

            iteration = FixIteration(
                iteration=iteration_num,
                issues_found=[],
                fixes_attempted=[]
            )

            # Step 1: Get Verifier report
            print("📥 Fetching verification report...")
            report = await self._get_verification_report(current_verification_id)

            if not report:
                iteration.verification_result = "FAILED"
                job_status.iterations.append(iteration)
                break

            # Check decision
            decision = report.get("decision", "UNKNOWN")
            iteration.verification_result = decision

            if decision == "APPROVED":
                print(f"✅ Service APPROVED!")
                job_status.final_decision = "APPROVED"
                job_status.status = FixStatus.VERIFIED
                job_status.iterations.append(iteration)
                break

            # Step 2: Analyze issues
            print("🔍 Analyzing issues...")
            issues = self.analyzer.analyze_verification_report(report)
            iteration.issues_found = issues

            if not issues:
                print("⚠️  No fixable issues found")
                job_status.final_decision = "FIXES_REQUIRED"
                job_status.iterations.append(iteration)
                break

            print(f"📋 Found {len(issues)} issues:")
            for issue in issues:
                print(f"  • [{issue.severity}] {issue.description}")

            # Step 3: Generate fixes
            print("🛠️  Generating fixes...")
            fixes = await self.generator.generate_fixes(droplet_path, issues)
            iteration.fixes_attempted = fixes

            if not fixes:
                print("❌ Could not generate fixes")
                job_status.final_decision = "ABANDONED"
                job_status.iterations.append(iteration)
                break

            print(f"✅ Generated {len(fixes)} fixes")

            # Step 4: Apply fixes
            print("📝 Applying fixes...")
            apply_result = self.applier.apply_fixes(fixes)

            print(f"✅ Applied {apply_result['applied']} fixes")
            if apply_result['failed'] > 0:
                print(f"❌ Failed {apply_result['failed']} fixes")

            job_status.total_fixes_applied += apply_result['applied']

            # Step 5: Re-verify
            print("🔍 Re-verifying service...")
            new_verification_id = await self._submit_verification(droplet_path, droplet_name)

            if not new_verification_id:
                print("❌ Failed to submit re-verification")
                job_status.final_decision = "FAILED"
                job_status.iterations.append(iteration)
                break

            # Wait for re-verification
            await self._wait_for_verification(new_verification_id)
            current_verification_id = new_verification_id

            # Mark iteration complete
            iteration.completed_at = datetime.now()
            iteration.duration_seconds = int(
                (iteration.completed_at - iteration.started_at).total_seconds()
            )

            job_status.iterations.append(iteration)
            job_status.current_iteration = iteration_num

        # Final status
        if not job_status.final_decision:
            job_status.final_decision = "FIXES_REQUIRED"

        job_status.completed_at = datetime.now()
        job_status.duration_seconds = int(
            (job_status.completed_at - job_status.started_at).total_seconds()
        )

        if job_status.final_decision == "APPROVED":
            job_status.status = FixStatus.VERIFIED
        else:
            job_status.status = FixStatus.FAILED

        return job_status

    async def _get_verification_report(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get verification report from Verifier"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.verifier_url}/verify/{job_id}/report",
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"❌ Error fetching report: {e}")

        return None

    async def _submit_verification(self, droplet_path: str, droplet_name: str) -> Optional[str]:
        """Submit service for verification"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.verifier_url}/verify",
                    json={
                        "droplet_path": droplet_path,
                        "droplet_name": droplet_name,
                        "quick_mode": False
                    },
                    timeout=10.0
                )

                if response.status_code == 202:
                    data = response.json()
                    return data.get("job_id")

        except Exception as e:
            print(f"❌ Error submitting verification: {e}")

        return None

    async def _wait_for_verification(self, job_id: str, timeout: int = 180):
        """Wait for verification to complete"""
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{settings.verifier_url}/verify/{job_id}",
                        timeout=5.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        status = data.get("status")

                        if status in ["completed", "failed"]:
                            return True

            except:
                pass

            await asyncio.sleep(3)

        return False


# Import at end to avoid circular import
from datetime import datetime
