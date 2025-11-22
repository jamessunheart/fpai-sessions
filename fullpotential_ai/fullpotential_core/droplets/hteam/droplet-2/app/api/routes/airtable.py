from fastapi import APIRouter, Request, Depends
from typing import Dict, Any
from ...services.airtable_service import airtable_service
from ...utils.auth import verify_jwt_token
from ...utils.logging import get_logger

router = APIRouter(tags=["Airtable Integration"])
log = get_logger(__name__)


# Business Logic APIs
@router.post("/write")
async def write_sample_data(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Push sample data to all Airtable tables"""
    try:
        results = airtable_service.write_sample_data()
        return results
    except Exception as e:
        log.error(f"Write sample data error: {str(e)}")
        return {"error": str(e)}


@router.get("/read")
async def read_records(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Fetch records from all Airtable tables"""
    try:
        results = airtable_service.read_all_records()
        return results
    except Exception as e:
        log.error(f"Read records error: {str(e)}")
        return {"error": str(e)}


# Sprints CRUD
@router.get("/sprints")
async def get_sprints(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Get all sprints"""
    try:
        result = airtable_service.get_records("Sprints")
        log.info(f"📖 Read Sprints: {len(result.get('records', []))} records")
        return result
    except Exception as e:
        log.error(f"Get sprints error: {str(e)}")
        return {"error": str(e)}


@router.post("/sprints")
async def create_sprint(request: Request, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Create new sprint"""
    try:
        data = await request.json()
        result = airtable_service.create_record("Sprints", data)
        log.info("✅ Created Sprint")
        return {"status": "success", "data": result}
    except Exception as e:
        log.error(f"Create sprint error: {str(e)}")
        return {"error": str(e)}


@router.put("/sprints/{record_id}")
async def update_sprint(record_id: str, request: Request, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Update sprint record"""
    try:
        data = await request.json()
        result = airtable_service.update_record("Sprints", record_id, data)
        log.info(f"✅ Updated Sprint {record_id}")
        return {"status": "success", "data": result}
    except Exception as e:
        log.error(f"Update sprint error: {str(e)}")
        return {"error": str(e)}


@router.delete("/sprints/{record_id}")
async def delete_sprint(record_id: str, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Delete sprint record"""
    try:
        result = airtable_service.delete_record("Sprints", record_id)
        log.info(f"✅ Deleted Sprint {record_id}")
        return {"status": "success", "message": "Sprint deleted"}
    except Exception as e:
        log.error(f"Delete sprint error: {str(e)}")
        return {"error": str(e)}


# Cells CRUD
@router.get("/cells")
async def get_cells(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Get all cells"""
    try:
        result = airtable_service.get_records("Cells")
        log.info(f"📖 Read Cells: {len(result.get('records', []))} records")
        return result
    except Exception as e:
        log.error(f"Get cells error: {str(e)}")
        return {"error": str(e)}


@router.post("/cells")
async def create_cell(request: Request, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Create new cell"""
    try:
        data = await request.json()
        result = airtable_service.create_record("Cells", data)
        log.info("✅ Created Cell")
        return {"status": "success", "data": result}
    except Exception as e:
        log.error(f"Create cell error: {str(e)}")
        return {"error": str(e)}


@router.put("/cells/{record_id}")
async def update_cell(record_id: str, request: Request, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Update cell record"""
    try:
        data = await request.json()
        result = airtable_service.update_record("Cells", record_id, data)
        log.info(f"✅ Updated Cell {record_id}")
        return {"status": "success", "data": result}
    except Exception as e:
        log.error(f"Update cell error: {str(e)}")
        return {"error": str(e)}


@router.delete("/cells/{record_id}")
async def delete_cell(record_id: str, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Delete cell record"""
    try:
        result = airtable_service.delete_record("Cells", record_id)
        log.info(f"✅ Deleted Cell {record_id}")
        return {"status": "success", "message": "Cell deleted"}
    except Exception as e:
        log.error(f"Delete cell error: {str(e)}")
        return {"error": str(e)}


# Proof CRUD
@router.get("/proof")
async def get_proof(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Get all proof records"""
    try:
        result = airtable_service.get_records("Proof")
        log.info(f"📖 Read Proof: {len(result.get('records', []))} records")
        return result
    except Exception as e:
        log.error(f"Get proof error: {str(e)}")
        return {"error": str(e)}


@router.post("/proof")
async def create_proof_record(request: Request, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Create new proof record"""
    try:
        data = await request.json()
        result = airtable_service.create_record("Proof", data)
        log.info("✅ Created Proof")
        return {"status": "success", "data": result}
    except Exception as e:
        log.error(f"Create proof error: {str(e)}")
        return {"error": str(e)}


@router.put("/proof/{record_id}")
async def update_proof(record_id: str, request: Request, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Update proof record"""
    try:
        data = await request.json()
        result = airtable_service.update_record("Proof", record_id, data)
        log.info(f"✅ Updated Proof {record_id}")
        return {"status": "success", "data": result}
    except Exception as e:
        log.error(f"Update proof error: {str(e)}")
        return {"error": str(e)}


@router.delete("/proof/{record_id}")
async def delete_proof(record_id: str, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Delete proof record"""
    try:
        result = airtable_service.delete_record("Proof", record_id)
        log.info(f"✅ Deleted Proof {record_id}")
        return {"status": "success", "message": "Proof deleted"}
    except Exception as e:
        log.error(f"Delete proof error: {str(e)}")
        return {"error": str(e)}


# Heartbeats CRUD
@router.get("/heartbeats")
async def get_heartbeats(token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Get all heartbeats"""
    try:
        result = airtable_service.get_records("Heartbeats")
        log.info(f"📖 Read Heartbeats: {len(result.get('records', []))} records")
        return result
    except Exception as e:
        log.error(f"Get heartbeats error: {str(e)}")
        return {"error": str(e)}


@router.post("/heartbeats")
async def create_heartbeat(request: Request, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Create new heartbeat"""
    try:
        data = await request.json()
        result = airtable_service.create_record("Heartbeats", data)
        log.info("✅ Created Heartbeat")
        return {"status": "success", "data": result}
    except Exception as e:
        log.error(f"Create heartbeat error: {str(e)}")
        return {"error": str(e)}


@router.put("/heartbeats/{record_id}")
async def update_heartbeat(record_id: str, request: Request, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Update heartbeat record"""
    try:
        data = await request.json()
        result = airtable_service.update_record("Heartbeats", record_id, data)
        log.info(f"✅ Updated Heartbeat {record_id}")
        return {"status": "success", "data": result}
    except Exception as e:
        log.error(f"Update heartbeat error: {str(e)}")
        return {"error": str(e)}


@router.delete("/heartbeats/{record_id}")
async def delete_heartbeat(record_id: str, token_data: Dict[str, Any] = Depends(verify_jwt_token)):
    """Delete heartbeat record"""
    try:
        result = airtable_service.delete_record("Heartbeats", record_id)
        log.info(f"✅ Deleted Heartbeat {record_id}")
        return {"status": "success", "message": "Heartbeat deleted"}
    except Exception as e:
        log.error(f"Delete heartbeat error: {str(e)}")
        return {"error": str(e)}