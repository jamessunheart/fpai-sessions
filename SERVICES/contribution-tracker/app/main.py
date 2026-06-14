"""Contribution Tracker Service - Main Application."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from .config import settings
from .database import init_db
from .routers import contributions, scores

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
        logger.warning(f"Database init skipped (may not be available): {e}")
    
    yield
    
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title="Contribution Tracker Service",
    description="Tracks member contributions and issues TRUST tokens for the Commons Ministry",
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

# Include routers - scores first to prevent /{id} from matching "aggregate"
app.include_router(scores.router)
app.include_router(contributions.router)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "status": "operational",
        "description": "Tracks member contributions and issues TRUST tokens",
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
        "service": "contribution-tracker",
        "version": "1.0.0",
        "endpoints": {
            "contributions": {
                "POST /api/contributions/log": "Log a new contribution",
                "POST /api/contributions/verify/{id}": "Verify a contribution",
                "GET /api/contributions/member/{member_id}": "Get member contributions",
                "GET /api/contributions/{id}": "Get specific contribution"
            },
            "scores": {
                "GET /api/contributions/score/{member_id}": "Get member score",
                "GET /api/contributions/aggregate": "Get aggregate metrics",
                "GET /api/contributions/leaderboard": "Get top contributors",
                "GET /api/trust/balance/{member_id}": "Get TRUST balance"
            }
        },
        "trust_rates": {
            "service_per_hour": settings.TRUST_RATE_SERVICE_HOUR,
            "governance_vote": settings.TRUST_RATE_GOVERNANCE_VOTE,
            "referral": settings.TRUST_RATE_REFERRAL,
            "financial_per_uc": settings.TRUST_RATE_FINANCIAL_PER_UC
        },
        "tiers": {
            "active_min": settings.TIER_ACTIVE_MIN,
            "engaged_min": settings.TIER_ENGAGED_MIN
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.SERVICE_PORT,
        reload=settings.DEBUG
    )

