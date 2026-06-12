"""
WebSocket Endpoints - EXEMPT FROM UDC WRAPPING
Real-time updates for tasks and droplets

NOTE: WebSocket connections bypass HTTP middleware entirely.
WebSocket messages are already UDC-wrapped by websocket_manager.
No changes needed to this file.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import structlog

from app.services.websocket_manager import websocket_manager
from app.utils.auth import verify_websocket_token

log = structlog.get_logger()

router = APIRouter()


# ============================================================================
# WEBSOCKET ENDPOINTS (Already Handles UDC in Manager)
# ============================================================================

@router.websocket("/tasks")
async def websocket_tasks(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for task updates
    
    NO CHANGES NEEDED: WebSocket messages are already UDC-wrapped
    by websocket_manager when broadcasting events.
    
    Connect: ws://host/ws/tasks?token=YOUR_JWT_TOKEN
    
    Events received (all UDC-wrapped):
    - task_created: New task created
    - task_updated: Task status changed
    - task_assigned: Task assigned to droplet
    - task_completed: Task completed successfully
    - task_failed: Task failed with error
    - ping: Keepalive ping
    
    Example:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/tasks?token=YOUR_JWT');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // data is already UDC-wrapped envelope
        console.log('Task update:', data.payload);
    };
    ```
    """
    try:
        # Verify JWT token
        try:
            token_data = verify_websocket_token(token)
            droplet_id = token_data.get('droplet_id')
        except ValueError as e:
            await websocket.close(code=1008, reason=str(e))
            log.warning("websocket_auth_failed", reason=str(e))
            return
        
        # Accept connection and add to manager
        await websocket_manager.connect_task_channel(websocket)
        
        log.info(
            "websocket_connected",
            channel="tasks",
            droplet_id=droplet_id
        )
        
        try:
            # Keep connection alive and handle incoming messages
            while True:
                # Wait for messages (clients shouldn't send, but handle gracefully)
                data = await websocket.receive_text()
                
                # Echo back or ignore
                log.debug("websocket_message_received", channel="tasks", data=data[:100])
                
        except WebSocketDisconnect:
            # Client disconnected
            websocket_manager.disconnect(websocket)
            log.info(
                "websocket_disconnected",
                channel="tasks",
                droplet_id=droplet_id
            )
            
    except Exception as e:
        log.error(
            "websocket_error",
            channel="tasks",
            error=str(e)
        )
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
        websocket_manager.disconnect(websocket)


@router.websocket("/droplets")
async def websocket_droplets(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token")
):
    """
    WebSocket endpoint for droplet health updates
    
    NO CHANGES NEEDED: WebSocket messages are already UDC-wrapped
    by websocket_manager when broadcasting events.
    
    Connect: ws://host/ws/droplets?token=YOUR_JWT_TOKEN
    
    Events received (all UDC-wrapped):
    - droplet_registered: New droplet registered
    - droplet_health_changed: Droplet status changed (active/inactive/error)
    - droplet_heartbeat_missed: Droplet failed to send heartbeat
    - ping: Keepalive ping
    
    Example:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/droplets?token=YOUR_JWT');
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // data is already UDC-wrapped envelope
        console.log('Droplet update:', data.payload);
    };
    ```
    """
    try:
        # Verify JWT token
        try:
            token_data = verify_websocket_token(token)
            droplet_id = token_data.get('droplet_id')
        except ValueError as e:
            await websocket.close(code=1008, reason=str(e))
            log.warning("websocket_auth_failed", reason=str(e))
            return
        
        # Accept connection and add to manager
        await websocket_manager.connect_droplet_channel(websocket)
        
        log.info(
            "websocket_connected",
            channel="droplets",
            droplet_id=droplet_id
        )
        
        try:
            # Keep connection alive and handle incoming messages
            while True:
                # Wait for messages (clients shouldn't send, but handle gracefully)
                data = await websocket.receive_text()
                
                # Echo back or ignore
                log.debug("websocket_message_received", channel="droplets", data=data[:100])
                
        except WebSocketDisconnect:
            # Client disconnected
            websocket_manager.disconnect(websocket)
            log.info(
                "websocket_disconnected",
                channel="droplets",
                droplet_id=droplet_id
            )
            
    except Exception as e:
        log.error(
            "websocket_error",
            channel="droplets",
            error=str(e)
        )
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
        websocket_manager.disconnect(websocket)


# ============================================================================
# CONNECTION STATUS (HTTP Endpoint - Gets UDC Wrapped by Middleware)
# ============================================================================

@router.get("/status")
async def websocket_status():
    """
    Get WebSocket connection statistics
    
    Returns current number of active connections by channel.
    Useful for monitoring and debugging.
    
    MIDDLEWARE WRAPPED: Response automatically wrapped in UDC envelope
    """
    stats = websocket_manager.get_connection_count()
    
    # Return plain response - middleware wraps
    return {
        "websocket_enabled": True,
        "connections": stats,
        "channels": {
            "tasks": {
                "endpoint": "/ws/tasks",
                "description": "Real-time task updates",
                "active_connections": stats["task_connections"]
            },
            "droplets": {
                "endpoint": "/ws/droplets",
                "description": "Real-time droplet health updates",
                "active_connections": stats["droplet_connections"]
            }
        }
    }