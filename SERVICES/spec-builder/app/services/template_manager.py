"""Template Manager for SPEC Generation"""

import logging
from pathlib import Path
from typing import Dict, List
from app.config import settings

logger = logging.getLogger(__name__)


class TemplateManager:
    """Manages SPEC templates and reference patterns"""

    def __init__(self):
        self.base_path = Path(settings.services_base_path)
        self.reference_services = {
            "infrastructure": ["registry", "orchestrator", "proxy-manager", "verifier"],
            "sacred_loop": ["autonomous-executor"],
            "domain": ["jobs"],
            "api_gateway": [],
            "data": []
        }

    def get_reference_patterns(self, service_type: str) -> str:
        """
        Get reference patterns for a service type

        Args:
            service_type: Type of service

        Returns:
            String with reference patterns
        """
        services = self.reference_services.get(service_type, [])

        if not services:
            # Fallback to infrastructure patterns
            services = self.reference_services["infrastructure"][:2]

        patterns = []

        for service in services[:2]:  # Limit to 2 references to save tokens
            spec_path = self.base_path / service / "SPEC.md"
            if spec_path.exists():
                try:
                    content = spec_path.read_text()
                    # Extract key sections as patterns
                    patterns.append(f"## Reference: {service}")
                    patterns.append(self._extract_patterns(content))
                except Exception as e:
                    logger.warning(f"Could not read {service} SPEC: {e}")

        if not patterns:
            patterns.append("No reference patterns available - generate from scratch")

        return "\n\n".join(patterns)

    def _extract_patterns(self, spec_content: str) -> str:
        """Extract key patterns from a SPEC"""
        # Extract first 100 lines as pattern (header + main sections)
        lines = spec_content.split('\n')[:100]
        return '\n'.join(lines)

    def get_templates(self) -> List[Dict]:
        """Get available templates"""
        return [
            {
                "name": "infrastructure",
                "description": "For TIER 0 infrastructure services (registry, orchestrator, etc.)",
                "examples": ["registry", "orchestrator", "proxy-manager", "verifier"]
            },
            {
                "name": "sacred_loop",
                "description": "For TIER 1 autonomous Sacred Loop services",
                "examples": ["autonomous-executor", "coordinator"]
            },
            {
                "name": "domain",
                "description": "For business domain services (TIER 2+)",
                "examples": ["jobs", "payment-processor", "user-management"]
            },
            {
                "name": "api_gateway",
                "description": "For API gateway services",
                "examples": ["public-api", "graphql-gateway"]
            },
            {
                "name": "data",
                "description": "For data processing and analytics services",
                "examples": ["analytics-engine", "etl-pipeline"]
            }
        ]
