"""Aggregate API routers."""
from fastapi import APIRouter

from . import messages, tasks

api_router = APIRouter()
api_router.include_router(messages.router)
api_router.include_router(tasks.router)

__all__ = ("api_router",)

