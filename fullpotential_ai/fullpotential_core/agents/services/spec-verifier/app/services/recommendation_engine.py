"""Recommendation Engine for SPEC Improvements"""

from typing import Dict, List


class RecommendationEngine:
    """Generates recommendations for SPEC improvements"""

    def __init__(self):
        self.recommendations: List[str] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def generate_recommendations(
        self,
        parsed_spec: Dict,
        udc_validation: Dict,
        scores: Dict
    ) -> Dict:
        """
        Generate improvement recommendations

        Args:
            parsed_spec: Parsed SPEC from SpecParser
            udc_validation: UDC validation results
            scores: Quality scores

        Returns:
            Dictionary with recommendations, errors, warnings
        """
        self.recommendations = []
        self.errors = []
        self.warnings = []

        self._check_critical_issues(parsed_spec, udc_validation)
        self._check_completeness_issues(parsed_spec, scores)
        self._check_clarity_issues(parsed_spec, scores)
        self._check_build_readiness_issues(parsed_spec, scores)
        self._check_best_practices(parsed_spec)

        return {
            "recommendations": self.recommendations,
            "errors": self.errors,
            "warnings": self.warnings
        }

    def _check_critical_issues(self, parsed_spec: Dict, udc_validation: Dict):
        """Check for critical issues that block builds"""
        metadata = parsed_spec.get("metadata", {})

        # Missing service name
        if not metadata.get("service_name"):
            self.errors.append("Missing service name in SPEC header")

        # Missing port
        if not metadata.get("port"):
            self.errors.append("Missing port number in SPEC header")

        # Missing UDC endpoints
        missing_endpoints = udc_validation.get("missing", [])
        if missing_endpoints:
            self.errors.append(
                f"Missing UDC endpoints: {', '.join(missing_endpoints)}"
            )

        # No purpose section
        sections = parsed_spec.get("sections", {})
        if "Purpose" not in sections or len(sections.get("Purpose", "")) < 50:
            self.errors.append("Purpose section missing or too brief")

    def _check_completeness_issues(self, parsed_spec: Dict, scores: Dict):
        """Check completeness-related issues"""
        sections = parsed_spec.get("sections", {})

        # Missing recommended sections
        recommended = [
            ("Core Capabilities", "Capabilities"),
            ("Dependencies", None),
            ("Tech Stack", None),
            ("File Structure", None),
            ("Business Logic Endpoints", None)
        ]

        for primary, alternate in recommended:
            if primary not in sections and (not alternate or alternate not in sections):
                self.recommendations.append(f"Consider adding '{primary}' section")

        # Incomplete sections
        for section_name, content in sections.items():
            if 10 < len(content) < 50:
                self.warnings.append(
                    f"Section '{section_name}' seems incomplete (only {len(content)} chars)"
                )

    def _check_clarity_issues(self, parsed_spec: Dict, scores: Dict):
        """Check clarity-related issues"""
        sections = parsed_spec.get("sections", {})

        # Purpose too brief
        purpose = sections.get("Purpose", "")
        if 50 <= len(purpose) < 100:
            self.recommendations.append(
                "Purpose section could be more detailed (currently brief)"
            )

        # No code examples
        full_content = str(sections)
        if "```" not in full_content:
            self.recommendations.append(
                "Add code examples for API endpoints (JSON request/response)"
            )

        # Check for example usage
        if "Example Usage" not in sections:
            self.recommendations.append(
                "Add 'Example Usage' section with curl/code examples"
            )

    def _check_build_readiness_issues(self, parsed_spec: Dict, scores: Dict):
        """Check build readiness issues"""
        sections = parsed_spec.get("sections", {})
        dependencies = parsed_spec.get("dependencies", {})

        # No dependencies documented
        if not dependencies.get("required") and not dependencies.get("optional"):
            self.warnings.append(
                "No dependencies documented - ensure service is truly dependency-free"
            )

        # No tech stack
        if "Tech Stack" not in sections:
            self.recommendations.append(
                "Add 'Tech Stack' section (framework, language, libraries)"
            )

        # No file structure
        if "File Structure" not in sections:
            self.recommendations.append(
                "Add 'File Structure' section to guide implementation"
            )

        # No optimization opportunities
        if "Optimization Opportunities" not in sections:
            self.recommendations.append(
                "Add 'Optimization Opportunities' section for future enhancements"
            )

    def _check_best_practices(self, parsed_spec: Dict):
        """Check adherence to best practices"""
        sections = parsed_spec.get("sections", {})
        metadata = parsed_spec.get("metadata", {})

        # TIER not specified
        if metadata.get("tier") is None:
            self.warnings.append(
                "TIER level not specified (should be 0-4)"
            )

        # No version
        if not metadata.get("version"):
            self.warnings.append(
                "Version not specified (recommend semantic versioning like 1.0.0)"
            )

        # No success criteria
        if "Success Criteria" not in sections:
            self.recommendations.append(
                "Add 'Success Criteria' section to define done-ness"
            )

        # Auto-registration not documented
        full_content = str(sections)
        if "auto-register" not in full_content.lower() and "startup" not in full_content.lower():
            self.recommendations.append(
                "Document auto-registration with Registry in startup event"
            )

    def compare_with_references(
        self,
        parsed_spec: Dict,
        reference_specs: List[Dict]
    ) -> Dict:
        """
        Compare SPEC against reference specs

        Args:
            parsed_spec: Parsed SPEC to compare
            reference_specs: List of parsed reference SPECs

        Returns:
            Dictionary with similarities, differences, recommendations
        """
        similarities = []
        differences = []
        recommendations = []

        current_sections = set(parsed_spec.get("sections", {}).keys())

        # Find common patterns across references
        reference_sections = {}
        for ref in reference_specs:
            ref_sections = set(ref.get("sections", {}).keys())
            for section in ref_sections:
                reference_sections[section] = reference_sections.get(section, 0) + 1

        # Identify best practices (sections in 75%+ of references)
        threshold = len(reference_specs) * 0.75
        best_practice_sections = [
            section for section, count in reference_sections.items()
            if count >= threshold
        ]

        # Check similarities
        for section in best_practice_sections:
            if section in current_sections:
                similarities.append(
                    f"Includes '{section}' section (best practice from references)"
                )

        # Check differences
        for section in best_practice_sections:
            if section not in current_sections:
                differences.append(
                    f"Missing '{section}' section (present in {reference_sections[section]}/{len(reference_specs)} references)"
                )
                recommendations.append(
                    f"Add '{section}' section following reference pattern"
                )

        # Check for unique sections (not in any reference)
        unique_sections = [
            section for section in current_sections
            if section not in reference_sections
        ]
        if unique_sections:
            differences.append(
                f"Contains unique sections not in references: {', '.join(unique_sections)}"
            )

        # UDC endpoint format comparison
        current_udc = parsed_spec.get("udc_endpoints", [])
        if len(current_udc) == 5:
            similarities.append(
                "UDC endpoint documentation complete (matches best practices)"
            )

        return {
            "similarities": similarities,
            "differences": differences,
            "recommendations": recommendations
        }

    @staticmethod
    def get_recommendation_priorities() -> Dict:
        """Return recommendation priority levels"""
        return {
            "critical": [
                "Missing UDC endpoints",
                "Missing service name",
                "Missing port",
                "Missing purpose"
            ],
            "high": [
                "Missing dependencies section",
                "Missing tech stack",
                "No code examples"
            ],
            "medium": [
                "Missing file structure",
                "Missing optimization opportunities",
                "Purpose too brief"
            ],
            "low": [
                "Missing example usage",
                "Missing success criteria",
                "TIER not specified"
            ]
        }
