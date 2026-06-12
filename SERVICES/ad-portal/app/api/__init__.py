"""
API Routes
"""
from fastapi import APIRouter
from app.api.offers import router as offers_router
from app.api.campaigns import router as campaigns_router
from app.api.creatives import router as creatives_router
from app.api.analytics import router as analytics_router
from app.api.webhooks import router as webhooks_router

api_router = APIRouter()

api_router.include_router(offers_router, prefix="/offers", tags=["offers"])
api_router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(creatives_router, prefix="/creatives", tags=["creatives"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["webhooks"])


