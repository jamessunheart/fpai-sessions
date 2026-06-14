#!/usr/bin/env python3
"""
System Health Monitor
Monitors health of all droplets in the Full Potential AI system
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict


@dataclass
class DropletHealth:
    """Health status of a droplet"""
    id: str
    name: str
    url: str
    status: str  # online, degraded, offline, unknown
    response_time: float
    last_check: str
    capabilities: List[str]
    dependencies: List[str]
    error: str = None


class HealthMonitor:
    """Monitor health of all droplets"""

    def __init__(self, config_file: str = None):
        self.config_file = config_file
        self.droplets: List[Dict] = []
        self.health_results: List[DropletHealth] = []

    def load_config(self):
        """Load droplet configuration"""

        if self.config_file and os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.droplets = config.get('droplets', [])
        else:
            # Default droplets for testing
            self.droplets = [
                {'id': '1', 'name': 'Registry', 'url': 'http://localhost:8001'},
                {'id': '2', 'name': 'Dashboard', 'url': 'http://localhost:8002'},
                {'id': '3', 'name': 'Proxy Manager', 'url': 'http://localhost:8003'},
                {'id': '10', 'name': 'Orchestrator', 'url': 'http://localhost:8010'}
            ]

    async def check_droplet_health(self, session: aiohttp.ClientSession,
                                   droplet: Dict) -> DropletHealth:
        """Check health of a single droplet"""

        url = droplet['url'].rstrip('/')
        start_time = datetime.utcnow()

        try:
            # Check /health endpoint
            async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_time = (datetime.utcnow() - start_time).total_seconds()

                if response.status == 200:
                    health_data = await response.json()

                    # Get capabilities
                    capabilities = []
                    try:
                        async with session.get(f"{url}/capabilities",
                                              timeout=aiohttp.ClientTimeout(total=5)) as cap_response:
                            if cap_response.status == 200:
                                cap_data = await cap_response.json()
                                capabilities = cap_data.get('capabilities', [])
                    except Exception:
                        pass

                    # Get dependencies
                    dependencies = []
                    try:
                        async with session.get(f"{url}/dependencies",
                                              timeout=aiohttp.ClientTimeout(total=5)) as dep_response:
                            if dep_response.status == 200:
                                dep_data = await dep_response.json()
                                dependencies = dep_data.get('dependencies', [])
                    except Exception:
                        pass

                    # Determine status
                    droplet_status = health_data.get('status', 'unknown')

                    if droplet_status == 'active' and response_time < 1.0:
                        overall_status = 'online'
                    elif droplet_status == 'active':
                        overall_status = 'degraded'
                    else:
                        overall_status = 'degraded'

                    return DropletHealth(
                        id=droplet['id'],
                        name=droplet['name'],
                        url=url,
                        status=overall_status,
                        response_time=response_time,
                        last_check=datetime.utcnow().isoformat(),
                        capabilities=capabilities,
                        dependencies=dependencies
                    )
                else:
                    return DropletHealth(
                        id=droplet['id'],
                        name=droplet['name'],
                        url=url,
                        status='offline',
                        response_time=response_time,
                        last_check=datetime.utcnow().isoformat(),
                        capabilities=[],
                        dependencies=[],
                        error=f'HTTP {response.status}'
                    )

        except asyncio.TimeoutError:
            return DropletHealth(
                id=droplet['id'],
                name=droplet['name'],
                url=url,
                status='offline',
                response_time=5.0,
                last_check=datetime.utcnow().isoformat(),
                capabilities=[],
                dependencies=[],
                error='Timeout'
            )

        except Exception as e:
            return DropletHealth(
                id=droplet['id'],
                name=droplet['name'],
                url=url,
                status='offline',
                response_time=0.0,
                last_check=datetime.utcnow().isoformat(),
                capabilities=[],
                dependencies=[],
                error=str(e)
            )

    async def monitor_all(self) -> List[DropletHealth]:
        """Monitor health of all droplets"""

        async with aiohttp.ClientSession() as session:
            tasks = [self.check_droplet_health(session, droplet) for droplet in self.droplets]
            self.health_results = await asyncio.gather(*tasks)

        return self.health_results

    def generate_report(self, format: str = 'text') -> str:
        """Generate health report"""

        if format == 'json':
            return json.dumps([asdict(h) for h in self.health_results], indent=2)

        # Text format
        online = [h for h in self.health_results if h.status == 'online']
        degraded = [h for h in self.health_results if h.status == 'degraded']
        offline = [h for h in self.health_results if h.status == 'offline']

        report = f"""
🏥 FULL POTENTIAL AI - SYSTEM HEALTH REPORT
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Droplets: {len(self.health_results)}
🟢 Online: {len(online)}
🟡 Degraded: {len(degraded)}
🔴 Offline: {len(offline)}

System Health: {self._calculate_system_health()}%
"""

        if online:
            report += "\n🟢 ONLINE DROPLETS\n"
            report += "━" * 50 + "\n"
            for health in online:
                report += f"#{health.id} - {health.name}\n"
                report += f"   URL: {health.url}\n"
                report += f"   Response Time: {health.response_time:.3f}s\n"
                report += f"   Capabilities: {len(health.capabilities)}\n"
                report += f"   Dependencies: {len(health.dependencies)}\n\n"

        if degraded:
            report += "\n🟡 DEGRADED DROPLETS\n"
            report += "━" * 50 + "\n"
            for health in degraded:
                report += f"#{health.id} - {health.name}\n"
                report += f"   URL: {health.url}\n"
                report += f"   Response Time: {health.response_time:.3f}s\n"
                if health.error:
                    report += f"   Issue: {health.error}\n"
                report += "\n"

        if offline:
            report += "\n🔴 OFFLINE DROPLETS\n"
            report += "━" * 50 + "\n"
            for health in offline:
                report += f"#{health.id} - {health.name}\n"
                report += f"   URL: {health.url}\n"
                report += f"   Error: {health.error or 'Unknown'}\n\n"

        report += "━" * 50 + "\n"

        return report

    def _calculate_system_health(self) -> int:
        """Calculate overall system health percentage"""

        if not self.health_results:
            return 0

        online = len([h for h in self.health_results if h.status == 'online'])
        degraded = len([h for h in self.health_results if h.status == 'degraded'])

        # Online = 100%, Degraded = 50%, Offline = 0%
        total_health = (online * 100) + (degraded * 50)
        max_health = len(self.health_results) * 100

        return int((total_health / max_health) * 100)

    def save_report(self, filepath: str, format: str = 'text'):
        """Save health report to file"""

        report = self.generate_report(format)

        with open(filepath, 'w') as f:
            f.write(report)


def main():
    """Main entry point"""
    import argparse
    import os

    parser = argparse.ArgumentParser(description='Monitor Full Potential AI System Health')
    parser.add_argument('--config', help='Path to droplet configuration file')
    parser.add_argument('--output', help='Output file for report')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Report format')
    parser.add_argument('--watch', action='store_true',
                       help='Continuous monitoring mode')
    parser.add_argument('--interval', type=int, default=60,
                       help='Monitoring interval in seconds (for watch mode)')

    args = parser.parse_args()

    monitor = HealthMonitor(config_file=args.config)
    monitor.load_config()

    if args.watch:
        print(f"🔄 Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                asyncio.run(monitor.monitor_all())
                report = monitor.generate_report(args.format)
                print("\033[2J\033[H")  # Clear screen
                print(report)

                if args.output:
                    monitor.save_report(args.output, args.format)

                asyncio.run(asyncio.sleep(args.interval))

        except KeyboardInterrupt:
            print("\n\n✋ Monitoring stopped")

    else:
        print("🔍 Checking system health...")
        asyncio.run(monitor.monitor_all())

        report = monitor.generate_report(args.format)
        print(report)

        if args.output:
            monitor.save_report(args.output, args.format)
            print(f"📄 Report saved to: {args.output}")


if __name__ == '__main__':
    main()
