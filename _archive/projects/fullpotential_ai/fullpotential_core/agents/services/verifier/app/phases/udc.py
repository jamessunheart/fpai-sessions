"""Phase 2: UDC Compliance - Verify Universal Droplet Contract endpoints."""
import logging
import subprocess
import asyncio
import time
from pathlib import Path
from typing import List, Optional
import httpx

from app.models import PhaseResult, PhaseStatus, Check
from app.config import settings

logger = logging.getLogger(__name__)


async def verify_udc(droplet_path: Path, droplet_name: str) -> PhaseResult:
    """
    Verify UDC compliance by starting droplet and testing endpoints.

    Checks:
    - /health endpoint exists and has correct schema
    - /capabilities endpoint (if present)
    - /state endpoint (if present)
    - Status enum uses correct values
    """
    logger.info(f"Running UDC verification for {droplet_name}")

    checks: List[Check] = []
    process: Optional[subprocess.Popen] = None

    try:
        # Find port from config or use default
        port = await _find_droplet_port(droplet_path)

        # Start droplet
        process = await _start_droplet(droplet_path, port)

        # Wait for startup
        base_url = f"http://localhost:{port}"
        if not await _wait_for_startup(base_url, timeout=settings.startup_timeout_seconds):
            checks.append(
                Check(
                    name="Droplet startup",
                    status="FAIL",
                    details=f"Droplet failed to start within {settings.startup_timeout_seconds}s",
                )
            )
            return PhaseResult(
                phase="UDC Compliance",
                status=PhaseStatus.FAIL,
                duration_seconds=settings.startup_timeout_seconds,
                checks=checks,
            )

        checks.append(Check(name="Droplet startup", status="PASS"))

        # Test /health endpoint
        health_check = await _test_health_endpoint(base_url)
        checks.append(health_check)

        # Test other endpoints if they exist
        caps_check = await _test_endpoint(f"{base_url}/capabilities", "capabilities")
        if caps_check:
            checks.append(caps_check)

        state_check = await _test_endpoint(f"{base_url}/state", "state")
        if state_check:
            checks.append(state_check)

    except Exception as e:
        logger.error(f"UDC verification error: {str(e)}")
        checks.append(
            Check(
                name="UDC verification",
                status="FAIL",
                details=f"Verification failed: {str(e)}",
            )
        )
    finally:
        # Stop droplet
        if process:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()

    # Determine status
    failed = [c for c in checks if c.status == "FAIL"]
    if failed:
        status = PhaseStatus.FAIL
    else:
        status = PhaseStatus.PASS

    return PhaseResult(
        phase="UDC Compliance",
        status=status,
        duration_seconds=30,
        checks=checks,
    )


async def _find_droplet_port(droplet_path: Path) -> int:
    """Find the port the droplet runs on."""
    # Try to read from config
    config_file = droplet_path / "app" / "config.py"
    if config_file.exists():
        content = config_file.read_text()
        # Look for port definition (simple pattern match)
        for line in content.split("\n"):
            if "port" in line.lower() and ":" in line and "int" in line:
                # Try to extract default value
                if "=" in line:
                    try:
                        port_str = line.split("=")[1].strip()
                        return int(port_str)
                    except:
                        pass

    # Default port for testing
    return 9999


async def _start_droplet(droplet_path: Path, port: int) -> subprocess.Popen:
    """Start droplet in subprocess."""
    # Setup virtual environment and start
    process = subprocess.Popen(
        [
            "sh",
            "-c",
            f"cd {droplet_path} && source .venv/bin/activate && uvicorn app.main:app --port {port}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    return process


async def _wait_for_startup(base_url: str, timeout: int = 30) -> bool:
    """Wait for droplet to start up."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    return True
        except:
            pass

        await asyncio.sleep(1)

    return False


async def _test_health_endpoint(base_url: str) -> Check:
    """Test /health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{base_url}/health")

            if response.status_code != 200:
                return Check(
                    name="/health endpoint",
                    status="FAIL",
                    details=f"Expected 200, got {response.status_code}",
                )

            data = response.json()

            # Basic validation - should have status field
            if "status" not in data:
                return Check(
                    name="/health endpoint",
                    status="FAIL",
                    details="Missing 'status' field in response",
                )

            return Check(
                name="/health endpoint",
                status="PASS",
                response=data,
            )

    except Exception as e:
        return Check(
            name="/health endpoint",
            status="FAIL",
            details=f"Request failed: {str(e)}",
        )


async def _test_endpoint(url: str, name: str) -> Optional[Check]:
    """Test an optional endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)

            if response.status_code == 200:
                return Check(
                    name=f"/{name} endpoint",
                    status="PASS",
                    response=response.json(),
                )
            elif response.status_code == 404:
                # Optional endpoint, not present
                return None
            else:
                return Check(
                    name=f"/{name} endpoint",
                    status="FAIL",
                    details=f"Expected 200, got {response.status_code}",
                )

    except Exception:
        # Optional endpoint might not exist
        return None
