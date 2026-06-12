"""
Jobs Web Router
Public-facing job board pages
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))

DATA_PATH = Path("/Users/jamessunheart/Development/agents/services/jobs/data")
JOBS_FILE = DATA_PATH / "jobs.json"


@router.get("/jobs", response_class=HTMLResponse)
async def jobs_list_page(request: Request):
    """Public job listings page"""
    try:
        # Load jobs
        jobs = json.loads(JOBS_FILE.read_text())
        open_jobs = [j for j in jobs if j["status"] == "open"]
        open_jobs.sort(key=lambda x: x["posted_at"], reverse=True)

        return templates.TemplateResponse("jobs_list.html", {
            "request": request,
            "jobs": open_jobs,
            "total_jobs": len(open_jobs)
        })

    except Exception as e:
        logger.error(f"Error loading jobs page: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load jobs"
        })


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail_page(request: Request, job_id: str):
    """Job detail and application page"""
    try:
        jobs = json.loads(JOBS_FILE.read_text())
        job = next((j for j in jobs if j["id"] == job_id), None)

        if not job:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Job not found"
            })

        return templates.TemplateResponse("job_detail.html", {
            "request": request,
            "job": job
        })

    except Exception as e:
        logger.error(f"Error loading job detail: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Failed to load job details"
        })
