"""SPEC Verifier Service - Main Application"""

import time
import logging
import httpx
from datetime import datetime
from pathlib import Path
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
    VerifyRequest,
    VerifyFileRequest,
    VerificationResult,
    ReferenceSpec,
    CompareRequest,
    ComparisonResult
)
from app.services import (
    SpecParser,
    UDCValidator,
    QualityScorer,
    RecommendationEngine
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="SPEC Verifier Service",
    description="Validates SPEC files for UDC compliance and quality",
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
specs_verified = 0
total_score = 0.0


@app.on_event("startup")
async def startup_event():
    """Startup event - register with Registry"""
    logger.info(f"🚀 Starting {settings.service_name} v{settings.service_version}")

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
                        "purpose": "SPEC validation and verification"
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

    return UDCHealthResponse(
        status="active",
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/capabilities", response_model=UDCCapabilitiesResponse)
async def capabilities():
    """UDC /capabilities endpoint"""
    global request_count
    request_count += 1

    return UDCCapabilitiesResponse(
        version=settings.service_version,
        features=[
            "spec_validation",
            "udc_compliance_check",
            "quality_scoring",
            "optimization_recommendations",
            "spec_comparison",
            "reference_spec_library"
        ],
        dependencies=["registry"],
        udc_version="1.0",
        metadata={
            "supported_spec_versions": ["1.0"],
            "validation_rules": 25,
            "reference_specs": len(get_reference_spec_paths()),
            "min_build_ready_score": settings.min_build_ready_score
        }
    )


@app.get("/state", response_model=UDCStateResponse)
async def state():
    """UDC /state endpoint"""
    global request_count, error_count, specs_verified, total_score

    uptime = int(time.time() - start_time)
    avg_score = (total_score / specs_verified) if specs_verified > 0 else 0.0

    return UDCStateResponse(
        uptime_seconds=uptime,
        requests_total=request_count,
        errors_last_hour=error_count,
        last_restart=datetime.fromtimestamp(start_time).isoformat() + "Z",
        specs_verified_total=specs_verified,
        average_score=round(avg_score, 2),
        active_verifications=0
    )


@app.get("/dependencies", response_model=UDCDependenciesResponse)
async def dependencies():
    """UDC /dependencies endpoint"""
    global request_count
    request_count += 1

    # Check Registry availability
    registry_status = await check_registry_health()

    return UDCDependenciesResponse(
        required=[
            DependencyStatus(
                name="registry",
                status=registry_status["status"],
                url=settings.registry_url,
                version=registry_status.get("version")
            )
        ],
        optional=[],
        missing=[] if registry_status["status"] == "available" else ["registry"]
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

@app.post("/verify", response_model=VerificationResult)
async def verify_spec(request: VerifyRequest):
    """
    Verify SPEC content for quality and UDC compliance

    Args:
        request: SPEC content and verification options

    Returns:
        Verification result with scores and recommendations
    """
    global request_count, specs_verified, total_score, error_count

    request_count += 1

    try:
        # Parse SPEC
        parser = SpecParser()
        parsed = parser.parse(request.spec_content)

        # Validate UDC compliance
        validator = UDCValidator()
        udc_result = validator.validate(parsed)

        # Score quality
        scorer = QualityScorer()
        scores = scorer.score(parsed, udc_result)

        # Generate recommendations
        rec_engine = RecommendationEngine()
        recommendations = rec_engine.generate_recommendations(parsed, udc_result, scores)

        # Update metrics
        specs_verified += 1
        total_score += scores["overall"]

        # Build result
        result = VerificationResult(
            valid=len(recommendations["errors"]) == 0,
            score=scores,
            sections={
                "found": list(parsed["sections"].keys()),
                "missing": [
                    s for s in settings.required_sections
                    if s not in parsed["sections"] or len(parsed["sections"][s]) < 50
                ],
                "incomplete": [
                    s for s, content in parsed["sections"].items()
                    if 10 < len(content) < 50
                ]
            },
            udc_endpoints={
                "documented": udc_result["documented"],
                "required": udc_result["required"],
                "missing": udc_result["missing"],
                "compliant": udc_result["compliant"]
            },
            recommendations=recommendations["recommendations"],
            errors=recommendations["errors"],
            warnings=recommendations["warnings"]
        )

        logger.info(
            f"✅ SPEC verified: score={scores['overall']:.1f}, "
            f"valid={result.valid}, errors={len(result.errors)}"
        )

        return result

    except Exception as e:
        error_count += 1
        logger.error(f"❌ Verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


@app.post("/verify-file", response_model=VerificationResult)
async def verify_spec_file(request: VerifyFileRequest):
    """
    Verify SPEC file by path

    Args:
        request: File path and verification options

    Returns:
        Verification result
    """
    global error_count

    try:
        # Load file
        spec_content = SpecParser.load_from_file(request.file_path)

        # Verify using main endpoint
        return await verify_spec(
            VerifyRequest(
                spec_content=spec_content,
                spec_path=request.file_path,
                strict_mode=request.strict_mode
            )
        )

    except FileNotFoundError:
        error_count += 1
        raise HTTPException(status_code=404, detail=f"SPEC file not found: {request.file_path}")
    except Exception as e:
        error_count += 1
        logger.error(f"❌ File verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"File verification failed: {str(e)}")


@app.get("/reference-specs")
async def get_reference_specs():
    """
    Get list of reference SPEC files

    Returns:
        List of reference specs with metadata
    """
    global request_count
    request_count += 1

    try:
        ref_specs = []
        ref_paths = get_reference_spec_paths()

        for name, path in ref_paths.items():
            # Try to extract tier from SPEC
            try:
                content = SpecParser.load_from_file(path)
                parser = SpecParser()
                parsed = parser.parse(content)
                tier = parsed["metadata"].get("tier", 0)
            except:
                tier = 0

            ref_specs.append({
                "name": name,
                "path": path,
                "tier": tier,
                "exists": Path(path).exists()
            })

        return {
            "count": len(ref_specs),
            "specs": ref_specs
        }

    except Exception as e:
        logger.error(f"❌ Failed to get reference specs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compare", response_model=ComparisonResult)
async def compare_spec(request: CompareRequest):
    """
    Compare SPEC against reference specs

    Args:
        request: SPEC to compare and reference names

    Returns:
        Comparison result with similarities and differences
    """
    global request_count, error_count
    request_count += 1

    try:
        # Load SPEC content
        if request.spec_content:
            spec_content = request.spec_content
        elif request.spec_path:
            spec_content = SpecParser.load_from_file(request.spec_path)
        else:
            raise ValueError("Either spec_content or spec_path must be provided")

        # Parse target SPEC
        parser = SpecParser()
        parsed_spec = parser.parse(spec_content)

        # Load and parse reference specs
        ref_paths = get_reference_spec_paths()
        reference_specs = []

        compare_with = request.compare_with if request.compare_with else list(ref_paths.keys())

        for ref_name in compare_with:
            if ref_name not in ref_paths:
                continue

            try:
                ref_content = SpecParser.load_from_file(ref_paths[ref_name])
                ref_parsed = parser.parse(ref_content)
                reference_specs.append(ref_parsed)
            except Exception as e:
                logger.warning(f"⚠️ Could not load reference {ref_name}: {e}")

        # Compare
        rec_engine = RecommendationEngine()
        comparison = rec_engine.compare_with_references(parsed_spec, reference_specs)

        return ComparisonResult(**comparison)

    except Exception as e:
        error_count += 1
        logger.error(f"❌ Comparison failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comparison failed: {str(e)}")


# ==================== HELPER FUNCTIONS ====================

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


def get_reference_spec_paths() -> dict:
    """Get paths to reference SPEC files"""
    base = Path(settings.services_base_path)

    reference_services = [
        "registry",
        "orchestrator",
        "proxy-manager",
        "verifier",
        "autonomous-executor",
        "jobs"
    ]

    paths = {}
    for service in reference_services:
        spec_path = base / service / "SPEC.md"
        if spec_path.exists():
            paths[service] = str(spec_path)

    return paths


# ==================== ROOT ENDPOINT ====================

@app.get("/")
async def root():
    """Root endpoint with service info"""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "active",
        "udc_compliant": True,
        "endpoints": {
            "udc": ["/health", "/capabilities", "/state", "/dependencies", "/message"],
            "business": ["/verify", "/verify-file", "/reference-specs", "/compare"]
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
