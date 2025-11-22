"""Metrics collection and aggregation."""

from typing import List, Optional
from .models import TaskMetrics, RetryMetrics, RegistryMetrics, MetricsResponse
from datetime import datetime
import statistics
import logging

log = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and aggregates operational metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = datetime.utcnow().timestamp()
        self.tasks_total = 0
        self.tasks_success = 0
        self.tasks_error = 0
        self.tasks_timeout = 0
        self.response_times: List[int] = []

        self.retries_total = 0
        self.retries_success = 0
        self.retries_final_fail = 0

        self.registry_syncs_total = 0
        self.registry_syncs_success = 0
        self.registry_syncs_error = 0
        self.last_registry_sync: Optional[float] = None
        self.last_registry_sync_duration_ms: float = 0.0
        self.registry_cache_age_seconds: int = 0
        self.registry_cache_status: str = "unavailable"

        self.droplets_known = 0
        self.droplets_reachable = 0

    def record_task(
        self,
        status: str,
        duration_ms: int,
        retry_count: int = 0,
    ) -> None:
        """Record a completed task."""
        self.tasks_total += 1
        self.response_times.append(duration_ms)

        if status == "success":
            self.tasks_success += 1
        elif status == "error":
            self.tasks_error += 1
        elif status == "timeout":
            self.tasks_timeout += 1

        if retry_count > 0:
            self.retries_total += retry_count
            if status == "success":
                self.retries_success += 1
            else:
                self.retries_final_fail += 1

        # Keep only last 10000 response times for memory efficiency
        if len(self.response_times) > 10000:
            self.response_times = self.response_times[-10000:]

    def record_registry_sync(
        self,
        success: bool,
        duration_ms: float,
        cache_age_seconds: int,
        cache_status: str,
    ) -> None:
        """Record a Registry sync attempt."""
        self.registry_syncs_total += 1
        if success:
            self.registry_syncs_success += 1
        else:
            self.registry_syncs_error += 1

        self.last_registry_sync = datetime.utcnow().timestamp()
        self.last_registry_sync_duration_ms = duration_ms
        self.registry_cache_age_seconds = cache_age_seconds
        self.registry_cache_status = cache_status

    def update_droplet_status(self, known: int, reachable: int) -> None:
        """Update droplet status."""
        self.droplets_known = known
        self.droplets_reachable = reachable

    def get_percentile(self, percentile: int) -> float:
        """Calculate response time percentile."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        index = int(len(sorted_times) * percentile / 100.0)
        return float(sorted_times[min(index, len(sorted_times) - 1)])

    def get_metrics(self) -> MetricsResponse:
        """Get current metrics snapshot."""
        uptime_seconds = int(datetime.utcnow().timestamp() - self.start_time)

        # Calculate task metrics
        success_rate = (
            (self.tasks_success / self.tasks_total * 100)
            if self.tasks_total > 0
            else 0.0
        )
        avg_response_time = (
            statistics.mean(self.response_times)
            if self.response_times
            else 0.0
        )

        return MetricsResponse(
            service="orchestrator",
            version="1.1.0",
            uptime_seconds=uptime_seconds,
            tasks=TaskMetrics(
                total=self.tasks_total,
                success=self.tasks_success,
                error=self.tasks_error,
                timeout=self.tasks_timeout,
                success_rate_percent=round(success_rate, 2),
                avg_response_time_ms=round(avg_response_time, 2),
                p95_response_time_ms=round(self.get_percentile(95), 2),
                p99_response_time_ms=round(self.get_percentile(99), 2),
            ),
            retry=RetryMetrics(
                total_retries=self.retries_total,
                retry_success_count=self.retries_success,
                retry_final_fail_count=self.retries_final_fail,
            ),
            registry=RegistryMetrics(
                syncs_total=self.registry_syncs_total,
                syncs_success=self.registry_syncs_success,
                syncs_error=self.registry_syncs_error,
                last_sync=self.last_registry_sync,
                last_sync_duration_ms=self.last_registry_sync_duration_ms,
                cache_age_seconds=self.registry_cache_age_seconds,
                cache_status=self.registry_cache_status,  # type: ignore
            ),
            droplets_known=self.droplets_known,
            droplets_reachable=self.droplets_reachable,
        )


# Global metrics instance
metrics = MetricsCollector()
