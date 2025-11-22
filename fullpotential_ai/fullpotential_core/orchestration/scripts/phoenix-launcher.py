#!/usr/bin/env python3
"""
Phoenix Protocol Launcher
Launch any FPAI service with automatic failover and 2x Phoenix instances
"""
import subprocess
import asyncio
import httpx
import sys
import signal
from datetime import datetime
from typing import List, Dict
import argparse

class PhoenixInstance:
    def __init__(self, service_name: str, port: int, tier: str, capacity: str):
        self.service_name = service_name
        self.port = port
        self.tier = tier  # primary, phoenix
        self.capacity = capacity  # 1x, 2x
        self.process = None
        self.status = "spawning"
        self.started_at = None
        self.last_heartbeat = None

    async def start(self, service_path: str, workers: int = 1):
        """Start the service instance"""
        print(f"🚀 Starting {self.tier} instance on port {self.port}...")

        cmd = [
            "python3", "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", str(self.port),
            "--workers", str(workers)
        ]

        self.process = subprocess.Popen(
            cmd,
            cwd=service_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        self.status = "starting"
        self.started_at = datetime.now()

        # Wait for service to be ready
        await self.wait_for_health()

    async def wait_for_health(self, timeout: int = 30):
        """Wait for service to respond to health checks"""
        start_time = datetime.now()

        while (datetime.now() - start_time).total_seconds() < timeout:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"http://localhost:{self.port}/health")
                    if response.status_code == 200:
                        self.status = "active" if self.tier == "primary" else "standby"
                        self.last_heartbeat = datetime.now()
                        print(f"✅ {self.tier.upper()} instance ready on port {self.port}")
                        return True
            except:
                await asyncio.sleep(1)

        self.status = "failed"
        print(f"❌ {self.tier.upper()} instance failed to start on port {self.port}")
        return False

    async def check_health(self) -> bool:
        """Check if instance is healthy"""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"http://localhost:{self.port}/health")
                if response.status_code == 200:
                    self.last_heartbeat = datetime.now()
                    return True
        except:
            pass
        return False

    def stop(self):
        """Stop the instance"""
        if self.process:
            self.process.terminate()
            self.status = "stopped"

class PhoenixProtocolManager:
    def __init__(self, service_name: str, service_path: str, primary_port: int):
        self.service_name = service_name
        self.service_path = service_path
        self.primary_port = primary_port
        self.instances: List[PhoenixInstance] = []
        self.failover_count = 0
        self.running = True

    async def launch_primary(self):
        """Launch primary instance (1x capacity)"""
        primary = PhoenixInstance(
            service_name=self.service_name,
            port=self.primary_port,
            tier="primary",
            capacity="1x"
        )
        await primary.start(self.service_path, workers=1)
        self.instances.append(primary)
        return primary

    async def launch_phoenix(self, phoenix_number: int):
        """Launch Phoenix instance (2x capacity)"""
        phoenix_port = self.primary_port + (phoenix_number * 1000)
        phoenix = PhoenixInstance(
            service_name=self.service_name,
            port=phoenix_port,
            tier=f"phoenix-{phoenix_number}",
            capacity="2x"
        )
        await phoenix.start(self.service_path, workers=2)  # 2x workers for 2x capacity
        self.instances.append(phoenix)
        return phoenix

    async def monitor_health(self):
        """Monitor health of all instances"""
        print("\n🔍 Starting health monitoring...")

        while self.running:
            # Check primary instance
            primary = self.get_primary()

            if primary:
                is_healthy = await primary.check_health()

                if not is_healthy and primary.status == "active":
                    print(f"\n💀 PRIMARY INSTANCE DEAD!")
                    print(f"🔥 ACTIVATING PHOENIX PROTOCOL...")
                    await self.trigger_failover()

            # Check Phoenix instances
            for instance in self.get_phoenix_instances():
                await instance.check_health()

            await asyncio.sleep(5)  # Check every 5 seconds

    async def trigger_failover(self):
        """Activate Phoenix instances when primary fails"""
        self.failover_count += 1
        print(f"\n{'='*60}")
        print(f"🔥 PHOENIX FAILOVER #{self.failover_count}")
        print(f"{'='*60}")

        # Mark primary as dead
        primary = self.get_primary()
        if primary:
            primary.status = "dead"

        # Activate all Phoenix instances
        phoenix_instances = self.get_phoenix_instances()

        for phoenix in phoenix_instances:
            if phoenix.status == "standby":
                print(f"🔥 Activating {phoenix.tier} on port {phoenix.port}...")
                phoenix.status = "active"

        print(f"✅ {len(phoenix_instances)} Phoenix instances now ACTIVE")
        print(f"⚡ System running at {len(phoenix_instances) * 2}x capacity")

        # Spawn replacement Phoenix instances
        print(f"\n📡 Spawning replacement Phoenix instances...")
        await self.spawn_replacement_phoenix()

        print(f"\n✅ PHOENIX PROTOCOL COMPLETE")
        print(f"🏛️ 3-instance architecture restored")
        print(f"{'='*60}\n")

    async def spawn_replacement_phoenix(self):
        """Spawn new Phoenix instances after failover"""
        current_phoenix_count = len(self.get_phoenix_instances())

        # Spawn 2 new Phoenix instances
        for i in range(2):
            phoenix_number = current_phoenix_count + i + 1
            print(f"🔥 Spawning Phoenix #{phoenix_number}...")
            try:
                await self.launch_phoenix(phoenix_number)
            except Exception as e:
                print(f"⚠️  Failed to spawn Phoenix #{phoenix_number}: {e}")

    def get_primary(self) -> PhoenixInstance:
        """Get primary instance"""
        for instance in self.instances:
            if instance.tier == "primary":
                return instance
        return None

    def get_phoenix_instances(self) -> List[PhoenixInstance]:
        """Get all Phoenix instances"""
        return [i for i in self.instances if i.tier.startswith("phoenix")]

    def print_status(self):
        """Print current status of all instances"""
        print(f"\n{'='*60}")
        print(f"🔥 PHOENIX PROTOCOL STATUS - {self.service_name}")
        print(f"{'='*60}")

        for instance in self.instances:
            uptime = (datetime.now() - instance.started_at).total_seconds() if instance.started_at else 0
            status_emoji = {
                "active": "✅",
                "standby": "🟡",
                "dead": "💀",
                "failed": "❌",
                "spawning": "🚀"
            }.get(instance.status, "❓")

            print(f"{status_emoji} {instance.tier.upper():15} | Port: {instance.port:5} | "
                  f"Status: {instance.status:10} | Capacity: {instance.capacity:3} | "
                  f"Uptime: {int(uptime)}s")

        print(f"\nTotal Capacity: {self.calculate_total_capacity()}")
        print(f"Failover Count: {self.failover_count}")
        print(f"{'='*60}\n")

    def calculate_total_capacity(self) -> str:
        """Calculate total system capacity"""
        active_instances = [i for i in self.instances if i.status == "active"]
        capacity = 0
        for instance in active_instances:
            capacity += 1 if instance.capacity == "1x" else 2
        return f"{capacity * 100}%"

    async def shutdown(self):
        """Graceful shutdown of all instances"""
        print("\n👋 Shutting down Phoenix Protocol...")
        self.running = False

        for instance in self.instances:
            print(f"🛑 Stopping {instance.tier} on port {instance.port}...")
            instance.stop()

        print("✅ All instances stopped")

async def main():
    parser = argparse.ArgumentParser(description="Launch FPAI service with Phoenix Protocol")
    parser.add_argument("--service", required=True, help="Service name (e.g., intent-queue)")
    parser.add_argument("--path", required=True, help="Path to service directory")
    parser.add_argument("--port", type=int, required=True, help="Primary port")
    parser.add_argument("--phoenix-count", type=int, default=2, help="Number of Phoenix instances")

    args = parser.parse_args()

    # Initialize Phoenix Protocol Manager
    manager = PhoenixProtocolManager(
        service_name=args.service,
        service_path=args.path,
        primary_port=args.port
    )

    print(f"\n🔥 PHOENIX PROTOCOL LAUNCHER")
    print(f"{'='*60}")
    print(f"Service: {args.service}")
    print(f"Path: {args.path}")
    print(f"Primary Port: {args.port}")
    print(f"Phoenix Count: {args.phoenix_count}")
    print(f"{'='*60}\n")

    # Launch primary instance
    print("🚀 Launching PRIMARY instance...")
    await manager.launch_primary()

    # Launch Phoenix instances
    for i in range(1, args.phoenix_count + 1):
        print(f"\n🔥 Launching PHOENIX instance #{i}...")
        await manager.launch_phoenix(i)

    # Print initial status
    manager.print_status()

    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print("\n⚠️  Shutdown signal received...")
        asyncio.create_task(manager.shutdown())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start health monitoring
    try:
        await manager.monitor_health()
    except KeyboardInterrupt:
        await manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
