"""
Advanced Optimization Engine for I PROACTIVE

Continuously optimizes system performance:
- Response caching to reduce duplicate AI calls
- Resource usage optimization
- Performance pattern detection
- Predictive issue detection
- Auto-scaling recommendations
"""

import asyncio
import hashlib
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import deque
import statistics

from .config import settings


class ResponseCache:
    """
    Intelligent response cache for AI queries.

    Since we're using local Llama (free), we still want to cache
    to improve speed and reduce CPU load.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0
        self.access_times = deque(maxlen=1000)  # Track access patterns

    def _generate_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model"""
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, prompt: str, model: str) -> Optional[str]:
        """Get cached response if available and fresh"""
        key = self._generate_key(prompt, model)

        if key in self.cache:
            entry = self.cache[key]
            age_seconds = (datetime.now() - entry["timestamp"]).total_seconds()

            if age_seconds < self.ttl_seconds:
                self.hits += 1
                self.access_times.append(datetime.now())
                return entry["response"]
            else:
                # Expired, remove it
                del self.cache[key]

        self.misses += 1
        return None

    def set(self, prompt: str, model: str, response: str):
        """Cache a response"""
        # If cache is full, remove oldest entries
        if len(self.cache) >= self.max_size:
            # Remove 10% oldest entries
            remove_count = max(1, self.max_size // 10)
            oldest_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k]["timestamp"]
            )[:remove_count]

            for key in oldest_keys:
                del self.cache[key]

        key = self._generate_key(prompt, model)
        self.cache[key] = {
            "response": response,
            "timestamp": datetime.now()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": hit_rate,
            "ttl_seconds": self.ttl_seconds
        }

    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0


class PerformanceMonitor:
    """
    Monitor and analyze performance patterns.

    Detects:
    - Slow response times
    - High resource usage patterns
    - Usage spikes
    - Anomalies
    """

    def __init__(self, history_size: int = 1000):
        self.response_times = deque(maxlen=history_size)
        self.memory_usage = deque(maxlen=history_size)
        self.cpu_usage = deque(maxlen=history_size)
        self.request_counts = deque(maxlen=history_size)
        self.timestamps = deque(maxlen=history_size)

    def record_metric(
        self,
        response_time: float,
        memory_mb: float,
        cpu_percent: float,
        request_count: int
    ):
        """Record performance metrics"""
        self.response_times.append(response_time)
        self.memory_usage.append(memory_mb)
        self.cpu_usage.append(cpu_percent)
        self.request_counts.append(request_count)
        self.timestamps.append(datetime.now())

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect performance anomalies"""
        anomalies = []

        if len(self.response_times) < 10:
            return anomalies  # Need more data

        # Calculate statistics
        avg_response_time = statistics.mean(self.response_times)
        stddev_response_time = statistics.stdev(self.response_times)

        avg_memory = statistics.mean(self.memory_usage)
        avg_cpu = statistics.mean(self.cpu_usage)

        # Check current values against historical patterns
        current_response_time = self.response_times[-1]
        current_memory = self.memory_usage[-1]
        current_cpu = self.cpu_usage[-1]

        # Anomaly detection (simple statistical approach)
        # In production, would use ML models

        # Response time anomaly (> 3 std deviations)
        if current_response_time > avg_response_time + (3 * stddev_response_time):
            anomalies.append({
                "type": "slow_response",
                "severity": "warning",
                "current": current_response_time,
                "average": avg_response_time,
                "description": f"Response time {current_response_time:.2f}s is unusually slow"
            })

        # Memory usage anomaly
        if current_memory > avg_memory * 1.5:
            anomalies.append({
                "type": "high_memory",
                "severity": "warning",
                "current": current_memory,
                "average": avg_memory,
                "description": f"Memory usage {current_memory:.0f}MB is 50% above average"
            })

        # CPU usage anomaly
        if current_cpu > avg_cpu * 1.5:
            anomalies.append({
                "type": "high_cpu",
                "severity": "warning",
                "current": current_cpu,
                "average": avg_cpu,
                "description": f"CPU usage {current_cpu:.0f}% is 50% above average"
            })

        return anomalies

    def get_trends(self) -> Dict[str, Any]:
        """Analyze performance trends"""
        if len(self.response_times) < 10:
            return {"status": "insufficient_data"}

        # Calculate recent vs historical averages
        recent_window = 10
        recent_response_time = statistics.mean(list(self.response_times)[-recent_window:])
        historical_response_time = statistics.mean(list(self.response_times)[:-recent_window])

        recent_memory = statistics.mean(list(self.memory_usage)[-recent_window:])
        historical_memory = statistics.mean(list(self.memory_usage)[:-recent_window])

        return {
            "response_time": {
                "recent_avg": recent_response_time,
                "historical_avg": historical_response_time,
                "trend": "improving" if recent_response_time < historical_response_time else "degrading"
            },
            "memory_usage": {
                "recent_avg": recent_memory,
                "historical_avg": historical_memory,
                "trend": "increasing" if recent_memory > historical_memory else "stable"
            }
        }

    def get_recommendations(self) -> List[Dict[str, str]]:
        """Generate optimization recommendations based on patterns"""
        recommendations = []

        if len(self.response_times) < 10:
            return recommendations

        avg_response_time = statistics.mean(self.response_times)
        avg_memory = statistics.mean(self.memory_usage)
        avg_cpu = statistics.mean(self.cpu_usage)

        # Response time recommendations
        if avg_response_time > 5.0:
            recommendations.append({
                "category": "performance",
                "priority": "high",
                "recommendation": "Consider implementing request queuing to manage load",
                "reason": f"Average response time is {avg_response_time:.1f}s"
            })

        # Memory recommendations
        if avg_memory > 400:
            recommendations.append({
                "category": "resource",
                "priority": "medium",
                "recommendation": "Enable garbage collection or increase cache eviction",
                "reason": f"Average memory usage is {avg_memory:.0f}MB"
            })

        # CPU recommendations
        if avg_cpu > 60:
            recommendations.append({
                "category": "resource",
                "priority": "medium",
                "recommendation": "Consider horizontal scaling or request throttling",
                "reason": f"Average CPU usage is {avg_cpu:.0f}%"
            })

        return recommendations


class OptimizationEngine:
    """
    Main optimization engine that coordinates all optimization activities.

    Combines:
    - Response caching
    - Performance monitoring
    - Predictive analytics
    - Resource optimization
    """

    def __init__(self):
        self.cache = ResponseCache(max_size=1000, ttl_seconds=3600)
        self.performance_monitor = PerformanceMonitor(history_size=1000)
        self.optimizations_applied = []

    async def optimize_ai_call(
        self,
        prompt: str,
        model: str,
        execute_func
    ) -> Dict[str, Any]:
        """
        Optimize an AI call with caching and monitoring.

        Args:
            prompt: The prompt to send to AI
            model: Model name (e.g., "llama3.1:8b")
            execute_func: Async function that executes the actual AI call

        Returns:
            {
                "result": AI response,
                "from_cache": bool,
                "response_time": float
            }
        """
        start_time = datetime.now()

        # Try cache first
        cached_response = self.cache.get(prompt, model)
        if cached_response:
            response_time = (datetime.now() - start_time).total_seconds()
            return {
                "result": cached_response,
                "from_cache": True,
                "response_time": response_time,
                "model_used": model,
                "cost_usd": 0.0  # Always $0 with local Llama!
            }

        # Cache miss - execute actual call
        result = await execute_func()

        # Cache the result
        if "result" in result and result["result"]:
            self.cache.set(prompt, model, result["result"])

        response_time = (datetime.now() - start_time).total_seconds()

        # Record performance metrics
        # (In real implementation, would get actual memory/CPU)
        self.performance_monitor.record_metric(
            response_time=response_time,
            memory_mb=0,  # Would get from system
            cpu_percent=0,  # Would get from system
            request_count=1
        )

        return {
            **result,
            "from_cache": False,
            "response_time": response_time
        }

    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate comprehensive optimization report"""
        cache_stats = self.cache.get_stats()
        anomalies = self.performance_monitor.detect_anomalies()
        trends = self.performance_monitor.get_trends()
        recommendations = self.performance_monitor.get_recommendations()

        # Calculate efficiency score
        efficiency_score = self._calculate_efficiency_score(cache_stats, anomalies)

        return {
            "timestamp": datetime.now(),
            "efficiency_score": efficiency_score,
            "cache": cache_stats,
            "anomalies": anomalies,
            "trends": trends,
            "recommendations": recommendations,
            "optimizations_applied": len(self.optimizations_applied)
        }

    def _calculate_efficiency_score(
        self,
        cache_stats: Dict[str, Any],
        anomalies: List[Dict[str, Any]]
    ) -> int:
        """
        Calculate overall efficiency score (0-100).

        Factors:
        - Cache hit rate (higher is better)
        - Number of anomalies (fewer is better)
        - Response time consistency
        """
        score = 100

        # Cache hit rate contribution (up to 30 points)
        hit_rate = cache_stats.get("hit_rate_percent", 0)
        cache_score = (hit_rate / 100) * 30

        # Anomaly penalty (lose 10 points per anomaly, max -30)
        anomaly_penalty = min(len(anomalies) * 10, 30)

        # Calculate final score
        score = cache_score + (100 - 30 - anomaly_penalty)

        return max(0, min(100, int(score)))

    async def auto_optimize(self) -> List[Dict[str, str]]:
        """
        Automatically apply optimizations based on current state.

        Returns list of optimizations applied.
        """
        optimizations = []

        # Check cache stats
        cache_stats = self.cache.get_stats()
        if cache_stats["hit_rate_percent"] < 20 and cache_stats["size"] > 100:
            # Low hit rate with reasonable cache size - might need larger TTL
            optimizations.append({
                "type": "cache_ttl_increase",
                "action": "Increased cache TTL to improve hit rate",
                "timestamp": str(datetime.now())
            })
            # Actually apply it
            self.cache.ttl_seconds = min(self.cache.ttl_seconds * 1.5, 7200)

        # Check for memory pressure
        recommendations = self.performance_monitor.get_recommendations()
        for rec in recommendations:
            if rec["category"] == "resource" and rec["priority"] == "high":
                # Apply resource optimization
                optimizations.append({
                    "type": "resource_optimization",
                    "action": rec["recommendation"],
                    "timestamp": str(datetime.now())
                })

        # Store applied optimizations
        self.optimizations_applied.extend(optimizations)

        return optimizations
