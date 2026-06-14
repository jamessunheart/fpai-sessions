"""Aggregate API routes."""
from fastapi import APIRouter

from . import assets, transactions

api_router = APIRouter()
api_router.include_router(assets.router)
api_router.include_router(transactions.router)

__all__ = ("api_router",)

