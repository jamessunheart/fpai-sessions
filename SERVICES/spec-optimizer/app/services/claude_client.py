"""Claude API Client for SPEC Optimization"""

import logging
from typing import Dict, Optional
from anthropic import Anthropic, APIError
from app.config import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for Claude API interactions"""

    def __init__(self):
        self.api_key = settings.anthropic_api_key
        self.client = None
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)

        self.input_tokens_used = 0
        self.output_tokens_used = 0

    def is_available(self) -> bool:
        """Check if Claude API is available"""
        return self.client is not None

    async def optimize_spec(
        self,
        spec_content: str,
        verification_report: Dict,
        optimization_level: str,
        target_score: int
    ) -> Dict:
        """
        Optimize SPEC using Claude API

        Args:
            spec_content: Original SPEC content
            verification_report: Report from spec-verifier
            optimization_level: basic|standard|aggressive
            target_score: Target quality score

        Returns:
            Dictionary with optimized spec and metadata
        """
        if not self.is_available():
            raise ValueError("Claude API key not configured")

        try:
            # Build prompt
            prompt = self._build_optimization_prompt(
                spec_content,
                verification_report,
                optimization_level,
                target_score
            )

            # Call Claude API
            logger.info(f"🤖 Calling Claude API for {optimization_level} optimization...")

            response = self.client.messages.create(
                model=settings.claude_model,
                max_tokens=settings.max_tokens,
                temperature=settings.temperature,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract optimized spec from response
            optimized_spec = response.content[0].text

            # Track token usage
            self.input_tokens_used += response.usage.input_tokens
            self.output_tokens_used += response.usage.output_tokens

            # Calculate cost
            cost_usd = self._calculate_cost(
                response.usage.input_tokens,
                response.usage.output_tokens
            )

            logger.info(
                f"✅ Claude optimization complete: "
                f"in={response.usage.input_tokens}, "
                f"out={response.usage.output_tokens}, "
                f"cost=${cost_usd:.4f}"
            )

            return {
                "success": True,
                "optimized_spec": optimized_spec,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cost_usd": cost_usd
            }

        except APIError as e:
            logger.error(f"❌ Claude API error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"❌ Optimization failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _build_optimization_prompt(
        self,
        spec_content: str,
        verification_report: Dict,
        optimization_level: str,
        target_score: int
    ) -> str:
        """Build optimization prompt for Claude"""

        # Extract verification details
        score = verification_report.get("score", {}).get("overall", 0)
        errors = verification_report.get("errors", [])
        warnings = verification_report.get("warnings", [])
        recommendations = verification_report.get("recommendations", [])
        missing_sections = verification_report.get("sections", {}).get("missing", [])
        udc_missing = verification_report.get("udc_endpoints", {}).get("missing", [])

        # Build optimization instructions based on level
        if optimization_level == "basic":
            instructions = """
**Optimization Focus (Basic):**
1. Fix all critical errors
2. Add missing required sections
3. Ensure all 5 UDC endpoints are documented
4. Minimal changes - focus on compliance
"""
        elif optimization_level == "standard":
            instructions = """
**Optimization Focus (Standard):**
1. Fix all errors and warnings
2. Add missing sections with meaningful content
3. Ensure all 5 UDC endpoints with examples
4. Improve clarity and add code examples
5. Enhance descriptions and documentation
"""
        else:  # aggressive
            instructions = """
**Optimization Focus (Aggressive):**
1. Fix all errors, warnings, and recommendations
2. Add missing sections with comprehensive content
3. All 5 UDC endpoints with detailed examples
4. Add extensive code examples (JSON/curl)
5. Add Tech Stack, File Structure, Optimization Opportunities
6. Improve all descriptions for maximum clarity
7. Add Example Usage section with multiple examples
8. Follow best practices from high-scoring SPECs
"""

        prompt = f"""You are an expert SPEC optimization assistant for the FPAI droplet mesh architecture. Your task is to improve the following SPEC file while preserving its original intent and technical accuracy.

**CURRENT SPEC:**
```markdown
{spec_content}
```

**VERIFICATION REPORT:**
- Current Score: {score}/100
- Target Score: {target_score}+
- Errors: {len(errors)}
- Warnings: {len(warnings)}

**CRITICAL ISSUES:**
{chr(10).join(f"- {error}" for error in errors) if errors else "None"}

**WARNINGS:**
{chr(10).join(f"- {warning}" for warning in warnings) if warnings else "None"}

**RECOMMENDATIONS:**
{chr(10).join(f"- {rec}" for rec in recommendations) if recommendations else "None"}

**MISSING SECTIONS:**
{chr(10).join(f"- {section}" for section in missing_sections) if missing_sections else "None"}

**MISSING UDC ENDPOINTS:**
{chr(10).join(f"- {endpoint}" for endpoint in udc_missing) if udc_missing else "All present"}

{instructions}

**REQUIREMENTS:**
1. PRESERVE all existing content - enhance, don't replace
2. Maintain technical accuracy and original intent
3. Add missing UDC endpoints (must have all 5: /health, /capabilities, /state, /dependencies, /message)
4. Use proper markdown formatting
5. Add JSON examples for all endpoints
6. Ensure Service Name, Port, Version, TIER are in header
7. Output ONLY the complete optimized SPEC in markdown format
8. Do NOT include explanations or commentary - just the SPEC

**UDC STANDARD REFERENCE:**
All droplet SPECs must document these 5 endpoints:
1. GET /health - Returns status, service, version, timestamp
2. GET /capabilities - Returns features, dependencies, udc_version, metadata
3. GET /state - Returns uptime, requests, errors, metrics
4. GET /dependencies - Returns required/optional/missing dependencies
5. POST /message - Accepts UDC message protocol (trace_id, source, target, message_type, payload, timestamp)

Generate the optimized SPEC now:"""

        return prompt

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for Claude API usage"""
        input_cost = (input_tokens / 1_000_000) * settings.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * settings.output_cost_per_million
        return input_cost + output_cost

    def get_usage_stats(self) -> Dict:
        """Get cumulative usage statistics"""
        total_cost = self._calculate_cost(
            self.input_tokens_used,
            self.output_tokens_used
        )

        return {
            "input_tokens_total": self.input_tokens_used,
            "output_tokens_total": self.output_tokens_used,
            "total_cost_usd": round(total_cost, 4)
        }
