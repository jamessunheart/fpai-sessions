"""Task monitoring endpoints."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import TaskRead
from app.core.config import settings
from app.core.database import get_db
from app.services import list_tasks, update_task_status
from app.telemetry import client as telemetry_client

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("", response_model=list[TaskRead])
async def get_recent_tasks(limit: int = 50, session: AsyncSession = Depends(get_db)):
    return await list_tasks(session, limit=limit)


@router.post("/{task_id}/status", response_model=TaskRead)
async def set_task_status(
    task_id: str,
    status_payload: dict,
    session: AsyncSession = Depends(get_db),
):
    task = await update_task_status(
        session,
        uuid.UUID(task_id),
        status=status_payload.get("status", "processing"),
        result_data=status_payload.get("result"),
        error=status_payload.get("error"),
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if telemetry_client:
        telemetry_client.capture(
            settings.service_name,
            "task_status_updated",
            {
                "mission_id": settings.mission_id,
                "task_id": task_id,
                "status": task.status,
                "error": task.error,
            },
        )
    return task

