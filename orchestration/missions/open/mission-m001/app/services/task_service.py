"""Domain logic for task lifecycle."""
import uuid
from typing import Any, Dict

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task


async def enqueue_task(session: AsyncSession, payload: Dict[str, Any], priority: int = 5) -> Task:
    task = Task(payload=payload, priority=priority)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


async def list_tasks(session: AsyncSession, limit: int = 50) -> list[Task]:
    result = await session.execute(select(Task).order_by(Task.created_at.desc()).limit(limit))
    return result.scalars().all()


async def update_task_status(
    session: AsyncSession,
    task_id: uuid.UUID,
    *,
    status: str,
    result_data: Dict[str, Any] | None = None,
    error: str | None = None,
) -> Task | None:
    stmt = (
        update(Task)
        .where(Task.task_id == task_id)
        .values(status=status, result=result_data, error=error)
        .returning(Task)
    )
    result = await session.execute(stmt)
    task = result.scalar_one_or_none()
    if task:
        await session.commit()
    return task

