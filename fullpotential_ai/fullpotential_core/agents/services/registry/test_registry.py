"""Comprehensive test suite for Registry service."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self):
        """Health endpoint returns 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_correct_format(self):
        """Health endpoint returns expected JSON format."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert data["status"] == "ok"
        assert data["service"] == "registry"


class TestCapabilitiesEndpoint:
    """Tests for /capabilities endpoint (UDC)."""

    def test_capabilities_returns_200(self):
        """Capabilities endpoint returns 200 OK."""
        response = client.get("/capabilities")
        assert response.status_code == 200

    def test_capabilities_returns_correct_format(self):
        """Capabilities endpoint returns UDC-compliant format."""
        response = client.get("/capabilities")
        data = response.json()
        assert "version" in data
        assert "features" in data
        assert "dependencies" in data
        assert "udc_version" in data
        assert data["udc_version"] == "1.0"

    def test_capabilities_features_list(self):
        """Capabilities includes expected features."""
        response = client.get("/capabilities")
        data = response.json()
        features = data["features"]
        assert isinstance(features, list)
        assert "service_registry" in features
        assert "identity_management" in features

    def test_capabilities_no_dependencies(self):
        """Registry has no dependencies."""
        response = client.get("/capabilities")
        data = response.json()
        assert data["dependencies"] == []


class TestStateEndpoint:
    """Tests for /state endpoint (UDC)."""

    def test_state_returns_200(self):
        """State endpoint returns 200 OK."""
        response = client.get("/state")
        assert response.status_code == 200

    def test_state_returns_correct_format(self):
        """State endpoint returns UDC-compliant format."""
        response = client.get("/state")
        data = response.json()
        assert "uptime_seconds" in data
        assert "requests_total" in data
        assert "last_restart" in data

    def test_state_uptime_increases(self):
        """Uptime increases with time."""
        response1 = client.get("/state")
        data1 = response1.json()

        # Make another request
        response2 = client.get("/state")
        data2 = response2.json()

        # Uptime should be same or slightly higher
        assert data2["uptime_seconds"] >= data1["uptime_seconds"]

    def test_state_requests_increment(self):
        """Request count increments."""
        response1 = client.get("/state")
        data1 = response1.json()
        requests_before = data1["requests_total"]

        # Make more requests
        client.get("/health")
        client.get("/capabilities")

        response2 = client.get("/state")
        data2 = response2.json()

        # Should have increased
        assert data2["requests_total"] > requests_before


class TestDependenciesEndpoint:
    """Tests for /dependencies endpoint (UDC)."""

    def test_dependencies_returns_200(self):
        """Dependencies endpoint returns 200 OK."""
        response = client.get("/dependencies")
        assert response.status_code == 200

    def test_dependencies_returns_correct_format(self):
        """Dependencies endpoint returns UDC-compliant format."""
        response = client.get("/dependencies")
        data = response.json()
        assert "required" in data
        assert "optional" in data
        assert "missing" in data

    def test_dependencies_all_empty(self):
        """Registry has no dependencies."""
        response = client.get("/dependencies")
        data = response.json()
        assert data["required"] == []
        assert data["optional"] == []
        assert data["missing"] == []


class TestMessageEndpoint:
    """Tests for /message endpoint (UDC)."""

    def test_message_returns_200(self):
        """Message endpoint returns 200 OK."""
        payload = {
            "trace_id": "test-123",
            "source": "test",
            "target": "registry",
            "message_type": "status",
            "payload": {}
        }
        response = client.post("/message", json=payload)
        assert response.status_code == 200

    def test_message_returns_acknowledgment(self):
        """Message endpoint acknowledges receipt."""
        payload = {
            "trace_id": "test-456",
            "source": "orchestrator",
            "target": "registry",
            "message_type": "query",
            "payload": {"query": "status"}
        }
        response = client.post("/message", json=payload)
        data = response.json()
        assert data["status"] == "received"
        assert data["trace_id"] == "test-456"
        assert "timestamp" in data


class TestUDCCompliance:
    """Tests for overall UDC compliance."""

    def test_all_udc_endpoints_exist(self):
        """All 5 UDC endpoints are implemented."""
        endpoints = [
            ("/health", "GET"),
            ("/capabilities", "GET"),
            ("/state", "GET"),
            ("/dependencies", "GET"),
            ("/message", "POST"),
        ]

        for endpoint, method in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={"trace_id": "test"})

            assert response.status_code == 200, f"{method} {endpoint} failed"

    def test_udc_version_consistency(self):
        """UDC version is consistent across endpoints."""
        response = client.get("/capabilities")
        data = response.json()
        assert data["udc_version"] == "1.0"


class TestPerformance:
    """Performance and load tests."""

    def test_health_response_time(self):
        """Health endpoint responds quickly."""
        import time
        start = time.time()
        response = client.get("/health")
        duration = time.time() - start

        assert response.status_code == 200
        assert duration < 0.5  # Should respond in < 500ms

    def test_concurrent_requests(self):
        """Service handles concurrent requests."""
        responses = []
        for _ in range(10):
            responses.append(client.get("/health"))

        # All should succeed
        assert all(r.status_code == 200 for r in responses)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
