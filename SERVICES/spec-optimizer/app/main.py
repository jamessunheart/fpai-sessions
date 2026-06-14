"""SPEC Optimizer Service - Main Application"""

import time
import logging
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import (
    UDCHealthResponse,
    UDCCapabilitiesResponse,
    UDCStateResponse,
    UDCDependenciesResponse,
    DependencyStatus,
    UDCMessageRequest,
    UDCMessageResponse,
    OptimizeRequest,
    OptimizeFileRequest,
    BatchOptimizeRequest,
    OptimizationResult,
    BatchOptimizationResult
)
from app.services import OptimizationEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SPEC Optimizer Service",
    description="AI-powered SPEC optimization using Claude API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service state tracking
start_time = time.time()
request_count = 0
error_count = 0
specs_optimized = 0
total_score_before = 0.0
total_score_after = 0.0

# Optimization engine
optimization_engine = OptimizationEngine()


@app.on_event("startup")
async def startup_event():
    """Startup event - register with Registry"""
    logger.info(f"🚀 Starting {settings.service_name} v{settings.service_version}")

    # Check Claude API availability
    if optimization_engine.claude.is_available():
        logger.info("✅ Claude API configured")
    else:
        logger.warning("⚠️ Claude API key not configured")

    # Auto-register with Registry
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{settings.registry_url}/register",
                json={
                    "name": settings.service_name,
                    "id": settings.registry_id,
                    "url": f"http://localhost:{settings.service_port}",
                    "version": settings.service_version,
                    "metadata": {
                        "tier": 0,
                        "category": "quality_assurance",
                        "purpose": "AI-powered SPEC optimization"
                    }
                }
            )
            if response.status_code == 200:
                logger.info(f"✅ Registered with Registry (ID: {settings.registry_id})")
            else:
                logger.warning(f"⚠️ Registry registration failed: {response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ Could not register with Registry: {e}")

    logger.info(f"✅ {settings.service_name} ready on port {settings.service_port}")


# ==================== UDC ENDPOINTS ====================

@app.get("/health", response_model=UDCHealthResponse)
async def health():
    """UDC /health endpoint - Standard compliance"""
    global request_count
    request_count += 1

    # Check Claude API availability
    claude_available = optimization_engine.claude.is_available()

    status = "active" if claude_available else "inactive"

    return UDCHealthResponse(
        status=status,
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/capabilities", response_model=UDCCapabilitiesResponse)
async def capabilities():
    """UDC /capabilities endpoint"""
    global request_count
    request_count += 1

    avg_improvement = 0.0
    if specs_optimized > 0:
        avg_before = total_score_before / specs_optimized
        avg_after = total_score_after / specs_optimized
        avg_improvement = avg_after - avg_before

    return UDCCapabilitiesResponse(
        version=settings.service_version,
        features=[
            "ai_powered_optimization",
            "multi_pass_enhancement",
            "gap_filling",
            "quality_verification_loop",
            "intent_preservation",
            "batch_optimization"
        ],
        dependencies=["claude_api", "spec_verifier", "registry"],
        udc_version="1.0",
        metadata={
            "claude_model": settings.claude_model,
            "optimization_passes": 4,
            "average_score_improvement": round(avg_improvement, 2)
        }
    )


@app.get("/state", response_model=UDCStateResponse)
async def state():
    """UDC /state endpoint"""
    global request_count, error_count, specs_optimized, total_score_before, total_score_after

    uptime = int(time.time() - start_time)

    avg_before = (total_score_before / specs_optimized) if specs_optimized > 0 else 0.0
    avg_after = (total_score_after / specs_optimized) if specs_optimized > 0 else 0.0
    avg_improvement = avg_after - avg_before

    return UDCStateResponse(
        uptime_seconds=uptime,
        requests_total=request_count,
        errors_last_hour=error_count,
        last_restart=datetime.fromtimestamp(start_time).isoformat() + "Z",
        specs_optimized_total=specs_optimized,
        average_score_before=round(avg_before, 2),
        average_score_after=round(avg_after, 2),
        average_improvement=round(avg_improvement, 2),
        active_optimizations=0
    )


@app.get("/dependencies", response_model=UDCDependenciesResponse)
async def dependencies():
    """UDC /dependencies endpoint"""
    global request_count
    request_count += 1

    # Check dependencies
    claude_status = await check_claude_availability()
    verifier_status = await check_verifier_availability()
    registry_status = await check_registry_health()

    required_deps = [
        DependencyStatus(
            name="claude_api",
            status=claude_status["status"],
            version=claude_status.get("version")
        ),
        DependencyStatus(
            name="spec_verifier",
            status=verifier_status["status"],
            url=settings.spec_verifier_url,
            version=verifier_status.get("version")
        ),
        DependencyStatus(
            name="registry",
            status=registry_status["status"],
            url=settings.registry_url,
            version=registry_status.get("version")
        )
    ]

    missing = []
    for dep in required_deps:
        if dep.status != "available":
            missing.append(dep.name)

    return UDCDependenciesResponse(
        required=required_deps,
        optional=[],
        missing=missing
    )


@app.post("/message", response_model=UDCMessageResponse)
async def message(msg: UDCMessageRequest):
    """UDC /message endpoint"""
    global request_count
    request_count += 1

    logger.info(f"📨 Received message from {msg.source}: {msg.message_type}")

    # Process message based on type
    if msg.message_type == "query":
        logger.info(f"Processing query: {msg.payload}")
    elif msg.message_type == "command":
        logger.info(f"Processing command: {msg.payload}")
    elif msg.message_type == "event":
        logger.info(f"Processing event: {msg.payload}")

    return UDCMessageResponse(
        received=True,
        trace_id=msg.trace_id,
        processed_at=datetime.utcnow().isoformat() + "Z",
        result="success"
    )


# ==================== BUSINESS LOGIC ENDPOINTS ====================

@app.post("/optimize", response_model=OptimizationResult)
async def optimize_spec(request: OptimizeRequest):
    """
    Optimize SPEC content using AI

    Args:
        request: SPEC content and optimization options

    Returns:
        Optimization result with before/after comparison
    """
    global request_count, specs_optimized, total_score_before, total_score_after, error_count

    request_count += 1

    # Check Claude API
    if not optimization_engine.claude.is_available():
        error_count += 1
        raise HTTPException(
            status_code=503,
            detail="Claude API not configured. Set ANTHROPIC_API_KEY environment variable."
        )

    try:
        logger.info(f"🎯 Starting optimization: level={request.optimization_level.value}")

        # Optimize
        result = await optimization_engine.optimize(
            spec_content=request.spec_content,
            optimization_level=request.optimization_level.value,
            target_score=request.target_score,
            preserve_sections=request.preserve_sections
        )

        if result["success"]:
            # Update metrics
            specs_optimized += 1
            score_before = result["verification_before"].score.get("overall", 0)
            score_after = result["verification_after"].score.get("overall", 0)
            total_score_before += score_before
            total_score_after += score_after

            logger.info(
                f"✅ Optimization complete: "
                f"{score_before:.1f} → {score_after:.1f} "
                f"(Δ {result['score_improvement']:+.1f})"
            )

            return OptimizationResult(**result)
        else:
            error_count += 1
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Optimization failed")
            )

    except HTTPException:
        raise
    except Exception as e:
        error_count += 1
        logger.error(f"❌ Optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/optimize-file", response_model=OptimizationResult)
async def optimize_spec_file(request: OptimizeFileRequest):
    """
    Optimize SPEC file by path

    Args:
        request: File path and optimization options

    Returns:
        Optimization result
    """
    global request_count, error_count

    request_count += 1

    # Check Claude API
    if not optimization_engine.claude.is_available():
        error_count += 1
        raise HTTPException(
            status_code=503,
            detail="Claude API not configured"
        )

    try:
        result = await optimization_engine.optimize_file(
            file_path=request.file_path,
            optimization_level=request.optimization_level.value,
            save_backup=request.save_backup,
            overwrite=request.overwrite
        )

        if result["success"]:
            return OptimizationResult(**result)
        else:
            error_count += 1
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "File optimization failed")
            )

    except HTTPException:
        raise
    except Exception as e:
        error_count += 1
        logger.error(f"❌ File optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch-optimize", response_model=BatchOptimizationResult)
async def batch_optimize(request: BatchOptimizeRequest):
    """
    Optimize multiple SPEC files

    Args:
        request: List of file paths and optimization level

    Returns:
        Batch optimization results
    """
    global request_count, error_count

    request_count += 1

    # Check Claude API
    if not optimization_engine.claude.is_available():
        error_count += 1
        raise HTTPException(
            status_code=503,
            detail="Claude API not configured"
        )

    try:
        logger.info(f"📦 Batch optimizing {len(request.file_paths)} files...")

        result = await optimization_engine.batch_optimize(
            file_paths=request.file_paths,
            optimization_level=request.optimization_level.value
        )

        return BatchOptimizationResult(**result)

    except Exception as e:
        error_count += 1
        logger.error(f"❌ Batch optimization error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/optimization-strategies")
async def get_optimization_strategies():
    """Get available optimization strategies"""
    global request_count
    request_count += 1

    return {
        "levels": {
            "basic": {
                "description": "Fix critical errors only",
                "passes": 1,
                "cost_range": "$0.01-$0.02",
                "target_score": "75+"
            },
            "standard": {
                "description": "Fix errors + improve quality",
                "passes": 2,
                "cost_range": "$0.02-$0.04",
                "target_score": "85+"
            },
            "aggressive": {
                "description": "Maximum quality enhancement",
                "passes": 4,
                "cost_range": "$0.04-$0.08",
                "target_score": "90+"
            }
        }
    }


# ==================== HELPER FUNCTIONS ====================

async def check_claude_availability() -> dict:
    """Check Claude API availability"""
    if optimization_engine.claude.is_available():
        return {
            "status": "available",
            "version": settings.claude_model
        }
    return {"status": "unavailable"}


async def check_verifier_availability() -> dict:
    """Check spec-verifier availability"""
    available = await optimization_engine.verifier.check_health()
    if available:
        return {
            "status": "available",
            "version": "1.0.0"
        }
    return {"status": "unavailable"}


async def check_registry_health() -> dict:
    """Check Registry health"""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{settings.registry_url}/health")
            if response.status_code == 200:
                data = response.json()
                return {
                    "status": "available",
                    "version": data.get("version")
                }
    except:
        pass

    return {"status": "unavailable"}


# ==================== ROOT ENDPOINT ====================

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "active" if optimization_engine.claude.is_available() else "inactive",
        "udc_compliant": True,
        "endpoints": {
            "udc": ["/health", "/capabilities", "/state", "/dependencies", "/message"],
            "business": ["/optimize", "/optimize-file", "/batch-optimize", "/optimization-strategies"]
        },
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.service_host,
        port=settings.service_port
    )
