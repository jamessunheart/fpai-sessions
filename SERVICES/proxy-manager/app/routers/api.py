from fastapi import APIRouter, HTTPException
from app.models import Route, RouteCreate, RouteStatus
from app.nginx import NginxController
from datetime import datetime
import uuid

router = APIRouter()

# In-memory store for MVP
routes_db = {}

@router.get('/routes', response_model=list[Route])
async def list_routes():
    return list(routes_db.values())

@router.post('/routes', response_model=Route)
async def create_route(route_in: RouteCreate):
    route_id = str(uuid.uuid4())
    
    # 1. Generate Config
    try:
        NginxController.write_config(route_in.domain, route_in.upstream_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Config generation failed: {str(e)}')

    # 2. Validate Config
    if not NginxController.test_config():
        # Rollback
        NginxController.delete_config(route_in.domain)
        raise HTTPException(status_code=400, detail='Invalid NGINX configuration generated')

    # 3. Reload NGINX
    if not NginxController.reload():
        raise HTTPException(status_code=500, detail='Failed to reload NGINX')

    new_route = Route(
        id=route_id,
        **route_in.dict(),
        status=RouteStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    routes_db[route_id] = new_route
    return new_route

@router.delete('/routes/{route_id}')
async def delete_route(route_id: str):
    if route_id not in routes_db:
        raise HTTPException(status_code=404, detail='Route not found')
    
    route = routes_db[route_id]
    NginxController.delete_config(route.domain)
    NginxController.reload()
    
    del routes_db[route_id]
    return {'status': 'deleted'}

