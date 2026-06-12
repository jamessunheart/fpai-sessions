"""
Metrics and Analytics Endpoints - WORKING UDC SOLUTION
Uses dependency-based approach for UDC wrapping
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional
import structlog

from app.database import db
from app.utils.auth import verify_jwt_token
from app.utils.udc_deps import wrap_udc_response, get_udc_metadata
from app.services.task_router import get_routing_metrics
from app.services.health_monitor import get_droplet_health_summary

log = structlog.get_logger()
router = APIRouter()


# ============================================================================
# SYSTEM METRICS
# ============================================================================

@router.get("/summary")
async def get_metrics_summary(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Get system-wide metrics summary
    
    RESPONSE: UDC envelope with metrics summary
    """
    try:
        udc = get_udc_metadata(request)
        
        # Get task statistics
        task_stats = await db.fetchrow(
            """
            SELECT 
                COUNT(*) as total_created,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) 
                    FILTER (WHERE status = 'completed') as avg_completion_seconds,
                ROUND(
                    COUNT(*) FILTER (WHERE status = 'completed')::NUMERIC / 
                    NULLIF(COUNT(*) FILTER (WHERE status IN ('completed', 'failed')), 0) * 100,
                    2
                ) as success_rate_percent
            FROM tasks
            WHERE created_at > NOW() - INTERVAL '30 days'
            """
        )
        
        # Get droplet statistics
        droplet_stats = await get_droplet_health_summary()
        
        # Get system uptime and performance
        from app.utils.helpers import get_process_metrics
        system_metrics = get_process_metrics()
        
        log.debug(
            "metrics_summary_generated",
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "tasks": {
                    "total_created": task_stats['total_created'] or 0,
                    "completed": task_stats['completed'] or 0,
                    "failed": task_stats['failed'] or 0,
                    "pending": task_stats['pending'] or 0,
                    "in_progress": task_stats['in_progress'] or 0,
                    "average_completion_seconds": round(task_stats['avg_completion_seconds'] or 0, 2),
                    "success_rate_percent": float(task_stats['success_rate_percent'] or 0)
                },
                "droplets": {
                    "total_registered": droplet_stats.get('total_droplets', 0),
                    "active": droplet_stats.get('active_droplets', 0),
                    "inactive": droplet_stats.get('inactive_droplets', 0),
                    "error": droplet_stats.get('error_droplets', 0)
                },
                "system": {
                    "uptime_seconds": system_metrics.get('uptime_seconds', 0),
                    "cpu_percent": system_metrics.get('cpu_percent', 0.0),
                    "memory_mb": system_metrics.get('memory_mb', 0),
                    "requests_per_minute": 0
                }
            },
            request
        )
        
    except Exception as e:
        log.error("metrics_summary_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get metrics summary: {str(e)}"
        )


# ============================================================================
# TASK METRICS
# ============================================================================

@router.get("/tasks/performance")
async def get_task_performance(
    request: Request,
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    time_range: str = Query("24h", description="Time range (1h, 24h, 7d, 30d)"),
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Get task performance metrics
    
    RESPONSE: UDC envelope with performance metrics
    """
    try:
        udc = get_udc_metadata(request)
        
        # Parse time range
        time_ranges = {
            "1h": "1 hour",
            "24h": "24 hours",
            "7d": "7 days",
            "30d": "30 days"
        }
        
        if time_range not in time_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time_range. Must be one of: {list(time_ranges.keys())}"
            )
        
        interval = time_ranges[time_range]
        
        # Build query with optional task_type filter
        task_type_condition = ""
        params = [interval]
        
        if task_type:
            task_type_condition = "AND task_type = $2"
            params.append(task_type)
        
        # Get performance metrics
        metrics = await db.fetchrow(
            f"""
            SELECT 
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                ROUND(
                    COUNT(*) FILTER (WHERE status = 'completed')::NUMERIC / 
                    NULLIF(COUNT(*) FILTER (WHERE status IN ('completed', 'failed')), 0) * 100,
                    2
                ) as success_rate,
                ROUND(
                    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) 
                    FILTER (WHERE status = 'completed'),
                    2
                ) as average_duration_seconds,
                ROUND(
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at)))
                    FILTER (WHERE status = 'completed'),
                    2
                ) as p50_duration_seconds,
                ROUND(
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at)))
                    FILTER (WHERE status = 'completed'),
                    2
                ) as p95_duration_seconds,
                ROUND(
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM (completed_at - created_at)))
                    FILTER (WHERE status = 'completed'),
                    2
                ) as p99_duration_seconds
            FROM tasks
            WHERE created_at > NOW() - INTERVAL $1
            {task_type_condition}
            """,
            *params
        )
        
        log.debug(
            "task_performance_metrics_generated",
            task_type=task_type or "all",
            time_range=time_range,
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "task_type": task_type or "all",
                "time_range": time_range,
                "metrics": {
                    "count": metrics['count'] or 0,
                    "success_rate": float(metrics['success_rate'] or 0),
                    "average_duration_seconds": float(metrics['average_duration_seconds'] or 0),
                    "p50_duration_seconds": float(metrics['p50_duration_seconds'] or 0),
                    "p95_duration_seconds": float(metrics['p95_duration_seconds'] or 0),
                    "p99_duration_seconds": float(metrics['p99_duration_seconds'] or 0)
                }
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("task_performance_metrics_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task performance: {str(e)}"
        )


@router.get("/tasks/by-type")
async def get_tasks_by_type(
    request: Request,
    time_range: str = Query("24h", description="Time range (1h, 24h, 7d, 30d)"),
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Get task counts grouped by task type
    
    RESPONSE: UDC envelope with task type breakdown
    """
    try:
        udc = get_udc_metadata(request)
        
        # Parse time range
        time_ranges = {
            "1h": "1 hour",
            "24h": "24 hours",
            "7d": "7 days",
            "30d": "30 days"
        }
        
        if time_range not in time_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time_range. Must be one of: {list(time_ranges.keys())}"
            )
        
        interval = time_ranges[time_range]
        
        # Get task counts by type
        results = await db.fetch(
            """
            SELECT 
                task_type,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status IN ('pending', 'assigned', 'in_progress')) as active
            FROM tasks
            WHERE created_at > NOW() - INTERVAL $1
            GROUP BY task_type
            ORDER BY total DESC
            """,
            interval
        )
        
        log.debug(
            "tasks_by_type_generated",
            time_range=time_range,
            task_types_count=len(results),
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "time_range": time_range,
                "task_types": [
                    {
                        "task_type": r['task_type'],
                        "total": r['total'],
                        "completed": r['completed'],
                        "failed": r['failed'],
                        "active": r['active']
                    }
                    for r in results
                ]
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error("tasks_by_type_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get tasks by type: {str(e)}"
        )


# ============================================================================
# DROPLET METRICS
# ============================================================================

@router.get("/droplets/{droplet_id}/performance")
async def get_droplet_performance(
    droplet_id: int,
    request: Request,
    time_range: str = Query("24h", description="Time range (1h, 24h, 7d, 30d)"),
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Get performance metrics for a specific droplet
    
    RESPONSE: UDC envelope with droplet performance metrics
    """
    try:
        udc = get_udc_metadata(request)
        
        # Parse time range
        time_ranges = {
            "1h": "1 hour",
            "24h": "24 hours",
            "7d": "7 days",
            "30d": "30 days"
        }
        
        if time_range not in time_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid time_range. Must be one of: {list(time_ranges.keys())}"
            )
        
        interval = time_ranges[time_range]
        
        # Get droplet info
        droplet = await db.fetchrow(
            "SELECT id, name FROM droplets WHERE droplet_id = $1",
            droplet_id
        )
        
        if not droplet:
            raise HTTPException(
                status_code=404,
                detail=f"Droplet {droplet_id} not found"
            )
        
        # Get task performance
        task_stats = await db.fetchrow(
            """
            SELECT 
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                AVG(EXTRACT(EPOCH FROM (completed_at - assigned_at))) 
                    FILTER (WHERE status = 'completed') as avg_response_time_seconds
            FROM tasks
            WHERE assigned_droplet_id = $1
              AND created_at > NOW() - INTERVAL $2
            """,
            droplet['id'],
            interval
        )
        
        # Calculate uptime
        uptime_stats = await db.fetchrow(
            """
            SELECT 
                COUNT(*) as total_checks,
                COUNT(*) FILTER (WHERE status = 'active') as active_checks
            FROM heartbeats
            WHERE droplet_id = $1
              AND received_at > NOW() - INTERVAL $2
            """,
            droplet['id'],
            interval
        )
        
        total_checks = uptime_stats['total_checks'] or 0
        active_checks = uptime_stats['active_checks'] or 0
        uptime_percent = (active_checks / total_checks * 100) if total_checks > 0 else 0.0
        
        log.debug(
            "droplet_performance_metrics_generated",
            droplet_id=droplet_id,
            time_range=time_range,
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "droplet_id": droplet_id,
                "droplet_name": droplet['name'],
                "time_range": time_range,
                "tasks_completed": task_stats['completed'] or 0,
                "tasks_failed": task_stats['failed'] or 0,
                "average_response_time_ms": round((task_stats['avg_response_time_seconds'] or 0) * 1000, 2),
                "uptime_percent": round(uptime_percent, 2)
            },
            request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(
            "droplet_performance_metrics_failed",
            droplet_id=droplet_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get droplet performance: {str(e)}"
        )


# ============================================================================
# ROUTING METRICS
# ============================================================================

@router.get("/routing")
async def get_routing_metrics_endpoint(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Get task routing metrics
    
    RESPONSE: UDC envelope with routing metrics
    """
    try:
        udc = get_udc_metadata(request)
        
        metrics = await get_routing_metrics()
        
        log.debug(
            "routing_metrics_generated",
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(metrics, request)
        
    except Exception as e:
        log.error("routing_metrics_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get routing metrics: {str(e)}"
        )


# ============================================================================
# SYSTEM HEALTH METRICS
# ============================================================================

@router.get("/system/health")
async def get_system_health(
    request: Request,
    token_data: dict = Depends(verify_jwt_token)
):
    """
    Get detailed system health metrics
    
    RESPONSE: UDC envelope with system health data
    """
    try:
        udc = get_udc_metadata(request)
        
        from app.database import check_database_health
        from app.services.websocket_manager import websocket_manager
        from app.main import scheduler
        
        # Check database health
        db_healthy = await check_database_health()
        
        # Get WebSocket stats
        ws_stats = websocket_manager.get_connection_count()
        
        # Get scheduler status
        scheduler_jobs = [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in scheduler.get_jobs()
        ]
        
        log.debug(
            "system_health_check_performed",
            db_healthy=db_healthy,
            udc_trace_id=udc.get('trace_id')
        )
        
        # Wrap and return response
        return wrap_udc_response(
            {
                "healthy": db_healthy,
                "database": {
                    "connected": db_healthy,
                    "pool_status": "operational" if db_healthy else "error"
                },
                "scheduler": {
                    "running": scheduler.running,
                    "jobs": scheduler_jobs,
                    "total_jobs": len(scheduler_jobs)
                },
                "websocket": ws_stats,
                "timestamp": udc.get('timestamp')
            },
            request
        )
        
    except Exception as e:
        log.error("system_health_check_failed", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get system health: {str(e)}"
        )