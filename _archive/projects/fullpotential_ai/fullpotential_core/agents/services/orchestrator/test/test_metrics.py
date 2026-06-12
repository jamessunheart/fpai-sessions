"""Tests for metrics collection and aggregation."""

import pytest
from app.metrics import MetricsCollector


class TestMetricsCollection:
    """Tests for basic metrics collection."""

    @pytest.fixture
    def metrics(self):
        """Create fresh MetricsCollector."""
        return MetricsCollector()

    def test_metrics_start_at_zero(self, metrics):
        """Metrics start at zero."""
        assert metrics.tasks_total == 0
        assert metrics.tasks_success == 0
        assert metrics.tasks_error == 0
        assert metrics.tasks_timeout == 0
        assert metrics.retries_total == 0

    def test_record_successful_task(self, metrics):
        """Recording successful task increments counters."""
        metrics.record_task(status="success", duration_ms=100)

        assert metrics.tasks_total == 1
        assert metrics.tasks_success == 1
        assert metrics.tasks_error == 0

    def test_record_error_task(self, metrics):
        """Recording error task increments error counter."""
        metrics.record_task(status="error", duration_ms=100)

        assert metrics.tasks_total == 1
        assert metrics.tasks_success == 0
        assert metrics.tasks_error == 1

    def test_record_timeout_task(self, metrics):
        """Recording timeout task increments timeout counter."""
        metrics.record_task(status="timeout", duration_ms=5000)

        assert metrics.tasks_total == 1
        assert metrics.tasks_timeout == 1

    def test_record_task_with_retries(self, metrics):
        """Recording task with retries increments retry counters."""
        metrics.record_task(status="success", duration_ms=200, retry_count=2)

        assert metrics.retries_total == 2
        assert metrics.retries_success == 1

    def test_record_task_failed_retries(self, metrics):
        """Recording failed task with retries counts retry failures."""
        metrics.record_task(status="error", duration_ms=300, retry_count=3)

        assert metrics.retries_total == 3
        assert metrics.retries_final_fail == 1

    def test_response_times_tracked(self, metrics):
        """Response times are tracked."""
        metrics.record_task(status="success", duration_ms=100)
        metrics.record_task(status="success", duration_ms=200)

        assert len(metrics.response_times) == 2
        assert 100 in metrics.response_times
        assert 200 in metrics.response_times

    def test_response_times_limited_to_10000(self, metrics):
        """Response times limited to last 10000 entries."""
        for i in range(12000):
            metrics.record_task(status="success", duration_ms=i)

        assert len(metrics.response_times) == 10000


class TestRegistryMetrics:
    """Tests for Registry sync metrics."""

    @pytest.fixture
    def metrics(self):
        """Create fresh MetricsCollector."""
        return MetricsCollector()

    def test_record_registry_sync_success(self, metrics):
        """Recording successful Registry sync."""
        metrics.record_registry_sync(
            success=True,
            duration_ms=50.0,
            cache_age_seconds=0,
            cache_status="active",
        )

        assert metrics.registry_syncs_total == 1
        assert metrics.registry_syncs_success == 1
        assert metrics.registry_syncs_error == 0
        assert metrics.last_registry_sync is not None
        assert metrics.last_registry_sync_duration_ms == 50.0

    def test_record_registry_sync_error(self, metrics):
        """Recording failed Registry sync."""
        metrics.record_registry_sync(
            success=False,
            duration_ms=100.0,
            cache_age_seconds=300,
            cache_status="stale",
        )

        assert metrics.registry_syncs_total == 1
        assert metrics.registry_syncs_success == 0
        assert metrics.registry_syncs_error == 1
        assert metrics.registry_cache_status == "stale"

    def test_update_droplet_status(self, metrics):
        """Updating droplet status."""
        metrics.update_droplet_status(known=5, reachable=4)

        assert metrics.droplets_known == 5
        assert metrics.droplets_reachable == 4


class TestPercentileCalculations:
    """Tests for percentile calculations."""

    @pytest.fixture
    def metrics(self):
        """Create MetricsCollector with sample data."""
        m = MetricsCollector()
        # Add response times: 100, 200, 300, 400, 500
        for i in range(1, 6):
            m.record_task(status="success", duration_ms=i * 100)
        return m

    def test_percentile_calculation(self, metrics):
        """Percentile calculation works correctly."""
        p50 = metrics.get_percentile(50)
        p95 = metrics.get_percentile(95)
        p99 = metrics.get_percentile(99)

        assert p50 == 300.0
        assert p95 == 500.0
        assert p99 == 500.0

    def test_percentile_empty_list(self):
        """Percentile returns 0 for empty list."""
        m = MetricsCollector()
        assert m.get_percentile(95) == 0.0

    def test_percentile_single_value(self):
        """Percentile works with single value."""
        m = MetricsCollector()
        m.record_task(status="success", duration_ms=100)
        assert m.get_percentile(95) == 100.0


class TestMetricsResponse:
    """Tests for metrics response generation."""

    @pytest.fixture
    def metrics(self):
        """Create MetricsCollector with sample data."""
        m = MetricsCollector()
        m.record_task(status="success", duration_ms=100)
        m.record_task(status="success", duration_ms=200)
        m.record_task(status="error", duration_ms=150, retry_count=2)
        m.record_registry_sync(True, 50.0, 0, "active")
        m.update_droplet_status(known=3, reachable=3)
        return m

    def test_get_metrics_returns_response(self, metrics):
        """Get metrics returns MetricsResponse."""
        response = metrics.get_metrics()

        assert response.service == "orchestrator"
        assert response.version == "1.1.0"
        assert response.uptime_seconds >= 0

    def test_metrics_response_task_stats(self, metrics):
        """Metrics response includes task statistics."""
        response = metrics.get_metrics()

        assert response.tasks.total == 3
        assert response.tasks.success == 2
        assert response.tasks.error == 1
        assert response.tasks.success_rate_percent > 0

    def test_metrics_response_retry_stats(self, metrics):
        """Metrics response includes retry statistics."""
        response = metrics.get_metrics()

        assert response.retry.total_retries == 2
        assert response.retry.retry_final_fail_count == 1

    def test_metrics_response_registry_stats(self, metrics):
        """Metrics response includes Registry statistics."""
        response = metrics.get_metrics()

        assert response.registry.syncs_total == 1
        assert response.registry.syncs_success == 1
        assert response.registry.cache_status == "active"

    def test_metrics_response_droplet_stats(self, metrics):
        """Metrics response includes droplet statistics."""
        response = metrics.get_metrics()

        assert response.droplets_known == 3
        assert response.droplets_reachable == 3

    def test_success_rate_calculation(self, metrics):
        """Success rate calculated correctly."""
        response = metrics.get_metrics()
        expected_rate = (2 / 3) * 100  # 2 success out of 3 total
        assert abs(response.tasks.success_rate_percent - expected_rate) < 0.1

    def test_avg_response_time_calculation(self, metrics):
        """Average response time calculated correctly."""
        response = metrics.get_metrics()
        expected_avg = (100 + 200 + 150) / 3  # Average of 3 durations
        assert abs(response.tasks.avg_response_time_ms - expected_avg) < 0.1

    def test_metrics_response_percentiles(self, metrics):
        """Metrics response includes percentile calculations."""
        response = metrics.get_metrics()

        assert response.tasks.p95_response_time_ms >= 0
        assert response.tasks.p99_response_time_ms >= 0
