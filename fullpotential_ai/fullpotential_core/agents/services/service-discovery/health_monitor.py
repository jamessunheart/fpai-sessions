#!/usr/bin/env python3
"""
Service Health Monitor Daemon
Continuously monitors services and auto-restarts failed ones
"""
import json
import time
import subprocess
import logging
import requests
from pathlib import Path
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CATALOG_PATH = Path("/Users/jamessunheart/Development/agents/services/SERVICE_CATALOG.json")
SERVICES_DIR = Path("/Users/jamessunheart/Development/SERVICES")
CHECK_INTERVAL = 30  # seconds
RESTART_COOLDOWN = 300  # 5 minutes before retry


class ServiceMonitor:
    def __init__(self):
        self.last_restart = {}  # service_name -> timestamp
        self.restart_count = {}  # service_name -> count

    def load_catalog(self):
        """Load service catalog"""
        try:
            with open(CATALOG_PATH) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load catalog: {e}")
            return None

    def check_service_health(self, service):
        """Check if a service is responding"""
        if not service.get('port'):
            return None

        try:
            resp = requests.get(
                f"http://localhost:{service['port']}/health",
                timeout=2
            )
            return resp.status_code == 200
        except:
            return False

    def should_restart(self, service_name):
        """Check if enough time has passed since last restart"""
        if service_name not in self.last_restart:
            return True

        time_since = time.time() - self.last_restart[service_name]
        return time_since > RESTART_COOLDOWN

    def restart_service(self, service):
        """Attempt to restart a service"""
        service_name = service['name']
        service_dir = SERVICES_DIR / service_name

        if not service_dir.exists():
            logger.warning(f"Service directory not found: {service_name}")
            return False

        # Check for start script
        start_script = service_dir / "start.sh"
        main_py = service_dir / "main.py"
        app_dir = service_dir / "app"

        try:
            if start_script.exists():
                logger.info(f"Restarting {service_name} using start.sh...")
                subprocess.Popen(
                    ["bash", "start.sh"],
                    cwd=service_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            elif main_py.exists():
                logger.info(f"Restarting {service_name} using main.py...")
                subprocess.Popen(
                    ["python3", "main.py"],
                    cwd=service_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            elif app_dir.exists():
                logger.info(f"Restarting {service_name} using uvicorn...")
                subprocess.Popen(
                    ["python3", "-m", "uvicorn", "app.main:app",
                     "--host", "0.0.0.0", "--port", str(service['port'])],
                    cwd=service_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            else:
                logger.warning(f"No start method found for {service_name}")
                return False

            # Track restart
            self.last_restart[service_name] = time.time()
            self.restart_count[service_name] = self.restart_count.get(service_name, 0) + 1

            logger.info(f"✅ Restart initiated for {service_name} (attempt #{self.restart_count[service_name]})")
            return True

        except Exception as e:
            logger.error(f"Failed to restart {service_name}: {e}")
            return False

    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("🔍 Service Health Monitor started")
        logger.info(f"Check interval: {CHECK_INTERVAL}s")
        logger.info(f"Restart cooldown: {RESTART_COOLDOWN}s")
        logger.info("")

        iteration = 0

        while True:
            try:
                iteration += 1
                logger.info(f"=== Health Check #{iteration} ===")

                catalog = self.load_catalog()
                if not catalog:
                    logger.warning("Could not load catalog, skipping check")
                    time.sleep(CHECK_INTERVAL)
                    continue

                critical_services = ['nexus-event-bus', 'unified-chat', 'registry']
                services_to_check = catalog['services']

                # Prioritize critical services
                for service in services_to_check:
                    if service['status'] == 'offline' and service.get('port'):
                        is_critical = service['name'] in critical_services

                        # Check if actually down
                        is_healthy = self.check_service_health(service)

                        if not is_healthy:
                            if is_critical or self.should_restart(service['name']):
                                logger.warning(f"⚠️  Service DOWN: {service['name']} (port {service['port']})")

                                if is_critical:
                                    logger.error(f"🚨 CRITICAL service down: {service['name']}")

                                if self.should_restart(service['name']):
                                    self.restart_service(service)
                                else:
                                    logger.info(f"   Skipping (in cooldown)")

                # Report status
                total_checked = len([s for s in services_to_check if s.get('port')])
                total_restarts = sum(self.restart_count.values())
                logger.info(f"Checked {total_checked} services | Total restarts: {total_restarts}")
                logger.info("")

                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("\n👋 Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                time.sleep(CHECK_INTERVAL)


def main():
    monitor = ServiceMonitor()
    monitor.monitor_loop()


if __name__ == "__main__":
    main()
