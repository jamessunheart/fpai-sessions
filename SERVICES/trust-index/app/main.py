"""Trust Index Service - Main Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings, GUARDRAILS
from .routers import index
from .calculator import calculate_trust_index

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    
    # Initial calculation
    try:
        await calculate_trust_index(use_mocks=True)
        logger.info("Initial Trust Index calculated")
    except Exception as e:
        logger.warning(f"Initial calculation failed: {e}")
    
    yield
    
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="Trust Index Service",
    description="Calculates and publishes Trust Index for Commons Ministry policy",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(index.router)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "operational",
        "description": "Calculates Trust Index for Commons Ministry policy",
        "canonical_reference": "docs/protocols/TOKENS_STRATEGY.md"
    }


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "port": settings.SERVICE_PORT
    }


@app.get("/api/info")
async def api_info():
    """API information."""
    return {
        "service": "trust-index",
        "version": "1.0.0",
        "endpoints": {
            "GET /api/trust-index": "Get current Trust Index",
            "GET /api/trust-index/policy": "Get current policy parameters",
            "GET /api/trust-index/history": "Get historical values",
            "POST /api/trust-index/simulate": "Simulate with overrides",
            "GET /api/trust-index/guardrails": "Get hard guardrails"
        },
        "weights": {
            "solvency": settings.WEIGHT_SOLVENCY,
            "commons_health": settings.WEIGHT_COMMONS_HEALTH,
            "participation": settings.WEIGHT_PARTICIPATION
        },
        "thresholds": {
            "conservative": settings.THRESHOLD_CONSERVATIVE,
            "generous": settings.THRESHOLD_GENEROUS,
            "emergency": settings.EMERGENCY_FREEZE_THRESHOLD
        },
        "guardrails": GUARDRAILS
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )










