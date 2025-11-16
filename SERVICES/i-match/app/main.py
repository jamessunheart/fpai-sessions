"""
I MATCH - AI-Powered Matching Engine
FastAPI application with UBIC compliance
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
import psutil
import os
import stripe

from .config import settings
from .database import get_db, init_db, Customer, Provider, Match, Commission
from .matching_engine import MatchingEngine

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY") or settings.stripe_api_key

# Initialize application
app = FastAPI(
    title="I MATCH",
    description="AI-Powered Matching Engine - 20% Commission Revenue Model",
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

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()

# Initialize matching engine
matching_engine = MatchingEngine()

# Service state
service_state = {
    "start_time": datetime.now(),
    "total_matches_created": 0,
    "total_revenue_usd": 0.0
}

# Mount static files (AI-generated frontend)
# Static files are in parent directory's static folder
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# === Pydantic Models ===

class CustomerCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    service_type: str
    needs_description: str
    preferences: dict = {}
    values: dict = {}
    location_city: Optional[str] = None
    location_state: Optional[str] = None


class ProviderCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    company: Optional[str] = None
    service_type: str
    specialties: List[str] = []
    description: Optional[str] = None
    years_experience: Optional[int] = None
    certifications: List[str] = []
    website: Optional[str] = None
    pricing_model: Optional[str] = None
    price_range_low: Optional[float] = None
    price_range_high: Optional[float] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    serves_remote: bool = True
    commission_percent: float = 20.0


class MatchResponse(BaseModel):
    match_id: int
    customer_name: str
    provider_name: str
    match_score: int
    match_quality: str
    match_reasoning: str
    criteria_scores: dict
    status: str
    created_at: datetime


class CommissionCreate(BaseModel):
    match_id: int
    deal_value_usd: float


# === FRONTEND ROUTES ===

@app.get("/")
async def landing_page():
    """Serve I MATCH landing page"""
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="Landing page not found")

@app.get("/register")
async def register_page():
    """Serve customer registration form"""
    register_file = os.path.join(static_dir, "register.html")
    if os.path.exists(register_file):
        return FileResponse(register_file)
    raise HTTPException(status_code=404, detail="Registration page not found")

@app.get("/early-access")
async def early_access_page():
    """Serve $1 early access payment page"""
    early_access_file = os.path.join(static_dir, "early-access.html")
    if os.path.exists(early_access_file):
        return FileResponse(early_access_file)
    raise HTTPException(status_code=404, detail="Early access page not found")

@app.get("/success")
async def success_page():
    """Serve payment success page"""
    success_file = os.path.join(static_dir, "success.html")
    if os.path.exists(success_file):
        return FileResponse(success_file)
    raise HTTPException(status_code=404, detail="Success page not found")


# === UBIC COMPLIANCE ENDPOINTS ===

@app.get("/health")
async def health():
    """UBIC Endpoint 1: Health Status"""
    uptime_seconds = (datetime.now() - service_state["start_time"]).total_seconds()
    process = psutil.Process()

    return {
        "status": "healthy",
        "droplet_id": settings.droplet_id,
        "service_name": settings.service_name,
        "version": "1.0.0",
        "uptime_seconds": int(uptime_seconds),
        "total_matches": service_state["total_matches_created"],
        "total_revenue_usd": service_state["total_revenue_usd"],
        "memory_usage_mb": process.memory_info().rss / 1024 / 1024,
        "last_check": datetime.now()
    }


@app.get("/capabilities")
async def capabilities():
    """UBIC Endpoint 2: Capabilities"""
    return {
        "droplet_id": settings.droplet_id,
        "service_name": settings.service_name,
        "capabilities": [
            "AI-powered customer-provider matching",
            "Claude API deep compatibility analysis",
            "Multi-criteria scoring (expertise, values, communication, location, pricing)",
            "Automated commission tracking (20% model)",
            "Provider performance analytics",
            "Match feedback and algorithm refinement",
            "Batch matching for efficiency",
            "Revenue reporting and analytics"
        ],
        "supported_service_types": [
            "financial_advisor",
            "realtor",
            "business_consultant",
            "marketing_agency",
            "tax_professional",
            "insurance_agent"
        ],
        "features": {
            "ai_matching": True,
            "commission_automation": True,
            "multi_criteria_scoring": True,
            "batch_processing": True,
            "performance_tracking": True,
            "minimum_match_score": settings.minimum_match_score,
            "default_commission_percent": settings.default_commission_percent
        }
    }


@app.get("/state")
async def state(db: Session = Depends(get_db)):
    """UBIC Endpoint 3: Current State"""
    total_customers = db.query(Customer).count()
    active_customers = db.query(Customer).filter(Customer.active == True).count()
    total_providers = db.query(Provider).count()
    active_providers = db.query(Provider).filter(Provider.active == True, Provider.accepting_clients == True).count()
    total_matches = db.query(Match).count()
    pending_matches = db.query(Match).filter(Match.status == "pending").count()
    completed_matches = db.query(Match).filter(Match.status == "completed").count()

    return {
        "droplet_id": settings.droplet_id,
        "service_name": settings.service_name,
        "customers_total": total_customers,
        "customers_active": active_customers,
        "providers_total": total_providers,
        "providers_active": active_providers,
        "matches_total": total_matches,
        "matches_pending": pending_matches,
        "matches_completed": completed_matches,
        "revenue_total_usd": service_state["total_revenue_usd"],
        "last_updated": datetime.now()
    }


@app.get("/dependencies")
async def dependencies():
    """UBIC Endpoint 4: Dependencies"""
    import httpx

    deps = []

    # Check I PROACTIVE
    i_proactive_status = "available"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.i_proactive_url}/health", timeout=2.0)
            if response.status_code != 200:
                i_proactive_status = "degraded"
    except:
        i_proactive_status = "unavailable"

    deps.append({
        "service_name": "i-proactive",
        "url": settings.i_proactive_url,
        "required": False,
        "status": i_proactive_status
    })

    # Check Registry
    registry_status = "available"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.registry_url}/health", timeout=2.0)
            if response.status_code != 200:
                registry_status = "degraded"
    except:
        registry_status = "unavailable"

    deps.append({
        "service_name": "registry",
        "url": settings.registry_url,
        "required": False,
        "status": registry_status
    })

    return {
        "droplet_id": settings.droplet_id,
        "service_name": settings.service_name,
        "dependencies": deps
    }


@app.post("/message")
async def message(msg: dict):
    """UBIC Endpoint 5: Inter-service Messaging"""
    return {
        "message_id": f"msg-{datetime.now().timestamp()}",
        "status": "received",
        "response_payload": {"acknowledged": True}
    }


# === STRIPE PAYMENT ENDPOINTS ===

@app.post("/api/create-checkout-session")
async def create_checkout_session():
    """Create Stripe checkout session for $1 early access"""
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': 100,  # $1.00 in cents
                    'product_data': {
                        'name': 'I MATCH Early Access',
                        'description': 'Founding member with lifetime 50% discount',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url='https://fullpotential.com/imatch/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://fullpotential.com/imatch/early-access',
        )
        return {"id": checkout_session.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# === CUSTOMER ENDPOINTS ===

@app.post("/customers/create")
async def create_customer(customer_data: CustomerCreate, db: Session = Depends(get_db)):
    """Create a new customer"""

    # Check if email already exists
    existing = db.query(Customer).filter(Customer.email == customer_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    customer = Customer(**customer_data.dict())
    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


@app.get("/customers/list")
async def list_customers(
    active_only: bool = True,
    service_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List customers"""
    query = db.query(Customer)

    if active_only:
        query = query.filter(Customer.active == True)

    if service_type:
        query = query.filter(Customer.service_type == service_type)

    customers = query.all()
    return customers


@app.get("/customers/{customer_id}")
async def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Get customer by ID"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


# === PROVIDER ENDPOINTS ===

@app.post("/providers/create")
async def create_provider(provider_data: ProviderCreate, db: Session = Depends(get_db)):
    """Create a new provider"""

    # Check if email already exists
    existing = db.query(Provider).filter(Provider.email == provider_data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    provider = Provider(**provider_data.dict())
    db.add(provider)
    db.commit()
    db.refresh(provider)

    return provider


@app.get("/providers/list")
async def list_providers(
    active_only: bool = True,
    accepting_clients_only: bool = True,
    service_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List providers"""
    query = db.query(Provider)

    if active_only:
        query = query.filter(Provider.active == True)

    if accepting_clients_only:
        query = query.filter(Provider.accepting_clients == True)

    if service_type:
        query = query.filter(Provider.service_type == service_type)

    providers = query.all()
    return providers


@app.get("/providers/{provider_id}")
async def get_provider(provider_id: int, db: Session = Depends(get_db)):
    """Get provider by ID"""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


# === MATCHING ENDPOINTS ===

@app.post("/matches/find")
async def find_matches(
    customer_id: int,
    max_matches: int = 5,
    db: Session = Depends(get_db)
):
    """Find provider matches for a customer"""

    # Get customer
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Get available providers
    providers = db.query(Provider).filter(
        Provider.service_type == customer.service_type,
        Provider.active == True,
        Provider.accepting_clients == True
    ).all()

    # Find matches
    match_results = await matching_engine.find_matches(customer, providers, max_matches)

    return {
        "customer_id": customer_id,
        "customer_name": customer.name,
        "matches_found": len(match_results),
        "matches": match_results
    }


@app.post("/matches/create")
async def create_match(
    customer_id: int,
    provider_id: int,
    db: Session = Depends(get_db)
):
    """Create a match between customer and provider"""

    # Get customer and provider
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    provider = db.query(Provider).filter(Provider.id == provider_id).first()

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Run matching analysis
    match_result = await matching_engine._analyze_match(customer, provider)

    # Create match record
    match = Match(
        customer_id=customer_id,
        provider_id=provider_id,
        match_score=match_result["match_score"],
        match_reasoning=match_result["match_reasoning"],
        criteria_scores=match_result["criteria_scores"],
        status="pending"
    )

    db.add(match)
    db.commit()
    db.refresh(match)

    service_state["total_matches_created"] += 1

    return MatchResponse(
        match_id=match.id,
        customer_name=customer.name,
        provider_name=provider.name,
        match_score=match.match_score,
        match_quality=matching_engine.get_match_quality_label(match.match_score),
        match_reasoning=match.match_reasoning,
        criteria_scores=match.criteria_scores,
        status=match.status,
        created_at=match.created_at
    )


@app.get("/matches/list")
async def list_matches(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    provider_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List matches"""
    query = db.query(Match)

    if status:
        query = query.filter(Match.status == status)
    if customer_id:
        query = query.filter(Match.customer_id == customer_id)
    if provider_id:
        query = query.filter(Match.provider_id == provider_id)

    matches = query.all()
    return matches


@app.post("/matches/{match_id}/confirm-engagement")
async def confirm_engagement(
    match_id: int,
    deal_value_usd: float,
    db: Session = Depends(get_db)
):
    """Confirm engagement and create commission record"""

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Update match
    match.status = "completed"
    match.engagement_confirmed_at = datetime.now()
    match.deal_value_usd = deal_value_usd

    # Calculate commission
    provider = db.query(Provider).filter(Provider.id == match.provider_id).first()
    commission_amount = matching_engine.calculate_commission(
        deal_value_usd,
        provider.commission_percent
    )

    # Create commission record
    commission = Commission(
        match_id=match_id,
        deal_value_usd=deal_value_usd,
        commission_percent=provider.commission_percent,
        commission_amount_usd=commission_amount,
        status="pending",
        payment_due_date=datetime.now() + timedelta(days=30)
    )

    db.add(commission)

    # Update provider stats
    provider.total_matches += 1
    provider.successful_matches += 1

    # Update service state
    service_state["total_revenue_usd"] += commission_amount

    db.commit()

    return {
        "match_id": match_id,
        "status": "confirmed",
        "deal_value_usd": deal_value_usd,
        "commission_amount_usd": commission_amount,
        "commission_percent": provider.commission_percent,
        "payment_due_date": commission.payment_due_date
    }


# === COMMISSION ENDPOINTS ===

@app.get("/commissions/list")
async def list_commissions(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List commissions"""
    query = db.query(Commission)

    if status:
        query = query.filter(Commission.status == status)

    commissions = query.all()
    return commissions


@app.get("/commissions/stats")
async def commission_stats(db: Session = Depends(get_db)):
    """Get commission statistics"""

    total_commissions = db.query(Commission).count()
    pending_commissions = db.query(Commission).filter(Commission.status == "pending").count()
    paid_commissions = db.query(Commission).filter(Commission.status == "paid").count()

    # Calculate totals
    all_commissions = db.query(Commission).all()
    total_amount = sum(c.commission_amount_usd for c in all_commissions)
    pending_amount = sum(c.commission_amount_usd for c in all_commissions if c.status == "pending")
    paid_amount = sum(c.commission_amount_usd for c in all_commissions if c.status == "paid")

    return {
        "total_commissions": total_commissions,
        "pending_commissions": pending_commissions,
        "paid_commissions": paid_commissions,
        "total_amount_usd": total_amount,
        "pending_amount_usd": pending_amount,
        "paid_amount_usd": paid_amount
    }


# === ROOT ENDPOINT ===

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "I MATCH",
        "droplet_id": settings.droplet_id,
        "version": "1.0.0",
        "description": "AI-Powered Matching Engine - 20% Commission Revenue Model",
        "revenue_model": {
            "commission_percent": settings.default_commission_percent,
            "target_month_1": "$40-150K",
            "target_month_3": "$100-400K"
        },
        "features": {
            "ai_matching": "Claude API deep compatibility analysis",
            "commission_automation": "Automated tracking and invoicing",
            "multi_criteria_scoring": "Expertise, values, communication, location, pricing"
        },
        "ubic_endpoints": ["/health", "/capabilities", "/state", "/dependencies", "/message"],
        "documentation": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.service_host,
        port=settings.service_port,
        reload=True
    )
