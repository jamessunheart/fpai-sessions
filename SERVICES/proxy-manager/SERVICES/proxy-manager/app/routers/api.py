from fastapi import APIRouter

router = APIRouter()

@router.get('/routes')
async def list_routes():
    return []

