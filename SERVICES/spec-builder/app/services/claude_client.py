"""Claude API Client for SPEC Generation"""

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

    async def generate_spec(
        self,
        service_name: str,
        service_type: str,
        purpose: str,
        key_features: list,
        dependencies: list,
        port: int,
        tier: Optional[int],
        reference_patterns: str
    ) -> Dict:
        """
        Generate SPEC using Claude API

        Args:
            service_name: Name of the service
            service_type: Type of service
            purpose: Service purpose
            key_features: List of key features
            dependencies: List of dependencies
            port: Service port
            tier: TIER level
            reference_patterns: Reference spec patterns

        Returns:
            Dictionary with generated spec and metadata
        """
        if not self.is_available():
            raise ValueError("Claude API key not configured")

        try:
            # Build prompt
            prompt = self._build_generation_prompt(
                service_name,
                service_type,
                purpose,
                key_features,
                dependencies,
                port,
                tier,
                reference_patterns
            )

            # Call Claude API
            logger.info(f"🤖 Calling Claude API to generate SPEC for {service_name}...")

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

            # Extract generated spec
            spec_content = response.content[0].text

            # Track token usage
            self.input_tokens_used += response.usage.input_tokens
            self.output_tokens_used += response.usage.output_tokens

            # Calculate cost
            cost_usd = self._calculate_cost(
                response.usage.input_tokens,
                response.usage.output_tokens
            )

            logger.info(
                f"✅ SPEC generated: "
                f"in={response.usage.input_tokens}, "
                f"out={response.usage.output_tokens}, "
                f"cost=${cost_usd:.4f}"
            )

            return {
                "success": True,
                "spec_content": spec_content,
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
            logger.error(f"❌ Generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _build_generation_prompt(
        self,
        service_name: str,
        service_type: str,
        purpose: str,
        key_features: list,
        dependencies: list,
        port: int,
        tier: Optional[int],
        reference_patterns: str
    ) -> str:
        """Build generation prompt for Claude"""

        # Determine tier based on service type if not specified
        if tier is None:
            tier_map = {
                "infrastructure": 0,
                "sacred_loop": 1,
                "domain": 2,
                "api_gateway": 2,
                "data": 2
            }
            tier = tier_map.get(service_type, 2)

        features_list = "\n".join(f"- {f}" for f in key_features) if key_features else "- To be determined"
        deps_list = "\n".join(f"- {d}" for d in dependencies) if dependencies else "- None"

        prompt = f"""You are an expert SPEC architect for the FPAI droplet mesh. Generate a complete, production-ready SPEC.md file for a new service.

**Service Requirements:**
- Name: {service_name}
- Type: {service_type}
- Port: {port}
- TIER: {tier}
- Purpose: {purpose}

**Key Features:**
{features_list}

**Dependencies:**
{deps_list}

**Reference Patterns (Learn from these successful specs):**
{reference_patterns}

**SPEC Structure Requirements:**

Generate a complete SPEC.md with these sections:

1. **Header:**
   - Service Name: {service_name}
   - Port: {port}
   - Version: 1.0.0
   - TIER: {tier}

2. **Purpose** (2-3 paragraphs)
   - What this service does
   - Why it exists
   - How it fits in the mesh

3. **Core Capabilities** (3-7 main features)
   - Detailed feature descriptions
   - How each feature works

4. **UDC Endpoints (5/5)** - CRITICAL - ALL 5 REQUIRED:
   a. GET /health - Returns status, service, version, timestamp
   b. GET /capabilities - Returns features, dependencies, udc_version, metadata
   c. GET /state - Returns uptime, requests_total, errors_last_hour
   d. GET /dependencies - Returns required/optional/missing dependencies
   e. POST /message - Accepts UDC message protocol

   EACH endpoint MUST have:
   - JSON request example (if POST)
   - JSON response example
   - Description of what it does

5. **Business Logic Endpoints**
   - Service-specific endpoints
   - JSON request/response examples for each

6. **Dependencies**
   - Required: List with descriptions
   - Optional: List with descriptions

7. **Auto-Registration**
   - Python code for registering with Registry on startup

8. **Tech Stack**
   - Framework (FastAPI)
   - Language (Python 3.11+)
   - Libraries needed

9. **File Structure**
   - Complete directory tree

10. **Optimization Opportunities**
    - Future enhancements
    - Scalability improvements

11. **Example Usage**
    - Curl commands
    - Real-world examples

12. **Success Criteria**
    - Definition of done
    - Quality metrics

**CRITICAL REQUIREMENTS:**
1. MUST include ALL 5 UDC endpoints with complete examples
2. MUST include JSON examples for ALL endpoints
3. MUST be immediately build-ready for Sacred Loop
4. MUST follow markdown best practices
5. MUST include metadata header (Service Name, Port, Version, TIER)
6. Output ONLY the complete SPEC in markdown format
7. Do NOT include explanations or commentary
8. Do NOT use placeholder text - generate real content

Generate the complete SPEC.md now:"""

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
