"""
Treasury Arena - Main FastAPI Application

Serves:
- Dashboard (real-time performance metrics)
- Token Exchange API
- AI Wallet Management API
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from .api.dashboard import router as dashboard_router
from .api.token_exchange import router as token_router, wallet_router
from .api.leverage_trading import router as leverage_router

# Create FastAPI app
app = FastAPI(
    title="Treasury Arena",
    description="AI-Powered Leveraged Trading Platform - Get 2-5x leverage, trade tokenized strategies, multiply your wins",
    version="2.0.0",
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
app.include_router(dashboard_router)
app.include_router(token_router)
app.include_router(wallet_router)
app.include_router(leverage_router)


@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard"""
    return {
        "name": "Treasury Arena API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "dashboard": "/dashboard",
            "tokens": "/api/tokens",
            "wallets": "/api/wallet",
            "leverage": "/api/leverage",
        },
        "features": [
            "Tokenized DeFi Strategies",
            "AI Portfolio Management",
            "Leveraged Trading (2-5x)",
            "Controlled Withdrawals",
            "Fee Generation"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "treasury-arena",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8800)
