"""SPEC File Parser"""

import re
from typing import Dict, List, Optional
from pathlib import Path


class SpecParser:
    """Parses SPEC markdown files and extracts structured information"""

    def __init__(self):
        self.spec_content: str = ""
        self.sections: Dict[str, str] = {}
        self.headers: List[str] = []

    def parse(self, content: str) -> Dict:
        """
        Parse SPEC markdown content

        Args:
            content: SPEC markdown content

        Returns:
            Dictionary with parsed sections
        """
        self.spec_content = content
        self._extract_sections()
        self._extract_headers()

        return {
            "sections": self.sections,
            "headers": self.headers,
            "metadata": self._extract_metadata(),
            "udc_endpoints": self._extract_udc_endpoints(),
            "dependencies": self._extract_dependencies()
        }

    def _extract_sections(self):
        """Extract main sections from SPEC"""
        # Split by markdown headers
        lines = self.spec_content.split('\n')
        current_section = None
        current_content = []

        for line in lines:
            # Check if line is a header (# or ##)
            header_match = re.match(r'^(#{1,2})\s+(.+)$', line)
            if header_match:
                # Save previous section
                if current_section:
                    self.sections[current_section] = '\n'.join(current_content).strip()

                # Start new section
                current_section = header_match.group(2).strip()
                current_content = []
            else:
                if current_section:
                    current_content.append(line)

        # Save last section
        if current_section:
            self.sections[current_section] = '\n'.join(current_content).strip()

    def _extract_headers(self):
        """Extract all headers from SPEC"""
        self.headers = []
        for line in self.spec_content.split('\n'):
            header_match = re.match(r'^#{1,6}\s+(.+)$', line)
            if header_match:
                self.headers.append(header_match.group(1).strip())

    def _extract_metadata(self) -> Dict:
        """Extract service metadata (name, port, version, tier)"""
        metadata = {
            "service_name": None,
            "port": None,
            "version": None,
            "tier": None
        }

        # Look for metadata in first few lines
        first_lines = self.spec_content.split('\n')[:20]

        for line in first_lines:
            # Service name
            if line.startswith("**Service Name:**"):
                metadata["service_name"] = line.split(":", 1)[1].strip()

            # Port
            elif line.startswith("**Port:**"):
                port_str = line.split(":", 1)[1].strip()
                try:
                    metadata["port"] = int(port_str)
                except ValueError:
                    metadata["port"] = port_str

            # Version
            elif line.startswith("**Version:**"):
                metadata["version"] = line.split(":", 1)[1].strip()

            # TIER
            elif line.startswith("**TIER:**"):
                tier_str = line.split(":", 1)[1].strip()
                # Extract number from "0 (Infrastructure)" format
                tier_match = re.match(r'(\d+)', tier_str)
                if tier_match:
                    metadata["tier"] = int(tier_match.group(1))

        return metadata

    def _extract_udc_endpoints(self) -> List[str]:
        """Extract documented UDC endpoints"""
        endpoints = []

        # Look for UDC endpoint sections
        udc_section = self.sections.get("UDC Endpoints", "") + \
                      self.sections.get("UDC Endpoints (5/5)", "")

        # Find endpoint patterns like "### 1. GET /health"
        endpoint_pattern = r'###\s+\d+\.\s+(GET|POST|PUT|DELETE)\s+(/[\w/-]+)'
        matches = re.findall(endpoint_pattern, udc_section)

        for method, path in matches:
            endpoints.append(path)

        return endpoints

    def _extract_dependencies(self) -> Dict:
        """Extract documented dependencies"""
        dependencies = {
            "required": [],
            "optional": []
        }

        # Look in Dependencies section
        dep_section = self.sections.get("Dependencies", "")

        # Extract from "### Required" and "### Optional" subsections
        required_match = re.search(r'###\s+Required\s*(.+?)(?=###|$)', dep_section, re.DOTALL)
        if required_match:
            required_text = required_match.group(1)
            # Extract items from bullet points
            for line in required_text.split('\n'):
                if line.strip().startswith('-') or line.strip().startswith('*'):
                    dep_name = re.sub(r'^\s*[-*]\s+\*\*(.+?)\*\*.*', r'\1', line.strip())
                    if dep_name and dep_name != line.strip():
                        dependencies["required"].append(dep_name)

        optional_match = re.search(r'###\s+Optional\s*(.+?)(?=###|$)', dep_section, re.DOTALL)
        if optional_match:
            optional_text = optional_match.group(1)
            for line in optional_text.split('\n'):
                if line.strip().startswith('-') or line.strip().startswith('*'):
                    dep_name = re.sub(r'^\s*[-*]\s+\*\*(.+?)\*\*.*', r'\1', line.strip())
                    if dep_name and dep_name != line.strip():
                        dependencies["optional"].append(dep_name)

        return dependencies

    def check_section_completeness(self, section_name: str) -> bool:
        """
        Check if a section exists and has meaningful content

        Args:
            section_name: Name of section to check

        Returns:
            True if section exists and has content
        """
        content = self.sections.get(section_name, "").strip()

        # Section must have at least 50 characters to be considered complete
        return len(content) >= 50

    @staticmethod
    def load_from_file(file_path: str) -> str:
        """
        Load SPEC content from file

        Args:
            file_path: Path to SPEC.md file

        Returns:
            SPEC file content
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"SPEC file not found: {file_path}")

        return path.read_text()
