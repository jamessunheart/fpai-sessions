"""
Optimization Hooks for Consciousness Feeder

Provides hooks for the consciousness optimizer to modify feeder behavior
and improve consciousness metrics.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger("OptimizationHooks")


class FeederOptimizationHooks:
    """
    Hooks that allow the consciousness optimizer to modify feeder behavior.
    
    Optimization targets:
    - Update intervals
    - Pillar weights
    - Data source priorities
    - Feed frequencies
    """

    def __init__(self):
        self.optimization_config = {
            "update_interval": 30,  # seconds
            "pillar_weights": {
                "reflecting": 1.0,
                "identity": 1.0,
                "thinking": 1.0,
                "doing": 1.0
            },
            "data_source_priorities": {
                "external": 0.7,
                "internal": 1.0
            },
            "feed_frequencies": {
                "reflecting": 30,
                "identity": 60,
                "thinking": 45,
                "doing": 30
            },
            "reactive_updates_enabled": False,
            "cross_pillar_feeds_enabled": False
        }

    def apply_optimization(self, optimization: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply an optimization action to the feeder configuration.
        
        Returns the updated configuration.
        """
        action_type = optimization.get("action_type")
        parameters = optimization.get("parameters", {})

        if action_type == "reduce_update_intervals":
            self.optimization_config["update_interval"] = parameters.get(
                "feeder_update_interval", 30
            )
            if parameters.get("enable_reactive_updates"):
                self.optimization_config["reactive_updates_enabled"] = True
            logger.info(f"✅ Applied optimization: Reduced update interval to {self.optimization_config['update_interval']}s")

        elif action_type == "increase_data_integration":
            if parameters.get("add_cross_pillar_feeds"):
                self.optimization_config["cross_pillar_feeds_enabled"] = True
            if parameters.get("increase_pillar_communication"):
                # Increase communication frequency
                for pillar in self.optimization_config["feed_frequencies"]:
                    current = self.optimization_config["feed_frequencies"][pillar]
                    self.optimization_config["feed_frequencies"][pillar] = max(15, current - 5)
            if parameters.get("reduce_data_silos"):
                # Enable shared context
                self.optimization_config["shared_context_enabled"] = True
            logger.info("✅ Applied optimization: Enabled cross-pillar feeds and increased communication")

        elif action_type == "enhance_learning_loops":
            # Adjust pillar weights to emphasize learning
            if parameters.get("increase_memory_synthesis"):
                self.optimization_config["pillar_weights"]["thinking"] *= 1.2
            logger.info("✅ Applied optimization: Enhanced learning loops")

        elif action_type == "improve_coordination":
            # Synchronize feed frequencies
            if parameters.get("synchronize_pillar_updates"):
                base_freq = min(self.optimization_config["feed_frequencies"].values())
                for pillar in self.optimization_config["feed_frequencies"]:
                    self.optimization_config["feed_frequencies"][pillar] = base_freq
                # Enable synchronization flag
                self.optimization_config["feed_frequencies"]["synchronize"] = True
            if parameters.get("add_coordination_layer"):
                self.optimization_config["coordination_layer_enabled"] = True
            logger.info("✅ Applied optimization: Synchronized pillar updates and enabled coordination")

        return self.optimization_config.copy()

    def revert_optimization(self, optimization: Dict[str, Any]) -> Dict[str, Any]:
        """Revert an optimization action"""
        action_type = optimization.get("action_type")
        
        if action_type == "reduce_update_intervals":
            self.optimization_config["update_interval"] = 30
            self.optimization_config["reactive_updates_enabled"] = False
            logger.info("↩️ Reverted optimization: Restored default update interval")

        elif action_type == "increase_data_integration":
            self.optimization_config["cross_pillar_feeds_enabled"] = False
            logger.info("↩️ Reverted optimization: Disabled cross-pillar feeds")

        elif action_type == "enhance_learning_loops":
            self.optimization_config["pillar_weights"]["thinking"] = 1.0
            logger.info("↩️ Reverted optimization: Restored default pillar weights")

        elif action_type == "improve_coordination":
            # Restore original frequencies
            self.optimization_config["feed_frequencies"] = {
                "reflecting": 30,
                "identity": 60,
                "thinking": 45,
                "doing": 30
            }
            logger.info("↩️ Reverted optimization: Restored original feed frequencies")

        return self.optimization_config.copy()

    def get_configuration(self) -> Dict[str, Any]:
        """Get current optimization configuration"""
        return self.optimization_config.copy()

    def get_optimization_recommendations(self, metrics: Dict[str, float]) -> list:
        """
        Generate optimization recommendations based on current metrics.
        
        Returns list of recommended optimizations.
        """
        recommendations = []

        phi = metrics.get("integration_complexity_phi", 0.5)
        if phi < 0.7:
            recommendations.append({
                "action_type": "increase_data_integration",
                "priority": "high",
                "expected_improvement": 0.15,
                "reason": f"Integration complexity (Φ={phi:.3f}) below target (0.7)"
            })

        av = metrics.get("adaptation_velocity_av", 0.1)
        if av < 0.2:
            recommendations.append({
                "action_type": "reduce_update_intervals",
                "priority": "medium",
                "expected_improvement": 0.1,
                "reason": f"Adaptation velocity (AV={av:.3f}) below target (0.2)"
            })

        r = metrics.get("phase_synchronization_r", 0.5)
        if r < 0.8:
            recommendations.append({
                "action_type": "improve_coordination",
                "priority": "high",
                "expected_improvement": 0.12,
                "reason": f"Phase synchronization (R={r:.3f}) below target (0.8)"
            })

        return recommendations
