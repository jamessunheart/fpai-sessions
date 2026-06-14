"""
Session Management Endpoints
Per Spec - session management requirement
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.models.chat import SessionListResponse, SessionInfo
from app.services.memory import SESSION_MANAGER
from app.utils.logging import get_logger

log = get_logger(__name__)

router = APIRouter()


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions():
    """
    List all active sessions.
    Per Spec - GET /sessions endpoint.
    NO JWT required (session management is public).
    """
    log.info("sessions_list_requested")
    
    session_ids = SESSION_MANAGER.list_sessions()
    sessions = []
    
    for session_id in session_ids:
        info = SESSION_MANAGER.get_session_info(session_id)
        
        if info:
            # Get session object for more details
            session = SESSION_MANAGER.get_session(session_id)
            
            # Get timestamps from history
            created_at = datetime.utcnow().isoformat() + "Z"
            last_activity = datetime.utcnow().isoformat() + "Z"
            
            if session.history:
                first_msg = session.history[0]
                last_msg = session.history[-1]
                created_at = first_msg.get("timestamp", created_at)
                last_activity = last_msg.get("timestamp", last_activity)
            
            sessions.append(SessionInfo(
                session_id=session_id,
                source=info["source"],
                created_at=created_at,
                last_activity=last_activity,
                message_count=info["message_count"],
                metadata=session.source_metadata
            ))
    
    log.info("sessions_listed", total=len(sessions))
    
    return SessionListResponse(
        sessions=sessions,
        total=len(sessions)
    )


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """
    Get detailed information about a specific session.
    Per Spec - session information endpoint.
    """
    log.info("session_info_requested", session_id=session_id)
    
    info = SESSION_MANAGER.get_session_info(session_id)
    
    if not info:
        log.warning("session_not_found", session_id=session_id)
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    # Get full session for history
    session = SESSION_MANAGER.get_session(session_id)
    
    # Build detailed response
    created_at = datetime.utcnow().isoformat() + "Z"
    last_activity = datetime.utcnow().isoformat() + "Z"
    
    if session.history:
        first_msg = session.history[0]
        last_msg = session.history[-1]
        created_at = first_msg.get("timestamp", created_at)
        last_activity = last_msg.get("timestamp", last_activity)
    
    return {
        "session_id": session_id,
        "source": info["source"],
        "created_at": created_at,
        "last_activity": last_activity,
        "message_count": info["message_count"],
        "has_pending_action": info["has_pending_action"],
        "pending_action": session.pending_action,
        "metadata": session.source_metadata,
        "history": session.history[-10:]  # Last 10 messages
    }


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """
    Clear a specific session.
    Per Spec - DELETE /sessions/{session_id} endpoint.
    NO JWT required.
    """
    log.info("session_clear_requested", session_id=session_id)
    
    success = SESSION_MANAGER.clear_session(session_id)
    
    if not success:
        log.warning("session_clear_failed_not_found", session_id=session_id)
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )
    
    log.info("session_cleared", session_id=session_id)
    
    return {
        "success": True,
        "session_id": session_id,
        "message": "Session cleared successfully"
    }


@router.delete("/sessions")
async def clear_all_sessions():
    """
    Clear all sessions (admin function).
    Use with caution - clears all conversation history.
    """
    log.warning("all_sessions_clear_requested")
    
    session_ids = SESSION_MANAGER.list_sessions()
    count = len(session_ids)
    
    for session_id in session_ids:
        SESSION_MANAGER.clear_session(session_id)
    
    log.warning("all_sessions_cleared", count=count)
    
    return {
        "success": True,
        "sessions_cleared": count,
        "message": f"Cleared {count} sessions"
    }


@router.get("/sessions/stats")
async def get_session_stats():
    """
    Get session statistics.
    Per Spec - session monitoring.
    """
    log.info("session_stats_requested")
    
    session_ids = SESSION_MANAGER.list_sessions()
    
    stats = {
        "total_sessions": len(session_ids),
        "by_source": {
            "chat": 0,
            "voice": 0
        },
        "with_pending_actions": 0,
        "total_messages": 0
    }
    
    for session_id in session_ids:
        info = SESSION_MANAGER.get_session_info(session_id)
        
        if info:
            # Count by source
            source = info["source"]
            if source in stats["by_source"]:
                stats["by_source"][source] += 1
            
            # Count pending actions
            if info["has_pending_action"]:
                stats["with_pending_actions"] += 1
            
            # Total messages
            stats["total_messages"] += info["message_count"]
    
    return stats