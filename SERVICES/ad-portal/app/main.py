"""
Ad Portal - Main FastAPI Application

Unified advertising portal for managing Meta ad campaigns,
tracking conversions, and calculating profit.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import init_db, close_db
from app.api import api_router
from app.services.scheduler import scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Ad Portal...")
    await init_db()
    scheduler.start()
    logger.info("Ad Portal started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Ad Portal...")
    scheduler.stop()
    await close_db()
    logger.info("Ad Portal shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Ad Portal",
    description="Unified advertising portal for coaching offers - Meta Ads, Stripe, UC Credits",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


# Health check
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ad-portal",
        "version": settings.APP_VERSION
    }


# System info
@app.get("/info", tags=["system"])
async def system_info():
    """Get system information"""
    return {
        "service": "ad-portal",
        "version": settings.APP_VERSION,
        "environment": "production" if not settings.DEBUG else "development",
        "integrations": {
            "meta_ads": bool(settings.META_ACCESS_TOKEN),
            "stripe": bool(settings.STRIPE_SECRET_KEY),
            "uc_credits": bool(settings.UC_GATEWAY_URL),
            "ai_brain": bool(settings.AI_BRAIN_URL)
        }
    }


# Include API routes
app.include_router(api_router, prefix="/api")


# Root redirect to docs
@app.get("/", tags=["system"])
async def root():
    """Redirect to API documentation"""
    return {
        "message": "Ad Portal API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )


