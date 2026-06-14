"""
Simple Intake Form API for I MATCH
Handles customer intake submissions and creates matches
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import httpx
from typing import Optional

router = APIRouter(prefix="/api/intake")

class IntakeSubmission(BaseModel):
    """Customer intake form data"""
    name: str
    email: EmailStr
    phone: Optional[str] = None
    service_type: str
    needs_description: str
    budget_low: Optional[float] = None
    budget_high: Optional[float] = None
    timeline: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None

@router.post("/submit")
async def submit_intake(submission: IntakeSubmission):
    """
    Handle intake form submission
    1. Create customer in I MATCH
    2. Find best matches
    3. Send confirmation email (future)
    """
    try:
        # Create customer in I MATCH
        customer_data = {
            "name": submission.name,
            "email": submission.email,
            "phone": submission.phone,
            "service_type": submission.service_type,
            "needs_description": submission.needs_description,
            "location_city": submission.location_city,
            "location_state": submission.location_state
        }

        async with httpx.AsyncClient() as client:
            # Create customer
            customer_response = await client.post(
                "http://198.54.123.234:8401/customers/create",
                json=customer_data
            )

            if customer_response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create customer: {customer_response.text}"
                )

            customer = customer_response.json()
            customer_id = customer["id"]

            # Find matches
            matches_response = await client.post(
                f"http://198.54.123.234:8401/matches/find?customer_id={customer_id}"
            )

            matches = []
            if matches_response.status_code == 200:
                matches = matches_response.json()

            return {
                "status": "success",
                "message": "Thank you! We're finding your perfect match.",
                "customer_id": customer_id,
                "matches_found": len(matches),
                "top_matches": matches[:3] if matches else [],
                "next_steps": "You'll receive an email within 24 hours with your personalized provider recommendations."
            }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Intake processing failed: {str(e)}"
        )


@router.get("/services")
async def get_service_types():
    """Get available service types"""
    return {
        "service_types": [
            {
                "value": "church-formation",
                "label": "Church Formation (501c3/508c1a)",
                "description": "Help forming a church or religious organization"
            },
            {
                "value": "executive-coaching",
                "label": "Executive Coaching",
                "description": "Personal transformation and leadership development"
            },
            {
                "value": "ai-development",
                "label": "AI Development & Automation",
                "description": "Custom AI solutions and business automation"
            },
            {
                "value": "business-consulting",
                "label": "Business Consulting",
                "description": "Strategy, operations, and growth consulting"
            },
            {
                "value": "other",
                "label": "Other",
                "description": "Describe your needs in the form"
            }
        ]
    }
