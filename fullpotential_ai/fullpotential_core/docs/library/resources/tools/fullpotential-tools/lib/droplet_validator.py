#!/usr/bin/env python3
"""
Droplet Validator
Validates droplets against UDC (Universal Droplet Contract)
"""

import os
import json
import requests
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of a validation check"""
    passed: bool
    category: str
    check: str
    message: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW


class DropletValidator:
    """Validate droplets against Universal Droplet Contract"""

    REQUIRED_ENDPOINTS = [
        '/health',
        '/capabilities',
        '/state',
        '/dependencies',
        '/message'
    ]

    VALID_STATUSES = ['active', 'inactive', 'error']

    def __init__(self, droplet_url: str = None, local_path: str = None):
        self.droplet_url = droplet_url
        self.local_path = local_path
        self.results: List[ValidationResult] = []

    def validate_all(self) -> Tuple[bool, List[ValidationResult]]:
        """Run all validation checks"""

        self.results = []

        if self.droplet_url:
            self._validate_live_endpoints()

        if self.local_path:
            self._validate_local_structure()
            self._validate_code_standards()
            self._validate_security()
            self._validate_documentation()

        # Determine overall pass/fail
        critical_failures = [r for r in self.results if not r.passed and r.severity == 'CRITICAL']
        overall_pass = len(critical_failures) == 0

        return overall_pass, self.results

    def _validate_live_endpoints(self):
        """Validate live droplet endpoints"""

        base_url = self.droplet_url.rstrip('/')

        # Check required endpoints
        for endpoint in self.REQUIRED_ENDPOINTS:
            url = f"{base_url}{endpoint}"

            try:
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    self.results.append(ValidationResult(
                        passed=True,
                        category='UDC Endpoints',
                        check=f'Endpoint {endpoint}',
                        message=f'{endpoint} is accessible',
                        severity='CRITICAL'
                    ))

                    # Validate response format for specific endpoints
                    if endpoint == '/health':
                        self._validate_health_response(response.json())
                    elif endpoint == '/state':
                        self._validate_state_response(response.json())

                else:
                    self.results.append(ValidationResult(
                        passed=False,
                        category='UDC Endpoints',
                        check=f'Endpoint {endpoint}',
                        message=f'{endpoint} returned status {response.status_code}',
                        severity='CRITICAL'
                    ))

            except requests.RequestException as e:
                self.results.append(ValidationResult(
                    passed=False,
                    category='UDC Endpoints',
                    check=f'Endpoint {endpoint}',
                    message=f'{endpoint} not accessible: {str(e)}',
                    severity='CRITICAL'
                ))

    def _validate_health_response(self, data: Dict):
        """Validate /health endpoint response format"""

        required_fields = ['status', 'timestamp']

        for field in required_fields:
            if field not in data:
                self.results.append(ValidationResult(
                    passed=False,
                    category='UDC Compliance',
                    check=f'/health response format',
                    message=f'Missing required field: {field}',
                    severity='HIGH'
                ))
            elif field == 'status' and data[field] not in self.VALID_STATUSES:
                self.results.append(ValidationResult(
                    passed=False,
                    category='UDC Compliance',
                    check=f'/health status value',
                    message=f'Invalid status: {data[field]}. Must be one of {self.VALID_STATUSES}',
                    severity='HIGH'
                ))

    def _validate_state_response(self, data: Dict):
        """Validate /state endpoint response format"""

        if 'state' not in data:
            self.results.append(ValidationResult(
                passed=False,
                category='UDC Compliance',
                check='/state response format',
                message='Missing required field: state',
                severity='HIGH'
            ))

    def _validate_local_structure(self):
        """Validate local repository structure"""

        if not self.local_path or not os.path.exists(self.local_path):
            return

        required_files = [
            'README.md',
            'Dockerfile',
            'requirements.txt',
            '.gitignore'
        ]

        for file in required_files:
            file_path = os.path.join(self.local_path, file)

            if os.path.exists(file_path):
                self.results.append(ValidationResult(
                    passed=True,
                    category='Repository Structure',
                    check=f'Required file: {file}',
                    message=f'{file} exists',
                    severity='HIGH'
                ))
            else:
                self.results.append(ValidationResult(
                    passed=False,
                    category='Repository Structure',
                    check=f'Required file: {file}',
                    message=f'{file} is missing',
                    severity='HIGH'
                ))

        # Check for app directory
        app_dir = os.path.join(self.local_path, 'app')
        if os.path.exists(app_dir):
            self.results.append(ValidationResult(
                passed=True,
                category='Repository Structure',
                check='App directory',
                message='app/ directory exists',
                severity='MEDIUM'
            ))
        else:
            self.results.append(ValidationResult(
                passed=False,
                category='Repository Structure',
                check='App directory',
                message='app/ directory missing',
                severity='MEDIUM'
            ))

    def _validate_code_standards(self):
        """Validate code standards"""

        if not self.local_path:
            return

        # Check for type hints in Python files
        py_files = self._find_files('*.py')

        if py_files:
            self.results.append(ValidationResult(
                passed=True,
                category='Code Standards',
                check='Python files present',
                message=f'Found {len(py_files)} Python files',
                severity='LOW'
            ))

            # Sample check - would need more sophisticated analysis for production
            files_with_no_docstrings = []
            for py_file in py_files[:5]:  # Check first 5 files
                if not self._has_docstrings(py_file):
                    files_with_no_docstrings.append(os.path.basename(py_file))

            if files_with_no_docstrings:
                self.results.append(ValidationResult(
                    passed=False,
                    category='Code Standards',
                    check='Docstrings',
                    message=f'Files missing docstrings: {", ".join(files_with_no_docstrings)}',
                    severity='MEDIUM'
                ))

    def _validate_security(self):
        """Validate security requirements"""

        if not self.local_path:
            return

        # Check for hardcoded secrets (basic check)
        py_files = self._find_files('*.py')

        security_issues = []

        for py_file in py_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()

                    # Check for common security issues
                    if 'password' in content.lower() and '=' in content:
                        if 'password = "' in content.lower() or "password = '" in content.lower():
                            security_issues.append(f'{os.path.basename(py_file)}: Possible hardcoded password')

                    if 'api_key' in content.lower() and '=' in content:
                        if 'api_key = "' in content.lower() or "api_key = '" in content.lower():
                            security_issues.append(f'{os.path.basename(py_file)}: Possible hardcoded API key')

            except Exception:
                pass

        if security_issues:
            self.results.append(ValidationResult(
                passed=False,
                category='Security',
                check='Hardcoded secrets',
                message=f'Potential security issues found: {"; ".join(security_issues)}',
                severity='CRITICAL'
            ))
        else:
            self.results.append(ValidationResult(
                passed=True,
                category='Security',
                check='Hardcoded secrets',
                message='No obvious hardcoded secrets detected',
                severity='CRITICAL'
            ))

    def _validate_documentation(self):
        """Validate documentation requirements"""

        if not self.local_path:
            return

        readme_path = os.path.join(self.local_path, 'README.md')

        if os.path.exists(readme_path):
            try:
                with open(readme_path, 'r') as f:
                    content = f.read()

                required_sections = [
                    '## Overview',
                    '## Installation',
                    '## Usage',
                    '## API Endpoints'
                ]

                missing_sections = []
                for section in required_sections:
                    if section.lower() not in content.lower():
                        missing_sections.append(section)

                if missing_sections:
                    self.results.append(ValidationResult(
                        passed=False,
                        category='Documentation',
                        check='README completeness',
                        message=f'Missing sections: {", ".join(missing_sections)}',
                        severity='MEDIUM'
                    ))
                else:
                    self.results.append(ValidationResult(
                        passed=True,
                        category='Documentation',
                        check='README completeness',
                        message='README has all required sections',
                        severity='MEDIUM'
                    ))

            except Exception as e:
                self.results.append(ValidationResult(
                    passed=False,
                    category='Documentation',
                    check='README readability',
                    message=f'Error reading README: {str(e)}',
                    severity='MEDIUM'
                ))

    def _find_files(self, pattern: str) -> List[str]:
        """Find files matching pattern in local_path"""

        if not self.local_path:
            return []

        import glob
        search_pattern = os.path.join(self.local_path, '**', pattern)
        return glob.glob(search_pattern, recursive=True)

    def _has_docstrings(self, filepath: str) -> bool:
        """Check if Python file has docstrings"""

        try:
            with open(filepath, 'r') as f:
                content = f.read()
                return '"""' in content or "'''" in content
        except Exception:
            return False

    def generate_report(self) -> str:
        """Generate validation report"""

        passed = [r for r in self.results if r.passed]
        failed = [r for r in self.results if not r.passed]

        critical_failures = [r for r in failed if r.severity == 'CRITICAL']
        high_failures = [r for r in failed if r.severity == 'HIGH']

        report = f"""
🔍 DROPLET VALIDATION REPORT

Droplet URL: {self.droplet_url or 'N/A'}
Local Path: {self.local_path or 'N/A'}

SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Checks: {len(self.results)}
✅ Passed: {len(passed)}
❌ Failed: {len(failed)}

SEVERITY BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟥 Critical: {len(critical_failures)}
🟧 High: {len(high_failures)}
🟨 Medium: {len([r for r in failed if r.severity == 'MEDIUM'])}
🟩 Low: {len([r for r in failed if r.severity == 'LOW'])}

"""

        if critical_failures:
            report += "\n🟥 CRITICAL FAILURES\n"
            report += "━" * 45 + "\n"
            for result in critical_failures:
                report += f"❌ {result.check}\n"
                report += f"   {result.message}\n\n"

        if high_failures:
            report += "\n🟧 HIGH PRIORITY FAILURES\n"
            report += "━" * 45 + "\n"
            for result in high_failures:
                report += f"❌ {result.check}\n"
                report += f"   {result.message}\n\n"

        # Overall verdict
        if len(critical_failures) == 0:
            report += "\n✅ VERDICT: PASS\n"
            report += "This droplet meets UDC requirements.\n"
        else:
            report += "\n❌ VERDICT: FAIL\n"
            report += f"This droplet has {len(critical_failures)} critical issues that must be fixed.\n"

        return report


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Validate Droplet against UDC')
    parser.add_argument('--url', help='Live droplet URL to validate')
    parser.add_argument('--path', help='Local droplet repository path')
    parser.add_argument('--output', help='Output file for report')

    args = parser.parse_args()

    if not args.url and not args.path:
        print("❌ Error: Must provide either --url or --path")
        return

    validator = DropletValidator(droplet_url=args.url, local_path=args.path)

    print("🔍 Running validation checks...")
    overall_pass, results = validator.validate_all()

    report = validator.generate_report()
    print(report)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {args.output}")


if __name__ == '__main__':
    main()
