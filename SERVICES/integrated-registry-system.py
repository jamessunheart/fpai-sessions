#!/usr/bin/env python3
"""
Integrated Service Registry System
Combines manual SERVICE_REGISTRY.json with auto-discovered services from server
Syncs to server registry (port 8000) and updates SSOT.json for agent visibility
"""

import httpx
import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

# Configuration
LOCAL_REGISTRY = "/Users/jamessunheart/Development/SERVICES/SERVICE_REGISTRY.json"
SERVER_REGISTRY_URL = "http://198.54.123.234:8000"
SERVER_SERVICES_DIR = "/root/SERVICES"
SSOT_FILE = "/Users/jamessunheart/Development/docs/coordination/SSOT.json"

UDC_ENDPOINTS = ["/health", "/capabilities", "/state", "/dependencies", "/message", "/send"]


class IntegratedRegistry:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
        self.local_registry = {}
        self.server_services = []
        self.registered_droplets = []

    def load_local_registry(self) -> Dict:
        """Load SERVICE_REGISTRY.json"""
        if os.path.exists(LOCAL_REGISTRY):
            with open(LOCAL_REGISTRY, 'r') as f:
                self.local_registry = json.load(f)
                print(f"📋 Loaded local registry: {len(self.local_registry.get('services', []))} services")
                return self.local_registry
        return {}

    async def get_server_droplets(self) -> List[Dict]:
        """Get currently registered droplets from server registry"""
        try:
            response = await self.client.get(f"{SERVER_REGISTRY_URL}/droplets")
            if response.status_code == 200:
                data = response.json()
                self.registered_droplets = data.get('droplets', [])
                print(f"🌐 Server registry: {len(self.registered_droplets)} droplets")
                return self.registered_droplets
        except Exception as e:
            print(f"⚠️  Failed to get server droplets: {e}")
        return []

    async def check_service_health(self, url: str) -> Optional[Dict]:
        """Check service health and UDC compliance"""
        health_data = {}
        try:
            response = await self.client.get(f"{url}/health", timeout=5.0)
            if response.status_code == 200:
                health_data = response.json()
                health_data['reachable'] = True
                health_data['http_status'] = 200

                # Check UDC compliance
                udc_check = await self.check_udc_compliance(url)
                health_data['udc_compliant'] = udc_check['compliant']
                health_data['missing_endpoints'] = udc_check['missing']

                return health_data
        except Exception as e:
            return {
                'reachable': False,
                'error': str(e),
                'udc_compliant': False
            }
        return None

    async def check_udc_compliance(self, url: str) -> Dict:
        """Check if service has all UDC endpoints"""
        missing = []
        for endpoint in UDC_ENDPOINTS:
            try:
                response = await self.client.get(f"{url}{endpoint}", timeout=3.0)
                if response.status_code != 200:
                    missing.append(endpoint)
            except:
                missing.append(endpoint)

        return {
            'compliant': len(missing) == 0,
            'missing': missing
        }

    async def sync_to_server_registry(self, service: Dict) -> bool:
        """Register/update service in server registry"""
        try:
            # Check if already registered
            service_name = service.get('name')
            existing = next((d for d in self.registered_droplets if d['name'] == service_name), None)

            if existing:
                # Update existing
                update_payload = {
                    'endpoint': service.get('url_production') or service.get('url_local'),
                    'metadata': {
                        'port': service.get('port'),
                        'status': service.get('status'),
                        'revenue_potential': service.get('revenue_potential'),
                        'priority': service.get('priority'),
                        'tech_stack': service.get('tech_stack', []),
                        'last_synced': datetime.utcnow().isoformat() + 'Z'
                    }
                }
                response = await self.client.patch(
                    f"{SERVER_REGISTRY_URL}/droplets/{existing['id']}",
                    json=update_payload
                )
                if response.status_code == 200:
                    print(f"   ✅ Updated: {service_name}")
                    return True
            else:
                # Register new
                register_payload = {
                    'name': service_name,
                    'endpoint': service.get('url_production') or service.get('url_local'),
                    'steward': f"session-{service.get('responsible_session', 'auto')}",
                    'metadata': {
                        'description': service.get('description'),
                        'port': service.get('port'),
                        'status': service.get('status'),
                        'revenue_potential': service.get('revenue_potential'),
                        'priority': service.get('priority'),
                        'tech_stack': service.get('tech_stack', []),
                        'registered_from': 'SERVICE_REGISTRY.json'
                    }
                }
                response = await self.client.post(
                    f"{SERVER_REGISTRY_URL}/droplets",
                    json=register_payload
                )
                if response.status_code in [200, 201]:
                    print(f"   ✅ Registered: {service_name}")
                    return True
                elif response.status_code == 409:
                    print(f"   ℹ️  Already exists: {service_name}")
                    return True

        except Exception as e:
            print(f"   ❌ Sync error for {service.get('name')}: {e}")
        return False

    def update_ssot_services(self, services_data: List[Dict]):
        """Update services_status.json which gets merged into SSOT by ssot-watcher"""
        services_status_file = "/Users/jamessunheart/Development/docs/coordination/services_status.json"

        try:
            # Create services status object
            services_status = {
                'total': len(services_data),
                'active': len([s for s in services_data if s.get('status') == 'production']),
                'development': len([s for s in services_data if s.get('status') == 'development']),
                'planned': len([s for s in services_data if s.get('status') == 'planned']),
                'services': services_data,
                'last_updated': datetime.utcnow().isoformat() + 'Z'
            }

            # Write to services_status.json (will be merged into SSOT by watcher)
            with open(services_status_file, 'w') as f:
                json.dump(services_status, f, indent=2)

            print(f"✅ Updated services_status.json with {len(services_data)} services")
            print(f"   (Will appear in SSOT.json within 5 seconds)")
        except Exception as e:
            print(f"⚠️  Failed to update services status: {e}")

    async def run_integration(self):
        """Run complete integration cycle"""
        print(f"\n🔄 Integrated Registry System - {datetime.utcnow().isoformat()}")
        print("=" * 70)

        # 1. Load local SERVICE_REGISTRY.json
        registry = self.load_local_registry()
        local_services = registry.get('services', [])

        # 2. Get current server registry state
        await self.get_server_droplets()

        # 3. Check health of all services
        print(f"\n💓 Health Checks:")
        for service in local_services:
            url = service.get('url_production') or service.get('url_local')
            if url:
                health = await self.check_service_health(url)
                service['health'] = health

                status = "✅ Online" if health and health.get('reachable') else "❌ Offline"
                udc = "✅ UDC" if health and health.get('udc_compliant') else "❌ Non-UDC"
                print(f"   {service['name']}: {status} {udc}")

        # 4. Sync to server registry
        print(f"\n🔄 Syncing to Server Registry:")
        for service in local_services:
            if service.get('status') in ['production', 'development']:
                await self.sync_to_server_registry(service)

        # 5. Update SSOT for agent visibility
        print(f"\n📊 Updating SSOT for Agents:")
        self.update_ssot_services(local_services)

        # 6. Summary
        print(f"\n📋 Summary:")
        print(f"   Local Registry: {len(local_services)} services")
        print(f"   Server Droplets: {len(self.registered_droplets)} droplets")
        print(f"   UDC Compliant: {len([s for s in local_services if s.get('health', {}).get('udc_compliant')])}/{len(local_services)}")
        print(f"   Production: {len([s for s in local_services if s.get('status') == 'production'])}")
        print(f"   Development: {len([s for s in local_services if s.get('status') == 'development'])}")

    async def close(self):
        await self.client.aclose()


async def main():
    import sys

    registry = IntegratedRegistry()
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
            # Run continuous monitoring
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            print(f"🔁 Running continuously (interval: {interval}s)")
            while True:
                await registry.run_integration()
                print(f"\n⏸️  Sleeping {interval}s...\n")
                await asyncio.sleep(interval)
        else:
            # Run once
            await registry.run_integration()
    finally:
        await registry.close()


if __name__ == "__main__":
    asyncio.run(main())
