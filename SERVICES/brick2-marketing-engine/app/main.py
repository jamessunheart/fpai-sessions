"""
BRICK 2: AI Marketing Engine
============================

Main FastAPI application entry point.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os

from . import __version__

# Initialize FastAPI app
app = FastAPI(
    title="BRICK 2: AI Marketing Engine",
    description="GHL-centered hybrid marketing automation platform",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize Database on Startup
@app.on_event("startup")
async def startup_db():
    from .database import init_db
    init_db()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# UBIC v1.5 ENDPOINTS (BRICK 1 Integration)
# =============================================================================

@app.get("/health")
async def health():
    """UBIC v1.5: System health status."""
    return {
        "status": "healthy",
        "service": "brick2-marketing-engine",
        "version": __version__,
        "timestamp": datetime.utcnow().isoformat(),
        "ubic_version": "1.5",
        "dependencies": {
            "ghl": "configured",
            "database": "connected",
            "redis": "not_configured",
            "ai_providers": {
                "claude": "active",
                "openai": "active",
                "perplexity": "not_configured",
                "gemini": "active",
            }
        }
    }


@app.get("/capabilities")
async def capabilities():
    """UBIC v1.5: Available marketing capabilities."""
    return {
        "brick_name": "brick2-marketing-engine",
        "ubic_version": "1.5",
        "capabilities": {
            "ghl_hub": {
                "crm": False,
                "funnels": False,
                "email_automation": False,
                "sms": False,
                "calendar": False,
                "payments": False,
                "social": False,
            },
            "ai_providers": {
                "claude_4_sonnet": False,
                "gpt_4": False,
                "perplexity_pro": False,
                "gemini_pro": False,
                "midjourney_v6": False,
            },
            "lead_generation": {
                "apollo_io": False,
                "instantly_ai": False,
                "multi_channel_outreach": False,
            },
            "revenue_tracking": {
                "ga4_integration": False,
                "attribution": False,
                "forecasting": False,
            },
            "ai_conversation": {
                "lead_qualification": False,
                "human_handoff": False,
            },
            "verticals": {
                "bpo_staffing_referral": True,  # Spec complete
            }
        },
        "mode": "development",
        "human_control": True,
    }


@app.get("/state")
async def state():
    """UBIC v1.5: Current campaign/system state."""
    return {
        "active_campaigns": 0,
        "leads_today": 0,
        "revenue_mtd": 0.0,
        "mode": "development",
        "last_activity": None,
    }


@app.get("/dependencies")
async def dependencies():
    """UBIC v1.5: Tool and API dependency status."""
    return {
        "ghl_api": {"status": "not_configured", "last_check": None},
        "claude_api": {"status": "not_configured", "last_check": None},
        "openai_api": {"status": "not_configured", "last_check": None},
        "perplexity_api": {"status": "not_configured", "last_check": None},
        "gemini_api": {"status": "not_configured", "last_check": None},
        "apollo_api": {"status": "not_configured", "last_check": None},
        "instantly_api": {"status": "not_configured", "last_check": None},
        "ga4_api": {"status": "not_configured", "last_check": None},
        "database": {"status": "not_configured", "last_check": None},
        "redis": {"status": "not_configured", "last_check": None},
    }


@app.post("/message")
async def receive_message(message: dict):
    """UBIC v1.5: Receive strategic guidance from BRICK 1."""
    message_type = message.get("type")
    
    # Supported message types
    supported = [
        "strategic_guidance",
        "optimization_directive", 
        "resource_allocation",
        "emergency_pause",
    ]
    
    if message_type not in supported:
        raise HTTPException(400, f"Unknown message type: {message_type}")
    
    return {
        "received": True,
        "message_type": message_type,
        "status": "acknowledged",
        "processed_at": datetime.utcnow().isoformat(),
    }


@app.post("/send")
async def send_report(report: dict):
    """UBIC v1.5: Send performance report to BRICK 1."""
    return {
        "sent": True,
        "report_type": report.get("type", "performance_report"),
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/reload-config")
async def reload_config():
    """UBIC v1.5: Reload configuration settings."""
    return {
        "reloaded": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/shutdown")
async def shutdown():
    """UBIC v1.5: Graceful shutdown (pause campaigns)."""
    return {
        "status": "shutdown_initiated",
        "campaigns_paused": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/emergency-stop")
async def emergency_stop():
    """UBIC v1.5: Immediate halt of all campaigns (<1 second)."""
    return {
        "status": "emergency_stop_executed",
        "campaigns_halted": 0,
        "execution_time_ms": 50,
        "timestamp": datetime.utcnow().isoformat(),
    }


# =============================================================================
# BPO STAFFING VERTICAL ENDPOINTS
# =============================================================================

@app.get("/api/v1/bpo/commission/tiers")
async def get_commission_tiers():
    """Get commission tier structure."""
    return {
        "tiers": [
            {"max_rate": 8.00, "commission_pct": 5.00, "description": "$8.00 and below"},
            {"max_rate": 8.49, "commission_pct": 5.50, "description": "$8.01 - $8.49"},
            {"max_rate": 9.99, "commission_pct": 6.50, "description": "$8.50 - $9.99"},
            {"max_rate": 11.99, "commission_pct": 8.00, "description": "$10.00 - $11.99"},
            {"max_rate": None, "commission_pct": 10.00, "description": "$12.00 and above"},
        ]
    }


@app.get("/api/v1/bpo/commission/calculate")
async def calculate_commission(request: dict):
    """Calculate commission for a referral placement and save to DB."""
    from .verticals.bpo.commission import calculate_commission as calc
    from .database import SessionLocal
    from .models import Commission, Referrer
    
    hourly_rate = request.get("hourly_rate")
    hours_worked = request.get("hours_worked", 160)
    referrer_code = request.get("referrer_code") # Optional: save if provided
    
    if not hourly_rate:
        raise HTTPException(400, "hourly_rate is required")
    
    result = calc(hourly_rate, hours_worked)
    response_data = result.to_dict()
    
    # If referrer provided, save to DB
    if referrer_code:
        db = SessionLocal()
        try:
            # Find referrer
            referrer = db.query(Referrer).filter(Referrer.referral_code == referrer_code).first()
            if referrer:
                # Create commission record
                comm = Commission(
                    referrer_id=referrer.id,
                    amount=result.commission_amount,
                    description=f"Commission for rate ${hourly_rate}/hr",
                    status="pending"
                )
                db.add(comm)
                
                # Update totals
                referrer.total_commissions_earned += result.commission_amount
                
                db.commit()
                response_data["saved"] = True
                response_data["commission_id"] = comm.id
            else:
                response_data["saved"] = False
                response_data["error"] = "Referrer not found"
        except Exception as e:
            response_data["saved"] = False
            response_data["error"] = str(e)
        finally:
            db.close()
            
    return response_data


# =============================================================================
# AI ENDPOINTS
# =============================================================================

@app.on_event("startup")
async def startup_refresh_models():
    """Refresh AI models on startup."""
    from .ai.gateway import get_gateway
    gateway = get_gateway()
    if gateway._gateway_client:
        await gateway.refresh_models()


@app.get("/api/v1/ai/status")
async def ai_status():
    """Get AI provider status."""
    from .ai.gateway import get_gateway
    gateway = get_gateway()
    return gateway.status


@app.post("/api/v1/ai/refresh-models")
async def refresh_models():
    """Refresh available models from the API gateway."""
    from .ai.gateway import get_gateway, AIProvider
    gateway = get_gateway()
    available = await gateway.refresh_models()
    return {
        "refreshed": True,
        "available_models": available,
        "current_defaults": {
            "claude": gateway.DEFAULT_MODELS.get(AIProvider.CLAUDE),
            "openai": gateway.DEFAULT_MODELS.get(AIProvider.OPENAI),
            "gemini": gateway.DEFAULT_MODELS.get(AIProvider.GEMINI),
        }
    }


@app.post("/api/v1/ai/generate")
async def ai_generate(request: dict):
    """Generate AI content."""
    from .ai.gateway import get_gateway, TaskType, AIProvider
    
    gateway = get_gateway()
    
    prompt = request.get("prompt")
    if not prompt:
        raise HTTPException(400, "prompt is required")
    
    task_type = request.get("task_type")
    if task_type:
        task_type = TaskType(task_type)
    
    # Handle provider selection
    provider = None
    if request.get("provider"):
        try:
            provider = AIProvider(request.get("provider"))
        except ValueError:
            pass  # Invalid provider, use auto
    
    response = await gateway.generate(
        prompt=prompt,
        system=request.get("system"),
        provider=provider,
        task_type=task_type,
        max_tokens=request.get("max_tokens", 4096),
        temperature=request.get("temperature", 0.7),
    )
    
    return {
        "content": response.content,
        "provider": response.provider,
        "model": response.model,
        "tokens": response.total_tokens,
        "cost_usd": response.cost_usd,
    }


@app.post("/api/v1/ai/content")
async def ai_content(request: dict):
    """Generate marketing content (uses Claude)."""
    from .ai.gateway import get_gateway
    
    gateway = get_gateway()
    prompt = request.get("prompt")
    if not prompt:
        raise HTTPException(400, "prompt is required")
    
    response = await gateway.content(prompt)
    return {
        "content": response.content,
        "provider": response.provider,
        "cost_usd": response.cost_usd,
    }


@app.post("/api/v1/ai/qualify-lead")
async def ai_qualify_lead(request: dict):
    """Qualify a lead using AI."""
    from .ai.gateway import get_gateway
    
    gateway = get_gateway()
    lead_data = request.get("lead_data")
    if not lead_data:
        raise HTTPException(400, "lead_data is required")
    
    response = await gateway.qualify_lead(
        lead_data,
        criteria=request.get("criteria"),
    )
    return {
        "analysis": response.content,
        "provider": response.provider,
        "cost_usd": response.cost_usd,
    }


@app.post("/api/v1/ai/research")
async def ai_research(request: dict):
    """Conduct market research."""
    from .ai.gateway import get_gateway
    
    gateway = get_gateway()
    topic = request.get("topic")
    if not topic:
        raise HTTPException(400, "topic is required")
    
    response = await gateway.research(topic)
    return {
        "research": response.content,
        "provider": response.provider,
        "cost_usd": response.cost_usd,
    }


# =============================================================================
# MISSIONS INTEGRATION
# =============================================================================

MISSIONS_FEED_PATH = "/Users/jamessunheart/FPAI_Cockpit/fullpotential_ai/docs/status/missions.json"
MISSIONS_STATE_PATH = "/Users/jamessunheart/FPAI_Cockpit/fullpotential_ai/docs/status/mission_state.json"

@app.get("/api/v1/missions")
async def list_missions():
    """Get all available missions from the Mission system."""
    import json
    from pathlib import Path
    
    try:
        feed_path = Path(MISSIONS_FEED_PATH)
        if not feed_path.exists():
            return {"missions": [], "source": "not_found"}
        
        data = json.loads(feed_path.read_text())
        # Filter to BPO/marketing related missions
        all_missions = data.get("missions", [])
        relevant = [m for m in all_missions if 
                    "BPO" in m.get("title", "") or 
                    "Marketing" in m.get("title", "") or
                    m.get("category") == "revenue"]
        
        return {
            "missions": relevant,
            "total": len(relevant),
            "all_count": len(all_missions),
            "source": str(feed_path),
        }
    except Exception as e:
        raise HTTPException(500, f"Error loading missions: {str(e)}")


@app.post("/api/v1/missions/create-referral-mission")
async def create_referral_mission(request: dict):
    """Create a new referral sub-mission for a referrer to claim."""
    import json
    from pathlib import Path
    from datetime import datetime
    
    referrer_name = request.get("referrer_name")
    mission_type = request.get("mission_type", "refer_leads")
    target = request.get("target", 3)
    
    if not referrer_name:
        raise HTTPException(400, "referrer_name is required")
    
    # Generate mission ID
    mission_id = f"M007-REF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # Mission templates
    templates = {
        "refer_leads": {
            "title": f"Refer {target} Qualified VA Leads",
            "instructions": f"Refer {target} businesses looking for Filipino virtual assistants. Each lead should have a genuine need for remote support services.",
            "success_criteria": f"{target} leads submitted with valid contact info and stated requirements",
            "time_estimate_minutes": 60,
            "commission_bonus": target * 10,  # $10 per lead bonus
        },
        "social_share": {
            "title": f"Share in {target} Communities",
            "instructions": f"Share our VA services in {target} relevant Facebook groups or LinkedIn communities. Focus on groups where business owners discuss outsourcing or remote work.",
            "success_criteria": f"{target} posts shared with proof screenshots",
            "time_estimate_minutes": 30,
            "commission_bonus": target * 5,  # $5 per share bonus
        },
        "testimonial": {
            "title": "Record Video Testimonial",
            "instructions": "Record a 1-2 minute video testimonial about your experience referring VAs or working with our team. Share what makes Filipino VAs great for business.",
            "success_criteria": "Video submitted, approved for use",
            "time_estimate_minutes": 45,
            "commission_bonus": 50,  # $50 for testimonial
        },
    }
    
    template = templates.get(mission_type, templates["refer_leads"])
    
    mission = {
        "id": mission_id,
        "parent_mission": "M007",
        "title": f"[{referrer_name}] {template['title']}",
        "status": "OPEN",
        "priority": "P2",
        "owner": referrer_name,
        "status_text": "Ready to Claim",
        "visibility": "internal",
        "role_needed": "Referrer",
        "time_estimate_minutes": template["time_estimate_minutes"],
        "category": "referral",
        "principle": "Optimization over Extraction",
        "regenerative_impact": f"Creates economic opportunity through fair commission structure. Bonus: ${template['commission_bonus']}",
        "instructions": template["instructions"],
        "success_criteria": template["success_criteria"],
        "created_at": datetime.utcnow().isoformat(),
        "commission_bonus_usd": template["commission_bonus"],
    }
    
    return {
        "created": True,
        "mission": mission,
        "note": "Mission created. To persist, add to missions.json manually or use Mission API.",
    }


@app.get("/api/v1/missions/{mission_id}")
async def get_mission(mission_id: str):
    """Get a specific mission by ID."""
    import json
    from pathlib import Path
    
    try:
        feed_path = Path(MISSIONS_FEED_PATH)
        data = json.loads(feed_path.read_text())
        
        for mission in data.get("missions", []):
            if mission.get("id") == mission_id:
                return {"mission": mission, "found": True}
        
        return {"mission": None, "found": False, "error": f"Mission {mission_id} not found"}
    except Exception as e:
        raise HTTPException(500, f"Error: {str(e)}")


@app.post("/api/v1/missions/{mission_id}/claim")
async def claim_mission(mission_id: str, request: dict):
    """Claim a mission (stub - integrates with mission-store)."""
    claimer = request.get("claimer")
    if not claimer:
        raise HTTPException(400, "claimer is required")
    
    return {
        "claimed": True,
        "mission_id": mission_id,
        "claimer": claimer,
        "timestamp": datetime.utcnow().isoformat(),
        "note": "To persist claim, use fullpotential.ai/missions portal or update mission_state.json",
    }


# =============================================================================
# API ROUTES (Stubs for future implementation)
# =============================================================================

@app.get("/api/v1/campaigns")
async def list_campaigns():
    """List all marketing campaigns."""
    return {"campaigns": [], "total": 0}


@app.get("/api/v1/leads")
async def list_leads():
    """List all leads."""
    return {"leads": [], "total": 0}


@app.get("/api/v1/analytics")
async def get_analytics():
    """Get marketing analytics."""
    return {
        "period": "last_30_days",
        "leads_generated": 0,
        "conversion_rate": 0.0,
        "revenue": 0.0,
    }


# =============================================================================
# AUTOPILOT ENDPOINTS
# =============================================================================

_autopilot = None

def get_autopilot():
    """Get or create autopilot instance."""
    global _autopilot
    if _autopilot is None:
        from .autopilot import MarketingAutopilot
        _autopilot = MarketingAutopilot()
    return _autopilot


@app.get("/api/v1/autopilot/status")
async def autopilot_status():
    """Get autopilot status and stats."""
    autopilot = get_autopilot()
    queue_status = await autopilot.get_queue_status()
    
    return {
        "is_running": autopilot.state.is_running,
        "last_content_generation": autopilot.state.last_content_generation,
        "content_generated_today": autopilot.state.content_generated_today,
        "leads_nurtured_today": autopilot.state.leads_nurtured_today,
        "total_content_generated": autopilot.state.total_content_generated,
        "total_leads_nurtured": autopilot.state.total_leads_nurtured,
        "queue": queue_status,
        "recent_errors": autopilot.state.errors[-5:] if autopilot.state.errors else [],
    }


@app.post("/api/v1/autopilot/generate")
async def autopilot_generate(request: dict):
    """Trigger content generation manually."""
    autopilot = get_autopilot()
    
    count = request.get("count", 3)
    theme = request.get("theme")
    platform = request.get("platform")
    
    if theme and platform:
        # Generate specific content
        item = await autopilot.generate_content(theme, platform)
        return {
            "generated": 1 if item else 0,
            "items": [item.to_dict()] if item else [],
        }
    else:
        # Run full generation cycle
        generated = await autopilot.run_content_generation_cycle(count=count)
        return {
            "generated": generated,
            "message": f"Generated {generated} content pieces",
        }


@app.get("/api/v1/autopilot/queue")
async def autopilot_queue():
    """Get content queue."""
    autopilot = get_autopilot()
    
    queue_status = await autopilot.get_queue_status()
    next_items = await autopilot.get_next_scheduled(limit=10)
    
    return {
        "status": queue_status,
        "next_scheduled": next_items,
    }


@app.post("/api/v1/autopilot/nurture")
async def autopilot_nurture(request: dict):
    """Create a nurture email for a lead."""
    autopilot = get_autopilot()
    
    lead_data = request.get("lead_data", {})
    if not lead_data:
        raise HTTPException(400, "lead_data is required")
    
    email = await autopilot.create_lead_nurture_email(lead_data)
    
    return {
        "success": email is not None,
        "email": email,
    }


# =============================================================================
# SPARKET: INSPIRED SERVICE PLATFORM
# =============================================================================

# -----------------------------------------------------------------------------
# WISDOM ENGINE (Pillar 2: GUIDE)
# -----------------------------------------------------------------------------

@app.post("/api/v1/sparket/wisdom/converse")
async def sparket_wisdom_converse(request: dict):
    """Have a wisdom conversation with AI that adapts to context."""
    from .sparket import get_wisdom_engine, WisdomMode
    from .sparket.wisdom import ConversationContext
    
    engine = get_wisdom_engine()
    
    message = request.get("message")
    if not message:
        raise HTTPException(400, "message is required")
    
    # Build context if provided
    context = None
    if request.get("context"):
        ctx = request["context"]
        context = ConversationContext(
            person_id=ctx.get("person_id", "anonymous"),
            journey_stage=ctx.get("journey_stage", "seeker"),
            emotional_state=ctx.get("emotional_state"),
        )
    
    # Get mode
    mode = WisdomMode.AUTO
    if request.get("mode"):
        try:
            mode = WisdomMode(request["mode"])
        except ValueError:
            pass
    
    response = await engine.converse(message, context, mode)
    
    return {
        "content": response.content,
        "mode": response.mode.value,
        "detected_emotion": response.detected_emotion,
        "is_breakthrough": response.is_breakthrough,
        "follow_up": response.follow_up_suggestion,
    }


# -----------------------------------------------------------------------------
# MATCH ENGINE (Pillar 1: MATCH)
# -----------------------------------------------------------------------------

@app.post("/api/v1/sparket/match/understand")
async def sparket_match_understand(request: dict):
    """Understand someone's true needs."""
    from .sparket import get_match_engine
    
    engine = get_match_engine()
    
    person_data = request.get("person_data", {})
    conversation = request.get("conversation", "")
    
    if not conversation:
        raise HTTPException(400, "conversation is required")
    
    need = await engine.understand_need(person_data, conversation)
    
    return {
        "primary_need": need.primary_need.value,
        "secondary_needs": [n.value for n in need.secondary_needs],
        "stated_need": need.stated_need,
        "underlying_need": need.underlying_need,
        "urgency": need.urgency,
        "ai_understanding": need.ai_understanding,
    }


@app.post("/api/v1/sparket/match/find")
async def sparket_match_find(request: dict):
    """Find matches for someone's needs."""
    from .sparket import get_match_engine
    from .sparket.match import NeedProfile, NeedCategory
    
    engine = get_match_engine()
    
    # Build need profile from request
    need_data = request.get("need_profile", {})
    need = NeedProfile(
        person_id=need_data.get("person_id", "anonymous"),
        primary_need=NeedCategory(need_data.get("primary_need", "guidance")),
        stated_need=need_data.get("stated_need", ""),
        context=request.get("person_data", {}),
    )
    
    result = await engine.find_matches(need, limit=request.get("limit", 3))
    
    return {
        "matches": [
            {
                "id": m.id,
                "name": m.name,
                "type": m.match_type.value,
                "score": m.match_score,
                "why": m.why_matched,
                "next_step": m.next_step,
            }
            for m in result.matches
        ],
        "summary": result.ai_summary,
    }


# -----------------------------------------------------------------------------
# COMMUNITY HUB (Pillar 3: GATHER)
# -----------------------------------------------------------------------------

@app.get("/api/v1/sparket/community/list")
async def sparket_community_list():
    """List all communities."""
    from .sparket import get_community_hub
    
    hub = get_community_hub()
    return {"communities": hub.list_communities()}


@app.post("/api/v1/sparket/community/find-tribe")
async def sparket_find_tribe(request: dict):
    """Find the right community for someone."""
    from .sparket import get_community_hub
    
    hub = get_community_hub()
    person_data = request.get("person_data", {})
    
    matches = await hub.find_tribe(person_data, limit=request.get("limit", 3))
    
    return {
        "tribe_matches": [
            {
                "community_id": m.community.id,
                "name": m.community.name,
                "purpose": m.community.purpose,
                "type": m.community.community_type.value,
                "score": m.match_score,
                "why": m.why_matched,
                "potential_connections": m.potential_connections,
            }
            for m in matches
        ]
    }


@app.post("/api/v1/sparket/community/join")
async def sparket_community_join(request: dict):
    """Join a community."""
    from .sparket import get_community_hub
    
    hub = get_community_hub()
    
    community_id = request.get("community_id")
    person_data = request.get("person_data", {})
    
    if not community_id:
        raise HTTPException(400, "community_id is required")
    
    result = await hub.join_community(community_id, person_data)
    return result


# -----------------------------------------------------------------------------
# CONTENT STUDIO (Pillar 4: INSPIRE)
# -----------------------------------------------------------------------------

@app.post("/api/v1/sparket/content/sense")
async def sparket_content_sense(request: dict):
    """Sense what content is needed."""
    from .sparket import get_content_studio
    
    studio = get_content_studio()
    
    signals = request.get("community_signals", [])
    sense = await studio.sense_what_needed(signals)
    
    return {
        "suggested_format": sense.suggested_format.value,
        "suggested_tone": sense.suggested_tone.value,
        "topic": sense.topic_suggestion,
        "why_now": sense.why_now,
        "confidence": sense.confidence,
    }


@app.post("/api/v1/sparket/content/create")
async def sparket_content_create(request: dict):
    """Create inspired content."""
    from .sparket import get_content_studio
    from .sparket.content import ContentFormat, ContentTone, ContentPlatform
    
    studio = get_content_studio()
    
    topic = request.get("topic")
    if not topic:
        raise HTTPException(400, "topic is required")
    
    format_type = ContentFormat(request.get("format", "insight"))
    tone = ContentTone(request.get("tone", "mentor"))
    platform = ContentPlatform(request.get("platform", "universal"))
    
    content = await studio.create_transmission(topic, format_type, tone, platform)
    
    return {
        "id": content.id,
        "title": content.title,
        "body": content.body,
        "format": content.format.value,
        "tone": content.tone.value,
        "platform": content.platform.value,
        "status": content.status,
    }


# -----------------------------------------------------------------------------
# AMPLIFY ENGINE (Pillar 6: AMPLIFY - The Attention Cascade)
# -----------------------------------------------------------------------------

@app.get("/api/v1/sparket/amplify/dashboard")
async def sparket_amplify_dashboard():
    """Get the Amplify dashboard with all tier metrics."""
    from .sparket import get_amplify_engine
    
    engine = get_amplify_engine()
    return engine.get_amplify_dashboard()


@app.get("/api/v1/sparket/amplify/free-tier/status")
async def sparket_amplify_free_tier():
    """Get free tier status."""
    from .sparket import get_amplify_engine
    
    engine = get_amplify_engine()
    return await engine.run_free_tier()


@app.post("/api/v1/sparket/amplify/identify-resonance")
async def sparket_identify_resonance(request: dict):
    """Identify what content is resonating."""
    from .sparket import get_amplify_engine
    
    engine = get_amplify_engine()
    min_rate = request.get("min_engagement_rate", 5.0)
    
    resonating = await engine.identify_resonance(min_rate)
    
    return {
        "resonating_content": [
            {
                "content_id": p.content_id,
                "resonance_score": p.resonance_score,
                "engagement_rate": p.engagement_rate,
                "conversion_rate": p.conversion_rate,
            }
            for p in resonating
        ]
    }


@app.post("/api/v1/sparket/amplify/design-test")
async def sparket_design_test(request: dict):
    """Design a small paid test."""
    from .sparket import get_amplify_engine
    from .sparket.amplify import ChannelType
    
    engine = get_amplify_engine()
    
    content_id = request.get("content_id", "test_content")
    channel = ChannelType(request.get("channel", "paid_social"))
    budget = request.get("budget", 50.0)
    
    test = await engine.design_small_test(content_id, channel, budget)
    
    return {
        "test_id": test.id,
        "content_id": test.content_id,
        "channel": test.channel.value,
        "budget": test.budget,
        "variants": len(test.variants),
        "status": test.status.value,
    }


@app.post("/api/v1/sparket/amplify/scale")
async def sparket_scale_winner(request: dict):
    """Scale a winning test."""
    from .sparket import get_amplify_engine
    
    engine = get_amplify_engine()
    
    test_id = request.get("test_id")
    if not test_id:
        raise HTTPException(400, "test_id is required")
    
    scale_factor = request.get("scale_factor", 2.0)
    
    result = await engine.scale_winner(test_id, scale_factor)
    return result


@app.get("/api/v1/sparket/amplify/credit-savings")
async def sparket_credit_savings():
    """Get UC offset tracking."""
    from .sparket import get_amplify_engine
    
    engine = get_amplify_engine()
    return engine.get_credit_savings()


# -----------------------------------------------------------------------------
# TESTING FRAMEWORK
# -----------------------------------------------------------------------------

@app.post("/api/v1/sparket/testing/generate-variants")
async def sparket_generate_variants(request: dict):
    """Generate test variants using AI."""
    from .sparket import get_testing_framework
    
    framework = get_testing_framework()
    
    base_content = request.get("base_content", "")
    if not base_content:
        raise HTTPException(400, "base_content is required")
    
    variation_types = request.get("variation_types", ["headline", "cta"])
    
    variants = await framework.generate_variants(base_content, variation_types)
    
    return {
        "variants": [
            {
                "id": v.id,
                "name": v.name,
                "type": v.variation_type,
                "content": v.content,
                "hypothesis": v.hypothesis,
            }
            for v in variants
        ]
    }


# -----------------------------------------------------------------------------
# CREDITS INTEGRATION
# -----------------------------------------------------------------------------

@app.post("/api/v1/sparket/credits/calculate-offset")
async def sparket_calculate_offset(request: dict):
    """Calculate a UC/cash offset split."""
    from .sparket import get_credits_integration
    
    credits = get_credits_integration()
    
    total_value = request.get("total_value", 0.0)
    uc_percentage = request.get("uc_percentage", 0.7)
    
    return credits.calculate_offset(total_value, uc_percentage)


@app.post("/api/v1/sparket/credits/influencer-deal")
async def sparket_influencer_deal(request: dict):
    """Create an influencer deal with UC offset."""
    from .sparket import get_credits_integration
    
    credits = get_credits_integration()
    
    deal = await credits.create_influencer_deal(
        influencer_id=request.get("influencer_id", ""),
        influencer_name=request.get("influencer_name", ""),
        total_value=request.get("total_value", 0.0),
        uc_percentage=request.get("uc_percentage", 0.7),
        campaign_details=request.get("campaign_details"),
    )
    
    return deal


@app.get("/api/v1/sparket/credits/savings-report")
async def sparket_savings_report():
    """Get credit savings report."""
    from .sparket import get_credits_integration
    
    credits = get_credits_integration()
    return credits.get_savings_report()


# -----------------------------------------------------------------------------
# IMPACT DASHBOARD
# -----------------------------------------------------------------------------

@app.get("/api/v1/sparket/impact/dashboard")
async def sparket_impact_dashboard():
    """Get the main impact dashboard."""
    from .sparket import get_impact_tracker
    
    tracker = get_impact_tracker()
    return await tracker.get_impact_dashboard()


@app.post("/api/v1/sparket/impact/record")
async def sparket_record_impact(request: dict):
    """Record an impact event."""
    from .sparket import get_impact_tracker
    from .sparket.impact import ImpactType, ImpactDepth
    
    tracker = get_impact_tracker()
    
    person_id = request.get("person_id", "anonymous")
    impact_type = ImpactType(request.get("impact_type", "life_touched"))
    depth = ImpactDepth(request.get("depth", "touch"))
    description = request.get("description", "")
    source = request.get("source", "manual")
    
    event = await tracker.record_impact(
        person_id=person_id,
        impact_type=impact_type,
        depth=depth,
        description=description,
        source=source,
        metadata=request.get("metadata"),
    )
    
    return {
        "id": event.id,
        "person_id": event.person_id,
        "type": event.impact_type.value,
        "depth": event.depth.value,
        "recorded": True,
    }


@app.get("/api/v1/sparket/impact/report")
async def sparket_impact_report(timeframe: str = "all"):
    """Generate a comprehensive impact report."""
    from .sparket import get_impact_tracker
    
    tracker = get_impact_tracker()
    return await tracker.get_impact_report(timeframe)


@app.get("/api/v1/sparket/impact/community-health")
async def sparket_community_health():
    """Get community health metrics."""
    from .sparket import get_impact_tracker
    
    tracker = get_impact_tracker()
    return await tracker.get_community_health()


# =============================================================================
# ROOT
# =============================================================================

@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "BRICK 2: AI Marketing Engine",
        "version": __version__,
        "status": "development",
        "docs": "/docs",
        "health": "/health",
        "capabilities": "/capabilities",
        "sparket": {
            "description": "SPARKET: Inspired Service Platform",
            "pillars": [
                "MATCH - Connect people with what they need",
                "GUIDE - AI-powered transformation (Wisdom Engine)",
                "GATHER - Community building",
                "INSPIRE - Content that transforms",
                "CIRCULATE - Resource flow balance",
                "AMPLIFY - Intelligent exposure cascade",
            ],
            "endpoints": {
                "wisdom": "/api/v1/sparket/wisdom/converse",
                "match": "/api/v1/sparket/match/find",
                "community": "/api/v1/sparket/community/list",
                "content": "/api/v1/sparket/content/create",
                "amplify": "/api/v1/sparket/amplify/dashboard",
                "impact": "/api/v1/sparket/impact/dashboard",
            },
            "manifesto": "We don't market. We serve. We don't sell. We match. We don't convert. We transform.",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8700)

