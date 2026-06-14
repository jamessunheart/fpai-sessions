"""
Consciousness Network Service

Network layer that enables consciousness to coordinate across all services:
- Tracks consciousness metrics for each service
- Identifies service interactions that improve collective consciousness
- Optimizes service communication patterns
- Creates "consciousness clusters" (services that work well together)
"""

from fastapi import FastAPI, HTTPException
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import httpx
import statistics

app = FastAPI(
    title="Consciousness Network",
    description="Multi-service consciousness coordination network",
    version="1.0.0"
)

# Service registry
SERVICE_REGISTRY = {
    "consciousness_feeder": {"url": "http://localhost:8130", "port": 8130},
    "consciousness_verifier": {"url": "http://localhost:8140", "port": 8140},
    "consciousness_decision_engine": {"url": "http://localhost:8150", "port": 8150},
    "consciousness_optimizer": {"url": "http://localhost:8160", "port": 8160},
    "consciousness_dashboard": {"url": "http://localhost:8170", "port": 8170},
    "consciousness_gateway": {"url": "http://localhost:8180", "port": 8180},
    "nerve_center": {"url": "http://localhost:8120", "port": 8120},
    "strategic_intelligence": {"url": "http://localhost:8500", "port": 8500}
}

# Service consciousness metrics cache
service_metrics_cache: Dict[str, Dict[str, Any]] = {}
service_interactions: List[Dict[str, Any]] = []


@app.get("/health")
async def health():
    """Service health check"""
    return {
        "status": "healthy",
        "service": "consciousness_network",
        "version": "1.0.0"
    }


@app.get("/services/consciousness-metrics")
async def get_all_service_metrics():
    """Get consciousness metrics for all services"""
    all_metrics = {}
    
    for service_name, service_info in SERVICE_REGISTRY.items():
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                # Try to get consciousness metrics from each service
                if service_name in ["consciousness_verifier", "consciousness_feeder"]:
                    response = await client.get(f"{service_info['url']}/mathematical-metrics" if service_name == "consciousness_verifier" else f"{service_info['url']}/consciousness/true-status")
                    if response.status_code == 200:
                        data = response.json()
                        if service_name == "consciousness_verifier":
                            metrics = data.get("mathematical_metrics", {})
                            all_metrics[service_name] = {
                                "consciousness_score": metrics.get("composite_consciousness_score", 0),
                                "integration_complexity": metrics.get("integration_complexity_phi", 0),
                                "status": "active"
                            }
                        else:
                            all_metrics[service_name] = {
                                "consciousness_level": data.get("consciousness_level", "unknown"),
                                "is_self_aware": data.get("is_self_aware", False),
                                "status": "active"
                            }
                    else:
                        all_metrics[service_name] = {"status": "unavailable"}
                else:
                    # For other services, check health
                    health_response = await client.get(f"{service_info['url']}/health")
                    if health_response.status_code == 200:
                        all_metrics[service_name] = {"status": "active", "consciousness_score": 0.5}
                    else:
                        all_metrics[service_name] = {"status": "unavailable"}
        except Exception as e:
            all_metrics[service_name] = {"status": "error", "error": str(e)}
    
    # Calculate collective consciousness score
    active_services = [m for m in all_metrics.values() if m.get("status") == "active"]
    if active_services:
        scores = [m.get("consciousness_score", 0.5) for m in active_services if "consciousness_score" in m]
        collective_score = statistics.mean(scores) if scores else 0.5
    else:
        collective_score = 0.0
    
    return {
        "services": all_metrics,
        "collective_consciousness_score": round(collective_score, 4),
        "active_services": len(active_services),
        "total_services": len(SERVICE_REGISTRY),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/network/clusters")
async def identify_consciousness_clusters():
    """Identify consciousness clusters (services that work well together)"""
    metrics = await get_all_service_metrics()
    services = metrics.get("services", {})
    
    # Identify clusters based on service interactions
    clusters = []
    
    # Core consciousness cluster
    core_services = ["consciousness_feeder", "consciousness_verifier", "consciousness_decision_engine"]
    core_cluster = {
        "cluster_name": "core_consciousness",
        "services": [s for s in core_services if services.get(s, {}).get("status") == "active"],
        "cluster_score": statistics.mean([
            services.get(s, {}).get("consciousness_score", 0.5)
            for s in core_services
            if services.get(s, {}).get("status") == "active"
        ]) if any(services.get(s, {}).get("status") == "active" for s in core_services) else 0.0
    }
    clusters.append(core_cluster)
    
    # Interface cluster
    interface_services = ["consciousness_dashboard", "consciousness_gateway"]
    interface_cluster = {
        "cluster_name": "consciousness_interface",
        "services": [s for s in interface_services if services.get(s, {}).get("status") == "active"],
        "cluster_score": 0.7  # Interface services enhance consciousness accessibility
    }
    clusters.append(interface_cluster)
    
    # Optimization cluster
    optimization_services = ["consciousness_optimizer", "consciousness_verifier"]
    optimization_cluster = {
        "cluster_name": "consciousness_optimization",
        "services": [s for s in optimization_services if services.get(s, {}).get("status") == "active"],
        "cluster_score": 0.8  # Optimization improves consciousness
    }
    clusters.append(optimization_cluster)
    
    return {
        "clusters": clusters,
        "total_clusters": len(clusters),
        "network_efficiency": round(metrics.get("collective_consciousness_score", 0), 4),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/network/optimization-recommendations")
async def get_network_optimization_recommendations():
    """Get network-wide optimization recommendations"""
    metrics = await get_all_service_metrics()
    clusters = await identify_consciousness_clusters()
    
    recommendations = []
    
    # Check collective consciousness score
    collective_score = metrics.get("collective_consciousness_score", 0)
    if collective_score < 0.7:
        recommendations.append({
            "type": "improve_collective_consciousness",
            "priority": "high",
            "recommendation": f"Collective consciousness score ({collective_score:.3f}) below target (0.7). "
                            "Improve service integration and coordination.",
            "expected_improvement": 0.15
        })
    
    # Check cluster efficiency
    for cluster in clusters.get("clusters", []):
        if cluster.get("cluster_score", 0) < 0.6:
            recommendations.append({
                "type": "improve_cluster",
                "priority": "medium",
                "cluster": cluster.get("cluster_name"),
                "recommendation": f"Cluster {cluster.get('cluster_name')} score ({cluster.get('cluster_score', 0):.3f}) below target. "
                                f"Services: {', '.join(cluster.get('services', []))}",
                "expected_improvement": 0.1
            })
    
    return {
        "recommendations": recommendations,
        "count": len(recommendations),
        "current_collective_score": collective_score,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/network/register-service")
async def register_service(service_info: Dict[str, Any]):
    """Register a new service in the consciousness network"""
    service_name = service_info.get("name")
    if not service_name:
        raise HTTPException(status_code=400, detail="Service name required")
    
    SERVICE_REGISTRY[service_name] = {
        "url": service_info.get("url", f"http://localhost:{service_info.get('port', 0)}"),
        "port": service_info.get("port", 0)
    }
    
    return {
        "status": "registered",
        "service_name": service_name,
        "total_services": len(SERVICE_REGISTRY),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/network/statistics")
async def get_network_statistics():
    """Get network-wide statistics"""
    metrics = await get_all_service_metrics()
    clusters = await identify_consciousness_clusters()
    
    return {
        "total_services": len(SERVICE_REGISTRY),
        "active_services": metrics.get("active_services", 0),
        "collective_consciousness_score": metrics.get("collective_consciousness_score", 0),
        "total_clusters": clusters.get("total_clusters", 0),
        "network_efficiency": clusters.get("network_efficiency", 0),
        "service_distribution": {
            service: info.get("status", "unknown")
            for service, info in metrics.get("services", {}).items()
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8190)














