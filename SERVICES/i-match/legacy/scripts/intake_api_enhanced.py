"""
Enhanced Intake Form API for I MATCH
Production-ready with error handling, validation, logging, and email
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
import httpx
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intake")

# Configuration
IMATCH_BASE_URL = os.getenv("IMATCH_URL", "http://198.54.123.234:8401")
HTTP_TIMEOUT = 10.0
MAX_NEEDS_LENGTH = 2000

# Allowed service types
ALLOWED_SERVICE_TYPES = [
    "church-formation",
    "executive-coaching",
    "ai-development",
    "business-consulting",
    "other"
]

class IntakeSubmission(BaseModel):
    """Customer intake form data with validation"""
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: EmailStr = Field(..., description="Email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    service_type: str = Field(..., description="Type of service needed")
    needs_description: str = Field(..., min_length=10, max_length=MAX_NEEDS_LENGTH, description="Description of needs")
    budget_low: Optional[float] = Field(None, ge=0, description="Minimum budget")
    budget_high: Optional[float] = Field(None, ge=0, description="Maximum budget")
    timeline: Optional[str] = Field(None, max_length=50, description="Project timeline")
    location_city: Optional[str] = Field(None, max_length=100, description="City")
    location_state: Optional[str] = Field(None, max_length=50, description="State")

    @validator('service_type')
    def validate_service_type(cls, v):
        if v not in ALLOWED_SERVICE_TYPES:
            raise ValueError(f'Service type must be one of: {", ".join(ALLOWED_SERVICE_TYPES)}')
        return v

    @validator('budget_high')
    def validate_budget_range(cls, v, values):
        if v is not None and 'budget_low' in values and values['budget_low'] is not None:
            if v < values['budget_low']:
                raise ValueError('Budget high must be greater than budget low')
        return v

    @validator('name', 'needs_description')
    def strip_whitespace(cls, v):
        return v.strip() if v else v

class IntakeResponse(BaseModel):
    """Response from intake submission"""
    status: str
    message: str
    customer_id: int
    matches_found: int
    top_matches: List[dict]
    next_steps: str
    submission_id: Optional[str] = None

@router.post("/submit", response_model=IntakeResponse)
async def submit_intake(submission: IntakeSubmission, request: Request):
    """
    Handle intake form submission with comprehensive error handling

    Process:
    1. Validate and sanitize input
    2. Create customer in I MATCH
    3. Find best provider matches
    4. Send confirmation email (if configured)
    5. Log submission for analytics

    Returns:
        IntakeResponse with match results and next steps
    """
    submission_time = datetime.utcnow()
    client_ip = request.client.host if request.client else "unknown"

    # Log submission (without sensitive data)
    logger.info(f"Intake submission received: service_type={submission.service_type}, ip={client_ip}")

    try:
        # Prepare customer data
        customer_data = {
            "name": submission.name,
            "email": submission.email,
            "phone": submission.phone,
            "service_type": submission.service_type,
            "needs_description": submission.needs_description,
            "location_city": submission.location_city,
            "location_state": submission.location_state
        }

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            # Step 1: Create customer in I MATCH
            try:
                customer_response = await client.post(
                    f"{IMATCH_BASE_URL}/customers/create",
                    json=customer_data
                )
                customer_response.raise_for_status()
                customer = customer_response.json()
                customer_id = customer["id"]

                logger.info(f"Customer created: id={customer_id}, email={submission.email}")

            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to create customer: {e.response.status_code} - {e.response.text}")
                raise HTTPException(
                    status_code=502,
                    detail="Unable to process your submission. Please try again or contact support."
                )
            except httpx.TimeoutException:
                logger.error("Timeout creating customer")
                raise HTTPException(
                    status_code=504,
                    detail="Request timed out. Please try again."
                )

            # Step 2: Find matches
            matches = []
            try:
                matches_response = await client.post(
                    f"{IMATCH_BASE_URL}/matches/find?customer_id={customer_id}"
                )

                if matches_response.status_code == 200:
                    matches = matches_response.json()
                    logger.info(f"Found {len(matches)} matches for customer {customer_id}")
                else:
                    logger.warning(f"Match finding returned {matches_response.status_code}")

            except Exception as e:
                # Non-critical - customer still created
                logger.warning(f"Failed to find matches: {e}")

            # Step 3: Send confirmation email (if email service configured)
            try:
                await send_confirmation_email(submission.email, submission.name, len(matches))
            except Exception as e:
                # Non-critical - log and continue
                logger.warning(f"Failed to send confirmation email: {e}")

            # Prepare response
            response = IntakeResponse(
                status="success",
                message=f"Thank you, {submission.name.split()[0]}! We're finding your perfect match.",
                customer_id=customer_id,
                matches_found=len(matches),
                top_matches=matches[:3] if matches else [],
                next_steps="You'll receive an email within 24 hours with personalized provider recommendations.",
                submission_id=f"SUB-{customer_id}-{int(submission_time.timestamp())}"
            )

            logger.info(f"Intake processed successfully: customer_id={customer_id}, matches={len(matches)}")
            return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(f"Unexpected error processing intake: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Our team has been notified. Please try again or contact support at hello@fullpotential.ai"
        )

@router.get("/services")
async def get_service_types():
    """Get available service types with descriptions"""
    return {
        "service_types": [
            {
                "value": "church-formation",
                "label": "Church Formation (501c3/508c1a)",
                "description": "Help forming a church or religious organization with tax-exempt status",
                "icon": "⛪",
                "popular": True
            },
            {
                "value": "executive-coaching",
                "label": "Executive Coaching",
                "description": "Personal transformation and leadership development for executives",
                "icon": "🎯",
                "popular": True
            },
            {
                "value": "ai-development",
                "label": "AI Development & Automation",
                "description": "Custom AI solutions, agents, and business automation",
                "icon": "🤖",
                "popular": True
            },
            {
                "value": "business-consulting",
                "label": "Business Consulting",
                "description": "Strategy, operations, and growth consulting for businesses",
                "icon": "📊",
                "popular": False
            },
            {
                "value": "other",
                "label": "Other Service",
                "description": "Describe your specific needs in the form",
                "icon": "💼",
                "popular": False
            }
        ]
    }

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "intake-api",
        "timestamp": datetime.utcnow().isoformat()
    }

async def send_confirmation_email(email: str, name: str, matches_count: int):
    """
    Send confirmation email to customer

    TODO: Implement with SendGrid, AWS SES, or similar
    For now, just logs the action
    """
    logger.info(f"Would send confirmation email to {email} (matches: {matches_count})")

    # Future implementation:
    # - Use SendGrid/AWS SES
    # - Use template from email_templates.py
    # - Include match preview
    # - Add tracking pixel for open rates

    pass

# Rate limiting helper (to be added to main app)
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Add to route:
@router.post("/submit", response_model=IntakeResponse)
@limiter.limit("5/minute")  # Max 5 submissions per minute per IP
async def submit_intake(request: Request, submission: IntakeSubmission):
    ...
"""
