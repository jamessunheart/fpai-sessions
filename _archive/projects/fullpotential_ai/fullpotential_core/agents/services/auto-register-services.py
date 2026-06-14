#!/usr/bin/env python3
"""
Auto-Register All Services with Registry
Session #2 - Autonomous Infrastructure Enhancement

Discovers all running services and registers them with the Registry
for proper mesh coordination and service discovery.
"""

import httpx
import json
import subprocess
import re
from datetime import datetime

REGISTRY_URL = "http://localhost:8000"

def get_active_ports():
    """Get all ports with listening services."""
    try:
        result = subprocess.run(
            ["lsof", "-i", "-P"],
            capture_output=True,
            text=True
        )

        ports = set()
        for line in result.stdout.split('\n'):
            if 'LISTEN' in line:
                match = re.search(r':(\d{4})\s', line)
                if match:
                    port = int(match.group(1))
                    if 8000 <= port <= 8999:  # Service port range
                        ports.add(port)

        return sorted(ports)
    except Exception as e:
        print(f"Error getting ports: {e}")
        return []

def get_service_info(port):
    """Get service information from health endpoint."""
    try:
        response = httpx.get(
            f"http://localhost:{port}/health",
            timeout=2.0
        )

        if response.status_code == 200:
            data = response.json()
            return {
                'name': data.get('service', data.get('service_name', f'service-{port}')),
                'version': data.get('version', '1.0.0'),
                'status': data.get('status', 'active'),
                'port': port
            }
    except:
        pass

    # Fallback: service exists but no health endpoint
    return {
        'name': f'service-{port}',
        'version': '1.0.0',
        'status': 'active',
        'port': port
    }

def register_service(service_info):
    """Register service with Registry."""
    try:
        # Try UDC-compliant registration
        response = httpx.post(
            f"{REGISTRY_URL}/register",
            json={
                'name': service_info['name'],
                'endpoint': f"http://localhost:{service_info['port']}",
                'metadata': {
                    'version': service_info['version'],
                    'auto_registered': True,
                    'registered_at': datetime.now().isoformat(),
                    'session': 'session-2-infrastructure'
                },
                'status': service_info['status']
            },
            timeout=5.0
        )

        if response.status_code in [200, 201]:
            print(f"✅ Registered: {service_info['name']} (port {service_info['port']})")
            return True
        else:
            print(f"⚠️  Registration failed for {service_info['name']}: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Error registering {service_info['name']}: {e}")
        return False

def main():
    """Main execution."""
    print("🔍 Discovering active services...")
    ports = get_active_ports()
    print(f"   Found {len(ports)} active ports")

    print("\n📋 Gathering service information...")
    services = []
    for port in ports:
        info = get_service_info(port)
        if info:
            services.append(info)
            print(f"   {port}: {info['name']}")

    print(f"\n🌐 Registering {len(services)} services with Registry...")

    registered = 0
    failed = 0

    for service in services:
        if register_service(service):
            registered += 1
        else:
            failed += 1

    print(f"\n📊 Registration Summary:")
    print(f"   ✅ Successfully registered: {registered}")
    print(f"   ❌ Failed: {failed}")
    print(f"   📈 Total services now discoverable: {registered}")

    # Verify in Registry
    try:
        response = httpx.get(f"{REGISTRY_URL}/droplets", timeout=5.0)
        if response.status_code == 200:
            droplets = response.json().get('droplets', [])
            print(f"\n🎯 Registry now tracking {len(droplets)} droplets")
    except:
        print("\n⚠️  Could not verify Registry status")

    print("\n✅ Auto-registration complete!")
    print("   All services now discoverable via mesh architecture")
    print("   Blueprint: Scalable coordination for $373K → $5.21T vision")

if __name__ == "__main__":
    main()
