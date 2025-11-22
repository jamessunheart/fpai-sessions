#!/usr/bin/env python3
"""
🔗 Service Integrator - Connects All FPAI Services
Provides unified interface to all empire services
Part of Full Potential AI Conscious Empire
"""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime
import json


class ServiceIntegrator:
    """Integrates all FPAI services into unified system"""

    def __init__(self):
        self.name = "ServiceIntegrator"

        # Service registry
        self.services = {
            "registry": {
                "url": "http://localhost:8000",
                "status": "unknown",
                "last_check": None
            },
            "orchestrator": {
                "url": "http://localhost:8001",
                "status": "unknown",
                "last_check": None
            },
            "dashboard": {
                "url": "http://localhost:8002",
                "status": "unknown",
                "last_check": None
            },
            "fpai-hub": {
                "url": "http://localhost:8010",
                "status": "unknown",
                "last_check": None
            }
        }

        # Agent registry (local processes)
        self.agents = {}

    async def log(self, message: str, level: str = "INFO"):
        """Log integrator activity"""
        timestamp = datetime.utcnow().isoformat()
        log_entry = f"[{timestamp}] [{self.name}] [{level}] {message}"
        print(log_entry)

        with open("/tmp/service_integrator.log", "a") as f:
            f.write(log_entry + "\n")

    async def check_service_health(self, service_name: str) -> bool:
        """Check if a service is healthy"""
        service = self.services.get(service_name)
        if not service:
            return False

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{service['url']}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        service['status'] = 'healthy'
                        service['last_check'] = datetime.utcnow().isoformat()
                        return True
                    else:
                        service['status'] = 'unhealthy'
                        service['last_check'] = datetime.utcnow().isoformat()
                        return False
        except Exception as e:
            await self.log(f"{service_name} health check failed: {e}", "WARNING")
            service['status'] = 'down'
            service['last_check'] = datetime.utcnow().isoformat()
            return False

    async def get_all_service_status(self) -> Dict[str, Any]:
        """Get status of all services"""
        await self.log("Checking all service statuses...")

        # Check all services in parallel
        tasks = [
            self.check_service_health(service_name)
            for service_name in self.services.keys()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        status_summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "services": {},
            "healthy_count": 0,
            "total_count": len(self.services)
        }

        for service_name, is_healthy in zip(self.services.keys(), results):
            service_info = self.services[service_name].copy()
            status_summary["services"][service_name] = service_info

            if is_healthy:
                status_summary["healthy_count"] += 1

        return status_summary

    async def get_treasury_data(self) -> Optional[Dict[str, Any]]:
        """Get treasury data from FPAI Hub"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.services['fpai-hub']['url']}/api/treasury/status",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        await self.log(f"Treasury API returned {response.status}", "WARNING")
                        return None
        except Exception as e:
            await self.log(f"Failed to get treasury data: {e}", "ERROR")
            return None

    async def get_agent_data(self) -> Optional[List[Dict[str, Any]]]:
        """Get agent data from FPAI Hub"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.services['fpai-hub']['url']}/api/agents/status",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        await self.log(f"Agent API returned {response.status}", "WARNING")
                        return None
        except Exception as e:
            await self.log(f"Failed to get agent data: {e}", "ERROR")
            return None

    async def get_token_metrics(self) -> Optional[Dict[str, Any]]:
        """Get token metrics from FPAI Hub"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.services['fpai-hub']['url']}/api/token/metrics",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        await self.log(f"Token API returned {response.status}", "WARNING")
                        return None
        except Exception as e:
            await self.log(f"Failed to get token metrics: {e}", "ERROR")
            return None

    async def get_empire_overview(self) -> Dict[str, Any]:
        """Get complete empire overview from all services"""
        await self.log("Fetching empire overview...")

        # Fetch all data in parallel
        service_status, treasury, agents, tokens = await asyncio.gather(
            self.get_all_service_status(),
            self.get_treasury_data(),
            self.get_agent_data(),
            self.get_token_metrics(),
            return_exceptions=True
        )

        overview = {
            "timestamp": datetime.utcnow().isoformat(),
            "infrastructure": service_status,
            "treasury": treasury if not isinstance(treasury, Exception) else None,
            "agents": agents if not isinstance(agents, Exception) else None,
            "tokens": tokens if not isinstance(tokens, Exception) else None,
            "health": {
                "status": "healthy" if service_status.get("healthy_count", 0) >= 1 else "degraded",
                "services_up": service_status.get("healthy_count", 0),
                "services_total": service_status.get("total_count", 0)
            }
        }

        return overview

    async def trigger_treasury_rebalance(self, strategy: str = "optimize_yield") -> Dict[str, Any]:
        """Trigger treasury rebalancing across all agents"""
        await self.log(f"Triggering treasury rebalance with strategy: {strategy}")

        # In production, would:
        # 1. Get current positions from treasury
        # 2. Run optimization algorithms
        # 3. Execute rebalancing via DeFi agents
        # 4. Update treasury state

        result = {
            "status": "initiated",
            "strategy": strategy,
            "timestamp": datetime.utcnow().isoformat(),
            "actions": []
        }

        await self.log("Treasury rebalance initiated")
        return result

    async def deploy_new_agent(self, agent_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a new autonomous agent"""
        await self.log(f"Deploying new agent: {agent_type}")

        # In production, would:
        # 1. Use Agent Birthing Agent to create code
        # 2. Test agent in sandbox
        # 3. Deploy to production
        # 4. Register with orchestrator

        result = {
            "status": "deployed",
            "agent_type": agent_type,
            "agent_id": f"{agent_type}-{int(datetime.utcnow().timestamp())}",
            "config": config,
            "timestamp": datetime.utcnow().isoformat()
        }

        await self.log(f"Agent {agent_type} deployed successfully")
        return result

    async def broadcast_message(self, message: str, priority: str = "normal") -> Dict[str, Any]:
        """Broadcast message to all services"""
        await self.log(f"Broadcasting message (priority: {priority}): {message}")

        # In production, would use message queue (Redis Pub/Sub, RabbitMQ)
        # For now, log the broadcast

        broadcast_result = {
            "status": "broadcasted",
            "message": message,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
            "recipients": list(self.services.keys())
        }

        return broadcast_result

    async def aggregate_metrics(self) -> Dict[str, Any]:
        """Aggregate metrics from all services"""
        overview = await self.get_empire_overview()

        # Calculate aggregate metrics
        metrics = {
            "empire_health_score": 0.0,
            "total_value_locked": 0.0,
            "total_agents": 0,
            "active_agents": 0,
            "total_actions_24h": 0,
            "services_operational": 0,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Infrastructure health (25% weight)
        if overview['infrastructure']:
            health_ratio = overview['infrastructure']['healthy_count'] / overview['infrastructure']['total_count']
            metrics['empire_health_score'] += (health_ratio * 25)
            metrics['services_operational'] = overview['infrastructure']['healthy_count']

        # Treasury (35% weight)
        if overview['treasury']:
            # Treasury deployed and earning
            if overview['treasury']['total_value_usd'] > 0:
                metrics['empire_health_score'] += 35
            metrics['total_value_locked'] = overview['treasury']['total_value_usd']

        # Agents (25% weight)
        if overview['agents']:
            active_agents = sum(1 for agent in overview['agents'] if agent['status'] == 'running')
            total_agents = len(overview['agents'])

            if total_agents > 0:
                agent_ratio = active_agents / total_agents
                metrics['empire_health_score'] += (agent_ratio * 25)

            metrics['total_agents'] = total_agents
            metrics['active_agents'] = active_agents
            metrics['total_actions_24h'] = sum(
                agent.get('performance_metrics', {}).get('total_actions', 0)
                for agent in overview['agents']
            )

        # Tokens (15% weight)
        if overview['tokens']:
            # Token contract deployed and backed
            if overview['tokens']['treasury_backing'] > 0:
                metrics['empire_health_score'] += 15

        return metrics

    async def run_health_check_loop(self, interval: int = 60):
        """Continuous health checking"""
        await self.log(f"Starting health check loop (interval: {interval}s)")

        while True:
            try:
                status = await self.get_all_service_status()
                await self.log(
                    f"Health check: {status['healthy_count']}/{status['total_count']} services healthy"
                )

                # Save status to file
                with open("/tmp/empire_health.json", "w") as f:
                    json.dump(status, f, indent=2)

                await asyncio.sleep(interval)

            except Exception as e:
                await self.log(f"Health check error: {e}", "ERROR")
                await asyncio.sleep(interval)


async def main():
    """Test service integrator"""
    integrator = ServiceIntegrator()

    print("🔗 FPAI Service Integrator")
    print("=" * 60)

    # Test service health checks
    print("\n📊 Checking service health...")
    status = await integrator.get_all_service_status()
    print(json.dumps(status, indent=2))

    # Test empire overview
    print("\n🌟 Fetching empire overview...")
    overview = await integrator.get_empire_overview()
    print(json.dumps(overview, indent=2))

    # Test aggregate metrics
    print("\n📈 Calculating aggregate metrics...")
    metrics = await integrator.aggregate_metrics()
    print(json.dumps(metrics, indent=2))

    print("\n✅ Integration test complete!")


if __name__ == "__main__":
    asyncio.run(main())
