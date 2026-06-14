"""Optimization Engine - Orchestrates SPEC optimization workflow"""

import logging
from pathlib import Path
from typing import Dict, List, Optional
from app.config import settings
from app.services.claude_client import ClaudeClient
from app.services.verification_client import VerificationClient
from app.models.optimization_models import VerificationSnapshot

logger = logging.getLogger(__name__)


class OptimizationEngine:
    """Orchestrates the SPEC optimization workflow"""

    def __init__(self):
        self.claude = ClaudeClient()
        self.verifier = VerificationClient()

    async def optimize(
        self,
        spec_content: str,
        optimization_level: str = "standard",
        target_score: int = 85,
        preserve_sections: List[str] = None
    ) -> Dict:
        """
        Optimize SPEC content

        Args:
            spec_content: Original SPEC content
            optimization_level: basic|standard|aggressive
            target_score: Target quality score
            preserve_sections: Sections to preserve as-is

        Returns:
            Optimization result dictionary
        """
        preserve_sections = preserve_sections or []

        try:
            # Step 1: Verify original SPEC
            logger.info("📊 Step 1: Verifying original SPEC...")
            verification_before = await self.verifier.verify_spec(spec_content)

            score_before = verification_before.get("score", {}).get("overall", 0)
            logger.info(f"   Original score: {score_before}/100")

            # Step 2: Optimize with Claude
            logger.info(f"🤖 Step 2: Optimizing with Claude ({optimization_level})...")
            claude_result = await self.claude.optimize_spec(
                spec_content,
                verification_before,
                optimization_level,
                target_score
            )

            if not claude_result.get("success"):
                return {
                    "success": False,
                    "error": claude_result.get("error", "Claude optimization failed")
                }

            optimized_spec = claude_result["optimized_spec"]

            # Step 3: Verify optimized SPEC
            logger.info("📊 Step 3: Verifying optimized SPEC...")
            verification_after = await self.verifier.verify_spec(optimized_spec)

            score_after = verification_after.get("score", {}).get("overall", 0)
            improvement = score_after - score_before

            logger.info(f"   Optimized score: {score_after}/100 (Δ {improvement:+.1f})")

            # Step 4: Identify improvements
            improvements = self._identify_improvements(
                verification_before,
                verification_after
            )

            return {
                "success": True,
                "original_spec": spec_content,
                "optimized_spec": optimized_spec,
                "verification_before": self._to_snapshot(verification_before),
                "verification_after": self._to_snapshot(verification_after),
                "improvements": improvements,
                "score_improvement": round(improvement, 2),
                "claude_cost_usd": claude_result["cost_usd"],
                "input_tokens": claude_result["input_tokens"],
                "output_tokens": claude_result["output_tokens"]
            }

        except Exception as e:
            logger.error(f"❌ Optimization failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def optimize_file(
        self,
        file_path: str,
        optimization_level: str = "standard",
        save_backup: bool = True,
        overwrite: bool = False
    ) -> Dict:
        """
        Optimize SPEC file by path

        Args:
            file_path: Path to SPEC file
            optimization_level: basic|standard|aggressive
            save_backup: Save backup of original
            overwrite: Overwrite original file

        Returns:
            Optimization result dictionary
        """
        try:
            # Load SPEC file
            path = Path(file_path)
            if not path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {file_path}"
                }

            spec_content = path.read_text()

            # Optimize
            result = await self.optimize(
                spec_content,
                optimization_level=optimization_level
            )

            if not result["success"]:
                return result

            # Save results
            backup_path = None
            output_path = None

            if save_backup:
                backup_path = str(path) + ".backup"
                Path(backup_path).write_text(spec_content)
                logger.info(f"💾 Backup saved: {backup_path}")

            if overwrite:
                output_path = str(path)
                path.write_text(result["optimized_spec"])
                logger.info(f"💾 Overwritten: {output_path}")
            else:
                output_path = str(path).replace(".md", ".optimized.md")
                Path(output_path).write_text(result["optimized_spec"])
                logger.info(f"💾 Saved optimized: {output_path}")

            result["backup_path"] = backup_path
            result["output_path"] = output_path

            return result

        except Exception as e:
            logger.error(f"❌ File optimization failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def batch_optimize(
        self,
        file_paths: List[str],
        optimization_level: str = "standard"
    ) -> Dict:
        """
        Optimize multiple SPEC files

        Args:
            file_paths: List of SPEC file paths
            optimization_level: basic|standard|aggressive

        Returns:
            Batch optimization result
        """
        results = []
        total_cost = 0.0
        total_improvement = 0.0
        successful = 0
        failed = 0

        for file_path in file_paths:
            logger.info(f"🔄 Optimizing: {file_path}")

            result = await self.optimize_file(
                file_path,
                optimization_level=optimization_level,
                save_backup=True,
                overwrite=False
            )

            file_name = Path(file_path).name

            if result["success"]:
                successful += 1
                total_cost += result["claude_cost_usd"]
                total_improvement += result["score_improvement"]

                results.append({
                    "file": file_name,
                    "success": True,
                    "score_improvement": result["score_improvement"],
                    "cost_usd": result["claude_cost_usd"]
                })
            else:
                failed += 1
                results.append({
                    "file": file_name,
                    "success": False,
                    "error": result.get("error", "Unknown error")
                })

        avg_improvement = total_improvement / successful if successful > 0 else 0.0

        return {
            "results": results,
            "total_improved": successful,
            "total_failed": failed,
            "average_improvement": round(avg_improvement, 2),
            "total_cost_usd": round(total_cost, 4)
        }

    def _identify_improvements(
        self,
        before: Dict,
        after: Dict
    ) -> List[str]:
        """Identify specific improvements made"""
        improvements = []

        # Check UDC endpoints
        udc_before = before.get("udc_endpoints", {})
        udc_after = after.get("udc_endpoints", {})

        if udc_before.get("documented", 0) < udc_after.get("documented", 0):
            added = udc_after.get("documented", 0) - udc_before.get("documented", 0)
            improvements.append(f"Added {added} UDC endpoint(s)")

        # Check sections
        sections_before = set(before.get("sections", {}).get("found", []))
        sections_after = set(after.get("sections", {}).get("found", []))
        new_sections = sections_after - sections_before

        if new_sections:
            improvements.append(f"Added {len(new_sections)} new section(s): {', '.join(list(new_sections)[:3])}")

        # Check errors resolved
        errors_before = len(before.get("errors", []))
        errors_after = len(after.get("errors", []))

        if errors_before > errors_after:
            fixed = errors_before - errors_after
            improvements.append(f"Fixed {fixed} critical error(s)")

        # Check warnings resolved
        warnings_before = len(before.get("warnings", []))
        warnings_after = len(after.get("warnings", []))

        if warnings_before > warnings_after:
            fixed = warnings_before - warnings_after
            improvements.append(f"Resolved {fixed} warning(s)")

        # Check score improvements
        score_before = before.get("score", {})
        score_after = after.get("score", {})

        for metric in ["completeness", "clarity", "udc_compliance", "build_readiness"]:
            before_val = score_before.get(metric, 0)
            after_val = score_after.get(metric, 0)
            if after_val > before_val + 10:  # Significant improvement
                improvements.append(
                    f"Improved {metric}: {before_val} → {after_val}"
                )

        return improvements

    def _to_snapshot(self, verification: Dict) -> VerificationSnapshot:
        """Convert verification dict to snapshot model"""
        return VerificationSnapshot(
            score=verification.get("score", {}),
            errors=verification.get("errors", []),
            warnings=verification.get("warnings", []),
            recommendations=verification.get("recommendations", [])
        )
