#!/usr/bin/env python3
"""
Comprehensive Service Scanner
Discovers ALL running services and updates SSOT with real data
"""

import json
import subprocess
import requests
from datetime import datetime
from pathlib import Path

class ServiceScanner:
    """Scan and catalog all running services"""

    def __init__(self):
        self.services = []
        self.base_dir = Path("/Users/jamessunheart/Development")

    def get_listening_ports(self):
        """Find all ports with services listening"""
        try:
            cmd = "lsof -i -P -n | grep LISTEN | grep ':8'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            ports = {}
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 9:
                    # Port is in parts[8], format is "*:8000" or "127.0.0.1:8400"
                    port_part = parts[8].split(':')[-1].split('(')[0]
                    if port_part.isdigit() and port_part.startswith('8'):
                        pid = parts[1]
                        process = parts[0]
                        port = int(port_part)
                        if port not in ports:  # Avoid duplicates
                            ports[port] = {
                                'pid': pid,
                                'process': process
                            }

            return ports
        except Exception as e:
            print(f"Error getting ports: {e}")
            return {}

    def check_service_health(self, port):
        """Check if service responds to health check"""
        endpoints = ['/health', '/api/health', '/']

        for endpoint in endpoints:
            try:
                url = f"http://localhost:{port}{endpoint}"
                response = requests.get(url, timeout=2)

                if response.status_code == 200:
                    data = response.json() if endpoint != '/' else {}
                    return {
                        'healthy': True,
                        'endpoint': endpoint,
                        'status_code': response.status_code,
                        'data': data
                    }
            except:
                continue

        return {'healthy': False, 'endpoint': None}

    def identify_service(self, port, health_data):
        """Identify what service is running on this port"""
        if not health_data['healthy']:
            return {'name': f'unknown-{port}', 'type': 'unknown'}

        data = health_data.get('data', {})

        # Try to identify from health response
        service_name = (
            data.get('service') or
            data.get('service_name') or
            data.get('name') or
            f'service-{port}'
        )

        droplet_id = data.get('droplet_id')
        version = data.get('version', 'unknown')
        status = data.get('status', 'active')

        return {
            'name': service_name,
            'port': port,
            'droplet_id': droplet_id,
            'version': version,
            'status': status,
            'health': data
        }

    def find_service_path(self, port):
        """Try to find the service directory"""
        common_services = {
            8000: 'agents/services/registry',
            8001: 'agents/services/orchestrator',
            8002: 'agents/services/spec-verifier',
            8008: 'agents/services/dashboard',
            8010: 'agents/services/treasury-manager',
            8031: 'agents/services/visual-dashboard',
            8035: 'agents/services/treasury-arena',
            8200: 'agents/services/auto-fix-engine',
            8400: 'agents/services/i-proactive',
            8401: 'agents/services/i-match',
            8510: 'agents/services/spec-builder',
        }

        if port in common_services:
            path = self.base_dir / common_services[port]
            if path.exists():
                return str(path)

        return None

    def scan_all(self):
        """Scan all services and build catalog"""
        print("🔍 Scanning all services...")
        print()

        ports = self.get_listening_ports()
        print(f"Found {len(ports)} services listening on 8xxx ports")
        print()

        services = []

        for port in sorted(ports.keys()):
            print(f"Checking port {port}...", end=" ")

            health = self.check_service_health(port)
            service_info = self.identify_service(port, health)
            service_path = self.find_service_path(port)

            service = {
                'name': service_info['name'],
                'port': port,
                'pid': ports[port]['pid'],
                'process': ports[port]['process'],
                'healthy': health['healthy'],
                'health_endpoint': health['endpoint'],
                'droplet_id': service_info.get('droplet_id'),
                'version': service_info.get('version'),
                'status': service_info.get('status'),
                'path': service_path,
                'health_data': service_info.get('health', {})
            }

            services.append(service)

            if health['healthy']:
                print(f"✅ {service_info['name']}")
            else:
                print(f"⚠️  No health response")

        return services

    def generate_report(self, services):
        """Generate markdown report"""
        report = f"""# 📊 LIVE SERVICE SCAN
**Generated:** {datetime.utcnow().isoformat()}Z
**Scanner:** scan_all_services.py
**Total Services Found:** {len(services)}

---

## 🟢 HEALTHY SERVICES

"""
        healthy = [s for s in services if s['healthy']]
        unhealthy = [s for s in services if not s['healthy']]

        for service in healthy:
            report += f"""
### {service['name']} (Port {service['port']})
- **Status:** ✅ Healthy
- **PID:** {service['pid']}
- **Health Endpoint:** {service['health_endpoint']}
- **Version:** {service.get('version', 'unknown')}
- **Droplet ID:** {service.get('droplet_id', 'N/A')}
- **Path:** {service.get('path', 'Unknown')}
"""

            if service.get('health_data'):
                report += f"- **Health Data:** {json.dumps(service['health_data'], indent=2)}\n"

            report += "\n"

        if unhealthy:
            report += "---\n\n## ⚠️ SERVICES WITHOUT HEALTH CHECK\n\n"

            for service in unhealthy:
                report += f"""
### {service['name']} (Port {service['port']})
- **Status:** ⚠️ No health response
- **PID:** {service['pid']}
- **Path:** {service.get('path', 'Unknown')}

"""

        report += """---

## 📋 SUMMARY

"""

        report += f"**Total Services:** {len(services)}\n"
        report += f"**Healthy:** {len(healthy)}\n"
        report += f"**Without Health:** {len(unhealthy)}\n"
        report += "\n"

        # Group by service type
        by_type = {}
        for service in healthy:
            name = service['name']
            if name not in by_type:
                by_type[name] = []
            by_type[name].append(service['port'])

        report += "**Services by Type:**\n"
        for name, ports in sorted(by_type.items()):
            report += f"- {name}: {len(ports)} instance(s) on ports {', '.join(map(str, ports))}\n"

        return report

    def update_ssot(self, services):
        """Update SSOT.json with service data"""
        ssot_path = self.base_dir / "docs/coordination/SSOT.json"

        try:
            with open(ssot_path, 'r') as f:
                ssot = json.load(f)
        except:
            print("⚠️  Could not load SSOT.json")
            return False

        # Build services section
        services_data = {
            'total': len(services),
            'healthy': len([s for s in services if s['healthy']]),
            'without_health': len([s for s in services if not s['healthy']]),
            'last_scan': datetime.utcnow().isoformat() + 'Z',
            'services': []
        }

        for service in services:
            if service['healthy']:
                services_data['services'].append({
                    'name': service['name'],
                    'port': service['port'],
                    'status': service.get('status', 'active'),
                    'droplet_id': service.get('droplet_id'),
                    'version': service.get('version'),
                    'health_endpoint': service['health_endpoint'],
                    'path_local': service.get('path'),
                    'healthy': True
                })

        # Update SSOT
        ssot['services'] = services_data
        ssot['last_update'] = datetime.utcnow().isoformat() + 'Z'

        # Write back
        with open(ssot_path, 'w') as f:
            json.dump(ssot, f, indent=2)

        print(f"\n✅ Updated SSOT.json with {len(services)} services")
        return True

def main():
    scanner = ServiceScanner()

    # Scan all services
    services = scanner.scan_all()

    print()
    print("="*70)
    print()

    # Generate report
    report = scanner.generate_report(services)

    # Save report
    report_path = Path("/Users/jamessunheart/Development/LIVE_SERVICES_REPORT.md")
    with open(report_path, 'w') as f:
        f.write(report)

    print(f"📄 Report saved to: {report_path}")
    print()

    # Update SSOT
    scanner.update_ssot(services)

    print()
    print("="*70)
    print()
    print("📊 SUMMARY:")
    print(f"   Total services: {len(services)}")
    print(f"   Healthy: {len([s for s in services if s['healthy']])}")
    print(f"   Without health: {len([s for s in services if not s['healthy']])}")
    print()
    print("✅ Scan complete!")
    print()
    print("Next steps:")
    print("  1. Read LIVE_SERVICES_REPORT.md for full details")
    print("  2. Check updated docs/coordination/SSOT.json")
    print("  3. Verify dashboards show accurate data")
    print()

if __name__ == "__main__":
    main()
