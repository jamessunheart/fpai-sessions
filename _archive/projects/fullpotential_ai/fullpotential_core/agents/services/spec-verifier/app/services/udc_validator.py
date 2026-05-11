"""UDC Compliance Validator"""

from typing import List, Dict
from app.config import settings


class UDCValidator:
    """Validates SPEC compliance with UDC standard"""

    REQUIRED_ENDPOINTS = [
        "/health",
        "/capabilities",
        "/state",
        "/dependencies",
        "/message"
    ]

    def __init__(self):
        self.documented_endpoints: List[str] = []
        self.missing_endpoints: List[str] = []

    def validate(self, parsed_spec: Dict) -> Dict:
        """
        Validate UDC compliance

        Args:
            parsed_spec: Parsed SPEC dictionary from SpecParser

        Returns:
            Dictionary with validation results
        """
        self.documented_endpoints = parsed_spec.get("udc_endpoints", [])
        self.missing_endpoints = []

        # Check for missing endpoints
        for endpoint in self.REQUIRED_ENDPOINTS:
            if endpoint not in self.documented_endpoints:
                self.missing_endpoints.append(endpoint)

        # Calculate compliance score
        compliance_score = self._calculate_compliance_score()

        return {
            "documented": len(self.documented_endpoints),
            "required": len(self.REQUIRED_ENDPOINTS),
            "missing": self.missing_endpoints,
            "compliant": len(self.missing_endpoints) == 0,
            "score": compliance_score
        }

    def _calculate_compliance_score(self) -> int:
        """Calculate UDC compliance score (0-100)"""
        if not self.REQUIRED_ENDPOINTS:
            return 100

        # Base score: percentage of endpoints documented
        base_score = (len(self.documented_endpoints) / len(self.REQUIRED_ENDPOINTS)) * 100

        # Bonus for correct naming/formatting (check in documented_endpoints)
        bonus = 0
        if base_score == 100:
            bonus = 0  # Already at 100%

        return min(100, int(base_score + bonus))

    def check_endpoint_documentation_quality(self, spec_content: str, endpoint: str) -> Dict:
        """
        Check quality of endpoint documentation

        Args:
            spec_content: Full SPEC content
            endpoint: Endpoint path to check

        Returns:
            Dictionary with quality metrics
        """
        quality = {
            "has_request_example": False,
            "has_response_example": False,
            "has_description": False,
            "score": 0
        }

        # Find endpoint section in content
        import re
        endpoint_pattern = rf'###\s+\d+\.\s+\w+\s+{re.escape(endpoint)}'
        match = re.search(endpoint_pattern, spec_content)

        if not match:
            return quality

        # Get content after this endpoint (until next ### or end)
        start_pos = match.end()
        next_section = re.search(r'\n###\s+', spec_content[start_pos:])
        if next_section:
            end_pos = start_pos + next_section.start()
        else:
            end_pos = len(spec_content)

        endpoint_content = spec_content[start_pos:end_pos]

        # Check for examples
        if '```json' in endpoint_content or '```python' in endpoint_content:
            quality["has_request_example"] = True
            quality["has_response_example"] = True

        # Check for description (meaningful text)
        text_lines = [line for line in endpoint_content.split('\n')
                     if line.strip() and not line.strip().startswith('```')]
        if len(text_lines) > 2:
            quality["has_description"] = True

        # Calculate score
        checks = [
            quality["has_request_example"],
            quality["has_response_example"],
            quality["has_description"]
        ]
        quality["score"] = int((sum(checks) / len(checks)) * 100)

        return quality

    @staticmethod
    def get_udc_standards() -> Dict:
        """Return UDC standard requirements"""
        return {
            "version": "1.0",
            "required_endpoints": UDCValidator.REQUIRED_ENDPOINTS,
            "message_protocol": {
                "required_fields": [
                    "trace_id",
                    "source",
                    "target",
                    "message_type",
                    "payload",
                    "timestamp"
                ],
                "message_types": ["status", "event", "command", "query"]
            },
            "health_format": {
                "required_fields": ["status", "service", "version", "timestamp"],
                "valid_statuses": ["active", "inactive", "error"]
            }
        }
