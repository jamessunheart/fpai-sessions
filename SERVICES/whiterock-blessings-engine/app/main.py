"""
WhiteRock CORA Membership & Community Blessings System
v2.2 - Production-Ready with Security Enhancements

A member management and community support system for WhiteRock Church Trust.
Manages tithing members, CORA vitality credits with decay, and discretionary
blessing distribution - all under strict 508(c)(1)(A) compliance.

CRITICAL: This system has ZERO connection to any treasury/trading systems.
The Trust Firewall is absolute.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os

from app.config import settings
from app.database import init_db, close_db
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.services.cache_service import cache
from app.logging_config import configure_logging, logger, log_request_context, clear_request_context

# Configure structured logging
configure_logging()
from app.routes import (
    health_router,
    members_router,
    tithes_router,
    cora_router,
    service_router,
    blessings_router,
    reports_router,
    audit_router,
    capacity_router,
    metrics_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("service_starting", service=settings.APP_NAME, version=settings.APP_VERSION)
    
    # Initialize database
    try:
        await init_db()
        logger.info("database_initialized")
    except Exception as e:
        logger.error("database_init_failed", error=str(e))
    
    # Initialize cache
    try:
        await cache.initialize()
        logger.info("cache_initialized")
    except Exception as e:
        logger.warning("cache_init_failed", error=str(e))
    
    # Register with UDC Registry (if configured)
    if settings.REGISTRY_URL:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{settings.REGISTRY_URL}/register",
                    json={
                        "service_id": settings.SERVICE_ID,
                        "name": settings.APP_NAME,
                        "version": settings.APP_VERSION,
                        "url": f"http://localhost:{settings.PORT}",
                        "health_endpoint": "/health"
                    },
                    timeout=5.0
                )
                logger.info("registry_registered", registry_url=settings.REGISTRY_URL)
        except Exception as e:
            logger.warning("registry_registration_skipped", error=str(e))
    
    logger.info("service_ready", port=settings.PORT)
    
    yield
    
    # Shutdown
    logger.info("service_shutting_down")
    await cache.close()
    await close_db()
    logger.info("service_stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
WhiteRock CORA Membership & Community Blessings System

A member management and community support system for WhiteRock Church Trust
that tracks tithing members, manages CORA participation credits with vitality-based
decay, and enables discretionary blessing distribution to community members.

## Key Features

- **Member Management**: Registration, profiles, disclosure acknowledgment
- **CORA Vitality System**: Non-transferable credits with engagement-based decay
- **Tithe Processing**: Stripe integration with compliance tracking
- **Blessing Requests**: Formal state machine (draft → pending → review → approved/denied → disbursed)
- **Vendor-Direct Disbursements**: Payments to landlords, utilities, hospitals
- **Compliance Audit**: Full audit trail with integrity checks

## Trust Firewall

This system maintains ABSOLUTE separation from any treasury/trading systems.
No database tables, API endpoints, or code references connect to trading.

## Compliance

508(c)(1)(A) compliant religious organization operations.
All tithes store full disclosure text and acknowledgment confirmations.
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS configuration - Hardened for production
ALLOWED_ORIGINS = [
    "https://whiterock.us",
    "https://www.whiterock.us",
    "https://api.whiterock.us",
]
# Add localhost for development
if settings.DEBUG:
    ALLOWED_ORIGINS.extend([
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

# Include routers with /api prefix for API endpoints
app.include_router(health_router)  # UDC endpoints at root (keep for compatibility)
app.include_router(members_router, prefix="/api")
app.include_router(tithes_router, prefix="/api")
app.include_router(cora_router, prefix="/api")
app.include_router(service_router, prefix="/api")
app.include_router(blessings_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(capacity_router, prefix="/api")
app.include_router(metrics_router)  # Prometheus metrics (keep at root)

# Also include routers at root for backward compatibility
app.include_router(members_router)
app.include_router(tithes_router)
app.include_router(cora_router)
app.include_router(service_router)
app.include_router(blessings_router)
app.include_router(reports_router)
app.include_router(audit_router)
app.include_router(capacity_router)

# Static files for member portal
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Root endpoint - serve the landing page
@app.get("/", response_class=HTMLResponse)
async def root():
    """Landing page for WhiteRock Ministry."""
    landing_file = STATIC_DIR / "landing" / "index.html"
    if landing_file.exists():
        return FileResponse(landing_file)
    # Fallback if landing page doesn't exist
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>WhiteRock Blessings Engine</title>
            <style>
                body { font-family: sans-serif; background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; min-height: 100vh; display: flex; align-items: center; justify-content: center; margin: 0; }
                .container { text-align: center; padding: 40px; }
                h1 { font-size: 2.5rem; margin-bottom: 20px; }
                a { color: #93c5fd; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🙏 WhiteRock Blessings Engine</h1>
                <p>Member Management & Community Support System</p>
                <p style="margin-top: 2rem;">
                    <a href="/portal">Member Portal</a> |
                    <a href="/docs">API Docs</a> | 
                    <a href="/health">Health</a>
                </p>
            </div>
        </body>
        </html>
        """
    )


@app.get("/portal", response_class=HTMLResponse)
@app.get("/portal/{path:path}", response_class=HTMLResponse)
async def member_portal(path: str = ""):
    """Serve the member portal single-page application."""
    portal_file = STATIC_DIR / "portal" / "index.html"
    if portal_file.exists():
        return FileResponse(portal_file)
    return HTMLResponse(
        content="<h1>Portal not found</h1><p>The member portal is not available.</p>",
        status_code=404
    )


@app.get("/admin", response_class=HTMLResponse)
@app.get("/admin/{path:path}", response_class=HTMLResponse)
async def admin_dashboard(path: str = ""):
    """Serve the admin dashboard single-page application."""
    admin_file = STATIC_DIR / "admin" / "index.html"
    if admin_file.exists():
        return FileResponse(admin_file)
    return HTMLResponse(
        content="<h1>Admin not found</h1><p>The admin dashboard is not available.</p>",
        status_code=404
    )


# Run with uvicorn when called directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

