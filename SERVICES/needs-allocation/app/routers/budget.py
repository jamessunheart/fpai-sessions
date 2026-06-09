"""Budget endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..budget import get_current_budget
from ..database import get_db
from ..models import BudgetResponse
from ..config import CATEGORIES

router = APIRouter(prefix="/api/needs", tags=["budget"])


@router.get("/budget", response_model=BudgetResponse)
async def get_budget(db: AsyncSession = Depends(get_db)):
    """Get current budget allocation."""
    return await get_current_budget(db=db)


@router.get("/categories")
async def get_categories():
    """Get needs categories and their configuration."""
    return {
        "categories": CATEGORIES,
        "description": "Categories for needs-based ministry benefits"
    }




