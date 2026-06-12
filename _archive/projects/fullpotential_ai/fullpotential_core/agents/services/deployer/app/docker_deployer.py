"""Docker-based deployment"""

from typing import Tuple
from pathlib import Path

from .ssh_manager import SSHManager
from .config import settings


class DockerDeployer:
    """Deploys services using Docker on remote server"""

    def __init__(self, ssh: SSHManager):
        """Initialize Docker deployer"""
        self.ssh = ssh

    def check_docker_available(self) -> bool:
        """Check if Docker is available on server"""
        success, stdout, _ = self.ssh.execute_command("docker --version")
        return success and "Docker version" in stdout

    def check_docker_network(self, network_name: str) -> bool:
        """Check if Docker network exists"""
        success, stdout, _ = self.ssh.execute_command(
            f"docker network ls --format '{{{{.Name}}}}' | grep '^{network_name}$'"
        )
        return success and network_name in stdout

    def create_docker_network(self, network_name: str) -> bool:
        """Create Docker network if it doesn't exist"""
        if self.check_docker_network(network_name):
            print(f"✅ Docker network '{network_name}' exists")
            return True

        print(f"📦 Creating Docker network '{network_name}'...")
        success, _, stderr = self.ssh.execute_command(
            f"docker network create {network_name}"
        )

        if success:
            print(f"✅ Docker network created")
            return True
        else:
            print(f"❌ Failed to create network: {stderr}")
            return False

    def stop_existing_container(self, service_name: str) -> bool:
        """Stop and remove existing container"""
        print(f"🛑 Stopping existing container '{service_name}'...")

        # Stop container
        self.ssh.execute_command(f"docker stop {service_name} 2>/dev/null || true")

        # Remove container
        success, _, _ = self.ssh.execute_command(
            f"docker rm {service_name} 2>/dev/null || true"
        )

        return True  # Always return True, container might not exist

    def build_docker_image(
        self,
        service_name: str,
        deployment_path: str
    ) -> Tuple[bool, str]:
        """
        Build Docker image for service.

        Returns (success, image_id)
        """
        print(f"🔨 Building Docker image...")

        # Check if Dockerfile exists
        if not self.ssh.file_exists(f"{deployment_path}/Dockerfile"):
            print(f"❌ Dockerfile not found in {deployment_path}")
            return False, ""

        # Build image
        build_cmd = f"cd {deployment_path} && docker build -t {service_name}:latest ."
        success, stdout, stderr = self.ssh.execute_command(build_cmd)

        if success:
            print(f"✅ Docker image built")
            return True, f"{service_name}:latest"
        else:
            print(f"❌ Docker build failed:")
            print(stderr)
            return False, ""

    def run_docker_container(
        self,
        service_name: str,
        image_id: str,
        service_port: int,
        env_vars: dict = None
    ) -> bool:
        """
        Run Docker container.

        Returns True if successful.
        """
        print(f"🚀 Starting Docker container...")

        # Build environment variables string
        env_string = ""
        if env_vars:
            for key, value in env_vars.items():
                env_string += f" -e {key}={value}"

        # Build run command
        run_cmd = f"""docker run -d \\
            --name {service_name} \\
            --network {settings.default_network} \\
            -p {service_port}:{service_port} \\
            {env_string} \\
            --restart unless-stopped \\
            {image_id}
        """

        success, stdout, stderr = self.ssh.execute_command(run_cmd)

        if success:
            container_id = stdout.strip()[:12]
            print(f"✅ Container started: {container_id}")
            return True
        else:
            print(f"❌ Container start failed:")
            print(stderr)
            return False

    def check_container_running(self, service_name: str) -> bool:
        """Check if container is running"""
        success, stdout, _ = self.ssh.execute_command(
            f"docker ps --filter name={service_name} --format '{{{{.Names}}}}'"
        )
        return success and service_name in stdout

    def get_container_logs(self, service_name: str, lines: int = 50) -> str:
        """Get container logs"""
        success, stdout, _ = self.ssh.execute_command(
            f"docker logs --tail {lines} {service_name}"
        )
        return stdout if success else ""

    def deploy(
        self,
        service_name: str,
        deployment_path: str,
        service_port: int,
        env_vars: dict = None
    ) -> bool:
        """
        Complete Docker deployment.

        Returns True if successful.
        """
        # 1. Check Docker is available
        if not self.check_docker_available():
            print("❌ Docker not available on server")
            return False

        # 2. Ensure network exists
        if not self.create_docker_network(settings.default_network):
            print("❌ Failed to create Docker network")
            return False

        # 3. Stop existing container
        self.stop_existing_container(service_name)

        # 4. Build image
        success, image_id = self.build_docker_image(service_name, deployment_path)
        if not success:
            return False

        # 5. Run container
        if not self.run_docker_container(service_name, image_id, service_port, env_vars):
            return False

        # 6. Verify container is running
        import time
        time.sleep(2)  # Give container time to start

        if not self.check_container_running(service_name):
            print("❌ Container not running after start")
            logs = self.get_container_logs(service_name, 20)
            print("Container logs:")
            print(logs)
            return False

        print(f"✅ Docker deployment successful")
        return True
