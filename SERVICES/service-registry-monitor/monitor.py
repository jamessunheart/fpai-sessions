#!/usr/bin/env python3
"""
Service Registry Monitor - Auto-discovery, Health Monitoring, UDC Compliance
Scans /root/SERVICES/, monitors health, ensures UDC compliance, registers services
"""

import httpx
import asyncio
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

REGISTRY_URL = "http://198.54.123.234:8000"
SERVICES_DIR = "/root/SERVICES"

# UDC required endpoints
UDC_ENDPOINTS = [
    "/health",
    "/capabilities",
    "/state",
    "/dependencies",
    "/message",
    "/send"
]

class ServiceDiscovery:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self.discovered_services = {}
        self.registered_services = {}

    async def scan_services_directory(self) -> List[Dict]:
        """Scan /root/SERVICES/ for service directories"""
        services = []

        if not os.path.exists(SERVICES_DIR):
            print(f"⚠️  Services directory not found: {SERVICES_DIR}")
            return services

        for item in os.listdir(SERVICES_DIR):
            service_path = os.path.join(SERVICES_DIR, item)
            if os.path.isdir(service_path):
                service_info = await self.analyze_service(service_path, item)
                if service_info:
                    services.append(service_info)

        return services

    async def analyze_service(self, path: str, name: str) -> Optional[Dict]:
        """Analyze a service directory to extract port, health endpoint, etc."""
        service = {
            "name": name,
            "path": path,
            "port": None,
            "endpoint": None,
            "has_health": False,
            "udc_compliant": False,
            "missing_endpoints": [],
        }

        # Look for port configuration in common files
        port = await self.detect_port(path)
        if port:
            service["port"] = port
            service["endpoint"] = f"http://198.54.123.234:{port}"

            # Check if service is running
            health_status = await self.check_health(service["endpoint"])
            service["has_health"] = health_status is not None
            service["health_status"] = health_status

            # Check UDC compliance
            if service["has_health"]:
                udc_check = await self.check_udc_compliance(service["endpoint"])
                service["udc_compliant"] = udc_check["compliant"]
                service["missing_endpoints"] = udc_check["missing"]
                service["udc_details"] = udc_check

        return service

    async def detect_port(self, service_path: str) -> Optional[int]:
        """Detect service port from main.py, config files, etc."""
        # Check main.py for uvicorn.run(..., port=XXXX)
        main_py = os.path.join(service_path, "main.py")
        if os.path.exists(main_py):
            with open(main_py, 'r') as f:
                content = f.read()
                # Look for port= in uvicorn.run
                match = re.search(r'port=(\d+)', content)
                if match:
                    return int(match.group(1))

        # Check docker-compose.yml
        compose_file = os.path.join(service_path, "docker-compose.yml")
        if os.path.exists(compose_file):
            with open(compose_file, 'r') as f:
                content = f.read()
                # Look for ports: - "XXXX:XXXX"
                match = re.search(r'ports:.*?(\d+):', content, re.DOTALL)
                if match:
                    return int(match.group(1))

        return None

    async def check_health(self, endpoint: str) -> Optional[Dict]:
        """Check service health endpoint"""
        try:
            response = await self.client.get(f"{endpoint}/health")
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"   Health check failed for {endpoint}: {e}")
        return None

    async def check_udc_compliance(self, endpoint: str) -> Dict:
        """Check if service implements all UDC endpoints"""
        missing = []
        details = {}

        for udc_endpoint in UDC_ENDPOINTS:
            try:
                response = await self.client.get(f"{endpoint}{udc_endpoint}")
                if response.status_code == 200:
                    details[udc_endpoint] = "✅ OK"
                else:
                    missing.append(udc_endpoint)
                    details[udc_endpoint] = f"❌ HTTP {response.status_code}"
            except Exception as e:
                missing.append(udc_endpoint)
                details[udc_endpoint] = f"❌ {str(e)[:50]}"

        return {
            "compliant": len(missing) == 0,
            "missing": missing,
            "details": details
        }

    async def register_service(self, service: Dict) -> bool:
        """Register service to the registry"""
        if not service.get("endpoint"):
            return False

        try:
            payload = {
                "name": service["name"],
                "endpoint": service["endpoint"],
                "steward": "auto-discovery",
                "metadata": {
                    "path": service["path"],
                    "port": service["port"],
                    "udc_compliant": service["udc_compliant"],
                    "missing_endpoints": service["missing_endpoints"],
                    "auto_discovered": True,
                    "discovered_at": datetime.utcnow().isoformat() + "Z"
                }
            }

            response = await self.client.post(f"{REGISTRY_URL}/droplets", json=payload)
            if response.status_code in [200, 201]:
                print(f"   ✅ Registered: {service['name']}")
                return True
            elif response.status_code == 409:
                # Already registered
                print(f"   ℹ️  Already registered: {service['name']}")
                return True
            else:
                print(f"   ❌ Registration failed: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"   ❌ Registration error: {e}")
            return False

    async def get_registered_services(self) -> List[Dict]:
        """Get all services currently in the registry"""
        try:
            response = await self.client.get(f"{REGISTRY_URL}/droplets")
            if response.status_code == 200:
                data = response.json()
                return data.get("droplets", [])
        except Exception as e:
            print(f"⚠️  Failed to get registered services: {e}")
        return []

    async def monitor_cycle(self):
        """Run one monitoring cycle"""
        print(f"\n🔍 Service Discovery & Monitoring - {datetime.utcnow().isoformat()}")
        print("=" * 70)

        # Get currently registered services
        registered = await self.get_registered_services()
        print(f"\n📋 Currently Registered: {len(registered)} services")
        for svc in registered:
            print(f"   • {svc['name']} - {svc['endpoint']} ({svc['status']})")

        # Scan for services
        print(f"\n🔍 Scanning {SERVICES_DIR}...")
        discovered = await self.scan_services_directory()
        print(f"   Found {len(discovered)} services")

        # Analyze each discovered service
        print(f"\n📊 Service Analysis:")
        for service in discovered:
            print(f"\n   {service['name']}:")
            print(f"      Path: {service['path']}")
            print(f"      Port: {service.get('port', 'Not detected')}")
            if service.get('endpoint'):
                print(f"      Endpoint: {service['endpoint']}")
                print(f"      Health: {'✅ OK' if service['has_health'] else '❌ Not responding'}")
                udc_status = '✅ YES' if service['udc_compliant'] else f"❌ NO (missing {len(service['missing_endpoints'])} endpoints)"
                print(f"      UDC Compliant: {udc_status}")
                if service['missing_endpoints']:
                    print(f"         Missing: {', '.join(service['missing_endpoints'])}")

                # Auto-register if not registered
                is_registered = any(r['name'] == service['name'] for r in registered)
                if not is_registered and service['has_health']:
                    print(f"      🔄 Auto-registering...")
                    await self.register_service(service)

        # Health check all registered services
        print(f"\n💓 Health Monitoring:")
        for svc in registered:
            health = await self.check_health(svc['endpoint'])
            if health:
                status = health.get('status', 'unknown')
                print(f"   ✅ {svc['name']}: {status}")
            else:
                print(f"   ❌ {svc['name']}: offline")

    async def run_continuous(self, interval: int = 30):
        """Run continuous monitoring"""
        print(f"🚀 Starting Service Registry Monitor")
        print(f"   Registry: {REGISTRY_URL}")
        print(f"   Services Dir: {SERVICES_DIR}")
        print(f"   Interval: {interval}s")

        while True:
            try:
                await self.monitor_cycle()
            except Exception as e:
                print(f"\n❌ Monitoring error: {e}")

            print(f"\n⏸️  Sleeping {interval}s...")
            await asyncio.sleep(interval)

    async def close(self):
        await self.client.aclose()


async def main():
    import sys

    monitor = ServiceDiscovery()

    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--once":
            # Run once and exit
            await monitor.monitor_cycle()
        else:
            # Continuous monitoring
            await monitor.run_continuous(interval=30)
    finally:
        await monitor.close()


if __name__ == "__main__":
    asyncio.run(main())
