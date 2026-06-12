"""Needs Allocation Engine - Main Application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import settings, CATEGORIES
from .database import init_db
from .routers import requests, budget

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database init skipped: {e}")
    
    yield
    
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="Needs Allocation Engine",
    description="Distributes ministry benefits to eligible members based on genuine needs",
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
app.include_router(requests.router)
app.include_router(budget.router)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "operational",
        "description": "Distributes ministry benefits to eligible members",
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
        "service": "needs-allocation",
        "version": "1.0.0",
        "endpoints": {
            "requests": {
                "POST /api/needs/request": "Submit needs-support request",
                "GET /api/needs/request/{id}": "Get request status",
                "POST /api/needs/fulfill/{id}": "Mark request fulfilled",
                "GET /api/needs/eligibility/{member_id}": "Check eligibility",
                "GET /api/needs/committed": "Get committed needs"
            },
            "budget": {
                "GET /api/needs/budget": "Get current budget",
                "GET /api/needs/categories": "Get categories"
            }
        },
        "categories": list(CATEGORIES.keys()),
        "fairness_limits": {
            "max_single_percent": settings.MAX_SINGLE_ALLOCATION_PERCENT,
            "max_single_absolute": settings.MAX_SINGLE_ALLOCATION_ABSOLUTE,
            "max_requests_per_month": settings.MAX_REQUESTS_PER_MONTH
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )










