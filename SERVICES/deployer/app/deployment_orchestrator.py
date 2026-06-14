"""Main deployment orchestration"""

import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import (
    DeployRequest,
    DeployJobStatus,
    DeploymentStatus,
    DeploymentPhase,
    RegistrationInfo
)
from .ssh_manager import SSHManager
from .docker_deployer import DockerDeployer
from .registry_client import RegistryClient
from .config import settings


class DeploymentOrchestrator:
    """Orchestrates complete deployment process"""

    def __init__(self):
        """Initialize orchestrator"""
        self.registry = RegistryClient()

    async def execute_deployment(
        self,
        request: DeployRequest,
        job_status: DeployJobStatus
    ) -> DeployJobStatus:
        """
        Execute complete deployment.

        Returns updated job status.
        """
        print(f"\n🚀 Deploying {request.service_name}...")

        # Phase 1: Validate
        phase = await self._phase_validate(request)
        job_status.phases.append(phase)
        job_status.status = DeploymentStatus.VALIDATING

        if phase.status == "failed":
            job_status.status = DeploymentStatus.FAILED
            job_status.error = phase.error
            return job_status

        # Phase 2: Transfer files
        phase = await self._phase_transfer(request)
        job_status.phases.append(phase)
        job_status.status = DeploymentStatus.TRANSFERRING

        if phase.status == "failed":
            job_status.status = DeploymentStatus.FAILED
            job_status.error = phase.error
            return job_status

        # Phase 3: Build
        phase = await self._phase_build(request)
        job_status.phases.append(phase)
        job_status.status = DeploymentStatus.BUILDING

        if phase.status == "failed":
            job_status.status = DeploymentStatus.FAILED
            job_status.error = phase.error
            return job_status

        # Phase 4: Start service
        phase = await self._phase_start(request)
        job_status.phases.append(phase)
        job_status.status = DeploymentStatus.STARTING

        if phase.status == "failed":
            job_status.status = DeploymentStatus.FAILED
            job_status.error = phase.error
            return job_status

        # Phase 5: Verify service health
        phase = await self._phase_verify_health(request)
        job_status.phases.append(phase)
        job_status.status = DeploymentStatus.VERIFYING

        if phase.status == "failed":
            job_status.status = DeploymentStatus.FAILED
            job_status.error = phase.error
            return job_status

        # Phase 6: Register with Registry
        if request.auto_register:
            phase = await self._phase_register(request)
            job_status.phases.append(phase)
            job_status.status = DeploymentStatus.REGISTERING

            if phase.status == "success" and hasattr(phase, 'registration_info'):
                job_status.registration = phase.registration_info

        # Complete
        job_status.status = DeploymentStatus.COMPLETED
        job_status.success = True
        job_status.service_url = f"http://{settings.server_host}:{request.service_port}"

        # Calculate timing
        job_status.completed_at = datetime.now()
        job_status.duration_seconds = int(
            (job_status.completed_at - job_status.started_at).total_seconds()
        )

        print(f"\n✅ Deployment complete!")
        print(f"   Service URL: {job_status.service_url}")
        print(f"   Duration: {job_status.duration_seconds}s")

        return job_status

    async def _phase_validate(self, request: DeployRequest) -> DeploymentPhase:
        """Phase 1: Validate deployment request"""
        phase = DeploymentPhase(phase="Validation", status="running")

        try:
            # Check service path exists
            service_path = Path(request.service_path)
            if not service_path.exists():
                raise Exception(f"Service path not found: {request.service_path}")

            # Check for required files
            if request.deployment_method.value == "docker":
                dockerfile = service_path / "Dockerfile"
                if not dockerfile.exists():
                    raise Exception("Dockerfile not found")

            requirements = service_path / "requirements.txt"
            if not requirements.exists():
                print("⚠️  No requirements.txt found")

            phase.status = "success"
            phase.details = "Service files validated"

        except Exception as e:
            phase.status = "failed"
            phase.error = str(e)

        phase.completed_at = datetime.now()
        phase.duration_seconds = int(
            (phase.completed_at - phase.started_at).total_seconds()
        )

        return phase

    async def _phase_transfer(self, request: DeployRequest) -> DeploymentPhase:
        """Phase 2: Transfer files to server"""
        phase = DeploymentPhase(phase="Transfer", status="running")

        try:
            print("📤 Transferring files to server...")

            deployment_path = f"/opt/fpai/services/{request.service_name}"

            with SSHManager() as ssh:
                # Ensure deployment directory exists
                ssh.ensure_directory(deployment_path)

                # Transfer files
                success = ssh.transfer_directory(request.service_path, deployment_path)

                if not success:
                    raise Exception("File transfer failed")

            phase.status = "success"
            phase.details = f"Files transferred to {deployment_path}"

        except Exception as e:
            phase.status = "failed"
            phase.error = str(e)

        phase.completed_at = datetime.now()
        phase.duration_seconds = int(
            (phase.completed_at - phase.started_at).total_seconds()
        )

        return phase

    async def _phase_build(self, request: DeployRequest) -> DeploymentPhase:
        """Phase 3: Build service (Docker image, etc.)"""
        phase = DeploymentPhase(phase="Build", status="running")

        try:
            deployment_path = f"/opt/fpai/services/{request.service_name}"

            with SSHManager() as ssh:
                if request.deployment_method.value == "docker":
                    deployer = DockerDeployer(ssh)
                    success, image_id = deployer.build_docker_image(
                        request.service_name,
                        deployment_path
                    )

                    if not success:
                        raise Exception("Docker build failed")

                    phase.details = f"Docker image built: {image_id}"
                else:
                    # For systemd, install dependencies
                    success, _, stderr = ssh.execute_command(
                        f"cd {deployment_path} && pip install -r requirements.txt"
                    )

                    if not success:
                        raise Exception(f"Dependencies install failed: {stderr}")

                    phase.details = "Dependencies installed"

            phase.status = "success"

        except Exception as e:
            phase.status = "failed"
            phase.error = str(e)

        phase.completed_at = datetime.now()
        phase.duration_seconds = int(
            (phase.completed_at - phase.started_at).total_seconds()
        )

        return phase

    async def _phase_start(self, request: DeployRequest) -> DeploymentPhase:
        """Phase 4: Start service"""
        phase = DeploymentPhase(phase="Start Service", status="running")

        try:
            deployment_path = f"/opt/fpai/services/{request.service_name}"

            with SSHManager() as ssh:
                if request.deployment_method.value == "docker":
                    deployer = DockerDeployer(ssh)
                    success = deployer.deploy(
                        request.service_name,
                        deployment_path,
                        request.service_port,
                        request.environment_vars
                    )

                    if not success:
                        raise Exception("Docker deployment failed")

                    phase.details = "Docker container started"
                else:
                    # For systemd deployment
                    start_cmd = f"cd {deployment_path} && nohup uvicorn app.main:app --host 0.0.0.0 --port {request.service_port} > service.log 2>&1 &"
                    success, _, stderr = ssh.execute_command(start_cmd)

                    if not success:
                        raise Exception(f"Service start failed: {stderr}")

                    phase.details = "Service started with uvicorn"

            phase.status = "success"

        except Exception as e:
            phase.status = "failed"
            phase.error = str(e)

        phase.completed_at = datetime.now()
        phase.duration_seconds = int(
            (phase.completed_at - phase.started_at).total_seconds()
        )

        return phase

    async def _phase_verify_health(self, request: DeployRequest) -> DeploymentPhase:
        """Phase 5: Verify service is healthy"""
        phase = DeploymentPhase(phase="Verify Health", status="running")

        try:
            print("🔍 Checking service health...")

            # Wait for service to start
            await asyncio.sleep(5)

            # Check health endpoint
            max_attempts = 10
            for attempt in range(max_attempts):
                is_healthy = await self.registry.check_service_health(request.service_port)

                if is_healthy:
                    phase.status = "success"
                    phase.details = "Service is healthy"
                    break

                await asyncio.sleep(3)
            else:
                raise Exception("Service health check failed after 30s")

        except Exception as e:
            phase.status = "failed"
            phase.error = str(e)

        phase.completed_at = datetime.now()
        phase.duration_seconds = int(
            (phase.completed_at - phase.started_at).total_seconds()
        )

        return phase

    async def _phase_register(self, request: DeployRequest) -> DeploymentPhase:
        """Phase 6: Register with Registry"""
        phase = DeploymentPhase(phase="Register with Registry", status="running")

        try:
            print("📝 Registering with Registry...")

            response = await self.registry.register_service(
                request.service_name,
                request.service_port,
                request.droplet_id
            )

            if not response:
                raise Exception("Registry registration failed")

            # Extract registration info
            droplet_data = response.get("droplet", {})
            phase.registration_info = RegistrationInfo(
                droplet_id=droplet_data.get("id"),
                service_name=request.service_name,
                endpoint=droplet_data.get("endpoint"),
                registered_at=datetime.now(),
                registry_response=response
            )

            phase.status = "success"
            phase.details = f"Registered as Droplet #{droplet_data.get('id')}"

        except Exception as e:
            phase.status = "failed"
            phase.error = str(e)
            # Don't fail deployment if registration fails
            print(f"⚠️  Registration failed but deployment succeeded")

        phase.completed_at = datetime.now()
        phase.duration_seconds = int(
            (phase.completed_at - phase.started_at).total_seconds()
        )

        return phase
