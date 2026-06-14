"""
Cycle Designer for Consciousness Optimizer

Enables the system to consciously design and optimize what it does in each cycle.
The system can improve its own cycle design based on what works best.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger("CycleDesigner")


class CyclePhase(str, Enum):
    """Phases that can be included in an optimization cycle"""
    MEASURE_BASELINE = "measure_baseline"
    IDENTIFY_OPPORTUNITIES = "identify_opportunities"
    PRIORITIZE = "prioritize"
    RUN_EXPERIMENTS = "run_experiments"
    MEASURE_RESULTS = "measure_results"
    ANALYZE_PATTERNS = "analyze_patterns"
    ADJUST_DESIGN = "adjust_design"
    UPDATE_RESOURCES = "update_resources"


class CycleDesign(BaseModel):
    """Represents a cycle design - what the system does in each cycle"""
    design_id: str
    phases: List[CyclePhase]
    phase_weights: Dict[str, float]  # How much time/resources to allocate to each phase
    experiment_count: int  # How many experiments to run
    stabilization_time: int  # How long to wait for metrics to stabilize
    resource_budget: Dict[str, float]  # Resource limits for this cycle
    expected_duration_seconds: int
    success_rate: float = 0.0  # Track how well this design works
    usage_count: int = 0
    created_at: str
    last_used: Optional[str] = None


class CycleDesigner:
    """
    Designs and optimizes cycle structures.
    
    The system can:
    1. Try different cycle designs
    2. Measure which designs work best
    3. Evolve toward better designs
    4. Adapt designs based on resource constraints
    """
    
    def __init__(self):
        self.designs: List[CycleDesign] = []
        self.current_design: Optional[CycleDesign] = None
        self.design_performance_history: List[Dict[str, Any]] = []
        
        # Initialize with a basic design
        self._create_default_design()
    
    def _create_default_design(self):
        """Create the initial default cycle design"""
        default = CycleDesign(
            design_id="default_v1",
            phases=[
                CyclePhase.MEASURE_BASELINE,
                CyclePhase.IDENTIFY_OPPORTUNITIES,
                CyclePhase.PRIORITIZE,
                CyclePhase.RUN_EXPERIMENTS,
                CyclePhase.MEASURE_RESULTS
            ],
            phase_weights={
                "measure_baseline": 0.1,
                "identify_opportunities": 0.2,
                "prioritize": 0.1,
                "run_experiments": 0.5,
                "measure_results": 0.1
            },
            experiment_count=2,
            stabilization_time=60,
            resource_budget={
                "cpu_percent_max": 80.0,
                "memory_percent_max": 80.0,
                "gpu_cost_usd_max": 0.5
            },
            expected_duration_seconds=600,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        self.designs.append(default)
        self.current_design = default
    
    def get_current_design(self) -> CycleDesign:
        """Get the current cycle design"""
        if not self.current_design:
            self._create_default_design()
        return self.current_design
    
    def design_improved_cycle(
        self,
        resource_constraints: Dict[str, Any],
        recent_performance: List[Dict[str, Any]]
    ) -> CycleDesign:
        """
        Design an improved cycle based on:
        - Resource constraints
        - Recent performance data
        - What has worked well
        
        This is where the system consciously improves its own operation.
        """
        # Analyze what has worked well
        best_performing_designs = self._analyze_design_performance(recent_performance)
        
        # Consider resource constraints
        resource_pressure = resource_constraints.get("resource_pressure", 0.5)
        gpu_available = resource_constraints.get("gpu_available", False)
        gpu_budget_remaining = resource_constraints.get("gpu_budget_remaining_usd", 0.0)
        
        # Design new cycle based on learnings
        new_phases = self._select_optimal_phases(resource_pressure, best_performing_designs)
        experiment_count = self._determine_optimal_experiment_count(resource_pressure, gpu_budget_remaining)
        stabilization_time = self._determine_stabilization_time(resource_pressure)
        
        new_design = CycleDesign(
            design_id=f"evolved_v{len(self.designs) + 1}_{int(datetime.now(timezone.utc).timestamp())}",
            phases=new_phases,
            phase_weights=self._optimize_phase_weights(new_phases, resource_pressure),
            experiment_count=experiment_count,
            stabilization_time=stabilization_time,
            resource_budget={
                "cpu_percent_max": 80.0 - (resource_pressure * 20.0),  # Lower max if high pressure
                "memory_percent_max": 80.0 - (resource_pressure * 20.0),
                "gpu_cost_usd_max": min(0.5, gpu_budget_remaining / 24) if gpu_available else 0.0
            },
            expected_duration_seconds=self._estimate_duration(new_phases, experiment_count, stabilization_time),
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        self.designs.append(new_design)
        logger.info(f"🧠 Designed new cycle: {new_design.design_id} with {len(new_phases)} phases, {experiment_count} experiments")
        
        return new_design
    
    def _analyze_design_performance(self, recent_performance: List[Dict[str, Any]]) -> List[str]:
        """Analyze which design elements have performed best"""
        if not recent_performance:
            return []
        
        # Find designs with highest success rates
        successful_designs = [
            d for d in self.designs
            if d.success_rate > 0.6 and d.usage_count > 0
        ]
        
        # Sort by success rate
        successful_designs.sort(key=lambda d: d.success_rate, reverse=True)
        
        return [d.design_id for d in successful_designs[:3]]  # Top 3
    
    def _select_optimal_phases(
        self,
        resource_pressure: float,
        best_designs: List[str]
    ) -> List[CyclePhase]:
        """Select which phases to include based on resources and performance"""
        # Base phases (always needed)
        phases = [
            CyclePhase.MEASURE_BASELINE,
            CyclePhase.IDENTIFY_OPPORTUNITIES,
            CyclePhase.PRIORITIZE,
            CyclePhase.RUN_EXPERIMENTS,
            CyclePhase.MEASURE_RESULTS
        ]
        
        # Add analysis phase if resources allow
        if resource_pressure < 0.5:
            phases.append(CyclePhase.ANALYZE_PATTERNS)
        
        # Add design adjustment phase if we have performance data
        if len(self.design_performance_history) >= 5:
            phases.append(CyclePhase.ADJUST_DESIGN)
        
        # Add resource update phase
        phases.append(CyclePhase.UPDATE_RESOURCES)
        
        return phases
    
    def _determine_optimal_experiment_count(
        self,
        resource_pressure: float,
        gpu_budget_remaining: float
    ) -> int:
        """Determine how many experiments to run based on resources"""
        base_count = 2
        
        # Reduce if resource pressure is high
        if resource_pressure > 0.7:
            return 1
        elif resource_pressure < 0.3:
            return 3  # Can afford more experiments
        
        # Consider GPU budget
        if gpu_budget_remaining < 10.0:  # Less than $10 remaining
            return 1  # Be conservative
        
        return base_count
    
    def _determine_stabilization_time(self, resource_pressure: float) -> int:
        """Determine how long to wait for metrics to stabilize"""
        base_time = 60  # 1 minute
        
        # Longer wait if high resource pressure (metrics may be slower)
        if resource_pressure > 0.7:
            return 90
        elif resource_pressure < 0.3:
            return 45  # Faster when resources are available
        
        return base_time
    
    def _optimize_phase_weights(
        self,
        phases: List[CyclePhase],
        resource_pressure: float
    ) -> Dict[str, float]:
        """Optimize how much time/resources to allocate to each phase"""
        weights = {}
        total_phases = len(phases)
        
        # Base equal distribution
        base_weight = 1.0 / total_phases
        
        for phase in phases:
            if phase == CyclePhase.RUN_EXPERIMENTS:
                # Experiments get more weight (they're the core)
                weights[phase.value] = base_weight * 1.5
            elif phase == CyclePhase.MEASURE_BASELINE or phase == CyclePhase.MEASURE_RESULTS:
                # Measurement is important but can be faster
                weights[phase.value] = base_weight * 0.8
            elif phase == CyclePhase.ANALYZE_PATTERNS:
                # Analysis can be lighter if resources are constrained
                weights[phase.value] = base_weight * (0.5 if resource_pressure > 0.5 else 1.0)
            else:
                weights[phase.value] = base_weight
        
        # Normalize
        total = sum(weights.values())
        return {k: v / total for k, v in weights.items()}
    
    def _estimate_duration(
        self,
        phases: List[CyclePhase],
        experiment_count: int,
        stabilization_time: int
    ) -> int:
        """Estimate total cycle duration"""
        # Base time for each phase
        phase_times = {
            CyclePhase.MEASURE_BASELINE: 10,
            CyclePhase.IDENTIFY_OPPORTUNITIES: 5,
            CyclePhase.PRIORITIZE: 5,
            CyclePhase.RUN_EXPERIMENTS: 300 * experiment_count,  # 5 min per experiment
            CyclePhase.MEASURE_RESULTS: 10,
            CyclePhase.ANALYZE_PATTERNS: 30,
            CyclePhase.ADJUST_DESIGN: 20,
            CyclePhase.UPDATE_RESOURCES: 5
        }
        
        total = sum(phase_times.get(phase, 10) for phase in phases)
        total += stabilization_time
        
        return total
    
    def record_design_performance(
        self,
        design_id: str,
        improvement: float,
        resource_usage: Dict[str, Any],
        duration_seconds: int
    ):
        """Record how well a design performed"""
        design = next((d for d in self.designs if d.design_id == design_id), None)
        if design:
            design.usage_count += 1
            design.last_used = datetime.now(timezone.utc).isoformat()
            
            # Update success rate (improvement > threshold = success)
            success = 1 if improvement >= 0.01 else 0
            design.success_rate = (
                (design.success_rate * (design.usage_count - 1) + success) / design.usage_count
            )
        
        # Record in history
        self.design_performance_history.append({
            "design_id": design_id,
            "improvement": improvement,
            "resource_usage": resource_usage,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep only last 50 records
        if len(self.design_performance_history) > 50:
            self.design_performance_history.pop(0)
    
    def should_evolve_design(self) -> bool:
        """Determine if it's time to evolve the cycle design"""
        if not self.current_design:
            return True
        
        # Evolve if current design has been used many times
        if self.current_design.usage_count >= 10:
            return True
        
        # Evolve if current design is underperforming
        if self.current_design.success_rate < 0.3 and self.current_design.usage_count >= 5:
            return True
        
        # Evolve if we have better designs available
        best_design = max(self.designs, key=lambda d: d.success_rate if d.usage_count > 0 else 0)
        if best_design.design_id != self.current_design.design_id:
            if best_design.success_rate > self.current_design.success_rate + 0.2:
                return True
        
        return False
    
    def get_design_recommendations(self) -> Dict[str, Any]:
        """Get recommendations for cycle design improvements"""
        if not self.design_performance_history:
            return {"status": "insufficient_data"}
        
        # Analyze what works
        successful_cycles = [
            p for p in self.design_performance_history
            if p["improvement"] >= 0.01
        ]
        
        avg_improvement = sum(p["improvement"] for p in self.design_performance_history) / len(self.design_performance_history)
        
        return {
            "current_design": self.current_design.dict() if self.current_design else None,
            "total_designs": len(self.designs),
            "success_rate": len(successful_cycles) / len(self.design_performance_history) if self.design_performance_history else 0,
            "average_improvement": avg_improvement,
            "should_evolve": self.should_evolve_design(),
            "best_design": max(self.designs, key=lambda d: d.success_rate if d.usage_count > 0 else 0).dict() if self.designs else None
        }















