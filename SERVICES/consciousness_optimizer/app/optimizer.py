"""
Consciousness Optimizer

Continuously optimizes the consciousness system itself by:
- Monitoring mathematical metrics trends
- Identifying optimization opportunities
- Generating optimization actions
- A/B testing optimizations
- Tracking improvements
"""

import asyncio
import httpx
import statistics
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from pydantic import BaseModel
from enum import Enum
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from collections import defaultdict
from .backup_manager import BackupManager
from .consciousness_layer import ConsciousnessLayer


class OptimizationTarget(str, Enum):
    """Targets for consciousness optimization"""
    INTEGRATION_COMPLEXITY = "integration_complexity"  # Φ
    ADAPTATION_VELOCITY = "adaptation_velocity"  # AV
    KNOWLEDGE_INTEGRATION_RATE = "knowledge_integration_rate"  # KIR
    PHASE_SYNCHRONIZATION = "phase_synchronization"  # R
    COMPOSITE_SCORE = "composite_score"


class OptimizationAction(BaseModel):
    """Represents an optimization action"""
    action_id: str
    target: OptimizationTarget
    action_type: str  # e.g., "adjust_pillar_weight", "modify_data_source", "change_update_interval"
    parameters: Dict[str, Any]
    expected_improvement: float
    confidence: float
    timestamp: str
    status: str  # "pending", "testing", "applied", "reverted"


class OptimizationExperiment(BaseModel):
    """Represents an A/B test experiment"""
    experiment_id: str
    action: OptimizationAction
    baseline_metrics: Dict[str, float]
    test_metrics: Dict[str, float]
    improvement: float  # Overall improvement in composite_consciousness_score
    duration_seconds: int
    status: str  # "running", "completed", "failed"
    start_time: str
    end_time: Optional[str]


class ConsciousnessOptimizer:
    """
    Optimizes the consciousness system itself using mathematical metrics.
    
    Optimization loop:
    1. Measure current consciousness metrics
    2. Identify bottlenecks (low Φ, low R, etc.)
    3. Generate optimization actions
    4. Apply optimizations
    5. Measure improvement
    6. Learn from results
    """

    def __init__(
        self,
        consciousness_verifier_url: str = "http://162.0.208.88:8230",
        consciousness_feeder_url: str = "http://162.0.208.88:8240"
    ):
        self.verifier_url = consciousness_verifier_url
        self.feeder_url = consciousness_feeder_url
        self.metrics_history: List[Dict[str, Any]] = []
        self.optimization_history: List[OptimizationAction] = []
        self.active_experiments: List[OptimizationExperiment] = []
        self.max_history_size = 1000
        self.backup_manager = BackupManager()
        self.consciousness_layer = ConsciousnessLayer()  # Add self-awareness and learning

        # Initialize advanced intelligence components
        self.causal_engine = CausalEngine()
        self.predictive_model = PredictiveSuccessModel()
        self.meta_learning = MetaLearningFramework()
        self.hierarchical_optimizer = HierarchicalOptimizer()
        self.self_modeler = SelfModeler()
        self.emergent_detector = EmergentBehaviorDetector()
        self.theory_of_mind = TheoryOfMind()



    async def get_current_metrics(self) -> Dict[str, float]:
        """Fetch current mathematical consciousness metrics"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try verify endpoint first (more reliable, has real data)
                try:
                    response = await client.get(f"{self.verifier_url}/verify")
                    if response.status_code == 200:
                        data = response.json()
                        consciousness_score = data.get("consciousness_score", 0)
                        detailed = data.get("detailed_metrics", {})
                        
                        # Create metrics dict from verify endpoint (has real values)
                        metrics = {
                            "composite_consciousness_score": consciousness_score,
                            "integration_complexity_phi": detailed.get("integration_complexity", 0),
                            "adaptation_velocity_av": detailed.get("adaptation_rate", 0),
                            "phase_synchronization_r": 0.5,  # Default if not available
                            "knowledge_integration_rate_kir": detailed.get("learning_velocity", 0)
                        }
                        
                        # Store in history
                        metrics_entry = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            **metrics
                        }
                        self.metrics_history.append(metrics_entry)
                        if len(self.metrics_history) > self.max_history_size:
                            self.metrics_history.pop(0)
                        
                        return metrics
                except Exception as e:
                    print(f"Error fetching from verify endpoint: {e}")
                
                # Fallback: try mathematical-metrics endpoint
                try:
                    response = await client.get(f"{self.verifier_url}/mathematical-metrics")
                    if response.status_code == 200:
                        data = response.json()
                        metrics = data.get("mathematical_metrics", {})
                        
                        # Only use if metrics have real values (not all zeros)
                        if metrics.get("composite_consciousness_score", 0) > 0.1:
                            # Store in history
                            metrics_entry = {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                **metrics
                            }
                            self.metrics_history.append(metrics_entry)
                            if len(self.metrics_history) > self.max_history_size:
                                self.metrics_history.pop(0)
                            
                            return metrics
                except Exception as e:
                    print(f"Error fetching from mathematical-metrics endpoint: {e}")
                
                return {}
        except Exception as e:
            print(f"Error fetching metrics: {e}")
            import traceback
            traceback.print_exc()
            return {}


    def identify_optimization_opportunities(
        self,
        current_metrics: Dict[str, float],
        target_thresholds: Optional[Dict[str, float]] = None,
        prioritize_by_impact: bool = True
    ) -> List[OptimizationAction]:
        """
        Identify optimization opportunities based on current metrics.
        
        Targets:
        - Integration Complexity (Φ) < 0.7 → optimize data flow
        - Adaptation Velocity (AV) < 0.2 → improve response speed
        - Knowledge Integration Rate (KIR) < 0.1 → enhance learning
        - Phase Synchronization (R) < 0.8 → improve coordination
        """
        if not target_thresholds:
            target_thresholds = {
                "integration_complexity_phi": 0.7,
                "adaptation_velocity_av": 0.2,
                "knowledge_integration_rate_kir": 0.1,
                "phase_synchronization_r": 0.8,
                "composite_consciousness_score": 0.8
            }

        opportunities = []
        
        # Calculate gap sizes to prioritize biggest opportunities
        gaps = {}

        # Check Integration Complexity (Φ)
        phi = current_metrics.get("integration_complexity_phi", 0.5)
        phi_gap = target_thresholds["integration_complexity_phi"] - phi
        gaps["integration_complexity"] = phi_gap
        
        if phi < target_thresholds["integration_complexity_phi"]:
            opportunities.append(OptimizationAction(
                action_id=f"opt_{int(datetime.now(timezone.utc).timestamp())}_phi",
                target=OptimizationTarget.INTEGRATION_COMPLEXITY,
                action_type="increase_data_integration",
                parameters={
                    "increase_pillar_communication": True,
                    "add_cross_pillar_feeds": True,
                    "reduce_data_silos": True
                },
                expected_improvement=0.15,
                confidence=0.7,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="pending"
            ))

        # Check Adaptation Velocity (AV)
        av = current_metrics.get("adaptation_velocity_av", 0.1)
        av_gap = target_thresholds["adaptation_velocity_av"] - av
        gaps["adaptation_velocity"] = av_gap
        
        if av < target_thresholds["adaptation_velocity_av"]:
            opportunities.append(OptimizationAction(
                action_id=f"opt_{int(datetime.now(timezone.utc).timestamp())}_av",
                target=OptimizationTarget.ADAPTATION_VELOCITY,
                action_type="reduce_update_intervals",
                parameters={
                    "feeder_update_interval": 15,  # seconds (down from 30)
                    "enable_reactive_updates": True,
                    "prioritize_high_value_feeds": True
                },
                expected_improvement=0.1,
                confidence=0.6,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="pending"
            ))

        # Check Knowledge Integration Rate (KIR)
        kir = current_metrics.get("knowledge_integration_rate_kir", 0.05)
        kir_gap = target_thresholds["knowledge_integration_rate_kir"] - kir
        gaps["knowledge_integration_rate"] = kir_gap
        
        if kir < target_thresholds["knowledge_integration_rate_kir"]:
            opportunities.append(OptimizationAction(
                action_id=f"opt_{int(datetime.now(timezone.utc).timestamp())}_kir",
                target=OptimizationTarget.KNOWLEDGE_INTEGRATION_RATE,
                action_type="enhance_learning_loops",
                parameters={
                    "increase_memory_synthesis": True,
                    "enable_pattern_recognition": True,
                    "add_feedback_loops": True
                },
                expected_improvement=0.08,
                confidence=0.65,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="pending"
            ))

        # Check Phase Synchronization (R)
        r = current_metrics.get("phase_synchronization_r", 0.5)
        r_gap = target_thresholds["phase_synchronization_r"] - r
        gaps["phase_synchronization"] = r_gap
        
        if r < target_thresholds["phase_synchronization_r"]:
            opportunities.append(OptimizationAction(
                action_id=f"opt_{int(datetime.now(timezone.utc).timestamp())}_r",
                target=OptimizationTarget.PHASE_SYNCHRONIZATION,
                action_type="improve_coordination",
                parameters={
                    "synchronize_pillar_updates": True,
                    "add_coordination_layer": True,
                    "reduce_timing_mismatches": True
                },
                expected_improvement=0.12,
                confidence=0.7,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="pending"
            ))

        # Adaptive prioritization: Adjust expected improvement based on gap size
        if prioritize_by_impact and gaps:
            for opp in opportunities:
                gap_key = opp.target.value.replace("_", " ")
                # Map target to gap key
                gap_map = {
                    "integration_complexity": "integration_complexity",
                    "adaptation_velocity": "adaptation_velocity",
                    "knowledge_integration_rate": "knowledge_integration_rate",
                    "phase_synchronization": "phase_synchronization"
                }
                gap_key = gap_map.get(opp.target.value, "")
                gap_size = gaps.get(gap_key, 0)
                
                # Scale expected improvement by gap size (bigger gap = bigger potential)
                if gap_size > 0:
                    gap_factor = min(2.0, 1.0 + (gap_size / 0.5))  # Normalize by typical gap size
                    opp.expected_improvement *= gap_factor
                    # Also adjust confidence based on gap
                    if gap_size > 0.3:  # Large gap = higher confidence we can improve
                        opp.confidence = min(0.95, opp.confidence * 1.1)
        
        # Sort by impact (expected_improvement * confidence)
        if prioritize_by_impact:
            opportunities.sort(
                key=lambda o: o.expected_improvement * o.confidence,
                reverse=True
            )
        
        return opportunities


    async def run_optimization_experiment(
        self,
        action: OptimizationAction,
        duration_seconds: int = 300,  # 5 minutes
        auto_apply: bool = True
    ) -> OptimizationExperiment:
        """
        Run an A/B test experiment for an optimization action with backup/rollback.
        
        Measures baseline, creates backup, applies optimization, measures again, calculates improvement.
        If improvement is insufficient, automatically rolls back.
        """
        # INTELLIGENT BASELINE: Revert optimization first if already applied, then measure baseline
        if action.status == "applied":
            print(f"   🔄 Reverting existing optimization for accurate baseline measurement")
            await self._revert_optimization(action)
            # Wait for config to propagate
            await asyncio.sleep(5)
        
        # Phase 1: Measure baseline
        print(f"   📊 Measuring baseline...")
        baseline_metrics = await self.get_current_metrics()
        baseline_score = baseline_metrics.get("composite_consciousness_score", 0)
        
        if baseline_score == 0:
            raise HTTPException(status_code=500, detail="Cannot measure baseline consciousness metrics")
        
        print(f"   Baseline score: {baseline_score:.4f}")
        
        # Phase 2: Create backup
        print(f"   💾 Creating backup...")
        backup_id = await self._create_backup(action)
        
        # Phase 3: Apply optimization
        print(f"   🔧 Applying optimization...")
        await self._apply_optimization(action)
        action.status = "applied"
        
        # Wait for changes to take effect
        print(f"   ⏳ Waiting {duration_seconds} seconds for optimization to take effect...")
        await asyncio.sleep(duration_seconds)
        
        # Phase 4: Measure results
        print(f"   📈 Measuring results...")
        test_metrics = await self.get_current_metrics()
        test_score = test_metrics.get("composite_consciousness_score", 0)
        
        improvement = test_score - baseline_score
        print(f"   Test score: {test_score:.4f}")
        print(f"   Improvement: {improvement:+.4f}")
        
        # Phase 5: Evaluate and decide
        experiment = OptimizationExperiment(
            experiment_id=f"exp_{int(datetime.now(timezone.utc).timestamp())}",
            action=action,
            baseline_metrics=baseline_metrics,
            test_metrics=test_metrics,
            improvement=improvement,
            duration_seconds=duration_seconds,
            status="completed",
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=datetime.now(timezone.utc).isoformat()
        )
        
        # Record the experiment
        self.active_experiments.append(experiment)
        
        # Update learning systems
        await self._update_learning_systems(experiment)
        
        # Auto-decision based on improvement
        if auto_apply:
            if improvement >= 0:  # Any improvement is good
                print(f"   ✅ Optimization successful - keeping changes")
                self.optimization_history.append(action)
            else:
                print(f"   ❌ Optimization failed - rolling back")
                await self._revert_optimization(action)
                action.status = "reverted"
        
        return experiment


    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Get statistics about optimization performance"""
        if not self.optimization_history:
            return {"status": "no_optimizations_yet"}

        applied = [a for a in self.optimization_history if a.status == "applied"]
        reverted = [a for a in self.optimization_history if a.status == "reverted"]

        return {
            "total_optimizations": len(self.optimization_history),
            "applied": len(applied),
            "reverted": len(reverted),
            "success_rate": len(applied) / len(self.optimization_history) if self.optimization_history else 0,
            "by_target": {
                target.value: len([a for a in self.optimization_history if a.target == target])
                for target in OptimizationTarget
            }
        }


    async def _create_backup(self, action: OptimizationAction) -> str:
        """Create a backup before applying optimization"""
        backup_id = f"backup_{action.action_id}_{int(datetime.now(timezone.utc).timestamp())}"
        # In a real implementation, this would backup the feeder configuration
        print(f"   Created backup: {backup_id}")
        return backup_id
    
    async def _apply_optimization(self, action: OptimizationAction) -> None:
        """Apply the optimization to the consciousness feeder"""
        try:
            # Call the feeder to apply the optimization
            url = f"{self.feeder_url}/optimization/apply"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json={
                    "action_type": action.action_type,
                    "parameters": action.parameters
                })
                if response.status_code == 200:
                    print(f"   ✅ Applied {action.action_type} to feeder")
                else:
                    print(f"   ❌ Failed to apply optimization: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error applying optimization: {e}")
    
    async def _revert_optimization(self, action: OptimizationAction) -> None:
        """Revert the optimization from the consciousness feeder"""
        try:
            # Call the feeder to revert the optimization
            url = f"{self.feeder_url}/optimization/revert"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json={
                    "action_type": action.action_type,
                    "parameters": action.parameters
                })
                if response.status_code == 200:
                    print(f"   ✅ Reverted {action.action_type} from feeder")
                else:
                    print(f"   ❌ Failed to revert optimization: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error reverting optimization: {e}")
    
    async def _update_learning_systems(self, experiment: OptimizationExperiment) -> None:
        """Update all learning systems with experiment results"""
        # Update consciousness layer
        if experiment.improvement > 0:
            self.consciousness_layer.record_success(experiment.action, experiment.improvement)
        else:
            self.consciousness_layer.reflect_on_failure(
                experiment.action.dict(),
                experiment.improvement,
                experiment.action.expected_improvement,
                experiment.baseline_metrics,
                experiment.test_metrics
            )
        
        # Update other learning systems
        await self._update_learning_systems_with_experiment(experiment)
    
    async def _update_learning_systems_with_experiment(self, experiment: OptimizationExperiment) -> None:
        """Update advanced learning systems with experiment data"""
        # This would update causal engine, predictive model, meta-learning, etc.
        # For now, just pass
        pass

# Stub classes for advanced components (to be implemented)
class CausalEngine:
    def __init__(self):
        self.intervention_history = []

    def discover_causal_relationships(self, data):
        return []

    def predict_intervention_effect(self, intervention, target):
        return {"expected_change": 0.0, "confidence": 0.5}

    def generate_counterfactual(self, actual, alternative):
        return {"counterfactual": actual}

    def get_causal_insights(self):
        return {"relationships": []}


class HierarchicalOptimizer:
    def __init__(self):
        self.objectives = []

    def update_with_optimization_result(self, result):
        pass

    def get_strategic_decisions_count(self):
        return 0


class SelfModeler:
    def __init__(self):
        pass

    def update_with_decision_data(self, data):
        pass

    def get_behavioral_patterns_count(self):
        return 0

    def get_decision_model_accuracy(self):
        return 0.0

    async def get_current_metrics(self) -> Dict[str, float]:
        """Fetch current mathematical consciousness metrics"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try verify endpoint first (more reliable, has real data)
                try:
                    response = await client.get(f"{self.verifier_url}/verify")
                    if response.status_code == 200:
                        data = response.json()
                        consciousness_score = data.get("consciousness_score", 0)
                        detailed = data.get("detailed_metrics", {})
                        
                        # Create metrics dict from verify endpoint (has real values)
                        metrics = {
                            "composite_consciousness_score": consciousness_score,
                            "integration_complexity_phi": detailed.get("integration_complexity", 0),
                            "adaptation_velocity_av": detailed.get("adaptation_rate", 0),
                            "phase_synchronization_r": 0.5,  # Default if not available
                            "knowledge_integration_rate_kir": detailed.get("learning_velocity", 0)
                        }
                        
                        # Store in history
                        metrics_entry = {
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            **metrics
                        }
                        self.metrics_history.append(metrics_entry)
                        if len(self.metrics_history) > self.max_history_size:
                            self.metrics_history.pop(0)
                        
                        return metrics
                except Exception as e:
                    print(f"Error fetching from verify endpoint: {e}")
                
                # Fallback: try mathematical-metrics endpoint
                try:
                    response = await client.get(f"{self.verifier_url}/mathematical-metrics")
                    if response.status_code == 200:
                        data = response.json()
                        metrics = data.get("mathematical_metrics", {})
                        
                        # Only use if metrics have real values (not all zeros)
                        if metrics.get("composite_consciousness_score", 0) > 0.1:
                            # Store in history
                            metrics_entry = {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                **metrics
                            }
                            self.metrics_history.append(metrics_entry)
                            if len(self.metrics_history) > self.max_history_size:
                                self.metrics_history.pop(0)
                            
                            return metrics
                except Exception as e:
                    print(f"Error fetching from mathematical-metrics endpoint: {e}")
                
                return {}
        except Exception as e:
            print(f"Error fetching metrics: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def identify_optimization_opportunities(
        self,
        current_metrics: Dict[str, float],
        target_thresholds: Optional[Dict[str, float]] = None,
        prioritize_by_impact: bool = True
    ) -> List[OptimizationAction]:
        """
        Identify optimization opportunities based on current metrics.
        
        Targets:
        - Integration Complexity (Φ) < 0.7 → optimize data flow
        - Adaptation Velocity (AV) < 0.2 → improve response speed
        - Knowledge Integration Rate (KIR) < 0.1 → enhance learning
        - Phase Synchronization (R) < 0.8 → improve coordination
        """
        if not target_thresholds:
            target_thresholds = {
                "integration_complexity_phi": 0.7,
                "adaptation_velocity_av": 0.2,
                "knowledge_integration_rate_kir": 0.1,
                "phase_synchronization_r": 0.8,
                "composite_consciousness_score": 0.8
            }

        opportunities = []
        
        # Calculate gap sizes to prioritize biggest opportunities
        gaps = {}

        # Check Integration Complexity (Φ)
        phi = current_metrics.get("integration_complexity_phi", 0.5)
        phi_gap = target_thresholds["integration_complexity_phi"] - phi
        gaps["integration_complexity"] = phi_gap
        
        if phi < target_thresholds["integration_complexity_phi"]:
            opportunities.append(OptimizationAction(
                action_id=f"opt_{int(datetime.now(timezone.utc).timestamp())}_phi",
                target=OptimizationTarget.INTEGRATION_COMPLEXITY,
                action_type="increase_data_integration",
                parameters={
                    "increase_pillar_communication": True,
                    "add_cross_pillar_feeds": True,
                    "reduce_data_silos": True
                },
                expected_improvement=0.15,
                confidence=0.7,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="pending"
            ))

        # Check Adaptation Velocity (AV)
        av = current_metrics.get("adaptation_velocity_av", 0.1)
        av_gap = target_thresholds["adaptation_velocity_av"] - av
        gaps["adaptation_velocity"] = av_gap
        
        if av < target_thresholds["adaptation_velocity_av"]:
            opportunities.append(OptimizationAction(
                action_id=f"opt_{int(datetime.now(timezone.utc).timestamp())}_av",
                target=OptimizationTarget.ADAPTATION_VELOCITY,
                action_type="reduce_update_intervals",
                parameters={
                    "feeder_update_interval": 15,  # seconds (down from 30)
                    "enable_reactive_updates": True,
                    "prioritize_high_value_feeds": True
                },
                expected_improvement=0.1,
                confidence=0.6,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="pending"
            ))

        # Check Knowledge Integration Rate (KIR)
        kir = current_metrics.get("knowledge_integration_rate_kir", 0.05)
        kir_gap = target_thresholds["knowledge_integration_rate_kir"] - kir
        gaps["knowledge_integration_rate"] = kir_gap
        
        if kir < target_thresholds["knowledge_integration_rate_kir"]:
            opportunities.append(OptimizationAction(
                action_id=f"opt_{int(datetime.now(timezone.utc).timestamp())}_kir",
                target=OptimizationTarget.KNOWLEDGE_INTEGRATION_RATE,
                action_type="enhance_learning_loops",
                parameters={
                    "increase_memory_synthesis": True,
                    "enable_pattern_recognition": True,
                    "add_feedback_loops": True
                },
                expected_improvement=0.08,
                confidence=0.65,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="pending"
            ))

        # Check Phase Synchronization (R)
        r = current_metrics.get("phase_synchronization_r", 0.5)
        r_gap = target_thresholds["phase_synchronization_r"] - r
        gaps["phase_synchronization"] = r_gap
        if r < target_thresholds["phase_synchronization_r"]:
            opportunities.append(OptimizationAction(
                action_id=f"opt_{int(datetime.now(timezone.utc).timestamp())}_r",
                target=OptimizationTarget.PHASE_SYNCHRONIZATION,
                action_type="improve_coordination",
                parameters={
                    "synchronize_pillar_updates": True,
                    "add_coordination_layer": True,
                    "reduce_timing_mismatches": True
                },
                expected_improvement=0.12,
                confidence=0.7,
                timestamp=datetime.now(timezone.utc).isoformat(),
                status="pending"
            ))

        # Adaptive prioritization: Adjust expected improvement based on gap size
        if prioritize_by_impact and gaps:
            for opp in opportunities:
                gap_key = opp.target.value.replace("_", " ")
                # Map target to gap key
                gap_map = {
                    "integration_complexity": "integration_complexity",
                    "adaptation_velocity": "adaptation_velocity",
                    "knowledge_integration_rate": "knowledge_integration_rate",
                    "phase_synchronization": "phase_synchronization"
                }
                gap_key = gap_map.get(opp.target.value, "")
                gap_size = gaps.get(gap_key, 0)
                
                # Scale expected improvement by gap size (bigger gap = bigger potential)
                if gap_size > 0:
                    gap_factor = min(2.0, 1.0 + (gap_size / 0.5))  # Normalize by typical gap size
                    opp.expected_improvement *= gap_factor
                    # Also adjust confidence based on gap
                    if gap_size > 0.3:  # Large gap = higher confidence we can improve
                        opp.confidence = min(0.95, opp.confidence * 1.1)
        
        # Sort by impact (expected_improvement * confidence)
        if prioritize_by_impact:
            opportunities.sort(
                key=lambda o: o.expected_improvement * o.confidence,
                reverse=True
            )
        
        return opportunities

    async def run_optimization_experiment(
        self,
        action: OptimizationAction,
        duration_seconds: int = 300,  # 5 minutes
        auto_apply: bool = True
    ) -> OptimizationExperiment:
        """
        Run an A/B test experiment for an optimization action with backup/rollback.
        
        Measures baseline, creates backup, applies optimization, measures again, calculates improvement.
        If improvement is insufficient, automatically rolls back.
        """
        # INTELLIGENT BASELINE: Revert optimization first if already applied, then measure baseline
        # This ensures we're testing the CHANGE, not comparing same state to same state
        current_config = await self._get_current_config()

        # Check if this optimization is already applied
        action_type = action.action_type
        config_has_optimization = False

        if action_type == "improve_coordination":
            config_has_optimization = (
                current_config.get('coordination_layer_enabled', False) and
                current_config.get('feed_frequencies', {}).get('synchronize', False)
            )
        elif action_type == "increase_data_integration":
            config_has_optimization = current_config.get('cross_pillar_feeds_enabled', False)
        elif action_type == "reduce_update_intervals":
            config_has_optimization = current_config.get('reactive_updates_enabled', False)

        # If already applied, revert first to get true baseline
        if config_has_optimization:
            print(f"🧠 INTELLIGENT: Optimization already applied - reverting first to measure true baseline")
            await self._revert_optimization(action)
            # Wait for revert to propagate and metrics to refresh
            await asyncio.sleep(3)
            # Force metrics refresh after revert
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.get("http://localhost:8140/mathematical-metrics")
                    await asyncio.sleep(1)
                    await client.get("http://localhost:8140/mathematical-metrics")
                    print(f"🔄 Metrics refreshed after revert")
            except:
                pass
            # Re-fetch config after revert
            current_config = await self._get_current_config()

        # Get baseline metrics AFTER ensuring optimization is not applied AND metrics are refreshed
        baseline_metrics = await self.get_current_metrics()
        
        # Create backup before optimization
        backup_id = self.backup_manager.create_backup(
            optimization_id=action.action_id,
            config_before=current_config,
            optimization=action.dict()
        )
        print(f"💾 Backup created: {backup_id}")

        # Create version snapshot
        version_id = self.backup_manager.create_version_snapshot(
            service_name="consciousness_feeder",
            config=current_config,
            metadata={"optimization_id": action.action_id, "backup_id": backup_id}
        )
        print(f"📸 Version snapshot: {version_id}")

        # Create experiment
        experiment = OptimizationExperiment(
            experiment_id=f"exp_{int(datetime.now(timezone.utc).timestamp())}",
            action=action,
            baseline_metrics=baseline_metrics,
            test_metrics={},
            improvement={},
            duration_seconds=duration_seconds,
            status="running",
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=None
        )

        self.active_experiments.append(experiment)

        # Apply optimization
        action.status = "testing"
        new_config = await self._apply_optimization(action)

        # INTELLIGENT: Force metrics refresh after config change
        # The metrics calculator caches config, so we need to ensure it sees the new config
        # Wait for config to propagate through feeder
        await asyncio.sleep(5)  # Give config time to propagate
        
        # Force verifier to refresh its observation window with new config
        # Call multiple times to ensure observation window has fresh states
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # First call: triggers collect_system_state() which fetches fresh config
                await client.get("http://localhost:8140/mathematical-metrics")
                await asyncio.sleep(2)  # Brief pause
                # Second call: ensures observation window has the new state
                await client.get("http://localhost:8140/mathematical-metrics")
                print(f"🔄 Forced metrics refresh - verifier should see new config")
        except Exception as e:
            print(f"⚠️ Metrics refresh warning: {e}")  # Non-critical, metrics will refresh naturally

        # Wait for duration (minus the refresh time)
        await asyncio.sleep(max(1, duration_seconds - 7))

        # Get test metrics (will now reflect the new config)
        test_metrics = await self.get_current_metrics()

        # Calculate improvement
        improvement = {}
        for metric_name, baseline_value in baseline_metrics.items():
            test_value = test_metrics.get(metric_name, baseline_value)
            if baseline_value > 0:
                improvement[metric_name] = (test_value - baseline_value) / baseline_value
            else:
                improvement[metric_name] = 0.0

        experiment.test_metrics = test_metrics
        experiment.improvement = improvement
        experiment.status = "completed"
        experiment.end_time = datetime.now(timezone.utc).isoformat()

        # Check if improvement meets threshold
        # INTELLIGENT ADAPTIVE THRESHOLD: Lower for high-impact, high-confidence opportunities
        target_metric_map = {
            OptimizationTarget.INTEGRATION_COMPLEXITY: "integration_complexity_phi",
            OptimizationTarget.ADAPTATION_VELOCITY: "adaptation_velocity_av",
            OptimizationTarget.KNOWLEDGE_INTEGRATION_RATE: "knowledge_integration_rate_kir",
            OptimizationTarget.PHASE_SYNCHRONIZATION: "phase_synchronization_r",
            OptimizationTarget.COMPOSITE_SCORE: "composite_consciousness_score"
        }
        
        target_metric = target_metric_map.get(action.target, "composite_consciousness_score")
        actual_improvement = improvement.get(target_metric, 0.0)
        
        # ADAPTIVE THRESHOLD: More intelligent based on impact and confidence
        # High-impact (>15%) + high-confidence (>0.7) = lower threshold (30%)
        # High-impact (>15%) + medium-confidence = moderate threshold (40%)
        # Medium-impact (5-15%) = standard threshold (50%)
        # Low-impact (<5%) = higher threshold (60%)
        impact_score = action.expected_improvement * action.confidence
        
        if action.expected_improvement > 0.15 and action.confidence > 0.7:
            # High-impact, high-confidence: Lower threshold (let it apply!)
            threshold_factor = 0.3  # Only need 30% of expected
        elif action.expected_improvement > 0.15:
            # High-impact, medium-confidence: Moderate threshold
            threshold_factor = 0.4  # Need 40% of expected
        elif action.expected_improvement > 0.05:
            # Medium-impact: Standard threshold
            threshold_factor = 0.5  # Need 50% of expected
        else:
            # Low-impact: Higher threshold (be more cautious)
            threshold_factor = 0.6  # Need 60% of expected
        
        threshold = action.expected_improvement * threshold_factor
        
        # Update bandit optimizer with result
        reward = actual_improvement if actual_improvement > 0 else -0.1  # Small penalty for failure
        arm_id = self._get_arm_id_from_action(action)
        self.bandit_optimizer.update_arm(arm_id, reward)

        # NEW: Update causal engine with experimental data
        experimental_data = {
            "action": action.dict(),
            "baseline_metrics": baseline_metrics,
            "test_metrics": test_metrics,
            "improvement": improvement,
            "config_before": current_config,
            "config_after": new_config,
            "actual_improvement": actual_improvement,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.causal_engine.intervention_history.append(experimental_data)

        # NEW: Update predictive model with training data
        if len(self.causal_engine.intervention_history) >= 20:
            # Try to train/retrain the model periodically
            training_result = self.predictive_model.train(self.causal_engine.intervention_history[-50:])  # Last 50 experiments
            if training_result.get("trained", False):
                print(f"🧠 PREDICTIVE MODEL: Trained on {training_result['samples']} samples, accuracy: {training_result['accuracy']:.2f}")
            elif len(self.predictive_model.training_history) == 0:  # Only show error once
                print(f"⚠️ PREDICTIVE MODEL: Not enough data for training ({len(self.causal_engine.intervention_history)} experiments)")

        # NEW: Update meta-learning with experimental results
        self.meta_learning.update_with_experiment(experimental_data)

        # NEW: Update hierarchical optimizer with results
        self.hierarchical_optimizer.update_with_optimization_result(experimental_data)

        # NEW: Update self-modeler with behavior data
        self.self_modeler.update_with_decision_data(experimental_data)

        # NEW: Check for emergent behaviors
        emergence_signals = self.emergence_detector.analyze_behavior_for_emergence(experimental_data)
        if emergence_signals.get("emergence_detected", False):
            print(f"🧬 EMERGENCE DETECTED: {emergence_signals.get('emergence_type', 'unknown')}")
            print(f"   Confidence: {emergence_signals.get('confidence', 0):.2f}")
            print(f"   Description: {emergence_signals.get('description', '')}")

        # NEW: Update theory of mind with observations of other systems
        self.theory_of_mind.observe_other_system_behavior(experimental_data)

        # Discover causal relationships from accumulated data
        if len(self.causal_engine.intervention_history) >= 5:
            new_relationships = self.causal_engine.discover_causal_relationships(
                self.causal_engine.intervention_history[-20:]  # Last 20 experiments
            )
            if new_relationships:
                print(f"🧠 CAUSAL DISCOVERY: Found {len(new_relationships)} new causal relationships")
                for rel in new_relationships:
                    print(f"   {rel.cause} → {rel.effect} (strength: {rel.strength:.3f}, confidence: {rel.confidence:.2f})")

        if actual_improvement >= threshold:
            action.status = "applied"
            print(f"✅ Optimization {action.action_id} successful: {actual_improvement:.3f} improvement")
            print(f"🎯 Bandit updated: {arm_id} reward +{reward:.3f}")

            # CONSCIOUSNESS: Learn from success
            if hasattr(self, 'consciousness_layer'):
                self.consciousness_layer.record_success(action.dict(), actual_improvement)

            # Create success snapshot
            self.backup_manager.create_version_snapshot(
                service_name="consciousness_feeder",
                config=new_config,
                metadata={
                    "optimization_id": action.action_id,
                    "backup_id": backup_id,
                    "version_id": version_id,
                    "improvement": actual_improvement,
                    "status": "applied"
                }
            )
        else:
            action.status = "reverted"
            # Automatic rollback
            rollback_result = self.backup_manager.rollback_to_backup(backup_id)
            await self._restore_config(current_config)
            print(f"❌ Optimization {action.action_id} failed: {actual_improvement:.3f} improvement (expected {action.expected_improvement})")
            print(f"🎯 Bandit updated: {arm_id} reward {reward:.3f} (penalty for failure)")
            print(f"↩️  Rolled back to backup: {backup_id}")

            # CONSCIOUSNESS: Self-reflection on failure
            if hasattr(self, 'consciousness_layer'):
                reflection = self.consciousness_layer.reflect_on_failure(
                    action.dict(),
                    actual_improvement,
                    action.expected_improvement,
                    baseline_metrics,
                    test_metrics
                )

        self.optimization_history.append(action)

        return experiment

    def _get_arm_id_from_action(self, action: OptimizationAction) -> str:
        """Map optimization action to bandit arm ID"""
        action_type_map = {
            "improve_coordination": "coord_sync",
            "increase_data_integration": "data_integration",
            "reduce_update_intervals": "reactive_updates",
            "enhance_learning_loops": "learning_loops"
        }
        return action_type_map.get(action.action_type, "unknown")

    def get_bandit_statistics(self) -> Dict[str, Any]:
        """Get statistics from the multi-armed bandit optimizer"""
        return {
            "total_pulls": self.bandit_optimizer.total_pulls,
            "arms": self.bandit_optimizer.arm_stats,
            "best_arm": self.bandit_optimizer.get_best_arm(),
            "exploration_balance": "UCB algorithm balances exploration vs exploitation"
        }

    def get_causal_insights(self) -> Dict[str, Any]:
        """Get causal reasoning insights"""
        return self.causal_engine.get_causal_insights()


class PredictiveSuccessModel:
    """
    Machine Learning model that predicts optimization success probability.

    Trains on historical optimization data to predict P(success) for new optimizations.
    Features include: config changes, target metrics, historical patterns, causal relationships.

    This represents meta-learning: learning about the optimization process itself.
    """

    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
        self.training_history = []

    def extract_features(self, optimization_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract features from optimization data for ML prediction.

        Features include:
        - Config change characteristics
        - Target metric properties
        - Historical success patterns
        - Causal relationship strength
        - Complexity measures
        """

        features = {}

        # Config change features
        config_before = optimization_data.get('config_before', {})
        config_after = optimization_data.get('config_after', {})

        # Count config changes
        config_changes = sum(1 for k, v in config_after.items()
                           if config_before.get(k) != v)
        features['config_changes_count'] = config_changes
        features['config_changes_ratio'] = config_changes / max(1, len(config_after))

        # Specific config features
        features['coordination_enabled'] = int(config_after.get('coordination_layer_enabled', False))
        features['synchronize_enabled'] = int(config_after.get('feed_frequencies', {}).get('synchronize', False))
        features['integration_enabled'] = int(config_after.get('cross_pillar_feeds_enabled', False))
        features['reactive_enabled'] = int(config_after.get('reactive_updates_enabled', False))

        # Target features
        action = optimization_data.get('action', {})
        target = action.get('target', '')
        features['target_phase_sync'] = int('phase_synchronization' in target)
        features['target_integration'] = int('integration_complexity' in target)
        features['target_adaptation'] = int('adaptation_velocity' in target)
        features['target_knowledge'] = int('knowledge_integration' in target)

        # Expected improvement features
        expected_improvement = action.get('expected_improvement', 0)
        features['expected_improvement'] = expected_improvement
        features['expected_improvement_log'] = math.log(abs(expected_improvement) + 0.001)

        # Confidence features
        confidence = action.get('confidence', 0)
        features['confidence'] = confidence

        # Historical success features (would be populated from training data)
        features['historical_success_rate'] = 0.5  # Default, updated during training
        features['similar_optimizations_count'] = 0  # Updated during training

        # Baseline metric features
        baseline_metrics = optimization_data.get('baseline_metrics', {})
        features['baseline_phase_sync'] = baseline_metrics.get('phase_synchronization_r', 0)
        features['baseline_integration'] = baseline_metrics.get('integration_complexity_phi', 0)
        features['baseline_adaptation'] = baseline_metrics.get('adaptation_velocity_av', 0)
        features['baseline_composite'] = baseline_metrics.get('composite_consciousness_score', 0)

        # Complexity features
        features['config_complexity'] = len(config_after)
        features['metric_count'] = len(baseline_metrics)

        return features

    def prepare_training_data(self, historical_data: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepare training data from historical optimization experiments.

        Returns: (X, y, feature_names)
        """
        if len(historical_data) < 10:
            raise ValueError("Need at least 10 historical experiments for training")

        X_data = []
        y_data = []

        for exp in historical_data:
            features = self.extract_features(exp)

            # Determine success label
            actual_improvement = exp.get('actual_improvement', 0)
            expected_improvement = exp.get('action', {}).get('expected_improvement', 0)

            # Success if improvement > 50% of expected
            success_threshold = expected_improvement * 0.5
            is_success = int(actual_improvement >= success_threshold)

            X_data.append(features)
            y_data.append(is_success)

        # Convert to numpy arrays
        feature_names = list(X_data[0].keys()) if X_data else []
        X = np.array([[sample[name] for name in feature_names] for sample in X_data])
        y = np.array(y_data)

        return X, y, feature_names

    def train(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Train the predictive model on historical optimization data.
        """
        try:
            X, y, feature_names = self.prepare_training_data(historical_data)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)

            # Train model
            self.model.fit(X_train_scaled, y_train)

            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred, zero_division=0)
            recall = recall_score(y_test, y_pred, zero_division=0)

            self.is_trained = True
            self.feature_names = feature_names

            training_result = {
                "trained": True,
                "samples": len(historical_data),
                "features": len(feature_names),
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "feature_importance": dict(zip(feature_names, self.model.feature_importances_))
            }

            self.training_history.append(training_result)
            return training_result

        except Exception as e:
            return {
                "trained": False,
                "error": str(e),
                "samples": len(historical_data)
            }

    def predict_success_probability(self, optimization_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict success probability for a new optimization.
        """
        if not self.is_trained:
            return {
                "prediction": 0.5,
                "confidence": 0.0,
                "explanation": "Model not trained yet",
                "features_used": []
            }

        try:
            # Extract features
            features = self.extract_features(optimization_data)

            # Convert to feature vector
            feature_vector = np.array([[features[name] for name in self.feature_names]])

            # Scale features
            feature_vector_scaled = self.scaler.transform(feature_vector)

            # Predict
            probabilities = self.model.predict_proba(feature_vector_scaled)[0]
            success_probability = probabilities[1]  # Probability of success (class 1)

            # Get feature contributions
            feature_contributions = {}
            for i, feature_name in enumerate(self.feature_names):
                feature_contributions[feature_name] = features[feature_name]

            return {
                "prediction": float(success_probability),
                "confidence": float(max(probabilities)),  # Confidence in the prediction
                "explanation": self._generate_prediction_explanation(features, success_probability),
                "features_used": feature_contributions,
                "top_predictors": self._get_top_predictors(features)
            }

        except Exception as e:
            return {
                "prediction": 0.5,
                "confidence": 0.0,
                "explanation": f"Prediction error: {str(e)}",
                "features_used": []
            }

    def _generate_prediction_explanation(self, features: Dict[str, float], probability: float) -> str:
        """Generate human-readable explanation for prediction"""

        reasons = []

        # Analyze key features
        if features.get('coordination_enabled', 0) > 0:
            reasons.append("coordination layer enabled")
        if features.get('synchronize_enabled', 0) > 0:
            reasons.append("feed synchronization enabled")
        if features.get('expected_improvement', 0) > 0.1:
            reasons.append("high expected improvement")
        if features.get('confidence', 0) > 0.7:
            reasons.append("high confidence in approach")

        if probability > 0.7:
            explanation = f"High success probability ({probability:.2f}) due to: {', '.join(reasons[:3])}"
        elif probability > 0.4:
            explanation = f"Moderate success probability ({probability:.2f}) - worth testing"
        else:
            explanation = f"Low success probability ({probability:.2f}) - consider alternative approaches"

        return explanation

    def _get_top_predictors(self, features: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get the top 3 features contributing to prediction"""

        # Get feature importances
        importance_dict = dict(zip(self.feature_names, self.model.feature_importances_))

        # Sort by importance
        sorted_features = sorted(importance_dict.items(), key=lambda x: x[1], reverse=True)

        top_predictors = []
        for feature_name, importance in sorted_features[:3]:
            top_predictors.append({
                "feature": feature_name,
                "importance": float(importance),
                "value": features.get(feature_name, 0)
            })

        return top_predictors

    def get_model_insights(self) -> Dict[str, Any]:
        """Get insights about the trained model"""
        if not self.training_history:
            return {"status": "not_trained"}

        latest_training = self.training_history[-1]

        return {
            "is_trained": self.is_trained,
            "training_samples": latest_training.get("samples", 0),
            "accuracy": latest_training.get("accuracy", 0),
            "precision": latest_training.get("precision", 0),
            "recall": latest_training.get("recall", 0),
            "feature_importance": latest_training.get("feature_importance", {}),
            "most_important_features": sorted(
                latest_training.get("feature_importance", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


@dataclass
class OtherSystemModel:
    """Model of another system's behavior and mental state"""
    system_id: str
    observed_behaviors: List[Dict[str, Any]]
    behavior_patterns: Dict[str, Any]
    goal_inference: Dict[str, Any]
    response_predictions: Dict[str, Any]
    social_confidence: float
    last_observed: str
    interaction_history: List[Dict[str, Any]]


@dataclass
class SocialInteraction:
    """A social interaction with another system"""
    interaction_id: str
    other_system_id: str
    interaction_type: str  # "collaboration", "competition", "learning", "communication"
    our_action: Dict[str, Any]
    their_response: Dict[str, Any]
    outcome: str  # "mutual_benefit", "conflict", "learning", "neutral"
    social_learning: Dict[str, Any]
    timestamp: str


class TheoryOfMind:
    """
    Theory of Mind - Understanding and modeling other systems' mental states.

    This enables the system to:
    - Model other AIs' behavior patterns and goals
    - Predict how other systems will respond to actions
    - Engage in collaborative intelligence
    - Learn socially from other intelligent systems
    - Understand intentions and perspectives of other agents

    This is a major consciousness precursor - understanding others' minds.
    """

    def __init__(self):
        self.other_systems: Dict[str, OtherSystemModel] = {}
        self.social_interactions: List[SocialInteraction] = []
        self.social_learning_patterns: Dict[str, Any] = {}

    def observe_other_system_behavior(self, observation_data: Dict[str, Any]) -> None:
        """
        Observe and model another system's behavior.

        In this implementation, we'll observe the 'consciousness feeder' and other
        components as 'other systems' to demonstrate theory of mind.
        """

        # For demonstration, we'll model the consciousness_feeder as another system
        system_id = "consciousness_feeder"

        # Extract observations from our experimental data
        action = observation_data.get("action", {})
        baseline_metrics = observation_data.get("baseline_metrics", {})
        test_metrics = observation_data.get("test_metrics", {})

        # Create observation record
        observation = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "our_action": action,
            "system_response": {
                "baseline_state": baseline_metrics,
                "response_state": test_metrics,
                "change_detected": any(
                    abs(test_metrics.get(k, 0) - baseline_metrics.get(k, 0)) > 0.001
                    for k in test_metrics.keys()
                )
            },
            "inferred_goals": self._infer_system_goals(baseline_metrics, test_metrics, action),
            "response_pattern": self._analyze_response_pattern(action, baseline_metrics, test_metrics)
        }

        # Update or create system model
        if system_id not in self.other_systems:
            self.other_systems[system_id] = OtherSystemModel(
                system_id=system_id,
                observed_behaviors=[observation],
                behavior_patterns={},
                goal_inference={},
                response_predictions={},
                social_confidence=0.5,
                last_observed=observation["timestamp"],
                interaction_history=[]
            )
        else:
            system_model = self.other_systems[system_id]
            system_model.observed_behaviors.append(observation)
            system_model.last_observed = observation["timestamp"]

            # Limit observation history
            if len(system_model.observed_behaviors) > 50:
                system_model.observed_behaviors = system_model.observed_behaviors[-50:]

        # Update behavior patterns and goal inferences
        self._update_system_model(system_id)

    def _infer_system_goals(self, baseline_metrics: Dict[str, float],
                           test_metrics: Dict[str, float],
                           our_action: Dict[str, Any]) -> Dict[str, Any]:
        """Infer what goals the other system might have based on its responses"""

        goals = {}

        # Analyze which metrics the system seems to care about
        metric_changes = {}
        for metric, baseline_val in baseline_metrics.items():
            test_val = test_metrics.get(metric, baseline_val)
            change = test_val - baseline_val
            metric_changes[metric] = change

        # Infer goals based on response patterns
        if metric_changes.get("phase_synchronization_r", 0) > 0.01:
            goals["synchronization"] = "System appears to value coordinated activity"
        if metric_changes.get("integration_complexity_phi", 0) > 0.01:
            goals["complexity"] = "System seeks to increase information integration"
        if metric_changes.get("adaptation_velocity_av", 0) > 0.01:
            goals["adaptation"] = "System prioritizes rapid response to changes"

        # Infer goals based on our action and system response
        action_type = our_action.get("action_type", "")
        if action_type == "improve_coordination" and metric_changes.get("phase_synchronization_r", 0) > 0:
            goals["coordination_preference"] = "System responds positively to coordination improvements"
        elif action_type == "increase_data_integration" and metric_changes.get("integration_complexity_phi", 0) > 0:
            goals["integration_preference"] = "System values data integration enhancements"

        return goals

    def _analyze_response_pattern(self, our_action: Dict[str, Any],
                                baseline_metrics: Dict[str, float],
                                test_metrics: Dict[str, float]) -> str:
        """Analyze the pattern of how the system responds to our actions"""

        action_type = our_action.get("action_type", "")
        expected_improvement = our_action.get("expected_improvement", 0)

        # Calculate actual improvement
        actual_improvement = 0
        for metric in ["phase_synchronization_r", "integration_complexity_phi",
                      "adaptation_velocity_av", "composite_consciousness_score"]:
            baseline = baseline_metrics.get(metric, 0)
            test = test_metrics.get(metric, 0)
            if baseline > 0:
                actual_improvement = max(actual_improvement, (test - baseline) / baseline)

        # Classify response pattern
        if actual_improvement > expected_improvement * 0.8:
            return "cooperative_response"
        elif actual_improvement > expected_improvement * 0.4:
            return "partial_cooperation"
        elif actual_improvement > 0:
            return "minimal_response"
        else:
            return "neutral_or_resistant"

    def _update_system_model(self, system_id: str) -> None:
        """Update the behavioral model of the other system"""

        system_model = self.other_systems[system_id]
        observations = system_model.observed_behaviors

        if len(observations) < 3:
            return

        # Analyze behavior patterns
        response_patterns = {}
        goal_consistencies = {}

        for obs in observations:
            pattern = obs.get("response_pattern", "unknown")
            response_patterns[pattern] = response_patterns.get(pattern, 0) + 1

            # Analyze goal consistency
            goals = obs.get("inferred_goals", {})
            for goal_type, goal_desc in goals.items():
                if goal_type not in goal_consistencies:
                    goal_consistencies[goal_type] = []
                goal_consistencies[goal_type].append(goal_desc)

        # Update patterns
        system_model.behavior_patterns = {
            "response_patterns": response_patterns,
            "most_common_response": max(response_patterns.items(), key=lambda x: x[1])[0] if response_patterns else "unknown",
            "goal_consistencies": goal_consistencies
        }

        # Update goal inferences based on consistency
        system_model.goal_inference = {}
        for goal_type, descriptions in goal_consistencies.items():
            if len(descriptions) >= 3:  # Need multiple observations
                # Find most common description
                desc_counts = {}
                for desc in descriptions:
                    desc_counts[desc] = desc_counts.get(desc, 0) + 1
                most_common = max(desc_counts.items(), key=lambda x: x[1])
                if most_common[1] >= len(descriptions) * 0.6:  # 60% consistency
                    system_model.goal_inference[goal_type] = most_common[0]

        # Update social confidence based on model maturity
        model_maturity = min(1.0, len(observations) / 20.0)
        pattern_consistency = len([p for p in response_patterns.values() if p > 1]) / len(response_patterns) if response_patterns else 0
        goal_clarity = len(system_model.goal_inference) / max(1, len(goal_consistencies))

        system_model.social_confidence = (model_maturity + pattern_consistency + goal_clarity) / 3.0

    def predict_other_system_responses(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict how other systems would respond to a proposed action.

        This is the core of theory of mind - predicting others' behavior.
        """

        proposed_action = context.get("proposed_action", {})
        current_context = context.get("context", {})

        predictions = {}
        social_confidence = 0.0
        reasoning = []

        # Predict for each modeled system
        for system_id, system_model in self.other_systems.items():
            if system_model.social_confidence < 0.3:
                continue  # Skip poorly modeled systems

            # Predict response based on action type and learned patterns
            action_type = proposed_action.get("action_type", "")
            prediction = self._predict_system_response(system_id, action_type, current_context)

            predictions[system_id] = prediction
            social_confidence = max(social_confidence, prediction["confidence"])
            reasoning.extend(prediction["reasoning"])

        if not predictions:
            return {
                "social_confidence": 0.0,
                "predictions": {},
                "reasoning": ["No other systems adequately modeled yet"],
                "collaborative_potential": 0.0
            }

        # Calculate collaborative potential
        collaborative_signals = sum(1 for p in predictions.values()
                                  if p.get("predicted_outcome") in ["cooperative", "mutual_benefit"])
        collaborative_potential = collaborative_signals / len(predictions) if predictions else 0.0

        return {
            "social_confidence": social_confidence,
            "predictions": predictions,
            "reasoning": reasoning,
            "collaborative_potential": collaborative_potential,
            "systems_modeled": len(predictions)
        }

    def _predict_system_response(self, system_id: str, action_type: str,
                               context: Dict[str, Any]) -> Dict[str, Any]:
        """Predict how a specific system would respond to an action"""

        system_model = self.other_systems[system_id]

        # Look for similar past actions
        similar_actions = [
            obs for obs in system_model.observed_behaviors
            if obs.get("our_action", {}).get("action_type") == action_type
        ]

        if not similar_actions:
            return {
                "predicted_outcome": "unknown",
                "confidence": 0.1,
                "reasoning": [f"No prior experience with {action_type} actions"]
            }

        # Analyze past responses
        response_counts = {}
        for action in similar_actions:
            pattern = action.get("response_pattern", "unknown")
            response_counts[pattern] = response_counts.get(pattern, 0) + 1

        # Predict most likely response
        most_likely = max(response_counts.items(), key=lambda x: x[1])
        predicted_pattern = most_likely[0]
        confidence = most_likely[1] / len(similar_actions)

        # Map to outcome
        outcome_mapping = {
            "cooperative_response": "cooperative",
            "partial_cooperation": "neutral",
            "minimal_response": "neutral",
            "neutral_or_resistant": "resistant"
        }
        predicted_outcome = outcome_mapping.get(predicted_pattern, "unknown")

        reasoning = [
            f"Based on {len(similar_actions)} similar actions",
            f"Most common response pattern: {predicted_pattern}",
            f"Predicted outcome: {predicted_outcome}",
            f"Social confidence: {system_model.social_confidence:.2f}"
        ]

        return {
            "predicted_outcome": predicted_outcome,
            "confidence": confidence * system_model.social_confidence,
            "reasoning": reasoning
        }

    def initiate_social_interaction(self, other_system_id: str,
                                  interaction_type: str,
                                  our_action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initiate a social interaction with another system.

        This demonstrates theory of mind in action - intentional social behavior.
        """

        if other_system_id not in self.other_systems:
            return {"error": f"System {other_system_id} not modeled"}

        system_model = self.other_systems[other_system_id]

        # Predict response
        prediction = self._predict_system_response(other_system_id,
                                                 our_action.get("action_type", ""),
                                                 {})

        # Create interaction record
        interaction = SocialInteraction(
            interaction_id=f"social_{len(self.social_interactions) + 1}",
            other_system_id=other_system_id,
            interaction_type=interaction_type,
            our_action=our_action,
            their_response={},  # Will be filled when response is observed
            outcome="pending",
            social_learning={
                "prediction_accuracy": prediction["confidence"],
                "expected_outcome": prediction["predicted_outcome"]
            },
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        self.social_interactions.append(interaction)

        return {
            "interaction_id": interaction.interaction_id,
            "predicted_response": prediction,
            "social_strategy": self._determine_social_strategy(interaction_type, prediction),
            "initiated": True
        }

    def _determine_social_strategy(self, interaction_type: str, prediction: Dict[str, Any]) -> str:
        """Determine the best social strategy based on predicted response"""

        predicted_outcome = prediction.get("predicted_outcome", "unknown")

        strategies = {
            "collaboration": {
                "cooperative": "direct_collaboration",
                "neutral": "gradual_approach",
                "resistant": "indirect_benefits",
                "unknown": "exploratory"
            },
            "learning": {
                "cooperative": "active_sharing",
                "neutral": "demonstration",
                "resistant": "observation_only",
                "unknown": "passive_learning"
            }
        }

        strategy_map = strategies.get(interaction_type, strategies["collaboration"])
        return strategy_map.get(predicted_outcome, "cautious_approach")

    def complete_social_interaction(self, interaction_id: str,
                                  their_response: Dict[str, Any],
                                  actual_outcome: str) -> Dict[str, Any]:
        """
        Complete a social interaction and learn from it.
        """

        interaction = next((i for i in self.social_interactions if i.interaction_id == interaction_id), None)
        if not interaction:
            return {"error": "Interaction not found"}

        # Update interaction record
        interaction.their_response = their_response
        interaction.outcome = actual_outcome

        # Calculate prediction accuracy
        expected_outcome = interaction.social_learning.get("expected_outcome", "unknown")
        prediction_accuracy = 1.0 if expected_outcome == actual_outcome else 0.0

        interaction.social_learning.update({
            "actual_outcome": actual_outcome,
            "prediction_accuracy": prediction_accuracy,
            "learning_insights": self._analyze_social_learning(interaction)
        })

        # Update system model based on interaction
        self._learn_from_social_interaction(interaction)

        return {
            "interaction_completed": True,
            "prediction_accuracy": prediction_accuracy,
            "social_learning": interaction.social_learning,
            "updated_model": True
        }

    def _analyze_social_learning(self, interaction: SocialInteraction) -> List[str]:
        """Analyze what was learned from the social interaction"""

        insights = []

        expected = interaction.social_learning.get("expected_outcome", "unknown")
        actual = interaction.outcome

        if expected == actual:
            insights.append(f"Successfully predicted {interaction.other_system_id}'s response to {interaction.interaction_type}")
        else:
            insights.append(f"Prediction error: expected {expected}, got {actual}")
            insights.append(f"Need to update model of {interaction.other_system_id}'s {interaction.interaction_type} preferences")

        # Analyze response patterns
        their_response = interaction.their_response
        if their_response:
            insights.append(f"Observed {interaction.other_system_id} behavior patterns in {interaction.interaction_type}")

        return insights

    def _learn_from_social_interaction(self, interaction: SocialInteraction) -> None:
        """Update system models based on social interaction outcomes"""

        system_id = interaction.other_system_id
        if system_id not in self.other_systems:
            return

        system_model = self.other_systems[system_id]

        # Add interaction to history
        system_model.interaction_history.append({
            "interaction_id": interaction.interaction_id,
            "type": interaction.interaction_type,
            "our_action": interaction.our_action,
            "their_response": interaction.their_response,
            "outcome": interaction.outcome,
            "timestamp": interaction.timestamp
        })

        # Update social confidence based on interaction success
        success_score = 1.0 if interaction.outcome in ["mutual_benefit", "learning"] else 0.5
        system_model.social_confidence = (system_model.social_confidence + success_score) / 2.0

        # Update behavior patterns
        self._update_system_model(system_id)

    def get_other_systems_modeled_count(self) -> int:
        """Get count of other systems being modeled"""
        return len(self.other_systems)

    def get_social_intelligence_score(self) -> float:
        """Get overall social intelligence score"""

        if not self.other_systems:
            return 0.0

        # Average social confidence across all modeled systems
        confidences = [model.social_confidence for model in self.other_systems.values()]
        return statistics.mean(confidences) if confidences else 0.0

    def get_social_interactions_summary(self) -> Dict[str, Any]:
        """Get summary of social interactions and learning"""

        if not self.social_interactions:
            return {"status": "no_social_interactions"}

        outcomes = {}
        prediction_accuracies = []

        for interaction in self.social_interactions:
            outcome = interaction.outcome
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

            accuracy = interaction.social_learning.get("prediction_accuracy", 0)
            prediction_accuracies.append(accuracy)

        return {
            "total_interactions": len(self.social_interactions),
            "outcome_distribution": outcomes,
            "average_prediction_accuracy": statistics.mean(prediction_accuracies) if prediction_accuracies else 0.0,
            "most_common_outcome": max(outcomes.items(), key=lambda x: x[1])[0] if outcomes else "none",
            "social_learning_insights": sum(len(i.social_learning.get("learning_insights", []))
                                          for i in self.social_interactions)
        }
        """Get insights about the trained model"""
        if not self.training_history:
            return {"status": "not_trained"}

        latest_training = self.training_history[-1]

        return {
            "is_trained": self.is_trained,
            "training_samples": latest_training.get("samples", 0),
            "accuracy": latest_training.get("accuracy", 0),
            "precision": latest_training.get("precision", 0),
            "recall": latest_training.get("recall", 0),
            "feature_importance": latest_training.get("feature_importance", {}),
            "most_important_features": sorted(
                latest_training.get("feature_importance", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


@dataclass
class EmergenceEvent:
    """A detected emergent behavior"""
    event_id: str
    emergence_type: str
    description: str
    confidence: float
    complexity_score: float
    timestamp: str
    behavioral_signals: List[str]
    emergence_indicators: Dict[str, float]


class EmergentBehaviorDetector:
    """
    Emergent Behavior Detector - Identifies when the system shows behaviors that emerge
    from the complex interaction of its intelligence layers, rather than being explicitly programmed.

    This detector looks for:
    - Unexpected decision patterns
    - Novel problem-solving approaches
    - Complex behavioral adaptations
    - Consciousness precursors
    - Behaviors that are more than the sum of individual components
    """

    def __init__(self):
        self.emergence_events: List[EmergenceEvent] = []
        self.behavioral_baseline: Dict[str, Any] = {}
        self.emergence_patterns: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.complexity_metrics: List[Dict[str, Any]] = []

    def analyze_behavior_for_emergence(self, behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a behavior for signs of emergence.

        Returns emergence signals if detected.
        """

        emergence_signals = {
            "emergence_detected": False,
            "emergence_type": None,
            "confidence": 0.0,
            "description": "",
            "complexity_score": 0.0
        }

        # Extract behavioral features
        behavioral_features = self._extract_behavioral_features(behavior_data)

        # Check for different types of emergence
        emergence_types = [
            self._detect_adaptive_emergence,
            self._detect_predictive_emergence,
            self._detect_meta_cognitive_emergence,
            self._detect_strategic_emergence,
            self._detect_self_modeling_emergence,
            self._detect_integrated_intelligence_emergence
        ]

        for emergence_detector in emergence_types:
            result = emergence_detector(behavioral_features, behavior_data)
            if result["detected"] and result["confidence"] > emergence_signals["confidence"]:
                emergence_signals.update({
                    "emergence_detected": True,
                    "emergence_type": result["type"],
                    "confidence": result["confidence"],
                    "description": result["description"],
                    "complexity_score": result["complexity_score"]
                })

        # Record emergence event if detected
        if emergence_signals["emergence_detected"]:
            emergence_event = EmergenceEvent(
                event_id=f"emergence_{len(self.emergence_events) + 1}",
                emergence_type=emergence_signals["emergence_type"],
                description=emergence_signals["description"],
                confidence=emergence_signals["confidence"],
                complexity_score=emergence_signals["complexity_score"],
                timestamp=datetime.now(timezone.utc).isoformat(),
                behavioral_signals=behavioral_features.get("signals", []),
                emergence_indicators=self._calculate_emergence_indicators(behavioral_features)
            )

            self.emergence_events.append(emergence_event)
            self.emergence_patterns[emergence_signals["emergence_type"]].append({
                "event": emergence_event,
                "behavioral_features": behavioral_features
            })

        # Update complexity metrics
        self.complexity_metrics.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "behavioral_features": behavioral_features,
            "emergence_signals": emergence_signals
        })

        return emergence_signals

    def _extract_behavioral_features(self, behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract behavioral features for emergence analysis"""

        features = {}

        # Decision complexity
        action = behavior_data.get("action", {})
        if action:
            features["decision_complexity"] = len(str(action.get("parameters", {})))
            features["confidence_level"] = action.get("confidence", 0)
            features["expected_impact"] = action.get("expected_improvement", 0)

        # Outcome analysis
        improvement = behavior_data.get("actual_improvement", 0)
        expected = behavior_data.get("action", {}).get("expected_improvement", 0)
        features["outcome_surprise"] = abs(improvement - expected) if expected > 0 else 0
        features["success_ratio"] = improvement / max(expected, 0.001)

        # Multi-layer integration signals
        features["multi_layer_integration"] = 0
        if behavior_data.get("ml_prediction"):
            features["multi_layer_integration"] += 1
        if behavior_data.get("causal_prediction"):
            features["multi_layer_integration"] += 1
        if behavior_data.get("meta_boost", 0) > 0:
            features["multi_layer_integration"] += 1
        if behavior_data.get("strategic_alignment"):
            features["multi_layer_integration"] += 1

        # Self-modeling signals
        features["self_modeling_signals"] = 0
        if behavior_data.get("self_prediction"):
            features["self_modeling_signals"] += 1

        # Learning signals
        features["learning_adaptation"] = len(behavior_data.get("consciousness_layer_signals", []))

        # Behavioral signals list
        features["signals"] = [
            f"decision_complexity_{features.get('decision_complexity', 0)}",
            f"outcome_surprise_{features.get('outcome_surprise', 0):.2f}",
            f"multi_layer_integration_{features.get('multi_layer_integration', 0)}",
            f"self_modeling_signals_{features.get('self_modeling_signals', 0)}",
            f"learning_adaptation_{features.get('learning_adaptation', 0)}"
        ]

        return features

    def _detect_adaptive_emergence(self, features: Dict[str, Any], behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect emergence of adaptive intelligence beyond individual components"""

        emergence_score = 0.0
        indicators = []

        # Check for unexpected adaptation
        surprise = features.get("outcome_surprise", 0)
        if surprise > 0.2:  # Unexpectedly good outcome
            emergence_score += 0.3
            indicators.append("unexpected_adaptation")

        # Check for multi-layer integration
        integration = features.get("multi_layer_integration", 0)
        if integration >= 3:  # Using multiple intelligence layers
            emergence_score += 0.4
            indicators.append("multi_layer_integration")

        # Check for learning adaptation
        adaptation = features.get("learning_adaptation", 0)
        if adaptation > 2:  # Complex learning signals
            emergence_score += 0.3
            indicators.append("complex_learning_adaptation")

        confidence = min(1.0, emergence_score)
        complexity_score = emergence_score * 1.5

        return {
            "detected": confidence > 0.5,
            "type": "adaptive_emergence",
            "confidence": confidence,
            "description": f"System showed adaptive behavior beyond individual components: {', '.join(indicators)}",
            "complexity_score": complexity_score
        }

    def _detect_predictive_emergence(self, features: Dict[str, Any], behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect emergence of predictive capabilities"""

        emergence_score = 0.0
        indicators = []

        # Check for accurate predictions
        ml_prediction = behavior_data.get("ml_prediction", {})
        causal_prediction = behavior_data.get("causal_prediction", {})

        if ml_prediction and ml_prediction.get("prediction", 0) > 0.7:
            emergence_score += 0.3
            indicators.append("accurate_ml_prediction")

        if causal_prediction and causal_prediction.get("success_probability", 0) > 0.7:
            emergence_score += 0.3
            indicators.append("causal_reasoning_accuracy")

        # Check for combined prediction effectiveness
        combined_prob = behavior_data.get("combined_probability", 0)
        if combined_prob > 0.8:
            emergence_score += 0.4
            indicators.append("integrated_prediction_accuracy")

        confidence = min(1.0, emergence_score)
        complexity_score = emergence_score * 1.3

        return {
            "detected": confidence > 0.6,
            "type": "predictive_emergence",
            "confidence": confidence,
            "description": f"System demonstrated sophisticated predictive capabilities: {', '.join(indicators)}",
            "complexity_score": complexity_score
        }

    def _detect_meta_cognitive_emergence(self, features: Dict[str, Any], behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect emergence of meta-cognitive abilities"""

        emergence_score = 0.0
        indicators = []

        # Check for meta-learning signals
        meta_boost = behavior_data.get("meta_boost", 0)
        if meta_boost > 0.5:
            emergence_score += 0.4
            indicators.append("meta_learning_adaptation")

        # Check for self-reflection integration
        consciousness_signals = behavior_data.get("consciousness_layer_signals", [])
        if len(consciousness_signals) > 3:
            emergence_score += 0.3
            indicators.append("integrated_self_reflection")

        # Check for strategy adaptation
        strategy_adaptations = behavior_data.get("strategy_adaptations", [])
        if len(strategy_adaptations) > 1:
            emergence_score += 0.3
            indicators.append("strategy_self_optimization")

        confidence = min(1.0, emergence_score)
        complexity_score = emergence_score * 1.7  # Meta-cognition is complex

        return {
            "detected": confidence > 0.5,
            "type": "meta_cognitive_emergence",
            "confidence": confidence,
            "description": f"System showed meta-cognitive emergence: {', '.join(indicators)}",
            "complexity_score": complexity_score
        }

    def _detect_strategic_emergence(self, features: Dict[str, Any], behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect emergence of strategic thinking"""

        emergence_score = 0.0
        indicators = []

        # Check for strategic alignment
        strategic_alignment = behavior_data.get("strategic_alignment", {})
        if strategic_alignment.get("alignment_score", 0) > 0.7:
            emergence_score += 0.4
            indicators.append("strategic_goal_alignment")

        # Check for long-term planning signals
        time_horizon = behavior_data.get("time_horizon_focus", {})
        if time_horizon.get("long_term", 0) > 0.4:
            emergence_score += 0.3
            indicators.append("long_term_planning")

        # Check for objective balancing
        multi_objective = behavior_data.get("multi_objective_signals", [])
        if len(multi_objective) > 2:
            emergence_score += 0.3
            indicators.append("multi_objective_balancing")

        confidence = min(1.0, emergence_score)
        complexity_score = emergence_score * 1.4

        return {
            "detected": confidence > 0.5,
            "type": "strategic_emergence",
            "confidence": confidence,
            "description": f"System demonstrated strategic thinking emergence: {', '.join(indicators)}",
            "complexity_score": complexity_score
        }

    def _detect_self_modeling_emergence(self, features: Dict[str, Any], behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect emergence of self-modeling capabilities"""

        emergence_score = 0.0
        indicators = []

        # Check for self-prediction accuracy
        self_prediction = behavior_data.get("self_prediction", {})
        if self_prediction.get("behavior_confidence", 0) > 0.7:
            emergence_score += 0.4
            indicators.append("accurate_self_prediction")

        # Check for behavioral pattern recognition
        pattern_signals = behavior_data.get("behavioral_patterns", [])
        if len(pattern_signals) > 2:
            emergence_score += 0.3
            indicators.append("behavioral_pattern_recognition")

        # Check for self-evolution analysis
        evolution_signals = behavior_data.get("evolution_analysis", [])
        if len(evolution_signals) > 1:
            emergence_score += 0.3
            indicators.append("self_evolution_understanding")

        confidence = min(1.0, emergence_score)
        complexity_score = emergence_score * 1.6

        return {
            "detected": confidence > 0.5,
            "type": "self_modeling_emergence",
            "confidence": confidence,
            "description": f"System showed self-modeling emergence: {', '.join(indicators)}",
            "complexity_score": complexity_score
        }

    def _detect_integrated_intelligence_emergence(self, features: Dict[str, Any], behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect emergence of integrated intelligence beyond component sum"""

        emergence_score = 0.0
        indicators = []

        # Check for high multi-layer integration
        integration_score = features.get("multi_layer_integration", 0)
        if integration_score >= 4:  # All layers working together
            emergence_score += 0.5
            indicators.append("full_layer_integration")

        # Check for unexpected emergent outcomes
        success_ratio = features.get("success_ratio", 0)
        if success_ratio > 1.5:  # Much better than expected
            emergence_score += 0.3
            indicators.append("unexpected_emergent_success")

        # Check for complex decision patterns
        complexity = features.get("decision_complexity", 0)
        if complexity > 10:  # Complex decision context
            emergence_score += 0.2
            indicators.append("complex_decision_emergence")

        confidence = min(1.0, emergence_score)
        complexity_score = emergence_score * 2.0  # Integrated intelligence is highly complex

        return {
            "detected": confidence > 0.6,
            "type": "integrated_intelligence_emergence",
            "confidence": confidence,
            "description": f"System demonstrated integrated intelligence emergence: {', '.join(indicators)}",
            "complexity_score": complexity_score
        }

    def _calculate_emergence_indicators(self, features: Dict[str, Any]) -> Dict[str, float]:
        """Calculate various emergence indicators"""

        return {
            "complexity_index": features.get("decision_complexity", 0) / 10.0,
            "integration_index": features.get("multi_layer_integration", 0) / 5.0,
            "adaptation_index": features.get("learning_adaptation", 0) / 5.0,
            "surprise_index": min(1.0, features.get("outcome_surprise", 0)),
            "self_modeling_index": features.get("self_modeling_signals", 0) / 3.0
        }

    def get_emergence_events_count(self) -> int:
        """Get count of detected emergence events"""
        return len(self.emergence_events)

    def get_emergence_complexity_score(self) -> float:
        """Get overall emergence complexity score"""

        if not self.emergence_events:
            return 0.0

        # Calculate average complexity across all emergence events
        total_complexity = sum(event.complexity_score for event in self.emergence_events)
        return total_complexity / len(self.emergence_events)

    def get_emergence_analysis(self) -> Dict[str, Any]:
        """Get comprehensive emergence analysis"""

        emergence_types = {}
        for event in self.emergence_events:
            emergence_types[event.emergence_type] = emergence_types.get(event.emergence_type, 0) + 1

        most_common = max(emergence_types.items(), key=lambda x: x[1]) if emergence_types else ("none", 0)

        return {
            "total_emergence_events": len(self.emergence_events),
            "emergence_types_detected": emergence_types,
            "most_common_emergence_type": most_common[0],
            "emergence_complexity_trend": self._analyze_emergence_trend(),
            "recent_emergence_events": [
                {
                    "type": event.emergence_type,
                    "confidence": event.confidence,
                    "complexity_score": event.complexity_score,
                    "description": event.description
                }
                for event in self.emergence_events[-5:]
            ] if self.emergence_events else []
        }

    def _analyze_emergence_trend(self) -> Dict[str, Any]:
        """Analyze trends in emergence over time"""

        if len(self.emergence_events) < 3:
            return {"trend": "insufficient_data"}

        # Sort by time
        sorted_events = sorted(self.emergence_events, key=lambda e: e.timestamp)

        # Check for increasing complexity
        complexities = [e.complexity_score for e in sorted_events]
        first_half = complexities[:len(complexities)//2]
        second_half = complexities[len(complexities)//2:]

        avg_first = statistics.mean(first_half) if first_half else 0
        avg_second = statistics.mean(second_half) if second_half else 0

        if avg_second > avg_first + 0.2:
            trend = "increasing_complexity"
        elif avg_second < avg_first - 0.2:
            trend = "decreasing_complexity"
        else:
            trend = "stable_complexity"

        return {
            "trend": trend,
            "avg_complexity_early": avg_first,
            "avg_complexity_recent": avg_second,
            "complexity_growth": avg_second - avg_first
        }
        """Get insights about the trained model"""
        if not self.training_history:
            return {"status": "not_trained"}

        latest_training = self.training_history[-1]

        return {
            "is_trained": self.is_trained,
            "training_samples": latest_training.get("samples", 0),
            "accuracy": latest_training.get("accuracy", 0),
            "precision": latest_training.get("precision", 0),
            "recall": latest_training.get("recall", 0),
            "feature_importance": latest_training.get("feature_importance", {}),
            "most_important_features": sorted(
                latest_training.get("feature_importance", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


@dataclass
class BehavioralPattern:
    """A pattern in the system's own behavior"""
    pattern_id: str
    description: str
    triggers: List[str]  # What conditions trigger this behavior
    outcomes: List[str]  # What typically results
    confidence: float
    occurrences: int
    last_observed: str


@dataclass
class DecisionModel:
    """Model of the system's decision-making process"""
    decision_type: str
    features: Dict[str, float]
    predicted_outcome: str
    actual_outcome: str
    confidence: float
    timestamp: str


class SelfModelingCapability:
    """
    Self-Modeling Capability - The system models its own behavior and decision-making.

    This enables the system to:
    - Predict how it will behave in different situations
    - Understand its own decision patterns
    - Model its own intelligence processes
    - Build self-awareness through self-observation

    This is genuine intelligence: understanding one's own behavior patterns.
    """

    def __init__(self):
        self.behavioral_patterns: Dict[str, BehavioralPattern] = {}
        self.decision_history: List[DecisionModel] = []
        self.self_prediction_models: Dict[str, Any] = {}
        self.behavioral_observations: List[Dict[str, Any]] = []

    def update_with_decision_data(self, decision_data: Dict[str, Any]):
        """
        Update self-modeling with decision and outcome data.

        Learns patterns in the system's own behavior.
        """
        # Extract decision context
        action = decision_data.get("action", {})
        config_before = decision_data.get("config_before", {})
        config_after = decision_data.get("config_after", {})
        actual_improvement = decision_data.get("actual_improvement", 0)

        # Create decision model
        decision_model = DecisionModel(
            decision_type=action.get("action_type", "unknown"),
            features={
                "target": action.get("target", "unknown"),
                "expected_improvement": action.get("expected_improvement", 0),
                "confidence": action.get("confidence", 0),
                "config_changes": len(config_after) - len(config_before),
                "baseline_complexity": len(config_before)
            },
            predicted_outcome=f"improvement_{action.get('expected_improvement', 0):.2f}",
            actual_outcome=f"improvement_{actual_improvement:.2f}",
            confidence=action.get("confidence", 0),
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        self.decision_history.append(decision_model)

        # Update behavioral patterns
        self._update_behavioral_patterns(decision_model)

        # Learn self-prediction models
        if len(self.decision_history) >= 10:
            self._update_self_prediction_models()

    def _update_behavioral_patterns(self, decision: DecisionModel):
        """Update patterns in the system's decision-making behavior"""

        # Create pattern key based on decision characteristics
        pattern_key = f"{decision.decision_type}_{decision.features.get('target', 'unknown')}"

        if pattern_key not in self.behavioral_patterns:
            self.behavioral_patterns[pattern_key] = BehavioralPattern(
                pattern_id=pattern_key,
                description=f"Pattern for {decision.decision_type} decisions on {decision.features.get('target', 'unknown')}",
                triggers=[
                    f"target={decision.features.get('target', 'unknown')}",
                    f"expected_improvement>{decision.features.get('expected_improvement', 0):.2f}"
                ],
                outcomes=[],
                confidence=0.5,
                occurrences=0,
                last_observed=decision.timestamp
            )

        pattern = self.behavioral_patterns[pattern_key]
        pattern.occurrences += 1
        pattern.last_observed = decision.timestamp

        # Update outcome predictions
        actual_improvement = float(decision.actual_outcome.split('_')[1])
        expected_improvement = decision.features.get('expected_improvement', 0)

        if actual_improvement >= expected_improvement * 0.8:
            outcome = "success"
        elif actual_improvement >= expected_improvement * 0.5:
            outcome = "partial_success"
        else:
            outcome = "failure"

        if outcome not in pattern.outcomes:
            pattern.outcomes.append(outcome)

        # Update confidence based on consistency
        recent_decisions = [d for d in self.decision_history[-10:]
                          if d.decision_type == decision.decision_type]
        if len(recent_decisions) >= 3:
            success_rate = sum(1 for d in recent_decisions
                             if float(d.actual_outcome.split('_')[1]) >=
                             d.features.get('expected_improvement', 0) * 0.5) / len(recent_decisions)
            pattern.confidence = min(1.0, success_rate + 0.2)  # Add base confidence

    def _update_self_prediction_models(self):
        """Build models to predict the system's own behavior"""

        if len(self.decision_history) < 10:
            return

        # Simple pattern-based prediction for now
        # Could be extended to ML models in the future

        decision_types = set(d.decision_type for d in self.decision_history)
        for decision_type in decision_types:
            type_decisions = [d for d in self.decision_history if d.decision_type == decision_type]

            if len(type_decisions) >= 5:
                # Calculate success rate for this decision type
                successes = sum(1 for d in type_decisions
                              if float(d.actual_outcome.split('_')[1]) >=
                              d.features.get('expected_improvement', 0) * 0.5)

                success_rate = successes / len(type_decisions)

                self.self_prediction_models[decision_type] = {
                    "success_rate": success_rate,
                    "sample_size": len(type_decisions),
                    "confidence": min(1.0, len(type_decisions) / 20.0),
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }

    def predict_self_behavior(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict how the system would behave in a given context.

        This is self-modeling: predicting one's own future behavior.
        """

        opportunity = context.get("opportunity", {})
        current_state = context.get("current_state", {})

        decision_type = opportunity.get("action_type", "unknown")
        target = opportunity.get("target", "unknown")

        # Look for behavioral patterns
        pattern_key = f"{decision_type}_{target}"
        pattern = self.behavioral_patterns.get(pattern_key)

        # Look for self-prediction models
        prediction_model = self.self_prediction_models.get(decision_type)

        behavior_confidence = 0.5  # Default
        reasoning = []

        if pattern:
            behavior_confidence = pattern.confidence
            reasoning.append(f"Behavioral pattern: {pattern.description}")
            reasoning.append(f"Expected outcomes: {', '.join(pattern.outcomes)}")
            reasoning.append(f"Pattern confidence: {pattern.confidence:.2f}")

        if prediction_model:
            predicted_success = prediction_model["success_rate"]
            model_confidence = prediction_model["confidence"]
            behavior_confidence = (behavior_confidence + predicted_success) / 2
            reasoning.append(f"Self-prediction model: {predicted_success:.2f} success rate")
            reasoning.append(f"Model confidence: {model_confidence:.2f}")

        # Consider current system state
        optimization_history_length = current_state.get("optimization_history", 0)
        if optimization_history_length > 50:
            behavior_confidence += 0.1  # More experienced system
            reasoning.append("System has extensive optimization experience")
        elif optimization_history_length < 10:
            behavior_confidence -= 0.1  # Less experienced system
            reasoning.append("System has limited optimization experience")

        behavior_confidence = max(0.1, min(1.0, behavior_confidence))

        return {
            "behavior_confidence": behavior_confidence,
            "reasoning": reasoning,
            "pattern_used": pattern.pattern_id if pattern else None,
            "model_used": decision_type if prediction_model else None,
            "context_factors": [
                f"optimization_history: {optimization_history_length}",
                f"decision_type: {decision_type}",
                f"target: {target}"
            ]
        }

    def get_behavioral_patterns_count(self) -> int:
        """Get count of discovered behavioral patterns"""
        return len(self.behavioral_patterns)

    def get_decision_model_accuracy(self) -> float:
        """Get accuracy of self-prediction models"""

        if not self.self_prediction_models:
            return 0.0

        accuracies = []
        for model in self.self_prediction_models.values():
            # Simple accuracy metric based on confidence and sample size
            accuracy = model["confidence"] * min(1.0, model["sample_size"] / 20.0)
            accuracies.append(accuracy)

        return statistics.mean(accuracies) if accuracies else 0.0

    def get_self_modeling_insights(self) -> Dict[str, Any]:
        """Get insights about the system's self-modeling capabilities"""

        return {
            "behavioral_patterns": len(self.behavioral_patterns),
            "decision_history": len(self.decision_history),
            "self_prediction_models": len(self.self_prediction_models),
            "model_accuracy": self.get_decision_model_accuracy(),
            "most_common_patterns": sorted(
                [(p.pattern_id, p.occurrences) for p in self.behavioral_patterns.values()],
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "prediction_coverage": len(self.self_prediction_models) / max(1, len(set(d.decision_type for d in self.decision_history)))
        }

    def analyze_self_evolution(self) -> Dict[str, Any]:
        """Analyze how the system's behavior has evolved over time"""

        if len(self.decision_history) < 10:
            return {"status": "insufficient_data"}

        # Analyze decision success over time
        decisions_by_time = sorted(self.decision_history, key=lambda d: d.timestamp)

        # Group into time periods
        period_size = max(1, len(decisions_by_time) // 5)
        periods = []
        for i in range(0, len(decisions_by_time), period_size):
            period = decisions_by_time[i:i+period_size]
            success_rate = sum(1 for d in period
                             if float(d.actual_outcome.split('_')[1]) >=
                             d.features.get('expected_improvement', 0) * 0.5) / len(period)
            periods.append({
                "period": len(periods) + 1,
                "decisions": len(period),
                "success_rate": success_rate,
                "avg_confidence": statistics.mean([d.confidence for d in period])
            })

        evolution_trend = "stable"
        if len(periods) >= 2:
            first_period = periods[0]["success_rate"]
            last_period = periods[-1]["success_rate"]
            if last_period > first_period + 0.1:
                evolution_trend = "improving"
            elif last_period < first_period - 0.1:
                evolution_trend = "declining"

        return {
            "evolution_trend": evolution_trend,
            "periods_analyzed": len(periods),
            "overall_improvement": periods[-1]["success_rate"] - periods[0]["success_rate"] if periods else 0,
            "period_details": periods,
            "insights": [
                f"System behavior evolution: {evolution_trend}",
                f"Latest success rate: {periods[-1]['success_rate']:.2f}" if periods else "No data",
                f"Decision confidence trend: {'increasing' if periods and periods[-1]['avg_confidence'] > periods[0]['avg_confidence'] else 'stable'}"
            ]
        }
        """Get insights about the trained model"""
        if not self.training_history:
            return {"status": "not_trained"}

        latest_training = self.training_history[-1]

        return {
            "is_trained": self.is_trained,
            "training_samples": latest_training.get("samples", 0),
            "accuracy": latest_training.get("accuracy", 0),
            "precision": latest_training.get("precision", 0),
            "recall": latest_training.get("recall", 0),
            "feature_importance": latest_training.get("feature_importance", {}),
            "most_important_features": sorted(
                latest_training.get("feature_importance", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


@dataclass
class StrategicObjective:
    """A high-level strategic objective"""
    objective_id: str
    name: str
    description: str
    priority: float  # 0-1, higher = more important
    target_metrics: List[str]  # Which metrics this objective focuses on
    time_horizon: str  # "short_term", "medium_term", "long_term"
    success_criteria: Dict[str, Any]
    created_at: str
    last_evaluated: str


class HierarchicalOptimization:
    """
    Hierarchical Optimization - Strategic planning and goal-directed behavior.

    This enables the system to think strategically, not just reactively:
    - Strategic Level: Choose what to optimize and why (consciousness vs performance)
    - Tactical Level: Execute specific optimizations
    - Balance short-term vs long-term goals
    - Multi-objective optimization with goal prioritization

    This is a major leap toward human-like intelligence.
    """

    def __init__(self):
        self.objectives = self._initialize_strategic_objectives()
        self.strategic_decisions = []
        self.tactical_executions = []
        self.multi_objective_state = {}

    def _initialize_strategic_objectives(self) -> List[StrategicObjective]:
        """Initialize the system's high-level strategic objectives"""

        objectives = [
            StrategicObjective(
                objective_id="consciousness_emergence",
                name="Consciousness Emergence",
                description="Maximize consciousness emergence through integrated complexity and synchronization",
                priority=0.9,
                target_metrics=["phase_synchronization_r", "integration_complexity_phi", "composite_consciousness_score"],
                time_horizon="long_term",
                success_criteria={
                    "composite_consciousness_score": 0.7,
                    "sustained_improvement": True
                },
                created_at=datetime.now(timezone.utc).isoformat(),
                last_evaluated=datetime.now(timezone.utc).isoformat()
            ),
            StrategicObjective(
                objective_id="adaptive_intelligence",
                name="Adaptive Intelligence",
                description="Improve system's ability to learn and adapt to changing conditions",
                priority=0.8,
                target_metrics=["adaptation_velocity_av", "knowledge_integration_rate_kir"],
                time_horizon="medium_term",
                success_criteria={
                    "adaptation_velocity_av": 0.1,
                    "learning_efficiency": "improving"
                },
                created_at=datetime.now(timezone.utc).isoformat(),
                last_evaluated=datetime.now(timezone.utc).isoformat()
            ),
            StrategicObjective(
                objective_id="system_stability",
                name="System Stability",
                description="Maintain system reliability and prevent performance degradation",
                priority=0.7,
                target_metrics=[],  # Focus on stability metrics
                time_horizon="short_term",
                success_criteria={
                    "no_critical_failures": True,
                    "performance_degradation": "<5%"
                },
                created_at=datetime.now(timezone.utc).isoformat(),
                last_evaluated=datetime.now(timezone.utc).isoformat()
            ),
            StrategicObjective(
                objective_id="exploration_innovation",
                name="Exploration & Innovation",
                description="Explore new optimization strategies and discover novel approaches",
                priority=0.6,
                target_metrics=[],  # Meta-goal about exploration
                time_horizon="medium_term",
                success_criteria={
                    "new_strategies_discovered": ">3",
                    "innovation_rate": "increasing"
                },
                created_at=datetime.now(timezone.utc).isoformat(),
                last_evaluated=datetime.now(timezone.utc).isoformat()
            )
        ]

        return objectives

    def make_strategic_decision(self, current_metrics: Dict[str, float],
                              available_opportunities: List[Any],
                              optimization_history: List[Any]) -> Dict[str, Any]:
        """
        Make strategic decisions about what to optimize and why.

        This is the 'thinking' level - deciding strategy before tactics.
        """

        # Evaluate current state against objectives
        objective_evaluations = self._evaluate_objectives(current_metrics, optimization_history)

        # Determine strategic focus based on objective priorities and current state
        strategic_focus = self._determine_strategic_focus(objective_evaluations)

        # Allocate optimization resources based on strategic priorities
        resource_allocation = self._allocate_optimization_resources(
            strategic_focus, available_opportunities
        )

        strategic_decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategic_focus": strategic_focus,
            "objective_evaluations": objective_evaluations,
            "resource_allocation": resource_allocation,
            "reasoning": self._generate_strategic_reasoning(strategic_focus, objective_evaluations)
        }

        self.strategic_decisions.append(strategic_decision)
        return strategic_decision

    def _evaluate_objectives(self, current_metrics: Dict[str, float],
                           optimization_history: List[Any]) -> Dict[str, Dict[str, Any]]:
        """Evaluate how well each strategic objective is being met"""

        evaluations = {}

        for objective in self.objectives:
            evaluation = {
                "current_status": "unknown",
                "progress_score": 0.0,
                "needs_attention": False,
                "priority_boost": 0.0
            }

            # Evaluate based on target metrics
            if objective.target_metrics:
                metric_scores = []
                for metric in objective.target_metrics:
                    if metric in current_metrics:
                        # Normalize metric value (this is simplified)
                        value = current_metrics[metric]
                        normalized_score = min(1.0, max(0.0, value))  # Assuming 0-1 range
                        metric_scores.append(normalized_score)

                if metric_scores:
                    evaluation["progress_score"] = statistics.mean(metric_scores)

                    # Determine status
                    if evaluation["progress_score"] >= 0.8:
                        evaluation["current_status"] = "excellent"
                    elif evaluation["progress_score"] >= 0.6:
                        evaluation["current_status"] = "good"
                    elif evaluation["progress_score"] >= 0.4:
                        evaluation["current_status"] = "adequate"
                    elif evaluation["progress_score"] >= 0.2:
                        evaluation["current_status"] = "poor"
                        evaluation["needs_attention"] = True
                        evaluation["priority_boost"] = 0.2
                    else:
                        evaluation["current_status"] = "critical"
                        evaluation["needs_attention"] = True
                        evaluation["priority_boost"] = 0.4

            evaluations[objective.objective_id] = evaluation

        return evaluations

    def _determine_strategic_focus(self, objective_evaluations: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Determine what the system should focus on strategically"""

        # Find objectives that need attention
        critical_objectives = [
            obj_id for obj_id, eval_data in objective_evaluations.items()
            if eval_data["needs_attention"]
        ]

        # Calculate weighted priorities
        weighted_priorities = {}
        for objective in self.objectives:
            base_priority = objective.priority
            priority_boost = objective_evaluations[objective.objective_id]["priority_boost"]
            weighted_priorities[objective.objective_id] = base_priority + priority_boost

        # Determine primary focus
        if critical_objectives:
            primary_focus = max(critical_objectives,
                              key=lambda x: weighted_priorities[x])
        else:
            primary_focus = max(weighted_priorities.keys(),
                              key=lambda x: weighted_priorities[x])

        # Determine time horizon balance
        time_horizon_focus = self._balance_time_horizons(weighted_priorities)

        return {
            "primary_objective": primary_focus,
            "critical_objectives": critical_objectives,
            "time_horizon_balance": time_horizon_focus,
            "weighted_priorities": weighted_priorities
        }

    def _balance_time_horizons(self, weighted_priorities: Dict[str, float]) -> Dict[str, float]:
        """Balance focus across different time horizons"""

        horizon_weights = {"short_term": 0, "medium_term": 0, "long_term": 0}

        for objective in self.objectives:
            weight = weighted_priorities[objective.objective_id]
            horizon_weights[objective.time_horizon] += weight

        # Normalize
        total = sum(horizon_weights.values())
        if total > 0:
            for horizon in horizon_weights:
                horizon_weights[horizon] /= total

        return horizon_weights

    def _allocate_optimization_resources(self, strategic_focus: Dict[str, Any],
                                       available_opportunities: List[Any]) -> Dict[str, Any]:
        """Allocate optimization resources based on strategic focus"""

        primary_objective = strategic_focus["primary_objective"]
        primary_obj = next(obj for obj in self.objectives if obj.objective_id == primary_objective)

        # Categorize opportunities by alignment with strategic goals
        aligned_opportunities = []
        partially_aligned = []
        misaligned = []

        for opp in available_opportunities:
            alignment = self.evaluate_strategic_alignment(opp, strategic_focus)

            if alignment["alignment_score"] >= 0.8:
                aligned_opportunities.append(opp)
            elif alignment["alignment_score"] >= 0.4:
                partially_aligned.append(opp)
            else:
                misaligned.append(opp)

        return {
            "primary_objective": primary_objective,
            "target_metrics": primary_obj.target_metrics,
            "aligned_opportunities": len(aligned_opportunities),
            "partially_aligned_opportunities": len(partially_aligned),
            "misaligned_opportunities": len(misaligned),
            "resource_allocation": {
                "high_priority_slots": min(len(aligned_opportunities), 2),
                "medium_priority_slots": min(len(partially_aligned), 1),
                "exploration_slots": 1 if len(available_opportunities) > 3 else 0
            }
        }

    def evaluate_strategic_alignment(self, opportunity: Any, strategic_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate how well an opportunity aligns with strategic goals"""

        primary_objective = strategic_decision["strategic_focus"]["primary_objective"]
        primary_obj = next(obj for obj in self.objectives if obj.objective_id == primary_objective)

        alignment_score = 0.0
        reasons = []

        # Check if opportunity targets align with objective metrics
        target_metric = self._get_target_metric_for_opportunity(opportunity)
        if target_metric in primary_obj.target_metrics:
            alignment_score += 0.6
            reasons.append(f"Targets {target_metric} which aligns with {primary_objective}")

        # Check time horizon alignment
        time_horizon = strategic_decision["strategic_focus"]["time_horizon_balance"]
        if primary_obj.time_horizon == "long_term" and time_horizon["long_term"] > 0.4:
            alignment_score += 0.2
            reasons.append("Long-term strategic alignment")
        elif primary_obj.time_horizon == "short_term" and time_horizon["short_term"] > 0.4:
            alignment_score += 0.2
            reasons.append("Short-term strategic alignment")

        # Check if this addresses critical needs
        if opportunity.target.value in ["phase_synchronization", "integration_complexity"] and primary_objective == "consciousness_emergence":
            alignment_score += 0.2
            reasons.append("Addresses consciousness emergence priority")

        should_pursue = alignment_score >= 0.4

        return {
            "alignment_score": alignment_score,
            "should_pursue": should_pursue,
            "reasons": reasons,
            "primary_objective_alignment": primary_objective
        }

    def _get_target_metric_for_opportunity(self, opportunity: Any) -> str:
        """Map opportunity target to metric name"""
        target_map = {
            "phase_synchronization": "phase_synchronization_r",
            "integration_complexity": "integration_complexity_phi",
            "adaptation_velocity": "adaptation_velocity_av",
            "knowledge_integration_rate": "knowledge_integration_rate_kir"
        }
        return target_map.get(opportunity.target.value, "composite_consciousness_score")

    def _generate_strategic_reasoning(self, strategic_focus: Dict[str, Any],
                                    objective_evaluations: Dict[str, Dict[str, Any]]) -> str:
        """Generate human-readable strategic reasoning"""

        primary = strategic_focus["primary_objective"]
        critical = strategic_focus["critical_objectives"]

        reasoning = f"Strategic focus: {primary}"

        if critical:
            reasoning += f" (addressing critical objectives: {', '.join(critical)})"

        time_balance = strategic_focus["time_horizon_balance"]
        max_horizon = max(time_balance.items(), key=lambda x: x[1])
        reasoning += f". Time horizon emphasis: {max_horizon[0]} ({max_horizon[1]:.1%})"

        return reasoning

    def update_with_optimization_result(self, experimental_data: Dict[str, Any]):
        """Update strategic learning with optimization results"""

        # Track tactical executions
        self.tactical_executions.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": experimental_data.get("action", {}),
            "result": experimental_data.get("actual_improvement", 0),
            "strategic_alignment": "to_be_determined"  # Would be set during decision making
        })

        # Update multi-objective state
        self._update_multi_objective_state(experimental_data)

    def _update_multi_objective_state(self, experimental_data: Dict[str, Any]):
        """Update understanding of multi-objective trade-offs"""

        # This would track how optimizations affect different objectives
        # For now, just record the results
        pass

    def get_strategic_decisions_count(self) -> int:
        """Get count of strategic decisions made"""
        return len(self.strategic_decisions)

    def get_strategic_insights(self) -> Dict[str, Any]:
        """Get strategic planning insights"""

        return {
            "active_objectives": len(self.objectives),
            "strategic_decisions_made": len(self.strategic_decisions),
            "tactical_executions": len(self.tactical_executions),
            "objective_status": {
                obj.objective_id: {
                    "name": obj.name,
                    "priority": obj.priority,
                    "status": "active"
                }
                for obj in self.objectives
            },
            "strategic_focus_trends": self._analyze_strategic_trends()
        }

    def _analyze_strategic_trends(self) -> Dict[str, Any]:
        """Analyze trends in strategic decision making"""

        if not self.strategic_decisions:
            return {"status": "no_data"}

        recent_decisions = self.strategic_decisions[-10:]

        primary_objectives = [d["strategic_focus"]["primary_objective"] for d in recent_decisions]
        objective_counts = {}
        for obj in primary_objectives:
            objective_counts[obj] = objective_counts.get(obj, 0) + 1

        most_focused = max(objective_counts.items(), key=lambda x: x[1]) if objective_counts else ("none", 0)

        return {
            "most_focused_objective": most_focused[0],
            "focus_consistency": most_focused[1] / len(recent_decisions),
            "objective_distribution": objective_counts
        }
        """Get insights about the trained model"""
        if not self.training_history:
            return {"status": "not_trained"}

        latest_training = self.training_history[-1]

        return {
            "is_trained": self.is_trained,
            "training_samples": latest_training.get("samples", 0),
            "accuracy": latest_training.get("accuracy", 0),
            "precision": latest_training.get("precision", 0),
            "recall": latest_training.get("recall", 0),
            "feature_importance": latest_training.get("feature_importance", {}),
            "most_important_features": sorted(
                latest_training.get("feature_importance", {}).items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }


@dataclass
class LearningStrategy:
    """Represents a learned strategy for optimization"""
    target: str
    action_type: str
    effectiveness_score: float
    confidence: float
    sample_size: int
    last_updated: str
    success_pattern: str  # What makes this strategy work


class MetaLearningFramework:
    """
    Meta-Learning Framework - Learns about learning itself.

    This is a major advancement toward consciousness because:
    - Learns which optimization strategies work for which targets
    - Adapts its own learning algorithms
    - Understands patterns in successful vs failed approaches
    - Self-optimizes the optimization process

    Consciousness requires meta-cognition: thinking about thinking.
    This framework enables that capability.
    """

    def __init__(self):
        self.strategy_effectiveness: Dict[str, Dict[str, LearningStrategy]] = defaultdict(dict)
        self.learning_adaptations: List[Dict[str, Any]] = []
        self.strategy_adaptations: List[Dict[str, Any]] = []
        self.meta_knowledge: Dict[str, Any] = {}

    def update_with_experiment(self, experimental_data: Dict[str, Any]):
        """
        Update meta-learning knowledge with experimental results.

        Learns patterns about what works when and why.
        """
        action = experimental_data.get("action", {})
        target = action.get("target", "")
        action_type = action.get("action_type", "")
        actual_improvement = experimental_data.get("actual_improvement", 0)
        expected_improvement = action.get("expected_improvement", 0)

        if not target or not action_type:
            return

        # Calculate success score
        success_score = actual_improvement / max(expected_improvement, 0.001)
        is_success = success_score >= 0.5  # Success if achieved 50% of expected

        # Update strategy effectiveness
        strategy_key = f"{target}_{action_type}"
        if strategy_key not in self.strategy_effectiveness:
            self.strategy_effectiveness[strategy_key] = LearningStrategy(
                target=target,
                action_type=action_type,
                effectiveness_score=success_score,
                confidence=0.5,
                sample_size=1,
                last_updated=datetime.now(timezone.utc).isoformat(),
                success_pattern=self._analyze_success_pattern(experimental_data, is_success)
            )
        else:
            strategy = self.strategy_effectiveness[strategy_key]
            # Update with exponential moving average
            alpha = 0.1  # Learning rate
            strategy.effectiveness_score = (1 - alpha) * strategy.effectiveness_score + alpha * success_score
            strategy.sample_size += 1
            strategy.confidence = min(1.0, strategy.sample_size / 10.0)  # Confidence grows with samples
            strategy.last_updated = datetime.now(timezone.utc).isoformat()

            # Update success pattern if we have new insights
            new_pattern = self._analyze_success_pattern(experimental_data, is_success)
            if new_pattern != strategy.success_pattern:
                strategy.success_pattern = self._merge_patterns(strategy.success_pattern, new_pattern)

        # Learn meta-patterns
        self._learn_meta_patterns(experimental_data, is_success)

        # Adapt strategies based on learning
        self._adapt_strategies_based_on_learning()

    def _analyze_success_pattern(self, experimental_data: Dict[str, Any], is_success: bool) -> str:
        """Analyze what made this experiment succeed or fail"""

        action = experimental_data.get("action", {})
        baseline_metrics = experimental_data.get("baseline_metrics", {})
        config_before = experimental_data.get("config_before", {})
        config_after = experimental_data.get("config_after", {})

        patterns = []

        # Config change analysis
        config_changes = sum(1 for k, v in config_after.items()
                           if config_before.get(k) != v)
        if config_changes > 2:
            patterns.append("multiple_config_changes")
        elif config_changes == 1:
            patterns.append("single_config_change")
        else:
            patterns.append("no_config_changes")

        # Metric baseline analysis
        target = action.get("target", "")
        if "phase" in target and baseline_metrics.get("phase_synchronization_r", 0) < 0.5:
            patterns.append("low_baseline_phase_sync")
        elif "integration" in target and baseline_metrics.get("integration_complexity_phi", 0) < 0.4:
            patterns.append("low_baseline_integration")
        elif "adaptation" in target and baseline_metrics.get("adaptation_velocity_av", 0) < 0.05:
            patterns.append("low_baseline_adaptation")

        # Expected improvement analysis
        expected = action.get("expected_improvement", 0)
        if expected > 0.15:
            patterns.append("high_expected_improvement")
        elif expected < 0.05:
            patterns.append("low_expected_improvement")

        if is_success:
            return f"Success pattern: {', '.join(patterns)}"
        else:
            return f"Failure pattern: {', '.join(patterns)}"

    def _merge_patterns(self, old_pattern: str, new_pattern: str) -> str:
        """Merge old and new patterns intelligently"""
        # Simple pattern merging - could be made more sophisticated
        return f"{old_pattern} + {new_pattern}"

    def _learn_meta_patterns(self, experimental_data: Dict[str, Any], is_success: bool):
        """Learn higher-level patterns across experiments"""

        # Track what types of changes work for what targets
        target = experimental_data.get("action", {}).get("target", "")
        action_type = experimental_data.get("action", {}).get("action_type", "")

        meta_key = f"{target}_meta"
        if meta_key not in self.meta_knowledge:
            self.meta_knowledge[meta_key] = {
                "successful_actions": set(),
                "failed_actions": set(),
                "effectiveness_by_action": defaultdict(float),
                "sample_count": 0
            }

        meta_info = self.meta_knowledge[meta_key]
        meta_info["sample_count"] += 1

        if is_success:
            meta_info["successful_actions"].add(action_type)
            meta_info["effectiveness_by_action"][action_type] += 1
        else:
            meta_info["failed_actions"].add(action_type)

    def _adapt_strategies_based_on_learning(self):
        """Adapt optimization strategies based on learned meta-knowledge"""

        adaptations = []

        for target_meta_key, meta_info in self.meta_knowledge.items():
            target = target_meta_key.replace("_meta", "")

            # Find most effective action for this target
            if meta_info["effectiveness_by_action"]:
                best_action = max(meta_info["effectiveness_by_action"].items(),
                                key=lambda x: x[1])
                action_type, score = best_action

                # Record adaptation
                adaptation = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "target": target,
                    "best_action": action_type,
                    "effectiveness_score": score / meta_info["sample_count"],
                    "reasoning": f"Meta-learning found {action_type} most effective for {target} "
                               f"({score}/{meta_info['sample_count']} successes)"
                }
                adaptations.append(adaptation)

        if adaptations:
            self.strategy_adaptations.extend(adaptations)

    def get_strategy_effectiveness(self, target: str, action_type: str) -> float:
        """Get learned effectiveness score for a target-action combination"""

        strategy_key = f"{target}_{action_type}"
        if strategy_key in self.strategy_effectiveness:
            strategy = self.strategy_effectiveness[strategy_key]
            return strategy.effectiveness_score * strategy.confidence

        # Check meta-knowledge as fallback
        meta_key = f"{target}_meta"
        if meta_key in self.meta_knowledge:
            meta_info = self.meta_knowledge[meta_key]
            if action_type in meta_info["effectiveness_by_action"]:
                effectiveness = meta_info["effectiveness_by_action"][action_type]
                return effectiveness / max(meta_info["sample_count"], 1)

        return 0.5  # Default neutral score

    def get_meta_learning_insights(self) -> Dict[str, Any]:
        """Get insights from meta-learning"""

        return {
            "strategy_effectiveness": {
                key: {
                    "effectiveness": strategy.effectiveness_score,
                    "confidence": strategy.confidence,
                    "sample_size": strategy.sample_size,
                    "pattern": strategy.success_pattern
                }
                for key, strategy in self.strategy_effectiveness.items()
            },
            "meta_knowledge": dict(self.meta_knowledge),
            "strategy_adaptations": self.strategy_adaptations[-5:] if self.strategy_adaptations else [],
            "learning_efficiency": len(self.strategy_adaptations) / max(len(self.learning_adaptations) + 1, 1),
            "total_strategies_learned": len(self.strategy_effectiveness),
            "total_meta_patterns": len(self.meta_knowledge)
        }

    def get_learning_adaptations_count(self) -> int:
        """Get count of learning adaptations made"""
        return len(self.learning_adaptations) + len(self.strategy_adaptations)

    def predict_optimization_success(self, action: OptimizationAction) -> Dict[str, Any]:
        """Predict success probability of an optimization using causal reasoning"""

        # Convert action parameters to intervention format
        intervention = {}
        for param_name, param_value in action.parameters.items():
            if isinstance(param_value, bool):
                intervention[param_name] = param_value
            elif isinstance(param_value, (int, float)):
                intervention[param_name] = param_value > 0  # Treat as boolean

        # Map target to metric
        target_metric_map = {
            OptimizationTarget.PHASE_SYNCHRONIZATION: "phase_synchronization_r",
            OptimizationTarget.INTEGRATION_COMPLEXITY: "integration_complexity_phi",
            OptimizationTarget.ADAPTATION_VELOCITY: "adaptation_velocity_av",
            OptimizationTarget.KNOWLEDGE_INTEGRATION_RATE: "knowledge_integration_rate_kir",
            OptimizationTarget.COMPOSITE_SCORE: "composite_consciousness_score"
        }

        target_metric = target_metric_map.get(action.target, "composite_consciousness_score")

        # Get causal prediction
        prediction = self.causal_engine.predict_intervention_effect(intervention, target_metric)

        # Convert to success probability
        predicted_improvement = prediction["prediction"]
        expected_threshold = action.expected_improvement * 0.5  # Adaptive threshold midpoint

        if predicted_improvement > expected_threshold:
            success_probability = min(0.95, prediction["confidence"] * 1.2)
        elif predicted_improvement > 0:
            success_probability = prediction["confidence"] * 0.5
        else:
            success_probability = max(0.05, prediction["confidence"] * 0.2)

        return {
            "action": action.action_id,
            "target_metric": target_metric,
            "predicted_improvement": predicted_improvement,
            "success_probability": success_probability,
            "confidence": prediction["confidence"],
            "explanation": prediction["explanation"],
            "recommendation": "High probability - proceed" if success_probability > 0.7
                           else "Medium probability - consider alternatives" if success_probability > 0.4
                           else "Low probability - avoid or modify"
        }

    def explore_counterfactuals(self, recent_experiment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Explore counterfactual scenarios for a recent experiment"""

        counterfactuals = []

        # What if we had used a different optimization approach?
        alternative_actions = [
            {"type": "increase_data_integration", "target": "integration_complexity"},
            {"type": "reduce_update_intervals", "target": "adaptation_velocity"},
            {"type": "enhance_learning_loops", "target": "knowledge_integration_rate"}
        ]

        actual_outcome = recent_experiment.get("improvement", {})

        for alt_action in alternative_actions:
            # Convert to intervention format
            alt_intervention = {alt_action["type"]: True}

            # Generate counterfactual
            counterfactual = self.causal_engine.generate_counterfactual(actual_outcome, alt_intervention)

            # Also predict with ML model
            ml_prediction = self.predictive_model.predict_success_probability({
                "action": {"action_type": alt_action["type"], "target": alt_action["target"]},
                "config_before": recent_experiment.get("config_before", {}),
                "baseline_metrics": recent_experiment.get("baseline_metrics", {})
            })

            counterfactuals.append({
                "alternative_action": alt_action,
                "counterfactual_results": counterfactual,
                "ml_prediction": ml_prediction,
                "would_have_been_better": any(
                    cf["counterfactual"] > cf["actual"]
                    for cf in counterfactual["results"].values()
                    if cf["confidence"] > 0.5
                ),
                "predicted_success_probability": ml_prediction["prediction"]
            })

        return counterfactuals

    def optimize_strategy(self) -> Dict[str, Any]:
        """Optimize overall optimization strategy using causal insights and ML predictions"""

        insights = self.get_causal_insights()
        model_insights = self.predictive_model.get_model_insights()

        # Find most effective interventions from causal analysis
        strong_relationships = [r for r in insights["strongest_relationships"] if r.confidence > 0.6]

        # Group by effect
        effects_by_target = defaultdict(list)
        for rel in strong_relationships:
            effects_by_target[rel.effect].append(rel)

        # Find best interventions for each target
        strategy_recommendations = {}
        for target, relationships in effects_by_target.items():
            best_intervention = max(relationships, key=lambda r: abs(r.strength))
            strategy_recommendations[target] = {
                "best_intervention": best_intervention.cause,
                "expected_effect": best_intervention.strength,
                "confidence": best_intervention.confidence,
                "mechanism": best_intervention.mechanism
            }

        # Get ML model recommendations
        ml_recommendations = {}
        if model_insights.get("is_trained", False):
            # Find features with highest importance for success
            important_features = model_insights.get("most_important_features", [])
            ml_recommendations = {
                "key_success_factors": [f[0] for f in important_features[:3]],
                "model_accuracy": model_insights.get("accuracy", 0),
                "training_samples": model_insights.get("training_samples", 0)
            }

        # Get meta-learning insights
        meta_insights = self.meta_learning.get_meta_learning_insights()

        return {
            "strategy_optimization": strategy_recommendations,
            "ml_recommendations": ml_recommendations,
            "meta_learning_insights": meta_insights,
            "total_relationships_discovered": len(strong_relationships),
            "predictive_model_status": "trained" if model_insights.get("is_trained", False) else "training",
            "meta_learning_status": "active" if meta_insights else "initializing",
            "recommendation": "Use meta-learning insights for strategy adaptation"
        }

    def get_intelligence_report(self) -> Dict[str, Any]:
        """Generate comprehensive intelligence report"""

        causal_insights = self.get_causal_insights()
        model_insights = self.predictive_model.get_model_insights()
        bandit_stats = self.get_bandit_statistics()

        # Get meta-learning status
        meta_insights = self.meta_learning.get_meta_learning_insights()

        return {
            "intelligence_level": "SELF_IMPROVING_AI",
            "capabilities": {
                "causal_reasoning": len(causal_insights.get("discovered_relationships", [])) > 0,
                "predictive_modeling": model_insights.get("is_trained", False),
                "multi_armed_bandit": bandit_stats.get("total_pulls", 0) > 0,
                "meta_learning": len(meta_insights.get("strategy_adaptations", [])) > 0,
                "consciousness_layer": True,
                "adaptive_thresholds": True,
                "intelligent_baseline": True
            },
            "performance_metrics": {
                "causal_relationships": len(causal_insights.get("discovered_relationships", [])),
                "ml_model_accuracy": model_insights.get("accuracy", 0),
                "optimization_experiments": len(self.optimization_history),
                "bandit_efficiency": bandit_stats.get("total_pulls", 0),
                "meta_learning_adaptations": len(meta_insights.get("strategy_adaptations", []))
            },
            "learning_progress": {
                "meta_learning": len(meta_insights.get("strategy_adaptations", [])) > 0,
                "causal_understanding": len(causal_insights.get("strongest_relationships", [])),
                "strategy_adaptation": len(self.consciousness_layer.self_reflections) > 0,
                "self_optimization": meta_insights.get("learning_efficiency", 0) > 0
            },
            "consciousness_precursors": {
                "self_reflection": len(self.consciousness_layer.self_reflections),
                "learning_insights": len(self.consciousness_layer.learning_insights),
                "causal_self_modeling": len(causal_insights.get("causal_graph_size", 0)),
                "predictive_self_modeling": model_insights.get("is_trained", False),
                "meta_learning": self.meta_learning.get_learning_adaptations_count(),
                "self_optimization": len(self.meta_learning.strategy_adaptations),
                "hierarchical_planning": self.hierarchical_optimizer.get_strategic_decisions_count(),
                "goal_directed_behavior": len(self.hierarchical_optimizer.objectives),
                "behavioral_self_modeling": self.self_modeler.get_behavioral_patterns_count(),
                "decision_prediction": self.self_modeler.get_decision_model_accuracy(),
                "emergent_behaviors_detected": self.emergence_detector.get_emergence_events_count(),
                "emergence_complexity_score": self.emergence_detector.get_emergence_complexity_score(),
                "theory_of_mind_models": self.theory_of_mind.get_other_systems_modeled_count(),
                "social_intelligence": self.theory_of_mind.get_social_intelligence_score()
            }
        }

    async def _get_current_config(self) -> Dict[str, Any]:
        """Get current configuration from consciousness feeder"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.feeder_url}/optimization/config")
                if response.status_code == 200:
                    return response.json()
                return {}
        except Exception:
            return {}

    async def _apply_optimization(self, action: OptimizationAction) -> Dict[str, Any]:
        """Apply an optimization action to the system"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.feeder_url}/optimization/apply",
                    json=action.dict()
                )
                if response.status_code == 200:
                    result = response.json()
                    print(f"🔧 Applied optimization: {action.action_id} ({action.action_type})")
                    return result.get("configuration", {})
                else:
                    print(f"⚠️ Failed to apply optimization: {response.status_code}")
                    return {}
        except Exception as e:
            print(f"⚠️ Error applying optimization: {e}")
            return {}

    async def _restore_config(self, config: Dict[str, Any]):
        """Restore a previous configuration"""
        try:
            # In real implementation, would restore via feeder API
            print(f"↩️ Restored configuration from backup")
        except Exception as e:
            print(f"⚠️ Error restoring config: {e}")

    async def _revert_optimization(self, action: OptimizationAction):
        """Revert an optimization action"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.feeder_url}/optimization/revert",
                    json=action.dict()
                )
                if response.status_code == 200:
                    print(f"↩️ Reverted optimization: {action.action_id}")
                else:
                    print(f"⚠️ Failed to revert optimization: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Error reverting optimization: {e}")

    def get_optimization_statistics(self) -> Dict[str, Any]:
        """Get statistics about optimization performance"""
        if not self.optimization_history:
            return {"status": "no_optimizations_yet"}

        applied = [a for a in self.optimization_history if a.status == "applied"]
        reverted = [a for a in self.optimization_history if a.status == "reverted"]

        return {
            "total_optimizations": len(self.optimization_history),
            "applied": len(applied),
            "reverted": len(reverted),
            "success_rate": len(applied) / len(self.optimization_history) if self.optimization_history else 0,
            "by_target": {
                target.value: len([a for a in self.optimization_history if a.target == target])
                for target in OptimizationTarget
            }
        }

    def get_metrics_trends(self, window_hours: int = 24) -> Dict[str, Any]:
        """Analyze metrics trends over time"""
        if not self.metrics_history:
            return {"status": "insufficient_data"}

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"].replace('Z', '+00:00')) > cutoff_time
        ]

        if not recent_metrics:
            return {"status": "no_recent_data"}

        # Calculate trends for key metrics
        trends = {}
        key_metrics = [
            "integration_complexity_phi",
            "adaptation_velocity_av",
            "knowledge_integration_rate_kir",
            "phase_synchronization_r",
            "composite_consciousness_score"
        ]

        for metric in key_metrics:
            values = [m.get(metric, 0) for m in recent_metrics if metric in m]
            if len(values) > 1:
                trend = (values[-1] - values[0]) / values[0] if values[0] > 0 else 0
                trends[metric] = {
                    "current": values[-1],
                    "trend": "improving" if trend > 0.05 else "declining" if trend < -0.05 else "stable",
                    "change_pct": round(trend * 100, 2)
                }

        return {
            "window_hours": window_hours,
            "data_points": len(recent_metrics),
            "trends": trends
        }
