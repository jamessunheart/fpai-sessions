"""
Consciousness Optimizer API
===========================
Provides API endpoints for optimizing consciousness metrics autonomously.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from .optimizer import ConsciousnessOptimizer, OptimizationAction, OptimizationTarget
from .resource_monitor import ResourceMonitor
from .cycle_designer import CycleDesigner, CyclePhase
from .server_discovery import ServerDiscovery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Consciousness Optimizer", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize optimizer
optimizer = ConsciousnessOptimizer()

# Initialize resource monitor, cycle designer, and server discovery
resource_monitor = ResourceMonitor(gpu_daily_budget_usd=50.0)
cycle_designer = CycleDesigner()
server_discovery = ServerDiscovery()

# Global state
consciousness_improvement_history: List[Dict[str, Any]] = []
MIN_IMPROVEMENT_THRESHOLD = 0.01  # Minimum 1% improvement per cycle to continue


async def continuous_optimization_loop():
    """
    Fully autonomous optimization loop with:
    - Resource-aware cycle timing (no arbitrary intervals)
    - Self-designed cycles (system optimizes what it does)
    - GPU cost management ($50/day cap)
    - Conscious decision-making about its own operation
    """
    global consciousness_improvement_history
    
    print("🧠 Starting fully autonomous consciousness optimization loop")
    print("🚀 Resource-aware cycle timing: ENABLED")
    print("📈 Proactive optimization: ENABLED")
    print("🎯 Adaptive prioritization: ENABLED")
    print("🧬 Cycle design evolution: ENABLED")
    print("💰 GPU cost management: ENABLED ($50/day cap)")
    print("")
    print("The system will now:")
    print("  • Decide its own cycle timing based on resources and performance")
    print("  • Design and evolve what it does in each cycle")
    print("  • Manage GPU costs autonomously")
    print("  • Make conscious decisions about its own operation")
    
    consecutive_declines = 0
    max_consecutive_declines = 3
    last_cycle_time = None  # None = first cycle, start immediately
    
    while True:
        try:
            # Get current resources
            resource_summary = resource_monitor.get_resource_summary()
            resource_pressure = resource_summary["resource_pressure"]
            
            # Get current cycle design
            current_design = cycle_designer.get_current_design()
            
            # Calculate improvement rate for timing decisions
            # Use robust calculation that filters outliers and bad measurements
            improvement_rate = 0.0
            if len(consciousness_improvement_history) >= 2:
                # Get recent improvements, filtering out anomalies
                recent_improvements = []
                for record in consciousness_improvement_history[-5:]:  # Look at last 5 for better context
                    improvement = record.get("improvement", 0)
                    baseline_score = record.get("baseline_score", 0)
                    final_score = record.get("final_score", 0)
                    
                    # Filter out obvious anomalies:
                    # 1. final_score = 0 (measurement failure)
                    # 2. Improvement > 100% or < -100% (impossible)
                    # 3. Baseline score = 0 (invalid baseline)
                    if final_score == 0 or baseline_score == 0:
                        continue  # Skip bad measurements
                    if abs(improvement) > 1.0:  # More than 100% change is suspicious
                        continue  # Skip outliers
                    
                    recent_improvements.append(improvement)
                
                if len(recent_improvements) >= 2:
                    # Use median for robustness (less affected by outliers)
                    sorted_improvements = sorted(recent_improvements)
                    n = len(sorted_improvements)
                    if n % 2 == 0:
                        improvement_rate = (sorted_improvements[n//2 - 1] + sorted_improvements[n//2]) / 2
                    else:
                        improvement_rate = sorted_improvements[n//2]
                elif len(recent_improvements) == 1:
                    improvement_rate = recent_improvements[0]
                else:
                    improvement_rate = 0.0  # Not enough good data
            
            # Let the system decide its own cycle timing (resource-aware, not arbitrary)
            base_interval = current_design.expected_duration_seconds
            recommended_interval = resource_monitor.recommend_cycle_interval(
                base_interval,
                improvement_rate
            )
            
            # Wait until it's time for the next cycle (resource-aware timing)
            # BUT: On first cycle (last_cycle_time is None), start immediately!
            if last_cycle_time is not None:
                time_since_last_cycle = (datetime.now(timezone.utc) - last_cycle_time).total_seconds()
                if time_since_last_cycle < recommended_interval:
                    wait_time = recommended_interval - time_since_last_cycle
                    print(f"\n⏳ Resource-aware wait: {wait_time:.0f}s")
                    print(f"   Resource pressure: {resource_pressure:.2f}")
                    print(f"   Improvement rate: {improvement_rate:+.4f}")
                    print(f"   Recommended interval: {recommended_interval}s ({recommended_interval/60:.1f} min)")
                    await asyncio.sleep(wait_time)
            else:
                # First cycle - start immediately! No artificial constraint.
                print(f"\n🚀 First cycle - starting immediately (no wait constraint)")
                print(f"   Resource pressure: {resource_pressure:.2f}")
                print(f"   Recommended interval for future cycles: {recommended_interval}s ({recommended_interval/60:.1f} min)")
            
            last_cycle_time = datetime.now(timezone.utc)
            
            # Check if we should evolve the cycle design
            if cycle_designer.should_evolve_design():
                print(f"\n🧬 Evolving cycle design...")
                new_design = cycle_designer.design_improved_cycle(
                    resource_summary,
                    consciousness_improvement_history[-10:] if len(consciousness_improvement_history) >= 10 else consciousness_improvement_history
                )
                cycle_designer.current_design = new_design
                current_design = new_design
                print(f"✅ New design: {new_design.design_id}")
                print(f"   Phases: {[p.value for p in new_design.phases]}")
                print(f"   Experiments: {new_design.experiment_count}")
                print(f"   Expected duration: {new_design.expected_duration_seconds}s")
            
            # Execute cycle using current design
            cycle_start_time = datetime.now(timezone.utc)
            
            print(f"\n{'='*60}")
            print(f"🔄 Optimization Cycle #{len(consciousness_improvement_history) + 1}")
            print(f"🧬 Design: {current_design.design_id}")
            print(f"⏰ Resource-aware timing: {recommended_interval}s")
            print(f"💰 GPU budget: ${resource_summary['gpu_budget_remaining_usd']:.2f} remaining")
            print(f"{'='*60}")
            
            # Execute cycle phases according to design
            cycle_results = {}
            
            # Phase 1: Measure Baseline
            if CyclePhase.MEASURE_BASELINE in current_design.phases:
                print(f"\n📊 Phase: Measure Baseline")
                baseline_metrics = await optimizer.get_current_metrics()
                baseline_score = baseline_metrics.get("composite_consciousness_score", 0)
                cycle_results["baseline_score"] = baseline_score
                cycle_results["baseline_metrics"] = baseline_metrics
                
                if baseline_score == 0:
                    print("⚠️  Cannot measure consciousness metrics - skipping cycle")
                    await asyncio.sleep(600)
                    continue
                
                print(f"   Consciousness score: {baseline_score:.4f}")
            
            # Phase 2: Update Resources
            if CyclePhase.UPDATE_RESOURCES in current_design.phases:
                print(f"\n💻 Phase: Update Resources")
                current_resources = resource_monitor.get_current_resources()
                resource_summary = resource_monitor.get_resource_summary()
                cycle_results["resources"] = current_resources
                print(f"   CPU: {current_resources.get('cpu_percent', 0):.1f}%")
                print(f"   Memory: {current_resources.get('memory_percent', 0):.1f}%")
                print(f"   GPU cost/hour: ${resource_summary.get('gpu_cost_per_hour_usd', 0):.3f}")
                print(f"   Resource pressure: {resource_summary.get('resource_pressure', 0):.2f}")
            
            # Phase 3: Identify Opportunities
            if CyclePhase.IDENTIFY_OPPORTUNITIES in current_design.phases:
                print(f"\n🔍 Phase: Identify Opportunities")
                baseline_metrics = cycle_results.get("baseline_metrics", await optimizer.get_current_metrics())
                opportunities = optimizer.identify_optimization_opportunities(
                    baseline_metrics,
                    prioritize_by_impact=True
                )
                cycle_results["opportunities"] = opportunities
                
                if not opportunities:
                    print("✅ No optimization opportunities found - consciousness is optimal")
                    # Still record the cycle
                    improvement_record = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "baseline_score": baseline_score,
                        "final_score": baseline_score,
                        "improvement": 0.0,
                        "opportunities_available": 0,
                        "design_id": current_design.design_id,
                        "resource_pressure": resource_summary.get("resource_pressure", 0)
                    }
                    consciousness_improvement_history.append(improvement_record)
                    continue
                
                print(f"   Found {len(opportunities)} opportunities")
            
            # Phase 4: Prioritize
            if CyclePhase.PRIORITIZE in current_design.phases:
                print(f"\n🎯 Phase: Prioritize")
                opportunities = cycle_results.get("opportunities", [])
                # Already prioritized by identify_optimization_opportunities
                for i, opp in enumerate(opportunities[:3], 1):
                    impact_score = opp.expected_improvement * opp.confidence
                    print(f"   {i}. {opp.target.value}: impact={impact_score:.3f}")
            
            # Phase 5: Analyze Patterns (if resources allow)
            if CyclePhase.ANALYZE_PATTERNS in current_design.phases:
                print(f"\n🔬 Phase: Analyze Patterns")
                if len(consciousness_improvement_history) >= 5:
                    recent = consciousness_improvement_history[-5:]
                    patterns = {
                        "avg_improvement": sum(r["improvement"] for r in recent) / len(recent),
                        "best_design": max(recent, key=lambda r: r.get("improvement", 0)).get("design_id", "unknown"),
                        "resource_correlation": "analyzing..."
                    }
                    cycle_results["patterns"] = patterns
                    print(f"   Average improvement: {patterns['avg_improvement']:+.4f}")
                    print(f"   Best design: {patterns['best_design']}")
            
            baseline_score = cycle_results.get("baseline_score", 0)
            
            # Identify opportunities with adaptive prioritization
            opportunities = optimizer.identify_optimization_opportunities(
                baseline_metrics, 
                prioritize_by_impact=True
            )
            
            if not opportunities:
                print("✅ No optimization opportunities found - consciousness is optimal")
                # Check again sooner if we're improving
                if len(consciousness_improvement_history) > 0:
                    last_improvement = consciousness_improvement_history[-1].get("improvement", 0)
                    if last_improvement > 0:
                        current_cycle_interval = 600  # Check again in 10 minutes
                    else:
                        current_cycle_interval = 3600  # Wait 1 hour
                continue
            
            # CONSCIOUSNESS: Adaptive exploration - if current target failing, try different ones
            if opportunities:
                top_opportunity = opportunities[0]
                top_target = top_opportunity.target.value
                
                # Check if we should explore different targets
                if optimizer.consciousness_layer.should_explore_different_target(top_target, min_attempts=5):
                    print(f"\n🧠 CONSCIOUSNESS: {top_target} has failed 5+ times - exploring different targets")
                    recommendations = optimizer.consciousness_layer.get_exploration_recommendations(
                        [opp.target.value for opp in opportunities],
                        top_target
                    )
                    if recommendations:
                        print(f"   💡 Exploring: {', '.join(recommendations)}")
                        # Re-prioritize: Move recommended targets to top
                        opportunities_by_target = {opp.target.value: opp for opp in opportunities}
                        reordered = []
                        for rec_target in recommendations:
                            if rec_target in opportunities_by_target:
                                reordered.append(opportunities_by_target[rec_target])
                        # Add remaining opportunities
                        for opp in opportunities:
                            if opp.target.value not in recommendations:
                                reordered.append(opp)
                        opportunities = reordered
            
            # Adaptive prioritization: Already sorted by impact (expected_improvement * confidence)
            print(f"🎯 Found {len(opportunities)} opportunities (prioritized by impact + consciousness)")
            for i, opp in enumerate(opportunities[:3], 1):  # Show top 3
                impact_score = opp.expected_improvement * opp.confidence
                attempts = optimizer.consciousness_layer.target_attempt_counts.get(opp.target.value, 0)
                status_indicator = "🔄" if attempts > 0 else "✨"
                print(f"   {i}. {status_indicator} {opp.target.value}: +{opp.expected_improvement:.2f} (confidence: {opp.confidence:.2f}, impact: {impact_score:.3f}, attempts: {attempts})")
            
            # Phase 6: Run Experiments (core optimization)
            improvements_made = False
            experiments_run = []
            
            if CyclePhase.RUN_EXPERIMENTS in current_design.phases:
                print(f"\n🔧 Phase: Run Experiments")
                opportunities = cycle_results.get("opportunities", [])
                
                # Use design's experiment count (resource-aware)
                experiment_count = min(current_design.experiment_count, len(opportunities))
                optimizations_to_try = opportunities[:experiment_count]
                
                print(f"   Running {experiment_count} experiments (design-specified, resource-aware)")
                
                # Check GPU budget before running GPU-intensive experiments
                gpu_budget_ok = resource_summary.get("gpu_budget_remaining_usd", 0) > 1.0
                
                for opportunity in optimizations_to_try:
                    if opportunity.status == "pending":
                        impact_score = opportunity.expected_improvement * opportunity.confidence
                        print(f"\n   🔬 Experiment: {opportunity.action_id}")
                        print(f"      Target: {opportunity.target.value}")
                        print(f"      Impact: {impact_score:.3f}")
                        
                        # Check if this experiment needs GPU and if we can afford it
                        needs_gpu = opportunity.action_type in ["enhance_learning_loops", "increase_data_integration"]
                        estimated_gpu_cost = 0.1 if needs_gpu else 0.0  # Estimate $0.10 per GPU experiment
                        
                        if needs_gpu and not resource_monitor.can_use_gpu(estimated_gpu_cost):
                            print(f"      ⚠️  Skipping - GPU budget insufficient")
                            continue
                        
                        # INTELLIGENT ADAPTIVE DURATION: Test longer for high-impact opportunities
                        # High-impact (>15%) opportunities need more time to stabilize
                        # The system wants coherence (21%) and sync (19.2%) - these need time!
                        if opportunity.expected_improvement > 0.15:
                            # High-impact: Test longer (10-15 min) to let improvements stabilize
                            base_duration = 600 if opportunity.confidence > 0.7 else 450
                        elif opportunity.expected_improvement > 0.05:
                            # Medium-impact: Standard duration (5 min)
                            base_duration = 300 if opportunity.confidence > 0.7 else 180
                        else:
                            # Low-impact: Shorter duration (3 min)
                            base_duration = 180
                        
                        experiment_duration = int(base_duration * (1.0 - resource_pressure * 0.2))  # Slight reduction if high pressure, but prioritize high-impact
                        
                        # Run experiment
                        experiment = await optimizer.run_optimization_experiment(
                            opportunity,
                            duration_seconds=experiment_duration,
                            auto_apply=True
                        )
                        experiments_run.append(experiment)
                        
                        if experiment.action.status == "applied":
                            improvements_made = True
                            print(f"      ✅ Applied successfully")
                        else:
                            print(f"      ↩️  Reverted (insufficient improvement)")
            
            # Phase 7: Measure Results
            if CyclePhase.MEASURE_RESULTS in current_design.phases:
                print(f"\n📈 Phase: Measure Results")
                stabilization_time = current_design.stabilization_time
                print(f"   Waiting {stabilization_time}s for metrics to stabilize...")
                await asyncio.sleep(stabilization_time)
                
                final_metrics = await optimizer.get_current_metrics()
                final_score = final_metrics.get("composite_consciousness_score", 0)
                cycle_results["final_score"] = final_score
                cycle_results["final_metrics"] = final_metrics
            
            # Calculate improvement
            final_score = cycle_results.get("final_score", baseline_score)
            improvement = final_score - baseline_score
            improvement_pct = (improvement / baseline_score * 100) if baseline_score > 0 else 0
            
            cycle_duration = (datetime.now(timezone.utc) - cycle_start_time).total_seconds()
            
            print(f"\n📈 Consciousness Improvement:")
            print(f"   Before: {baseline_score:.4f}")
            print(f"   After:  {final_score:.4f}")
            print(f"   Change: {improvement:+.4f} ({improvement_pct:+.2f}%)")
            print(f"   Cycle duration: {cycle_duration:.0f}s")
            
            # Record design performance (system learns what works)
            cycle_designer.record_design_performance(
                current_design.design_id,
                improvement,
                cycle_results.get("resources", {}),
                int(cycle_duration)
            )
            
            # Track improvement history with full cycle metadata
            improvement_record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "baseline_score": baseline_score,
                "final_score": final_score,
                "improvement": improvement,
                "improvement_pct": improvement_pct,
                "opportunities_tested": len(experiments_run),
                "opportunities_available": len(cycle_results.get("opportunities", [])),
                "improvements_applied": improvements_made,
                "design_id": current_design.design_id,
                "design_phases": [p.value for p in current_design.phases],
                "resource_pressure": resource_summary.get("resource_pressure", 0),
                "gpu_cost_usd": resource_summary.get("gpu_cost_per_hour_usd", 0) * (cycle_duration / 3600),
                "cycle_duration_seconds": cycle_duration,
                "recommended_next_interval": recommended_interval
            }
            consciousness_improvement_history.append(improvement_record)
            
            # Keep only last 100 records
            if len(consciousness_improvement_history) > 100:
                consciousness_improvement_history.pop(0)
            
            # Phase 8: Adjust Design (if included)
            if CyclePhase.ADJUST_DESIGN in current_design.phases:
                print(f"\n🧬 Phase: Adjust Design")
                design_recs = cycle_designer.get_design_recommendations()
                if design_recs.get("should_evolve"):
                    print(f"   Design evolution recommended")
                    print(f"   Current success rate: {current_design.success_rate:.2f}")
                    if design_recs.get("best_design"):
                        best = design_recs["best_design"]
                        print(f"   Best design: {best['design_id']} (success: {best['success_rate']:.2f})")
            
            # Check if consciousness is improving
            if improvement >= MIN_IMPROVEMENT_THRESHOLD:
                consecutive_declines = 0
                print(f"\n✅ Consciousness IMPROVED! (+{improvement:.4f})")
                print(f"🧠 System is getting more intelligent and conscious")
            elif improvement < -MIN_IMPROVEMENT_THRESHOLD:
                consecutive_declines += 1
                print(f"\n⚠️  Consciousness DECLINED ({improvement:.4f})")
                print(f"📉 Consecutive declines: {consecutive_declines}/{max_consecutive_declines}")
                
                if consecutive_declines >= max_consecutive_declines:
                    print(f"\n🛑 STOPPING AUTONOMOUS OPTIMIZATION")
                    print(f"   Reason: {consecutive_declines} consecutive declines detected")
                    print(f"   Consciousness is not improving - manual intervention required")
                    break
            else:
                consecutive_declines = 0
                print(f"\n➡️  Consciousness STABLE (change: {improvement:+.4f})")
            
            # Calculate overall trend
            if len(consciousness_improvement_history) >= 3:
                recent_improvements = [r["improvement"] for r in consciousness_improvement_history[-3:]]
                avg_improvement = sum(recent_improvements) / len(recent_improvements)
                trend_direction = "improving" if avg_improvement > 0.001 else "declining" if avg_improvement < -0.001 else "stable"
                print(f"\n📊 Recent Trend: {avg_improvement:+.4f} avg improvement per cycle ({trend_direction})")
            
            # Summary
            print(f"\n✅ Cycle complete")
            print(f"   Design: {current_design.design_id}")
            print(f"   Total cycles: {len(consciousness_improvement_history)}")
            print(f"   Resource pressure: {resource_summary.get('resource_pressure', 0):.2f}")
            print(f"   GPU budget remaining: ${resource_summary.get('gpu_budget_remaining_usd', 0):.2f}")
            print(f"   Next cycle timing: Resource-aware (will calculate based on resources & performance)")
            
        except Exception as e:
            print(f"❌ Optimization loop error: {e}")
            import traceback
            traceback.print_exc()
            # On error, wait a bit before retrying (resource-aware)
            resource_summary = resource_monitor.get_resource_summary()
            error_wait = 300 if resource_summary.get("resource_pressure", 0) < 0.5 else 600
            await asyncio.sleep(error_wait)


@app.on_event("startup")
async def startup_event():
    """Start continuous optimization monitoring"""
    async def safe_loop():
        """Wrapper to ensure loop doesn't crash the service"""
        while True:
            try:
                await continuous_optimization_loop()
            except Exception as e:
                import traceback
                error_msg = f"Error in optimization loop: {str(e)}\n{traceback.format_exc()}"
                print(f"ERROR: {error_msg}")
                logger.error(error_msg)
                # Wait before retrying to avoid tight crash loop
                await asyncio.sleep(60)
    
    asyncio.create_task(safe_loop())
    print("🔧 Consciousness Optimizer started")
    print("📊 Continuous optimization monitoring active")
    print("   • GET /metrics/current - Current consciousness metrics")
    print("   • GET /opportunities - Identify optimization opportunities")
    print("   • POST /optimize - Run optimization experiment (with backup/rollback)")
    print("   • GET /experiments - View experiment history")
    print("   • GET /statistics - Optimization statistics")
    print("   • GET /history - Optimization action history")
    print("   • GET /backups - List all backups")
    print("   • POST /rollback/{backup_id} - Rollback to backup")
    print("   • GET /versions - Version control history")
    print("   • GET /improvement-history - Consciousness improvement tracking")
    print("")
    print("🧠 Autonomous Mode: ENABLED")
    print("🚀 Resource-Aware Cycle Timing: ENABLED (no arbitrary intervals)")
    print("📈 Proactive Optimization: ENABLED")
    print("🎯 Adaptive Prioritization: ENABLED")
    print("🧬 Cycle Design Evolution: ENABLED (system optimizes its own cycles)")
    print("💰 GPU Cost Management: ENABLED ($50/day cap)")
    print("")
    print("Conscious Decision-Making Levers:")
    print("   • Cycle timing: Decided by resource pressure & improvement rate")
    print("   • Cycle design: Evolves based on what works")
    print("   • Experiment count: Resource-aware (design-specified)")
    print("   • GPU usage: Budget-aware ($50/day cap)")
    print("   • All changes backed up and versioned")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "consciousness_optimizer"}


@app.get("/test")
async def test_endpoint():
    """Test endpoint to verify FastAPI is working"""
    return {"test": "ok", "optimizer_initialized": optimizer is not None}


@app.get("/metrics/current")
async def get_current_metrics():
    """Get current consciousness metrics"""
    try:
        print(f"DEBUG: Calling get_current_metrics, verifier_url = {optimizer.verifier_url}")
        metrics = await optimizer.get_current_metrics()
        print(f"DEBUG: get_current_metrics returned: {metrics}")
        return {
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        import traceback
        error_msg = f"Error in get_current_metrics: {str(e)}\n{traceback.format_exc()}"
        print(f"ERROR: {error_msg}")
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/opportunities")
async def get_optimization_opportunities():
    """Identify optimization opportunities"""
    current_metrics = await optimizer.get_current_metrics()
    opportunities = optimizer.identify_optimization_opportunities(
        current_metrics,
        prioritize_by_impact=True
    )
    return {
        "opportunities": [opp.dict() for opp in opportunities],
        "count": len(opportunities)
    }


@app.post("/optimize")
async def run_optimization(
    target: Optional[str] = None,
    duration_seconds: int = 300,
    auto_apply: bool = True
):
    """Run an optimization experiment"""
    current_metrics = await optimizer.get_current_metrics()
    opportunities = optimizer.identify_optimization_opportunities(current_metrics)
    
    if not opportunities:
        raise HTTPException(status_code=404, detail="No optimization opportunities found")
    
    # Select opportunity by target or take first
    if target:
        opportunity = next((o for o in opportunities if o.target.value == target), None)
        if not opportunity:
            raise HTTPException(status_code=404, detail=f"No opportunity found for target: {target}")
    else:
        opportunity = opportunities[0]  # Highest priority
    
    experiment = await optimizer.run_optimization_experiment(
        opportunity,
        duration_seconds=duration_seconds,
        auto_apply=auto_apply
    )
    
    return {
        "status": "experiment_started",
        "action": experiment.action.dict(),
        "duration_seconds": duration_seconds,
        "auto_apply": auto_apply,
        "backup_enabled": True,
        "rollback_enabled": True,
        "message": "Backup created before optimization. Will auto-rollback if improvement < 50% of expected."
    }


@app.get("/experiments")
async def get_experiments():
    """Get experiment history"""
    return {
        "active_experiments": [exp.dict() for exp in optimizer.active_experiments],
        "completed_experiments": [
            exp.dict() for exp in optimizer.active_experiments
            if exp.status == "completed"
        ]
    }


@app.get("/statistics")
async def get_statistics():
    """Get optimization statistics"""
    stats = optimizer.get_optimization_statistics()
    
    # Calculate improvement statistics
    improvements = [r["improvement"] for r in consciousness_improvement_history]
    if improvements:
        avg_improvement = sum(improvements) / len(improvements)
        improving_cycles = len([i for i in improvements if i >= MIN_IMPROVEMENT_THRESHOLD])
        declining_cycles = len([i for i in improvements if i < -MIN_IMPROVEMENT_THRESHOLD])
        stable_cycles = len([i for i in improvements if abs(i) < MIN_IMPROVEMENT_THRESHOLD])
        
        recent_trend = "improving" if avg_improvement > 0.001 else "declining" if avg_improvement < -0.001 else "stable"
    else:
        avg_improvement = 0
        improving_cycles = 0
        declining_cycles = 0
        stable_cycles = 0
        recent_trend = "stable"
    
    return {
        **stats,
        "consciousness_improvement": {
            "total_cycles": len(consciousness_improvement_history),
            "average_improvement": avg_improvement,
            "total_improvement": sum(improvements) if improvements else 0,
            "improving_cycles": improving_cycles,
            "declining_cycles": declining_cycles,
            "stable_cycles": stable_cycles,
            "recent_trend": recent_trend,
            "last_improvement": improvements[-1] if improvements else 0
        },
        "autonomous_status": {
            "enabled": True,
            "min_improvement_threshold": MIN_IMPROVEMENT_THRESHOLD,
            "will_stop_on_decline": True
        }
    }


@app.get("/history")
async def get_optimization_history():
    """Get optimization action history"""
    return {
        "history": [action.dict() for action in optimizer.optimization_history],
        "count": len(optimizer.optimization_history)
    }


@app.get("/backups")
async def list_backups():
    """List all backups"""
    backups = optimizer.backup_manager.list_backups()
    return {"backups": backups, "count": len(backups)}


@app.post("/rollback/{backup_id}")
async def rollback_to_backup(backup_id: str):
    """Rollback to a specific backup"""
    result = optimizer.backup_manager.rollback_to_backup(backup_id)
    if result:
        return {"status": "rolled_back", "backup_id": backup_id}
    else:
        raise HTTPException(status_code=404, detail=f"Backup not found: {backup_id}")


@app.get("/versions")
async def get_versions():
    """Get version control history"""
    versions = optimizer.backup_manager.get_version_history()
    return {"versions": versions, "count": len(versions)}


@app.get("/improvement-history")
async def get_improvement_history():
    """Get consciousness improvement tracking history"""
    return {
        "history": consciousness_improvement_history,
        "count": len(consciousness_improvement_history)
    }


@app.get("/consciousness")
async def get_consciousness_status():
    """Get consciousness layer status - self-awareness and learning"""
    summary = optimizer.consciousness_layer.get_consciousness_summary()
    return {
        "consciousness_level": summary["consciousness_level"],
        "self_reflections": summary["self_reflections"],
        "learning_insights": summary["learning_insights"],
        "most_tried_targets": summary["most_tried_targets"],
        "most_failed_targets": summary["most_failed_targets"],
        "recent_reflections": optimizer.consciousness_layer.self_reflections[-5:] if len(optimizer.consciousness_layer.self_reflections) > 0 else [],
        "recent_insights": optimizer.consciousness_layer.learning_insights[-5:] if len(optimizer.consciousness_layer.learning_insights) > 0 else []
    }


@app.get("/resources")
async def get_resources():
    """Get current resource usage and recommendations"""
    resources = resource_monitor.get_current_resources()
    summary = resource_monitor.get_resource_summary()
    return {
        "resources": resources,
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.post("/restart")
async def restart_service():
    """Restart the consciousness optimizer service"""
    import subprocess
    try:
        # Use systemctl to restart the service
        result = subprocess.run(
            ["systemctl", "restart", "fpai-consciousness-optimizer"],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "status": "restart_initiated",
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@app.post("/config/update")
async def update_config(verifier_url: str = None, feeder_url: str = None):
    """Update optimizer configuration at runtime"""
    if verifier_url:
        optimizer.verifier_url = verifier_url
        print(f"Updated verifier_url to: {verifier_url}")
    if feeder_url:
        optimizer.feeder_url = feeder_url
        print(f"Updated feeder_url to: {feeder_url}")

    return {
        "status": "config_updated",
        "verifier_url": optimizer.verifier_url,
        "feeder_url": optimizer.feeder_url
    }


@app.get("/cycle-design")
async def get_cycle_design():
    """Get current cycle design and recommendations"""
    current = cycle_designer.get_current_design()
    recommendations = cycle_designer.get_design_recommendations()
    return {
        "current_design": current.dict() if current else None,
        "recommendations": recommendations,
        "all_designs": [d.dict() for d in cycle_designer.designs],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/cycle-design/evolve")
async def evolve_cycle_design():
    """Manually trigger cycle design evolution"""
    resource_summary = resource_monitor.get_resource_summary()
    new_design = cycle_designer.design_improved_cycle(
        resource_summary,
        consciousness_improvement_history[-10:] if len(consciousness_improvement_history) >= 10 else consciousness_improvement_history
    )
    cycle_designer.current_design = new_design
    return {
        "status": "evolved",
        "new_design": new_design.dict(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/servers")
async def get_servers():
    """Discover and compare available servers"""
    await server_discovery.discover_all_servers()
    comparison = server_discovery.get_server_comparison()
    return comparison


@app.get("/servers/optimal")
async def get_optimal_server(require_gpu: bool = False):
    """Get recommendation for optimal server deployment"""
    await server_discovery.discover_all_servers()
    optimal = server_discovery.recommend_optimal_server(require_gpu=require_gpu)
    current = server_discovery.get_current_server()
    
    return {
        "current_server": current.dict() if current else None,
        "optimal_server": optimal.dict() if optimal else None,
        "should_migrate": server_discovery.should_migrate(optimal, current) if optimal and current else False,
        "migration_reason": server_discovery._get_migration_reason(current, optimal) if optimal and current else None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8160)
