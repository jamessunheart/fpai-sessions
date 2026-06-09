"""
AUTONOMOUS INCOME ENGINE
========================
This service autonomously generates leads and nurtures prospects for revenue.

It works with GOD (the system intelligence) to:
1. Generate personalized outreach content using AI Brain
2. Post content to configured channels
3. Capture and qualify leads
4. Track revenue opportunities

Port: 8560 (or next available)
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import httpx
import json
import asyncio

app = FastAPI(
    title="Autonomous Income Engine",
    description="AI-powered lead generation and revenue optimization",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
AI_BRAIN_URL = "http://162.0.208.88:8101"
SERVICES = {
    "ai_automation": {
        "name": "AI Automation Services",
        "port": 8750,
        "url": "http://198.54.123.234:8750",
        "payment_links": {
            "employee": "https://buy.stripe.com/6oU5kCesF2xncRnePj9R608",
            "team": "https://buy.stripe.com/5kQcN470d0pf2cJ4aF9R609",
            "department": "https://buy.stripe.com/8x27sK98l0pf5oVcHb9R60a"
        }
    },
    "i_match": {
        "name": "I-MATCH Service Provider Matching",
        "port": 8401,
        "url": "http://198.54.123.234:8401"
    },
    "whaletrack": {
        "name": "WhaleTrack Trading Signals",
        "port": 8600,
        "url": "http://198.54.123.234:8600"
    }
}

# In-memory storage (would be database in production)
LEADS = []
OUTREACH_QUEUE = []
CONTENT_LIBRARY = []
REVENUE_LOG = []


class Lead(BaseModel):
    name: str
    email: str
    company: Optional[str] = None
    service_interest: str
    source: str
    score: int = 50
    status: str = "new"  # new, contacted, qualified, converted
    created_at: datetime = None


class OutreachRequest(BaseModel):
    target_role: str = "COO"
    target_industry: Optional[str] = None
    service: str = "ai_automation"
    tone: str = "warm"
    channel: str = "linkedin"


class ContentRequest(BaseModel):
    content_type: str  # post, dm, email, ad
    service: str
    target_audience: str
    key_benefit: str


# ============================================================================
# AI CONTENT GENERATION
# ============================================================================

async def generate_with_ai_brain(prompt: str, max_tokens: int = 500) -> str:
    """Generate content using AI Brain service"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{AI_BRAIN_URL}/generate",
                json={"prompt": prompt, "max_tokens": max_tokens}
            )
            response.raise_for_status()
            result = response.json()
            return result.get("text", "")
        except Exception as e:
            return f"Error generating content: {e}"


@app.post("/api/generate/outreach")
async def generate_outreach(request: OutreachRequest):
    """Generate personalized outreach message"""
    
    service_info = SERVICES.get(request.service, SERVICES["ai_automation"])
    
    prompt = f"""Write a compelling {request.channel} DM message (under 300 characters) 
from James, founder of Full Potential AI, to a {request.target_role} at a company.

Service being offered: {service_info['name']}
Tone: {request.tone}, professional, not salesy

Focus on:
- Saving time on repetitive tasks
- Offering a free audit/consultation
- Being genuinely helpful

Output ONLY the message text, no quotes or formatting."""

    content = await generate_with_ai_brain(prompt, 200)
    
    return {
        "channel": request.channel,
        "target": request.target_role,
        "service": request.service,
        "content": content,
        "generated_at": datetime.now().isoformat()
    }


@app.post("/api/generate/content")
async def generate_content(request: ContentRequest):
    """Generate marketing content"""
    
    service_info = SERVICES.get(request.service, SERVICES["ai_automation"])
    
    prompts = {
        "post": f"""Write a LinkedIn post about {service_info['name']} for {request.target_audience}.
Key benefit to highlight: {request.key_benefit}
Include a clear call-to-action.
Keep it under 1000 characters.
Use emojis sparingly.
Output ONLY the post text.""",

        "dm": f"""Write a short LinkedIn DM (under 300 chars) about {service_info['name']}.
Target: {request.target_audience}
Focus on: {request.key_benefit}
Be warm and helpful, not salesy.""",

        "email": f"""Write a cold email subject line and body about {service_info['name']}.
Target: {request.target_audience}
Key benefit: {request.key_benefit}
Keep it concise and value-focused.
Format: SUBJECT: [subject]\n\n[body]""",

        "ad": f"""Write a Facebook/LinkedIn ad headline and body for {service_info['name']}.
Target: {request.target_audience}
Key benefit: {request.key_benefit}
Format: HEADLINE: [headline]\nBODY: [body]"""
    }
    
    prompt = prompts.get(request.content_type, prompts["post"])
    content = await generate_with_ai_brain(prompt, 500)
    
    # Store in library
    CONTENT_LIBRARY.append({
        "type": request.content_type,
        "service": request.service,
        "content": content,
        "created_at": datetime.now().isoformat()
    })
    
    return {
        "content_type": request.content_type,
        "service": request.service,
        "content": content,
        "generated_at": datetime.now().isoformat()
    }


# ============================================================================
# LEAD MANAGEMENT
# ============================================================================

@app.post("/api/leads/capture")
async def capture_lead(lead: Lead):
    """Capture a new lead"""
    lead.created_at = datetime.now()
    
    # Score lead based on signals
    if lead.company:
        lead.score += 10
    if lead.service_interest in ["ai_automation", "ai_department"]:
        lead.score += 20
    
    LEADS.append(lead.dict())
    
    return {
        "status": "captured",
        "lead_id": len(LEADS),
        "score": lead.score
    }


@app.get("/api/leads/list")
async def list_leads(status: Optional[str] = None):
    """List all leads"""
    if status:
        return [l for l in LEADS if l.get("status") == status]
    return LEADS


@app.get("/api/leads/stats")
async def lead_stats():
    """Get lead statistics"""
    total = len(LEADS)
    by_status = {}
    by_service = {}
    
    for lead in LEADS:
        status = lead.get("status", "unknown")
        service = lead.get("service_interest", "unknown")
        by_status[status] = by_status.get(status, 0) + 1
        by_service[service] = by_service.get(service, 0) + 1
    
    return {
        "total_leads": total,
        "by_status": by_status,
        "by_service": by_service,
        "conversion_rate": by_status.get("converted", 0) / total if total > 0 else 0
    }


# ============================================================================
# OUTREACH AUTOMATION
# ============================================================================

@app.post("/api/outreach/queue")
async def queue_outreach(request: OutreachRequest):
    """Queue an outreach message for sending"""
    
    # Generate content
    content_result = await generate_outreach(request)
    
    outreach = {
        "id": len(OUTREACH_QUEUE) + 1,
        "channel": request.channel,
        "target_role": request.target_role,
        "content": content_result["content"],
        "status": "queued",
        "created_at": datetime.now().isoformat()
    }
    
    OUTREACH_QUEUE.append(outreach)
    
    return outreach


@app.get("/api/outreach/queue")
async def get_outreach_queue():
    """Get pending outreach messages"""
    return [o for o in OUTREACH_QUEUE if o.get("status") == "queued"]


@app.post("/api/outreach/{outreach_id}/sent")
async def mark_outreach_sent(outreach_id: int):
    """Mark an outreach as sent"""
    for outreach in OUTREACH_QUEUE:
        if outreach.get("id") == outreach_id:
            outreach["status"] = "sent"
            outreach["sent_at"] = datetime.now().isoformat()
            return outreach
    raise HTTPException(status_code=404, detail="Outreach not found")


# ============================================================================
# REVENUE TRACKING
# ============================================================================

@app.post("/api/revenue/log")
async def log_revenue(
    amount: float,
    source: str,
    lead_id: Optional[int] = None,
    notes: Optional[str] = None
):
    """Log a revenue event"""
    entry = {
        "id": len(REVENUE_LOG) + 1,
        "amount": amount,
        "source": source,
        "lead_id": lead_id,
        "notes": notes,
        "timestamp": datetime.now().isoformat()
    }
    REVENUE_LOG.append(entry)
    
    # Update lead status if applicable
    if lead_id:
        for lead in LEADS:
            if LEADS.index(lead) + 1 == lead_id:
                lead["status"] = "converted"
    
    return entry


@app.get("/api/revenue/summary")
async def revenue_summary():
    """Get revenue summary"""
    total = sum(r.get("amount", 0) for r in REVENUE_LOG)
    by_source = {}
    
    for entry in REVENUE_LOG:
        source = entry.get("source", "unknown")
        by_source[source] = by_source.get(source, 0) + entry.get("amount", 0)
    
    return {
        "total_revenue": total,
        "by_source": by_source,
        "transaction_count": len(REVENUE_LOG),
        "average_deal": total / len(REVENUE_LOG) if REVENUE_LOG else 0
    }


# ============================================================================
# DASHBOARD & HEALTH
# ============================================================================

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "autonomous-income-engine",
        "version": "1.0.0",
        "leads": len(LEADS),
        "outreach_queued": len([o for o in OUTREACH_QUEUE if o.get("status") == "queued"]),
        "content_generated": len(CONTENT_LIBRARY),
        "total_revenue": sum(r.get("amount", 0) for r in REVENUE_LOG),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/dashboard")
async def dashboard():
    """Get complete dashboard data"""
    return {
        "leads": await lead_stats(),
        "outreach": {
            "queued": len([o for o in OUTREACH_QUEUE if o.get("status") == "queued"]),
            "sent": len([o for o in OUTREACH_QUEUE if o.get("status") == "sent"])
        },
        "content": {
            "total": len(CONTENT_LIBRARY),
            "by_type": {}  # Could aggregate by type
        },
        "revenue": await revenue_summary(),
        "services": SERVICES,
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# BULK CONTENT GENERATION (For immediate use)
# ============================================================================

@app.post("/api/generate/bulk")
async def generate_bulk_content():
    """Generate a batch of ready-to-use marketing content"""
    
    results = {
        "linkedin_posts": [],
        "linkedin_dms": [],
        "email_templates": [],
        "generated_at": datetime.now().isoformat()
    }
    
    # Generate LinkedIn post
    post_prompt = """Write a compelling LinkedIn post from James, founder of Full Potential AI, about AI automation services.

Key points to cover:
- AI agents that work 24/7 cost 30% of a human employee
- From $1,500/month (50% pilot discount)
- Free automation audit available
- Perfect for businesses spending >$5K/month on repetitive tasks

Include:
- One attention-grabbing opening line
- 3-4 bullet points of benefits
- Clear call-to-action
- Relevant hashtags at the end

Keep it under 1000 characters. Be authentic and helpful, not salesy."""

    post = await generate_with_ai_brain(post_prompt, 500)
    results["linkedin_posts"].append(post)
    
    # Generate LinkedIn DMs for different roles
    roles = ["COO", "VP Operations", "CEO of a 50-200 person company"]
    for role in roles:
        dm_prompt = f"""Write a short LinkedIn DM (under 300 chars) from James at Full Potential AI to a {role}.
Offer a free AI automation audit. Be warm and genuine, not salesy.
Focus on saving them time on repetitive tasks.
Output ONLY the message text."""
        
        dm = await generate_with_ai_brain(dm_prompt, 150)
        results["linkedin_dms"].append({"role": role, "message": dm})
    
    # Generate email template
    email_prompt = """Write a cold email about AI automation services.

From: James, Full Potential AI
To: Operations leaders at mid-size companies

Offer: Free AI automation audit
Price context: $1,500-$7,500/month (50% pilot discount available)
Key benefit: 24/7 AI employees at 30% the cost of humans

Format:
SUBJECT: [compelling subject line under 50 chars]

[email body - keep it concise, 3-4 short paragraphs max]

Best,
James
Founder, Full Potential AI"""

    email = await generate_with_ai_brain(email_prompt, 400)
    results["email_templates"].append(email)
    
    # Store all in content library
    for post in results["linkedin_posts"]:
        CONTENT_LIBRARY.append({"type": "post", "content": post, "created_at": datetime.now().isoformat()})
    for dm in results["linkedin_dms"]:
        CONTENT_LIBRARY.append({"type": "dm", "content": dm, "created_at": datetime.now().isoformat()})
    for email in results["email_templates"]:
        CONTENT_LIBRARY.append({"type": "email", "content": email, "created_at": datetime.now().isoformat()})
    
    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8580)







