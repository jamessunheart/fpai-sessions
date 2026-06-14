"""Task intake endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import TaskAssignment, TaskRead
from app.core.config import settings
from app.core.database import get_db
from app.services import enqueue_task
from app.telemetry import client as telemetry_client

router = APIRouter(prefix="/message", tags=["Tasks"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_202_ACCEPTED)
async def receive_task(message: TaskAssignment, session: AsyncSession = Depends(get_db)):
    task = await enqueue_task(session, payload=message.payload)
    if telemetry_client:
        telemetry_client.capture(
            settings.service_name,
            "task_enqueued",
            {
                "mission_id": settings.mission_id,
                "task_id": str(task.task_id),
                "priority": task.priority,
                "source": message.from_service,
            },
        )
    return task

