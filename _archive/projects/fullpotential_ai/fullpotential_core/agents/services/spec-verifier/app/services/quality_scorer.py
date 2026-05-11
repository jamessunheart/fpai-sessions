"""SPEC Quality Scorer"""

from typing import Dict, List
from app.config import settings


class QualityScorer:
    """Scores SPEC quality across multiple dimensions"""

    def __init__(self):
        self.parsed_spec: Dict = {}
        self.udc_validation: Dict = {}

    def score(self, parsed_spec: Dict, udc_validation: Dict) -> Dict:
        """
        Calculate quality scores

        Args:
            parsed_spec: Parsed SPEC from SpecParser
            udc_validation: UDC validation results from UDCValidator

        Returns:
            Dictionary with scores
        """
        self.parsed_spec = parsed_spec
        self.udc_validation = udc_validation

        completeness = self._score_completeness()
        clarity = self._score_clarity()
        udc_compliance = udc_validation.get("score", 0)
        build_readiness = self._score_build_readiness()

        # Weighted overall score
        # Completeness: 40%, Clarity: 30%, UDC: 20%, Build-Ready: 10%
        overall = (
            completeness * 0.40 +
            clarity * 0.30 +
            udc_compliance * 0.20 +
            build_readiness * 0.10
        )

        return {
            "completeness": completeness,
            "clarity": clarity,
            "udc_compliance": udc_compliance,
            "build_readiness": build_readiness,
            "overall": round(overall, 2)
        }

    def _score_completeness(self) -> int:
        """Score completeness of required sections (0-100)"""
        sections = self.parsed_spec.get("sections", {})

        # Required sections
        required = settings.required_sections
        found = 0

        for section in required:
            # Check if section exists and has meaningful content
            content = sections.get(section, "").strip()
            if len(content) >= 50:  # At least 50 chars
                found += 1

        # Bonus sections that improve score
        bonus_sections = [
            "Business Logic Endpoints",
            "Optimization Opportunities",
            "Tech Stack",
            "Example Usage"
        ]
        bonus_found = sum(1 for s in bonus_sections if s in sections and len(sections[s]) >= 50)

        # Base score from required sections
        base_score = (found / len(required)) * 85

        # Bonus up to 15 points
        bonus_score = (bonus_found / len(bonus_sections)) * 15

        return min(100, int(base_score + bonus_score))

    def _score_clarity(self) -> int:
        """Score clarity and quality of descriptions (0-100)"""
        sections = self.parsed_spec.get("sections", {})
        metadata = self.parsed_spec.get("metadata", {})

        score = 0
        max_score = 100

        # Check metadata completeness (30 points)
        metadata_fields = ["service_name", "port", "version"]
        metadata_complete = sum(1 for f in metadata_fields if metadata.get(f) is not None)
        score += (metadata_complete / len(metadata_fields)) * 30

        # Check Purpose section quality (30 points)
        purpose = sections.get("Purpose", "")
        if len(purpose) >= 100:
            score += 30
        elif len(purpose) >= 50:
            score += 15

        # Check Capabilities section quality (20 points)
        capabilities = sections.get("Capabilities", "") + sections.get("Core Capabilities", "")
        if len(capabilities) >= 200:
            score += 20
        elif len(capabilities) >= 100:
            score += 10

        # Check for code examples (20 points)
        full_content = str(sections)
        if "```json" in full_content or "```python" in full_content:
            score += 20

        return min(max_score, int(score))

    def _score_build_readiness(self) -> int:
        """Score readiness for Sacred Loop build (0-100)"""
        sections = self.parsed_spec.get("sections", {})
        dependencies = self.parsed_spec.get("dependencies", {})

        score = 0

        # Dependencies clearly documented (30 points)
        required_deps = dependencies.get("required", [])
        optional_deps = dependencies.get("optional", [])
        if required_deps or optional_deps:
            score += 30

        # Tech Stack section exists (20 points)
        if "Tech Stack" in sections and len(sections["Tech Stack"]) >= 50:
            score += 20

        # File Structure section exists (20 points)
        if "File Structure" in sections and len(sections["File Structure"]) >= 50:
            score += 20

        # Business endpoints documented (15 points)
        if "Business Logic Endpoints" in sections and len(sections["Business Logic Endpoints"]) >= 100:
            score += 15

        # Example usage provided (15 points)
        if "Example Usage" in sections and len(sections["Example Usage"]) >= 50:
            score += 15

        return min(100, int(score))

    def get_score_interpretation(self, overall_score: float) -> Dict:
        """
        Get interpretation of overall score

        Args:
            overall_score: Overall quality score

        Returns:
            Dictionary with interpretation
        """
        if overall_score >= 90:
            return {
                "grade": "A",
                "label": "Excellent",
                "message": "SPEC is ready for build",
                "ready_for_build": True
            }
        elif overall_score >= 75:
            return {
                "grade": "B",
                "label": "Good",
                "message": "SPEC is acceptable with minor improvements recommended",
                "ready_for_build": True
            }
        elif overall_score >= 60:
            return {
                "grade": "C",
                "label": "Fair",
                "message": "SPEC needs significant improvements before build",
                "ready_for_build": False
            }
        else:
            return {
                "grade": "F",
                "label": "Poor",
                "message": "SPEC is not ready for build - major revisions needed",
                "ready_for_build": False
            }

    @staticmethod
    def get_section_weight_info() -> Dict:
        """Return information about section scoring weights"""
        return {
            "overall_weights": {
                "completeness": 40,
                "clarity": 30,
                "udc_compliance": 20,
                "build_readiness": 10
            },
            "completeness_factors": {
                "required_sections": 85,
                "bonus_sections": 15
            },
            "clarity_factors": {
                "metadata": 30,
                "purpose_quality": 30,
                "capabilities_quality": 20,
                "code_examples": 20
            },
            "build_readiness_factors": {
                "dependencies": 30,
                "tech_stack": 20,
                "file_structure": 20,
                "business_endpoints": 15,
                "examples": 15
            }
        }
