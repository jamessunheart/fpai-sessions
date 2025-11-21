"""Generates fixes using Claude API"""

from typing import List, Dict, Any
from anthropic import Anthropic
import json
from pathlib import Path

from .config import settings
from .models import Issue, Fix, IssueType


class FixGenerator:
    """Generates code fixes using Claude API"""

    def __init__(self):
        """Initialize Claude API client"""
        self.client = None
        if settings.anthropic_api_key:
            self.client = Anthropic(api_key=settings.anthropic_api_key)

    async def generate_fixes(
        self,
        droplet_path: str,
        issues: List[Issue]
    ) -> List[Fix]:
        """
        Generate fixes for a list of issues.

        Uses Claude API to analyze code and generate appropriate fixes.
        """
        if not self.client:
            raise Exception("Anthropic API key not configured")

        fixes = []

        # Group issues by type for efficient fixing
        startup_issues = [i for i in issues if i.type == IssueType.STARTUP_FAILURE]
        test_issues = [i for i in issues if i.type == IssueType.TEST_FAILURE]
        quality_issues = [i for i in issues if i.type == IssueType.CODE_QUALITY]

        # Fix startup issues first (most critical)
        if startup_issues:
            startup_fix = await self._fix_startup_issues(droplet_path, startup_issues)
            if startup_fix:
                fixes.append(startup_fix)

        # Fix test failures
        if test_issues:
            test_fix = await self._fix_test_issues(droplet_path, test_issues)
            if test_fix:
                fixes.append(test_fix)

        # Fix code quality issues
        for issue in quality_issues:
            quality_fix = await self._fix_code_quality_issue(droplet_path, issue)
            if quality_fix:
                fixes.append(quality_fix)

        return fixes

    async def _fix_startup_issues(
        self,
        droplet_path: str,
        issues: List[Issue]
    ) -> Fix:
        """Fix startup failures (usually import/dependency issues)"""

        # Read the main.py file to analyze
        main_path = Path(droplet_path) / "app" / "main.py"
        requirements_path = Path(droplet_path) / "requirements.txt"

        if not main_path.exists():
            return None

        with open(main_path, 'r') as f:
            main_content = f.read()

        requirements_content = ""
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                requirements_content = f.read()

        # Build prompt for Claude
        prompt = f"""You are a Python expert fixing a service that won't start.

**Service:** {Path(droplet_path).name}

**Issue:** Service failed to start within 30 seconds during verification.

**Main app code (app/main.py):**
```python
{main_content[:3000]}  # First 3000 chars
```

**Requirements:**
```
{requirements_content}
```

**Common startup failure causes:**
1. Missing dependencies in requirements.txt
2. Import errors (modules not installed)
3. Circular imports
4. Missing environment variables
5. Syntax errors
6. Async/await issues

**Task:**
Analyze the code and identify why it won't start. Then provide:
1. Updated requirements.txt (if dependencies missing)
2. Updated app/main.py (if code fixes needed)
3. Brief explanation of the fix

**Output as JSON:**
{{
  "diagnosis": "Why the service won't start",
  "fix_type": "dependency_add" or "code_change" or "both",
  "requirements_txt": "Full updated requirements.txt content (if needed)",
  "main_py_changes": {{
    "old_code": "Code to replace",
    "new_code": "Fixed code"
  }},
  "reasoning": "Brief explanation of fix"
}}

Provide ONLY the JSON, no other text."""

        message = self.client.messages.create(
            model=settings.claude_model,
            max_tokens=settings.max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text

        # Extract JSON from response
        try:
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text

            fix_data = json.loads(json_text)

            # Build Fix object
            changes = {}
            files = []

            if fix_data.get("requirements_txt"):
                changes[str(requirements_path)] = fix_data["requirements_txt"]
                files.append(str(requirements_path))

            if fix_data.get("main_py_changes"):
                # Apply code changes
                old_code = fix_data["main_py_changes"].get("old_code", "")
                new_code = fix_data["main_py_changes"].get("new_code", "")
                if old_code and new_code:
                    updated_main = main_content.replace(old_code, new_code)
                    changes[str(main_path)] = updated_main
                    files.append(str(main_path))

            return Fix(
                issue=issues[0],
                fix_type=fix_data.get("fix_type", "code_change"),
                description=fix_data.get("diagnosis", "Fix startup issues"),
                files_to_modify=files,
                changes=changes,
                commands=["pip install -r requirements.txt"] if fix_data.get("requirements_txt") else [],
                reasoning=fix_data.get("reasoning", "")
            )

        except json.JSONDecodeError:
            # Couldn't parse response, return None
            return None

    async def _fix_test_issues(
        self,
        droplet_path: str,
        issues: List[Issue]
    ) -> Fix:
        """Fix test failures"""
        # Similar to startup fix but focused on test files
        # For now, return None (tests are less critical than startup)
        return None

    async def _fix_code_quality_issue(
        self,
        droplet_path: str,
        issue: Issue
    ) -> Fix:
        """Fix code quality issues (print statements, bare except, etc.)"""

        description = issue.description.lower()

        # Fix print statements -> logging
        if "print statement" in description:
            # Find files with print statements and convert to logging
            changes = {}
            # This would search files and replace print() with logging
            # Simplified for now

            return Fix(
                issue=issue,
                fix_type="code_change",
                description="Replace print statements with logging",
                files_to_modify=[],
                changes=changes,
                reasoning="Using logging instead of print for better production practices"
            )

        # Fix bare except
        if "bare except" in description:
            return Fix(
                issue=issue,
                fix_type="code_change",
                description="Replace bare except with specific exceptions",
                files_to_modify=[],
                changes={},
                reasoning="Bare except clauses can hide errors"
            )

        return None
