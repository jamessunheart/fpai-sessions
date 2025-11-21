"""
Progress Tracker - Maintains state of autonomous builds

Tracks each Sacred Loop step, progress percentage, files created, etc.
"""

from typing import Dict, List, Optional
from datetime import datetime
from .models import BuildProgress, BuildStatus, SacredLoopStep, StepProgress


class ProgressTracker:
    """In-memory progress tracking (TODO: Add database persistence)"""

    def __init__(self):
        self.builds: Dict[str, BuildProgress] = {}

    def create_build(
        self,
        build_id: str,
        droplet_id: int,
        droplet_name: str,
        architect_intent: str
    ) -> BuildProgress:
        """Initialize a new build"""
        # Define all Sacred Loop steps
        steps = [
            StepProgress(
                step=SacredLoopStep.INTENT,
                step_number=1,
                name="Architect Intent",
                status="pending"
            ),
            StepProgress(
                step=SacredLoopStep.SPEC_GENERATION,
                step_number=2,
                name="SPEC Generation",
                status="pending"
            ),
            StepProgress(
                step=SacredLoopStep.COORDINATOR_PACKAGE,
                step_number=3,
                name="Coordinator Package",
                status="pending"
            ),
            StepProgress(
                step=SacredLoopStep.APPRENTICE_BUILD,
                step_number=4,
                name="Apprentice Build (AI)",
                status="pending"
            ),
            StepProgress(
                step=SacredLoopStep.VERIFIER,
                step_number=5,
                name="Verifier",
                status="pending"
            ),
            StepProgress(
                step=SacredLoopStep.DEPLOYER,
                step_number=6,
                name="Deployer",
                status="pending"
            ),
            StepProgress(
                step=SacredLoopStep.REGISTRY_UPDATE,
                step_number=7,
                name="Registry Update",
                status="pending"
            ),
            StepProgress(
                step=SacredLoopStep.COMPLETE,
                step_number=8,
                name="Complete",
                status="pending"
            )
        ]

        progress = BuildProgress(
            build_id=build_id,
            droplet_id=droplet_id,
            droplet_name=droplet_name,
            status=BuildStatus.QUEUED,
            current_step=SacredLoopStep.INTENT,
            current_step_number=1,
            progress_percent=0,
            started_at=datetime.utcnow(),
            steps=steps
        )

        self.builds[build_id] = progress
        return progress

    def get_progress(self, build_id: str) -> Optional[BuildProgress]:
        """Get current progress for a build"""
        return self.builds.get(build_id)

    def list_builds(self, limit: int = 10, offset: int = 0) -> List[BuildProgress]:
        """List all builds"""
        all_builds = sorted(
            self.builds.values(),
            key=lambda x: x.started_at,
            reverse=True
        )
        return all_builds[offset:offset + limit]

    def update_status(self, build_id: str, status: BuildStatus):
        """Update overall build status"""
        if build_id in self.builds:
            self.builds[build_id].status = status

            if status == BuildStatus.COMPLETED:
                self.builds[build_id].completed_at = datetime.utcnow()
                self.builds[build_id].progress_percent = 100

    def start_step(self, build_id: str, step: SacredLoopStep):
        """Mark a step as started"""
        if build_id not in self.builds:
            return

        progress = self.builds[build_id]

        # Find the step
        for s in progress.steps:
            if s.step == step:
                s.status = "in_progress"
                s.started_at = datetime.utcnow()

                # Update current step
                progress.current_step = step
                progress.current_step_number = s.step_number

                # Update progress percentage (each step is 12.5%)
                progress.progress_percent = ((s.step_number - 1) / 8) * 100
                break

    def complete_step(self, build_id: str, step: SacredLoopStep):
        """Mark a step as completed"""
        if build_id not in self.builds:
            return

        progress = self.builds[build_id]

        # Find the step
        for s in progress.steps:
            if s.step == step:
                s.status = "completed"
                s.completed_at = datetime.utcnow()

                if s.started_at:
                    duration = (s.completed_at - s.started_at).total_seconds()
                    s.duration_seconds = int(duration)

                # Update progress percentage
                progress.progress_percent = (s.step_number / 8) * 100
                break

    def update_step_details(self, build_id: str, step: SacredLoopStep, details: dict):
        """Update step-specific details"""
        if build_id not in self.builds:
            return

        progress = self.builds[build_id]

        for s in progress.steps:
            if s.step == step:
                s.details.update(details)
                break

    def set_error(self, build_id: str, error: str):
        """Set error message for current step"""
        if build_id not in self.builds:
            return

        progress = self.builds[build_id]

        for s in progress.steps:
            if s.step == progress.current_step:
                s.status = "failed"
                s.error = error
                break

    def reset_to_step(self, build_id: str, step_number: int):
        """Reset build to a specific step (for retry)"""
        if build_id not in self.builds:
            return

        progress = self.builds[build_id]

        # Reset all steps from step_number onwards
        for s in progress.steps:
            if s.step_number >= step_number:
                s.status = "pending"
                s.started_at = None
                s.completed_at = None
                s.duration_seconds = None
                s.error = None
                s.details = {}

        # Update status
        progress.status = BuildStatus.IN_PROGRESS
        progress.current_step_number = step_number
