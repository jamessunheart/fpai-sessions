"""
Proactive monitoring engine
"""
import asyncio
import httpx
import time
import logging
import psutil
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import deque

from app.config import settings

logger = logging.getLogger(__name__)


class ServiceMonitor:
    """Monitors service health and performance"""

    def __init__(self):
        self.chief_url = settings.CHIEF_OF_STAFF_URL
        self.services = settings.services
        self.check_history: Dict[str, deque] = {}
        self.last_alert_time: Dict[str, datetime] = {}

        # Initialize history for each service
        for service in self.services:
            self.check_history[service['name']] = deque(maxlen=100)

    async def check_service(self, service: Dict) -> Dict:
        """
        Check a single service health

        Returns check result with status, response_time, etc.
        """
        name = service['name']
        port = service['port']
        url = f"http://localhost:{port}/health"

        start_time = time.time()

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    timeout=settings.HEALTH_CHECK_TIMEOUT
                )
                response_time = time.time() - start_time

                result = {
                    'service': name,
                    'port': port,
                    'status': 'healthy' if response.status_code == 200 else 'unhealthy',
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'timestamp': datetime.utcnow(),
                    'error': None
                }

                logger.info(f"{name}: {result['status']} ({response_time:.2f}s)")
                return result

        except httpx.TimeoutException:
            response_time = time.time() - start_time
            logger.warning(f"{name}: timeout after {response_time:.2f}s")
            return {
                'service': name,
                'port': port,
                'status': 'timeout',
                'status_code': None,
                'response_time': response_time,
                'timestamp': datetime.utcnow(),
                'error': 'Health check timed out'
            }

        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"{name}: {type(e).__name__}: {e}")
            return {
                'service': name,
                'port': port,
                'status': 'down',
                'status_code': None,
                'response_time': response_time,
                'timestamp': datetime.utcnow(),
                'error': str(e)
            }

    async def analyze_and_alert(self, check_result: Dict, service: Dict):
        """
        Analyze check result and send signal if issue detected
        """
        name = check_result['service']
        status = check_result['status']
        response_time = check_result['response_time']
        priority = service['priority']

        # Add to history
        self.check_history[name].append(check_result)

        # Don't alert too frequently (wait 10 minutes between alerts for same issue)
        last_alert = self.last_alert_time.get(name)
        if last_alert and (datetime.utcnow() - last_alert) < timedelta(minutes=10):
            return

        signal = None

        # Service Down
        if status == 'down':
            signal = {
                'source': 'proactive-monitor',
                'type': 'error',
                'title': f'{name} service is down',
                'description': f'Health check failed - service not responding on port {check_result["port"]}',
                'data': {
                    'service': name,
                    'port': check_result['port'],
                    'error': check_result['error'],
                    'priority': priority
                },
                'urgency_hint': 'urgent' if priority == 'critical' else 'important'
            }

        # Timeout
        elif status == 'timeout':
            signal = {
                'source': 'proactive-monitor',
                'type': 'error',
                'title': f'{name} health check timed out',
                'description': f'Service is not responding within {settings.HEALTH_CHECK_TIMEOUT}s timeout',
                'data': {
                    'service': name,
                    'port': check_result['port'],
                    'timeout': settings.HEALTH_CHECK_TIMEOUT,
                    'priority': priority
                },
                'urgency_hint': 'urgent' if priority == 'critical' else 'important'
            }

        # Very Slow Response
        elif response_time > settings.RESPONSE_TIME_VERY_SLOW_THRESHOLD:
            signal = {
                'source': 'proactive-monitor',
                'type': 'metric',
                'title': f'{name} responding very slowly',
                'description': f'Response time {response_time:.2f}s (threshold: {settings.RESPONSE_TIME_VERY_SLOW_THRESHOLD}s)',
                'data': {
                    'service': name,
                    'response_time': response_time,
                    'threshold': settings.RESPONSE_TIME_VERY_SLOW_THRESHOLD,
                    'priority': priority
                },
                'urgency_hint': 'important'
            }

        # Slow Response
        elif response_time > settings.RESPONSE_TIME_SLOW_THRESHOLD:
            # Get average from last 5 checks
            recent_checks = list(self.check_history[name])[-5:]
            if len(recent_checks) >= 3:
                avg_response = sum(c['response_time'] for c in recent_checks) / len(recent_checks)

                if avg_response > settings.RESPONSE_TIME_SLOW_THRESHOLD:
                    signal = {
                        'source': 'proactive-monitor',
                        'type': 'metric',
                        'title': f'{name} response time degraded',
                        'description': f'Average response time {avg_response:.2f}s over last 5 checks',
                        'data': {
                            'service': name,
                            'avg_response_time': avg_response,
                            'threshold': settings.RESPONSE_TIME_SLOW_THRESHOLD,
                            'priority': priority
                        }
                    }

        # Send signal if detected
        if signal:
            await self.send_signal(signal)
            self.last_alert_time[name] = datetime.utcnow()

    async def send_signal(self, signal: Dict):
        """Send signal to Chief of Staff"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.chief_url}/signal",
                    json=signal,
                    timeout=10.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Signal sent: {signal['title']} -> {result['category']}")
                else:
                    logger.error(f"Failed to send signal: {response.status_code}")

        except Exception as e:
            logger.error(f"Error sending signal: {e}")

    async def run_check_cycle(self):
        """Run one monitoring cycle"""
        logger.info("=== Starting monitoring cycle ===")

        for service in self.services:
            check_result = await self.check_service(service)
            await self.analyze_and_alert(check_result, service)

            # Small delay between checks
            await asyncio.sleep(0.5)

        logger.info("=== Monitoring cycle complete ===")

    async def run_forever(self):
        """Main monitoring loop"""
        logger.info(f"Proactive Monitor started - checking every {settings.CHECK_INTERVAL_SECONDS}s")
        logger.info(f"Monitoring {len(self.services)} services")
        logger.info(f"Sending alerts to: {self.chief_url}")

        while True:
            try:
                await self.run_check_cycle()
                await asyncio.sleep(settings.CHECK_INTERVAL_SECONDS)

            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute on error

    def get_status(self) -> Dict:
        """Get current monitoring status"""
        service_status = {}

        for service in self.services:
            name = service['name']
            history = list(self.check_history.get(name, []))

            if history:
                latest = history[-1]
                service_status[name] = {
                    'status': latest['status'],
                    'response_time': latest['response_time'],
                    'last_check': latest['timestamp'].isoformat(),
                    'checks_performed': len(history)
                }
            else:
                service_status[name] = {
                    'status': 'not_checked',
                    'checks_performed': 0
                }

        return {
            'services': service_status,
            'total_services': len(self.services),
            'chief_of_staff_url': self.chief_url
        }

    def get_local_server_metrics(self) -> Dict:
        """Get server metrics for local machine (primary)"""
        try:
            # Memory stats
            memory = psutil.virtual_memory()
            ram_total_gb = memory.total / (1024 ** 3)
            ram_used_gb = memory.used / (1024 ** 3)
            ram_free_gb = memory.available / (1024 ** 3)
            ram_percent = memory.percent

            # Disk stats (root partition)
            disk = psutil.disk_usage('/')
            disk_total_gb = disk.total / (1024 ** 3)
            disk_used_gb = disk.used / (1024 ** 3)
            disk_free_gb = disk.free / (1024 ** 3)
            disk_percent = disk.percent

            # CPU stats
            cpu_percent = psutil.cpu_percent(interval=0.1)

            return {
                'ram_total_gb': round(ram_total_gb, 2),
                'ram_used_gb': round(ram_used_gb, 2),
                'ram_free_gb': round(ram_free_gb, 2),
                'ram_percent': round(ram_percent, 1),
                'disk_total_gb': round(disk_total_gb, 2),
                'disk_used_gb': round(disk_used_gb, 2),
                'disk_free_gb': round(disk_free_gb, 2),
                'disk_percent': round(disk_percent, 1),
                'cpu_percent': round(cpu_percent, 1)
            }
        except Exception as e:
            logger.error(f"Error collecting local server metrics: {e}")
            return None

    async def get_remote_server_metrics(self, server_url: str) -> Optional[Dict]:
        """Get server metrics from remote server"""
        try:
            # Try to fetch from remote server's proactive-monitor
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{server_url}/server-health/local")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.warning(f"Could not fetch remote server metrics from {server_url}: {e}")
            return None

    async def get_server_health(self) -> Dict:
        """
        Get server health for both primary and secondary

        Returns:
            {
                "primary": {"ram_free_gb": 1.9, "disk_free_gb": 350, ...},
                "secondary": {"ram_free_gb": 12.0, "disk_free_gb": 420, ...}
            }
        """
        result = {}

        # Primary (local) metrics
        primary_metrics = self.get_local_server_metrics()
        if primary_metrics:
            result['primary'] = primary_metrics

        # Secondary (remote) metrics
        secondary_url = "http://162.0.208.88:8108"  # Secondary proactive-monitor
        secondary_metrics = await self.get_remote_server_metrics(secondary_url)
        if secondary_metrics:
            result['secondary'] = secondary_metrics

        return result


# Global instance
monitor = ServiceMonitor()
