"""SPEC Builder Service - Main Application"""

import time
import logging
import httpx
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import *
from app.services import GenerationEngine, TemplateManager, IntegrationClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SPEC Builder Service",
    description="AI-powered SPEC generation from architect intent",
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
specs_generated = 0
total_initial_score = 0.0
total_final_score = 0.0

# Engine
generation_engine = GenerationEngine()
template_manager = TemplateManager()
integration_client = IntegrationClient()


@app.on_event("startup")
async def startup_event():
    """Startup event - register with Registry"""
    logger.info(f"🚀 Starting {settings.service_name} v{settings.service_version}")

    if generation_engine.claude.is_available():
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
                        "purpose": "AI-powered SPEC generation"
                    }
                }
            )
            if response.status_code == 200:
                logger.info(f"✅ Registered with Registry (ID: {settings.registry_id})")
    except Exception as e:
        logger.warning(f"⚠️ Could not register with Registry: {e}")

    logger.info(f"✅ {settings.service_name} ready on port {settings.service_port}")


# ==================== UDC ENDPOINTS ====================

@app.get("/health", response_model=UDCHealthResponse)
async def health():
    global request_count
    request_count += 1

    status = "active" if generation_engine.claude.is_available() else "inactive"

    return UDCHealthResponse(
        status=status,
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/capabilities", response_model=UDCCapabilitiesResponse)
async def capabilities():
    global request_count, specs_generated, total_initial_score
    request_count += 1

    avg_initial = (total_initial_score / specs_generated) if specs_generated > 0 else 0.0

    return UDCCapabilitiesResponse(
        version=settings.service_version,
        features=[
            "intent_to_spec_generation",
            "template_based_generation",
            "interactive_refinement",
            "integration_pipeline",
            "multi_service_type_support"
        ],
        dependencies=["claude_api", "spec_verifier", "spec_optimizer", "registry"],
        udc_version="1.0",
        metadata={
            "claude_model": settings.claude_model,
            "supported_service_types": ["infrastructure", "sacred_loop", "domain", "api_gateway", "data"],
            "average_initial_score": round(avg_initial, 2)
        }
    )


@app.get("/state", response_model=UDCStateResponse)
async def state():
    global request_count, error_count, specs_generated, total_initial_score, total_final_score

    uptime = int(time.time() - start_time)
    avg_initial = (total_initial_score / specs_generated) if specs_generated > 0 else 0.0
    avg_final = (total_final_score / specs_generated) if specs_generated > 0 else 0.0

    return UDCStateResponse(
        uptime_seconds=uptime,
        requests_total=request_count,
        errors_last_hour=error_count,
        last_restart=datetime.fromtimestamp(start_time).isoformat() + "Z",
        specs_generated_total=specs_generated,
        average_initial_score=round(avg_initial, 2),
        average_final_score=round(avg_final, 2),
        active_generations=0
    )


@app.get("/dependencies", response_model=UDCDependenciesResponse)
async def dependencies():
    global request_count
    request_count += 1

    claude_status = "available" if generation_engine.claude.is_available() else "unavailable"
    verifier_status = "available" if await integration_client.check_verifier_health() else "unavailable"
    optimizer_status = "available" if await integration_client.check_optimizer_health() else "unavailable"

    # Check registry
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.registry_url}/health")
            registry_status = "available" if resp.status_code == 200 else "unavailable"
    except:
        registry_status = "unavailable"

    required_deps = [
        DependencyStatus(name="claude_api", status=claude_status, version=settings.claude_model),
        DependencyStatus(name="spec_verifier", status=verifier_status, url=settings.spec_verifier_url),
        DependencyStatus(name="spec_optimizer", status=optimizer_status, url=settings.spec_optimizer_url),
        DependencyStatus(name="registry", status=registry_status, url=settings.registry_url)
    ]

    missing = [dep.name for dep in required_deps if dep.status != "available"]

    return UDCDependenciesResponse(
        required=required_deps,
        optional=[],
        missing=missing
    )


@app.post("/message", response_model=UDCMessageResponse)
async def message(msg: UDCMessageRequest):
    global request_count
    request_count += 1

    logger.info(f"📨 Received message from {msg.source}: {msg.message_type}")

    return UDCMessageResponse(
        received=True,
        trace_id=msg.trace_id,
        processed_at=datetime.utcnow().isoformat() + "Z",
        result="success"
    )


# ==================== BUSINESS LOGIC ENDPOINTS ====================

@app.post("/generate", response_model=GenerationResult)
async def generate_spec(request: GenerateRequest):
    global request_count, specs_generated, total_initial_score, total_final_score, error_count

    request_count += 1

    if not generation_engine.claude.is_available():
        error_count += 1
        raise HTTPException(status_code=503, detail="Claude API not configured")

    try:
        logger.info(f"🎯 Generating SPEC: {request.service_name} ({request.service_type.value})")

        result = await generation_engine.generate(
            service_name=request.service_name,
            service_type=request.service_type.value,
            purpose=request.purpose,
            key_features=request.key_features,
            dependencies=request.dependencies,
            port=request.port,
            tier=request.tier,
            auto_optimize=request.auto_optimize,
            target_score=request.target_score
        )

        if result["success"]:
            specs_generated += 1
            initial = result["verification"].get("score", {}).get("overall", 0)
            final = result.get("final_score", initial)
            total_initial_score += initial
            total_final_score += final

            logger.info(f"✅ SPEC generated: {request.service_name} (score: {final})")

            return GenerationResult(**result)
        else:
            error_count += 1
            raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

    except HTTPException:
        raise
    except Exception as e:
        error_count += 1
        logger.error(f"❌ Generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates")
async def get_templates():
    global request_count
    request_count += 1

    return {"templates": template_manager.get_templates()}


@app.get("/")
async def root():
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "active" if generation_engine.claude.is_available() else "inactive",
        "udc_compliant": True,
        "endpoints": {
            "udc": ["/health", "/capabilities", "/state", "/dependencies", "/message"],
            "business": ["/generate", "/templates"]
        },
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.service_host, port=settings.service_port)
