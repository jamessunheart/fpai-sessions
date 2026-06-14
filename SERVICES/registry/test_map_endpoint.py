import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_system_map_returns_registry_node():
    """Test that the map endpoint returns at least the registry node."""
    response = client.get("/registry/map")
    assert response.status_code == 200
    data = response.json()
    
    assert "nodes" in data
    assert "edges" in data
    assert "timestamp" in data
    
    # Verify registry node exists
    registry_nodes = [n for n in data["nodes"] if n["id"] == "registry"]
    assert len(registry_nodes) == 1
    assert registry_nodes[0]["type"] == "core"

def test_get_system_map_with_registered_droplet():
    """Test that registering a droplet creates a node and an edge."""
    # 1. Register a droplet
    droplet_data = {
        "name": "test-droplet-m010",
        "endpoint": "http://test-droplet:8000"
    }
    reg_response = client.post("/droplets", json=droplet_data)
    assert reg_response.status_code == 201
    
    # 2. Get Map
    response = client.get("/registry/map")
    assert response.status_code == 200
    data = response.json()
    
    # 3. Verify Droplet Node
    droplet_nodes = [n for n in data["nodes"] if n["id"] == "test-droplet-m010"]
    assert len(droplet_nodes) == 1
    assert droplet_nodes[0]["type"] == "droplet"
    
    # 4. Verify Edge (Registry -> Droplet)
    edges = [e for e in data["edges"] if e["target"] == "test-droplet-m010"]
    assert len(edges) >= 1
    assert edges[0]["source"] == "registry"
    assert edges[0]["status"] == "active"

