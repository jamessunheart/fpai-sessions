"""
Sacred Loop Orchestrator - The Brain of Autonomous Execution

This module orchestrates the entire Sacred Loop autonomously:
1. Intent (received via API)
2. SPEC Generation (via fp-tools)
3. Coordinator Package (create repo structure)
4. Apprentice Build (via Claude API) ← KEY INNOVATION
5. Verifier (run tests)
6. Deployer (deploy to server)
7. Registry Update (register droplet)
8. Report Complete (notify architect)
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
import anthropic

from .models import (
    BuildRequest,
    BuildStatus,
    SacredLoopStep,
    StepProgress,
    ApprovalMode
)
from .config import settings
from .progress_tracker import ProgressTracker


class BuildOrchestrator:
    """Orchestrates autonomous Sacred Loop execution"""

    def __init__(self):
        self.claude_client = None
        if settings.anthropic_api_key:
            self.claude_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def execute_autonomous_build(
        self,
        build_id: str,
        request: BuildRequest,
        progress_tracker: ProgressTracker
    ):
        """
        Execute the full Sacred Loop autonomously.

        This is the main orchestration method that runs all 8 steps
        without human intervention (except approval gates if configured).
        """
        try:
            # Update status to in_progress
            progress_tracker.update_status(build_id, BuildStatus.IN_PROGRESS)

            # STEP 1: Intent (Already captured)
            await self._step_1_intent(build_id, request, progress_tracker)

            # STEP 2: SPEC Generation
            spec_content = await self._step_2_spec_generation(build_id, request, progress_tracker)

            # Approval gate (if checkpoint mode)
            if request.approval_mode == ApprovalMode.CHECKPOINTS:
                await self._wait_for_approval(build_id, progress_tracker, "spec_generated")

            # STEP 3: Coordinator Package
            repo_path = await self._step_3_coordinator_package(build_id, request, spec_content, progress_tracker)

            # STEP 4: Apprentice Build (THE MAGIC - Autonomous AI Building)
            await self._step_4_apprentice_build(build_id, request, repo_path, spec_content, progress_tracker)

            # STEP 5: Verifier
            test_results = await self._step_5_verifier(build_id, repo_path, progress_tracker)

            # STEP 6: Deployer
            if request.auto_deploy:
                deployment_url = await self._step_6_deployer(build_id, repo_path, progress_tracker)
            else:
                deployment_url = None

            # Approval gate (if final mode)
            if request.approval_mode == ApprovalMode.FINAL:
                await self._wait_for_approval(build_id, progress_tracker, "built_and_tested")

            # STEP 7: Registry Update
            await self._step_7_registry_update(build_id, request, deployment_url, progress_tracker)

            # STEP 8: Complete
            await self._step_8_complete(build_id, request, progress_tracker)

            # Mark as completed
            progress_tracker.update_status(build_id, BuildStatus.COMPLETED)

        except Exception as e:
            # Mark as failed
            progress_tracker.update_status(build_id, BuildStatus.FAILED)
            progress_tracker.set_error(build_id, str(e))
            raise

    async def _step_1_intent(self, build_id: str, request: BuildRequest, progress_tracker: ProgressTracker):
        """Step 1: Capture architect intent"""
        progress_tracker.start_step(build_id, SacredLoopStep.INTENT)

        # Intent already captured in the request
        progress_tracker.update_step_details(build_id, SacredLoopStep.INTENT, {
            "architect_intent": request.architect_intent,
            "droplet_id": request.droplet_id,
            "approval_mode": request.approval_mode
        })

        progress_tracker.complete_step(build_id, SacredLoopStep.INTENT)

    async def _step_2_spec_generation(
        self,
        build_id: str,
        request: BuildRequest,
        progress_tracker: ProgressTracker
    ) -> str:
        """Step 2: Generate SPEC using fp-tools or Claude API"""
        progress_tracker.start_step(build_id, SacredLoopStep.SPEC_GENERATION)

        # Try using fp-tools if available
        if os.path.exists(settings.fp_tools_path):
            try:
                # Call fp-tools to generate SPEC
                result = subprocess.run(
                    [
                        settings.fp_tools_path,
                        "spec",
                        "--droplet-id", str(request.droplet_id or 0),
                        "--intent", request.architect_intent
                    ],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    # Parse output to find SPEC file path
                    for line in result.stdout.split("\n"):
                        if "SPEC generated:" in line:
                            spec_file = line.split("SPEC generated:")[-1].strip()
                            with open(spec_file, 'r') as f:
                                spec_content = f.read()

                            progress_tracker.update_step_details(build_id, SacredLoopStep.SPEC_GENERATION, {
                                "spec_file": spec_file,
                                "method": "fp-tools"
                            })
                            progress_tracker.complete_step(build_id, SacredLoopStep.SPEC_GENERATION)
                            return spec_content
            except Exception as e:
                # Fall through to Claude API
                pass

        # Fallback: Use Claude API to generate SPEC
        if self.claude_client:
            spec_content = await self._generate_spec_with_claude(request.architect_intent)
            progress_tracker.update_step_details(build_id, SacredLoopStep.SPEC_GENERATION, {
                "method": "claude_api"
            })
            progress_tracker.complete_step(build_id, SacredLoopStep.SPEC_GENERATION)
            return spec_content

        raise Exception("No SPEC generation method available (fp-tools or Claude API)")

    async def _generate_spec_with_claude(self, intent: str) -> str:
        """Generate SPEC using Claude API"""
        message = self.claude_client.messages.create(
            model=settings.claude_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"""Generate a detailed technical SPEC for this droplet:

{intent}

Include:
- Purpose and vision
- Core requirements
- API endpoints
- Technical stack (FastAPI + Pydantic)
- UDC compliance requirements
- Success criteria
- Example usage

Return only the SPEC in markdown format."""
            }]
        )

        return message.content[0].text

    async def _step_3_coordinator_package(
        self,
        build_id: str,
        request: BuildRequest,
        spec_content: str,
        progress_tracker: ProgressTracker
    ) -> str:
        """Step 3: Create droplet repository structure"""
        progress_tracker.start_step(build_id, SacredLoopStep.COORDINATOR_PACKAGE)

        # Determine droplet name
        droplet_name = request.droplet_name or f"droplet-{request.droplet_id}"
        repo_path = f"{settings.development_base_path}/agents/services/{droplet_name}"

        # Create directory structure
        os.makedirs(f"{repo_path}/app", exist_ok=True)
        os.makedirs(f"{repo_path}/tests", exist_ok=True)
        os.makedirs(f"{repo_path}/docs", exist_ok=True)

        # Write SPEC
        with open(f"{repo_path}/docs/SPEC.md", 'w') as f:
            f.write(spec_content)

        # Copy Foundation Files (if they exist)
        if os.path.exists(settings.foundation_files_path):
            os.makedirs(f"{repo_path}/docs/foundation-files", exist_ok=True)
            # TODO: Copy foundation files

        # Create basic file structure
        files_created = [
            f"{repo_path}/app/__init__.py",
            f"{repo_path}/tests/__init__.py",
            f"{repo_path}/docs/SPEC.md"
        ]

        progress_tracker.update_step_details(build_id, SacredLoopStep.COORDINATOR_PACKAGE, {
            "repo_path": repo_path,
            "files_created": files_created
        })

        progress_tracker.complete_step(build_id, SacredLoopStep.COORDINATOR_PACKAGE)
        return repo_path

    async def _step_4_apprentice_build(
        self,
        build_id: str,
        request: BuildRequest,
        repo_path: str,
        spec_content: str,
        progress_tracker: ProgressTracker
    ):
        """
        Step 4: Apprentice Build - THE KEY INNOVATION

        Uses Claude API to autonomously generate all code files
        based on the SPEC. This is what makes true automation possible.
        """
        progress_tracker.start_step(build_id, SacredLoopStep.APPRENTICE_BUILD)

        if not self.claude_client:
            raise Exception("Claude API not configured - cannot build autonomously")

        # Read Foundation Files for context
        foundation_context = self._load_foundation_files()

        # Autonomous code generation
        iteration = 0
        max_iterations = settings.max_build_iterations

        while iteration < max_iterations:
            iteration += 1

            # Generate code via Claude API
            build_prompt = self._create_build_prompt(spec_content, foundation_context, iteration)

            message = self.claude_client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.max_tokens,
                messages=[{"role": "user", "content": build_prompt}]
            )

            # Extract files from response
            files = self._extract_files_from_response(message.content[0].text)

            # Write files to repository
            for file_path, file_content in files.items():
                full_path = f"{repo_path}/{file_path}"
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(file_content)

            # Update progress
            progress_tracker.update_step_details(build_id, SacredLoopStep.APPRENTICE_BUILD, {
                "iteration": iteration,
                "files_created": list(files.keys())
            })

            # Run tests
            test_passed = await self._run_tests(repo_path)

            if test_passed:
                # Success!
                progress_tracker.complete_step(build_id, SacredLoopStep.APPRENTICE_BUILD)
                return

        # Max iterations reached
        raise Exception(f"Build failed after {max_iterations} iterations")

    def _create_build_prompt(self, spec_content: str, foundation_context: str, iteration: int) -> str:
        """Create the prompt for autonomous building"""
        return f"""Build a complete FastAPI service based on this SPEC:

{spec_content}

Foundation Files Context:
{foundation_context}

Create ALL required files:
1. app/main.py - FastAPI application with all endpoints
2. app/models.py - Pydantic models
3. app/config.py - Settings from environment variables
4. tests/test_api.py - Pytest tests for all endpoints
5. requirements.txt - Python dependencies
6. Dockerfile - Docker containerization
7. README.md - Documentation
8. .env.example - Environment variables template

Return files in this format:
```filename
file content here
```

Iteration: {iteration}
Make sure all code is production-ready, follows best practices, and passes tests."""

    def _extract_files_from_response(self, response_text: str) -> dict:
        """Extract files from Claude's response"""
        files = {}
        current_file = None
        current_content = []

        for line in response_text.split("\n"):
            if line.startswith("```") and not line.strip() == "```":
                # New file starting
                if current_file:
                    files[current_file] = "\n".join(current_content)
                current_file = line.replace("```", "").strip()
                current_content = []
            elif line == "```":
                # File ending
                if current_file:
                    files[current_file] = "\n".join(current_content)
                    current_file = None
                    current_content = []
            elif current_file:
                current_content.append(line)

        return files

    async def _run_tests(self, repo_path: str) -> bool:
        """Run pytest tests"""
        try:
            result = subprocess.run(
                ["pytest", f"{repo_path}/tests"],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0
        except:
            return False

    def _load_foundation_files(self) -> str:
        """Load Foundation Files for context"""
        # TODO: Load actual foundation files
        return "Foundation files context..."

    async def _step_5_verifier(self, build_id: str, repo_path: str, progress_tracker: ProgressTracker) -> bool:
        """Step 5: Run verifier checks"""
        progress_tracker.start_step(build_id, SacredLoopStep.VERIFIER)

        # Run tests
        tests_passed = await self._run_tests(repo_path)

        progress_tracker.update_step_details(build_id, SacredLoopStep.VERIFIER, {
            "tests_passed": tests_passed
        })

        progress_tracker.complete_step(build_id, SacredLoopStep.VERIFIER)
        return tests_passed

    async def _step_6_deployer(self, build_id: str, repo_path: str, progress_tracker: ProgressTracker) -> str:
        """Step 6: Deploy to server"""
        progress_tracker.start_step(build_id, SacredLoopStep.DEPLOYER)

        # TODO: Implement actual deployment
        deployment_url = "http://localhost:8400"

        progress_tracker.update_step_details(build_id, SacredLoopStep.DEPLOYER, {
            "deployment_url": deployment_url
        })

        progress_tracker.complete_step(build_id, SacredLoopStep.DEPLOYER)
        return deployment_url

    async def _step_7_registry_update(
        self,
        build_id: str,
        request: BuildRequest,
        deployment_url: Optional[str],
        progress_tracker: ProgressTracker
    ):
        """Step 7: Update Registry"""
        progress_tracker.start_step(build_id, SacredLoopStep.REGISTRY_UPDATE)

        # TODO: Call Registry API to register droplet

        progress_tracker.complete_step(build_id, SacredLoopStep.REGISTRY_UPDATE)

    async def _step_8_complete(self, build_id: str, request: BuildRequest, progress_tracker: ProgressTracker):
        """Step 8: Mark complete and notify"""
        progress_tracker.start_step(build_id, SacredLoopStep.COMPLETE)

        # TODO: Send notifications (Slack, email, etc.)

        progress_tracker.complete_step(build_id, SacredLoopStep.COMPLETE)

    async def _wait_for_approval(self, build_id: str, progress_tracker: ProgressTracker, checkpoint: str):
        """Wait for human approval at checkpoint"""
        progress_tracker.update_status(build_id, BuildStatus.WAITING_APPROVAL)
        # TODO: Implement actual waiting mechanism
        pass

    async def resume_build(self, build_id: str):
        """Resume a paused build"""
        # TODO: Implement resume logic
        pass

    async def retry_build(self, build_id: str, from_step: int, progress_tracker: ProgressTracker):
        """Retry a failed build from a specific step"""
        # TODO: Implement retry logic
        pass
