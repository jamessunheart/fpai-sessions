"""Generation Engine - Orchestrates SPEC generation workflow"""

import logging
import time
from typing import Dict, Optional
from app.services.claude_client import ClaudeClient
from app.services.template_manager import TemplateManager
from app.services.integration_client import IntegrationClient

logger = logging.getLogger(__name__)


class GenerationEngine:
    """Orchestrates the SPEC generation workflow"""

    def __init__(self):
        self.claude = ClaudeClient()
        self.templates = TemplateManager()
        self.integration = IntegrationClient()

    async def generate(
        self,
        service_name: str,
        service_type: str,
        purpose: str,
        key_features: list,
        dependencies: list,
        port: int,
        tier: Optional[int],
        auto_optimize: bool,
        target_score: int
    ) -> Dict:
        """
        Generate SPEC from architect intent

        Args:
            service_name: Name of service
            service_type: Type of service
            purpose: Service purpose
            key_features: List of features
            dependencies: List of dependencies
            port: Service port
            tier: TIER level
            auto_optimize: Auto-optimize after generation
            target_score: Target quality score

        Returns:
            Generation result dictionary
        """
        start_time = time.time()

        try:
            # Step 1: Get reference patterns
            logger.info(f"📚 Step 1: Loading reference patterns for {service_type}...")
            reference_patterns = self.templates.get_reference_patterns(service_type)

            # Step 2: Generate SPEC with Claude
            logger.info(f"🤖 Step 2: Generating SPEC for {service_name}...")
            claude_result = await self.claude.generate_spec(
                service_name,
                service_type,
                purpose,
                key_features,
                dependencies,
                port,
                tier,
                reference_patterns
            )

            if not claude_result.get("success"):
                return {
                    "success": False,
                    "error": claude_result.get("error", "Claude generation failed")
                }

            spec_content = claude_result["spec_content"]
            cost_usd = claude_result["cost_usd"]

            # Step 3: Verify generated SPEC
            logger.info("📊 Step 3: Verifying generated SPEC...")
            verification = await self.integration.verify_spec(spec_content)
            initial_score = verification.get("score", {}).get("overall", 0)
            logger.info(f"   Initial score: {initial_score}/100")

            # Step 4: Optimize if needed
            optimized = False
            final_score = initial_score
            improvements = []

            if auto_optimize and initial_score < target_score:
                logger.info(f"🔧 Step 4: Optimizing SPEC (target: {target_score}+)...")
                opt_result = await self.integration.optimize_spec(spec_content, target_score)

                if opt_result.get("success"):
                    spec_content = opt_result["optimized_spec"]
                    final_score = opt_result["verification_after"]["score"]["overall"]
                    improvements = opt_result.get("improvements", [])
                    cost_usd += opt_result.get("claude_cost_usd", 0)
                    optimized = True
                    logger.info(f"   Optimized score: {final_score}/100")

            generation_time = time.time() - start_time

            return {
                "success": True,
                "spec_content": spec_content,
                "verification": verification,
                "optimized": optimized,
                "final_score": final_score,
                "improvements": improvements,
                "claude_cost_usd": round(cost_usd, 4),
                "generation_time_seconds": round(generation_time, 2)
            }

        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
