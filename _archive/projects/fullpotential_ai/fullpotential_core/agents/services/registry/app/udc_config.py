"""Static mesh configuration for the droplet registry.

This file acts as the local `udc_config` reference used by `/registry/map`.
Each entry represents a droplet and the upstream dependencies it expects
to reach inside the mesh. These dependencies are used to build the system
topology so the frontend can visualize the service graph.
"""

from __future__ import annotations

SYSTEM_TOPOLOGY = {
    "version": "2025-11-23",
    "droplets": [
        {
            "id": "registry",
            "name": "Registry",
            "status": "active",
            "type": "core",
            "endpoint": "https://fullpotential.ai/registry",
            "dependencies": [],
            "metadata": {
                "role": "System source of truth",
                "version": "1.0.0",
            },
        },
        {
            "id": "orchestrator",
            "name": "Orchestrator",
            "status": "active",
            "type": "coordination",
            "endpoint": "https://fullpotential.ai/orchestrator",
            "dependencies": ["registry"],
            "metadata": {
                "role": "Schedules and supervises droplets",
                "version": "1.2.0",
            },
        },
        {
            "id": "magnet",
            "name": "Magnet",
            "status": "active",
            "type": "revenue",
            "endpoint": "https://fullpotential.ai/magnet",
            "dependencies": ["registry", "orchestrator"],
            "metadata": {
                "role": "Demand generation and intake",
                "version": "0.9.4",
            },
        },
        {
            "id": "storefront",
            "name": "Storefront",
            "status": "error",
            "type": "experience",
            "endpoint": "https://fullpotential.ai",
            "dependencies": ["registry", "magnet"],
            "metadata": {
                "role": "Public experience layer",
                "version": "0.4.1",
            },
        },
    ],
}


