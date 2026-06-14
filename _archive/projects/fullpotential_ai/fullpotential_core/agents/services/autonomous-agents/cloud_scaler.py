#!/usr/bin/env python3
"""
☁️ Cloud Scaler - Auto-Scaling Infrastructure Manager
Integrates with DigitalOcean/AWS APIs to auto-scale infrastructure
Part of Full Potential AI Autonomous Intelligence System
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class CloudScaler:
    """Manages auto-scaling across cloud providers"""

    def __init__(self, provider: str = "digitalocean"):
        self.name = "CloudScaler"
        self.provider = provider
        self.api_key = os.environ.get("DIGITALOCEAN_API_KEY", "")

        # Current infrastructure state
        self.servers = []
        self.volumes = []
        self.load_balancers = []

        # Scaling history
        self.scaling_events = []

    async def log(self, message: str, level: str = "INFO"):
        """Log scaler activity"""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] [{self.name}] [{level}] {message}"
        print(log_entry)

        try:
            with open(f"/tmp/cloud_scaler.log", "a") as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Failed to write log: {e}")

    async def digitalocean_api_call(self, endpoint: str, method: str = "GET", data: Dict = None) -> Optional[Dict]:
        """Make DigitalOcean API call"""
        if not self.api_key:
            await self.log("No DigitalOcean API key configured", "WARNING")
            return None

        url = f"https://api.digitalocean.com/v2/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            await self.log(f"API error: {response.status}", "ERROR")
                            return None

                elif method == "POST":
                    async with session.post(url, headers=headers, json=data) as response:
                        if response.status in [200, 201]:
                            return await response.json()
                        else:
                            await self.log(f"API error: {response.status}", "ERROR")
                            return None

        except Exception as e:
            await self.log(f"API call failed: {e}", "ERROR")
            return None

    async def list_droplets(self) -> List[Dict]:
        """List all droplets"""
        result = await self.digitalocean_api_call("droplets")

        if result and "droplets" in result:
            self.servers = result["droplets"]
            await self.log(f"Found {len(self.servers)} droplets")
            return self.servers

        return []

    async def create_droplet(self, name: str, size: str = "s-1vcpu-1gb", region: str = "nyc3") -> Optional[Dict]:
        """Create a new droplet (server)"""
        await self.log(f"Creating new droplet: {name} ({size}) in {region}")

        data = {
            "name": name,
            "region": region,
            "size": size,
            "image": "ubuntu-22-04-x64",
            "ssh_keys": [],  # Add your SSH key IDs
            "backups": False,
            "ipv6": True,
            "monitoring": True,
            "tags": ["fpai", "autonomous-agent"]
        }

        result = await self.digitalocean_api_call("droplets", method="POST", data=data)

        if result and "droplet" in result:
            droplet = result["droplet"]
            await self.log(f"✅ Created droplet: {droplet['id']} - {droplet['name']}")

            # Record scaling event
            self.scaling_events.append({
                "type": "create_droplet",
                "droplet_id": droplet["id"],
                "name": name,
                "size": size,
                "region": region,
                "timestamp": datetime.utcnow().isoformat()
            })

            return droplet

        return None

    async def resize_droplet(self, droplet_id: int, new_size: str) -> bool:
        """Resize existing droplet (vertical scaling)"""
        await self.log(f"Resizing droplet {droplet_id} to {new_size}")

        data = {
            "type": "resize",
            "size": new_size
        }

        result = await self.digitalocean_api_call(
            f"droplets/{droplet_id}/actions",
            method="POST",
            data=data
        )

        if result and "action" in result:
            await self.log(f"✅ Resize initiated: action {result['action']['id']}")

            self.scaling_events.append({
                "type": "resize_droplet",
                "droplet_id": droplet_id,
                "new_size": new_size,
                "timestamp": datetime.utcnow().isoformat()
            })

            return True

        return False

    async def create_volume(self, name: str, size_gb: int, region: str = "nyc3") -> Optional[Dict]:
        """Create storage volume"""
        await self.log(f"Creating volume: {name} ({size_gb}GB) in {region}")

        data = {
            "size_gigabytes": size_gb,
            "name": name,
            "description": "Auto-scaled storage for FPAI",
            "region": region,
            "filesystem_type": "ext4"
        }

        result = await self.digitalocean_api_call("volumes", method="POST", data=data)

        if result and "volume" in result:
            volume = result["volume"]
            await self.log(f"✅ Created volume: {volume['id']} - {volume['name']}")

            self.scaling_events.append({
                "type": "create_volume",
                "volume_id": volume["id"],
                "name": name,
                "size_gb": size_gb,
                "timestamp": datetime.utcnow().isoformat()
            })

            return volume

        return None

    async def get_cost_estimate(self, action: str, **params) -> Dict[str, Any]:
        """Estimate cost of scaling action"""
        # DigitalOcean pricing (approximate)
        pricing = {
            "s-1vcpu-1gb": 6,      # $6/month
            "s-1vcpu-2gb": 12,     # $12/month
            "s-2vcpu-2gb": 18,     # $18/month
            "s-2vcpu-4gb": 24,     # $24/month
            "s-4vcpu-8gb": 48,     # $48/month
            "volume_gb": 0.10      # $0.10/GB/month
        }

        if action == "create_droplet":
            size = params.get("size", "s-1vcpu-1gb")
            monthly_cost = pricing.get(size, 12)

            return {
                "action": action,
                "monthly_cost_usd": monthly_cost,
                "annual_cost_usd": monthly_cost * 12,
                "details": f"New {size} droplet"
            }

        elif action == "resize_droplet":
            old_size = params.get("old_size", "s-1vcpu-1gb")
            new_size = params.get("new_size", "s-2vcpu-2gb")
            old_cost = pricing.get(old_size, 12)
            new_cost = pricing.get(new_size, 24)
            delta = new_cost - old_cost

            return {
                "action": action,
                "monthly_cost_increase_usd": delta,
                "annual_cost_increase_usd": delta * 12,
                "details": f"Resize from {old_size} to {new_size}"
            }

        elif action == "create_volume":
            size_gb = params.get("size_gb", 50)
            monthly_cost = size_gb * pricing["volume_gb"]

            return {
                "action": action,
                "monthly_cost_usd": monthly_cost,
                "annual_cost_usd": monthly_cost * 12,
                "details": f"{size_gb}GB storage volume"
            }

        return {"error": "Unknown action"}

    async def execute_scaling_plan(self, plan: Dict[str, Any], auto_approve: bool = False) -> bool:
        """Execute a scaling plan"""
        action = plan.get("action")

        if not auto_approve:
            await self.log(f"⏸️ Scaling plan requires approval: {action}", "WARNING")
            await self.log(f"Plan: {json.dumps(plan, indent=2)}", "INFO")
            return False

        await self.log(f"🚀 Executing scaling plan: {action}")

        if action == "create_droplet":
            droplet = await self.create_droplet(
                name=plan.get("name", f"fpai-agent-{datetime.utcnow().timestamp()}"),
                size=plan.get("size", "s-1vcpu-1gb"),
                region=plan.get("region", "nyc3")
            )
            return droplet is not None

        elif action == "resize_droplet":
            success = await self.resize_droplet(
                droplet_id=plan.get("droplet_id"),
                new_size=plan.get("target_size")
            )
            return success

        elif action == "create_volume":
            volume = await self.create_volume(
                name=plan.get("name", f"fpai-storage-{datetime.utcnow().timestamp()}"),
                size_gb=plan.get("size_gb", 50),
                region=plan.get("region", "nyc3")
            )
            return volume is not None

        return False


class ScalingOrchestrator:
    """Coordinates resource monitoring with cloud scaling"""

    def __init__(self):
        self.scaler = CloudScaler()
        self.pending_plans = []

    async def monitor_and_scale(self):
        """Main loop - monitor resources and auto-scale"""
        while True:
            # Check for scaling recommendations
            try:
                with open("/tmp/scaling_latest.json", "r") as f:
                    plan = json.load(f)

                # Check if this plan is new
                if plan not in self.pending_plans:
                    print(f"\n🔔 NEW SCALING RECOMMENDATION:")
                    print(json.dumps(plan, indent=2))

                    # Get cost estimate
                    cost = await self.scaler.get_cost_estimate(
                        plan["action"],
                        **plan
                    )
                    print(f"\n💰 Cost estimate:")
                    print(json.dumps(cost, indent=2))

                    self.pending_plans.append(plan)

                    print(f"\n⏸️ Requires approval to execute")
                    print(f"Set auto_approve=True to enable automatic scaling")

            except FileNotFoundError:
                pass
            except Exception as e:
                print(f"Error: {e}")

            await asyncio.sleep(60)


async def main():
    """Run the cloud scaler"""
    orchestrator = ScalingOrchestrator()
    await orchestrator.monitor_and_scale()


if __name__ == "__main__":
    print("☁️ Full Potential AI - Cloud Auto-Scaler")
    print("=" * 60)
    asyncio.run(main())
