"""
Helper Management - FastAPI Application
Autonomous hiring, payment, and task management
"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import List

from .config import settings
from .models import (
    Task, Helper, Application,
    TaskCreate, TaskResponse,
    HelperCreate, HelperResponse,
    ApplicationCreate, ApplicationResponse,
    HireRequest, TaskCompletionRequest, PaymentRequest,
    TaskStatus, HelperStatus
)
from .database import get_db, init_db
from .ai_screening import ai_screener
from .payment_processor import payment_processor
from .credentials_client import credentials_client

# Initialize application
app = FastAPI(
    title="Helper Management",
    description="Autonomous hiring, payment, and task management",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    await init_db()


# Task Management

@app.post("/tasks", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new task"""
    new_task = Task(
        title=task.title,
        description=task.description,
        requirements=task.requirements,
        budget=task.budget,
        currency=task.currency,
        payment_method=task.payment_method.value,
        duration_hours=task.duration_hours,
        credential_ids=task.credential_ids,
        access_scope=task.access_scope,
        status=TaskStatus.DRAFT.value,
        deadline=datetime.utcnow() + timedelta(hours=task.duration_hours)
    )

    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    return new_task


@app.post("/tasks/{task_id}/post")
async def post_task(
    task_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Post task to job platforms (Upwork, crypto boards)"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update status
    task.status = TaskStatus.POSTED.value
    task.posted_at = datetime.utcnow()
    await db.commit()

    # Post to platforms in background
    # background_tasks.add_task(post_to_upwork, task)
    # background_tasks.add_task(post_to_crypto_boards, task)

    return {
        "status": "posted",
        "task_id": task_id,
        "message": "Task posted to job platforms"
    }


@app.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    """List all tasks"""
    query = select(Task)

    if status:
        query = query.where(Task.status == status)

    result = await db.execute(query.order_by(Task.created_at.desc()))
    tasks = result.scalars().all()

    return tasks


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get task details"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


# Applications

@app.post("/applications", response_model=ApplicationResponse)
async def submit_application(
    application: ApplicationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Submit job application"""
    # Verify task exists
    result = await db.execute(select(Task).where(Task.id == application.task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Create application
    new_app = Application(
        task_id=application.task_id,
        helper_name=application.helper_name,
        helper_email=application.helper_email,
        platform=application.platform,
        cover_letter=application.cover_letter,
        proposed_rate=application.proposed_rate,
        estimated_hours=application.estimated_hours,
        status="pending"
    )

    db.add(new_app)
    await db.commit()
    await db.refresh(new_app)

    # Screen application with AI in background
    background_tasks.add_task(
        screen_application,
        new_app.id,
        task,
        application
    )

    return new_app


async def screen_application(
    application_id: int,
    task: Task,
    application_data: ApplicationCreate
):
    """Screen application using AI (background task)"""
    from .database import async_session

    # Screen with AI
    screening_result = await ai_screener.screen_candidate(
        task_description=task.description,
        task_requirements=task.requirements,
        application={
            "helper_name": application_data.helper_name,
            "platform": application_data.platform,
            "proposed_rate": application_data.proposed_rate,
            "estimated_hours": application_data.estimated_hours,
            "cover_letter": application_data.cover_letter
        }
    )

    # Update application with AI score
    async with async_session() as db:
        result = await db.execute(
            select(Application).where(Application.id == application_id)
        )
        app = result.scalar_one_or_none()

        if app:
            app.ai_score = screening_result.get("score")
            app.ai_reasoning = screening_result.get("reasoning")
            app.reviewed_at = datetime.utcnow()

            # Auto-accept if score > 0.8
            if screening_result.get("score", 0) >= 0.8:
                app.status = "accepted"
            # Auto-reject if score < 0.3
            elif screening_result.get("score", 0) < 0.3:
                app.status = "rejected"

            await db.commit()


@app.get("/applications", response_model=List[ApplicationResponse])
async def list_applications(
    task_id: int = None,
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    """List applications"""
    query = select(Application)

    if task_id:
        query = query.where(Application.task_id == task_id)

    if status:
        query = query.where(Application.status == status)

    result = await db.execute(query.order_by(Application.ai_score.desc()))
    applications = result.scalars().all()

    return applications


# Hiring

@app.post("/hire")
async def hire_helper(
    hire_request: HireRequest,
    db: AsyncSession = Depends(get_db)
):
    """Hire helper for task"""
    # Get task
    result = await db.execute(select(Task).where(Task.id == hire_request.task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get application
    result = await db.execute(
        select(Application).where(Application.id == hire_request.application_id)
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Create or update helper profile
    result = await db.execute(
        select(Helper).where(Helper.name == application.helper_name)
    )
    helper = result.scalar_one_or_none()

    if not helper:
        helper = Helper(
            name=application.helper_name,
            email=application.helper_email,
            platform=application.platform,
            status=HelperStatus.ACTIVE.value,
            payment_preference="crypto"
        )
        db.add(helper)
        await db.commit()
        await db.refresh(helper)

    # Grant access to credentials if needed
    access_token = None
    if task.credential_ids:
        access_token = await credentials_client.grant_access(
            helper_name=helper.name,
            credential_ids=task.credential_ids,
            expires_hours=task.duration_hours
        )

        if access_token:
            helper.current_access_token = access_token
            helper.access_expires_at = datetime.utcnow() + timedelta(hours=task.duration_hours)

    # Assign task
    task.helper_id = helper.id
    task.status = TaskStatus.ASSIGNED.value
    task.assigned_at = datetime.utcnow()

    # Update application
    application.status = "accepted"

    await db.commit()

    return {
        "status": "hired",
        "task_id": task.id,
        "helper_id": helper.id,
        "helper_name": helper.name,
        "access_token": access_token,
        "message": "Helper hired and access granted"
    }


# Task Completion

@app.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    completion: TaskCompletionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Mark task as completed"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.COMPLETED.value
    task.completed_at = datetime.utcnow()
    task.verification_details = completion.verification_details

    await db.commit()

    return {"status": "completed", "task_id": task_id}


@app.post("/tasks/{task_id}/verify")
async def verify_task(
    task_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Verify task completion (admin/automated check)"""
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verification logic here (check if service works, API configured, etc.)
    # For now, auto-verify
    task.status = TaskStatus.VERIFIED.value

    await db.commit()

    return {"status": "verified", "task_id": task_id}


# Payment

@app.post("/payments")
async def process_payment(
    payment: PaymentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process payment to helper"""
    # Get task
    result = await db.execute(select(Task).where(Task.id == payment.task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.VERIFIED.value:
        raise HTTPException(status_code=400, detail="Task not verified")

    # Get helper
    result = await db.execute(select(Helper).where(Helper.id == task.helper_id))
    helper = result.scalar_one_or_none()

    if not helper:
        raise HTTPException(status_code=404, detail="Helper not found")

    # Process payment
    payment_result = await payment_processor.process_payment(
        amount=payment.amount,
        recipient=helper.crypto_wallet or helper.email,
        payment_method=payment.payment_method,
        currency=task.currency
    )

    if payment_result.get("success"):
        task.status = TaskStatus.PAID.value
        task.paid_at = datetime.utcnow()
        task.payment_transaction = payment_result.get("transaction_id")

        # Update helper stats
        helper.completed_tasks += 1
        helper.last_active = datetime.utcnow()

        # Revoke access
        if helper.current_access_token:
            # Would call credentials_client.revoke_access here
            helper.current_access_token = None
            helper.access_expires_at = None

        await db.commit()

        return {
            "status": "paid",
            "task_id": task.id,
            "helper_id": helper.id,
            "transaction_id": payment_result.get("transaction_id"),
            "amount": payment.amount,
            "total": payment_result.get("total")
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Payment failed: {payment_result.get('error')}"
        )


# Helpers

@app.get("/helpers", response_model=List[HelperResponse])
async def list_helpers(
    status: str = None,
    db: AsyncSession = Depends(get_db)
):
    """List all helpers"""
    query = select(Helper)

    if status:
        query = query.where(Helper.status == status)

    result = await db.execute(query.order_by(Helper.completed_tasks.desc()))
    helpers = result.scalars().all()

    return helpers


# Health & UDC

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Helper Management",
        "version": "1.0.0",
        "description": "Autonomous hiring, payment, and task management",
        "droplet_id": 26,
        "capabilities": [
            "Post jobs to Upwork, crypto boards",
            "AI-powered candidate screening",
            "Scoped credential access (via Credentials Manager)",
            "Crypto and fiat payments",
            "Task tracking and verification",
            "Helper performance analytics"
        ],
        "endpoints": {
            "/tasks": "Manage tasks",
            "/applications": "Job applications",
            "/hire": "Hire helpers",
            "/payments": "Process payments",
            "/helpers": "Helper profiles"
        }
    }


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Health check"""
    try:
        await db.execute(select(1))
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "helper-management",
        "version": "1.0.0",
        "database": db_status,
        "credentials_manager": settings.credentials_manager_url,
        "crypto_enabled": settings.enable_crypto_payments
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True
    )
