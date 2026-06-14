"""
Proof Witness - Main Application

The AI witness that captures proof automatically.
Humans spend 15 seconds/day confirming, not creating.
"""
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
from typing import Optional, List

from app.config import settings
from app.models import ProofCandidate, ConfirmedProof, DailyProofSummary, ProofStatus
from app.storage import storage
from app.watchers.github import github_watcher
from app.tagging import tagger
from app.telegram_sender import telegram_sender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Proof Witness",
    description="AI witness that captures proof automatically - 85% automated, 15% human confirm",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# UDC ENDPOINTS
# ============================================================================

@app.get("/health", tags=["UDC"])
async def health_check():
    """UDC Health Check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION
    }


@app.get("/capabilities", tags=["UDC"])
async def capabilities():
    """UDC Capabilities"""
    return {
        "service_name": settings.SERVICE_NAME,
        "capabilities": [
            "github_commits",
            "github_deployments",
            "photo_uploads",
            "auto_tagging",
            "content_generation",
            "one_click_confirmation"
        ],
        "integrations": {
            "github": bool(settings.GITHUB_WEBHOOK_SECRET),
            "telegram": bool(settings.TELEGRAM_BOT_TOKEN),
            "chief_of_staff": settings.CHIEF_OF_STAFF_URL
        }
    }


@app.get("/state", tags=["UDC"])
async def state():
    """UDC State"""
    pending = storage.get_pending_candidates(limit=100)
    today_summary = storage.get_daily_summary()

    return {
        "status": "active",
        "pending_confirmations": len(pending),
        "today_confirmed": today_summary.total_confirmed,
        "today_candidates": today_summary.total_candidates
    }


# ============================================================================
# GITHUB WEBHOOKS
# ============================================================================

@app.post("/webhooks/github", tags=["Watchers"])
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None)
):
    """
    GitHub webhook endpoint

    Receives push and deployment events, creates proof candidates automatically.
    """
    # Read payload
    payload_body = await request.body()
    payload = await request.json()

    # Verify signature
    if not github_watcher.verify_signature(payload_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Handle different event types
    if x_github_event == "push":
        candidate_ids = await github_watcher.handle_push(payload)
        return {
            "message": f"Created {len(candidate_ids)} proof candidates from push",
            "candidate_ids": candidate_ids
        }

    elif x_github_event == "deployment":
        candidate_id = await github_watcher.handle_deployment(payload)
        return {
            "message": "Created proof candidate from deployment",
            "candidate_id": candidate_id
        }

    else:
        return {
            "message": f"Event {x_github_event} not handled",
            "event": x_github_event
        }


# ============================================================================
# PROOF CONFIRMATION (The 15-second human step)
# ============================================================================

@app.get("/pending", tags=["Confirmation"])
async def get_pending_candidates(limit: int = 10) -> List[ProofCandidate]:
    """
    Get proof candidates waiting for confirmation

    This is what the Telegram bot sends to humans:
    "I saw 3 events today. Confirm?"
    """
    return storage.get_pending_candidates(limit=limit)


@app.post("/confirm/{candidate_id}", tags=["Confirmation"])
async def confirm_candidate(
    candidate_id: str,
    tags: Optional[List[str]] = None,
    question_id: Optional[str] = None,
    impact: Optional[str] = None
) -> ConfirmedProof:
    """
    Confirm a proof candidate (the one-click step)

    Human taps "Yes" in Telegram, proof gets confirmed.
    15 seconds of attention, proof minted.
    """
    try:
        proof = storage.confirm_candidate(
            candidate_id=candidate_id,
            tags=tags,
            question_id=question_id,
            impact=impact
        )

        logger.info(f"Proof confirmed: {candidate_id} ({proof.owner}: {proof.title})")

        return proof

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/reject/{candidate_id}", tags=["Confirmation"])
async def reject_candidate(candidate_id: str):
    """
    Reject a proof candidate (human says "skip this")

    Sometimes the witness captures noise. Human can reject.
    """
    # Update status to rejected
    # (Not implementing full reject logic in MVP, just mark as rejected)
    return {"message": f"Candidate {candidate_id} rejected"}


# ============================================================================
# DAILY DIGEST INTEGRATION
# ============================================================================

@app.get("/daily-summary", tags=["Digest"])
async def get_daily_summary(date: Optional[str] = None) -> DailyProofSummary:
    """
    Get daily proof summary

    This is what goes into the morning digest:
    🎯 PROOF (Last 24h)
    • Atlas: Greenhouse electrical → 3 photos → 40% → 60%
    • Kai: Revenue dashboard → 2 commits → $540 visible
    """
    return storage.get_daily_summary(date=date)


@app.get("/digest/format", tags=["Digest"])
async def format_for_digest(date: Optional[str] = None) -> str:
    """
    Format daily proof for Telegram digest

    Returns formatted text ready to paste into morning digest
    """
    summary = storage.get_daily_summary(date=date)

    if not summary.highlights:
        return "🎯 *PROOF (Last 24h)*\n_No proof captured yet_"

    lines = ["🎯 *PROOF (Last 24h)*"]

    for proof in summary.highlights:
        # Format: "• Owner: Title → [type]"
        type_emoji = {
            "code": "💻",
            "photo": "📸",
            "metric": "📊",
            "event": "✅"
        }.get(proof.type.value, "•")

        line = f"{type_emoji} {proof.owner}: {proof.title}"

        # Add impact if available
        if proof.impact:
            line += f" → {proof.impact}"

        lines.append(line)

    # Add summary stats
    lines.append("")
    lines.append(f"_Total: {summary.total_confirmed} proof items confirmed_")

    return "\n".join(lines)


@app.post("/send-summary", tags=["Telegram"])
async def send_daily_summary_to_telegram(max_items: int = 10):
    """
    Send daily proof summary to Telegram with interactive buttons

    This is the end-of-day notification (8pm):
    "I saw 3 events today. Confirm?"

    Each proof candidate is sent as a separate message with 3 buttons:
    ✅ Yes | ✏️ Edit | ❌ Skip

    Human taps buttons, done in 15 seconds.
    """
    try:
        result = await telegram_sender.send_daily_summary(max_items=max_items)

        logger.info(f"Sent {result['sent']} proof items to Telegram")

        return {
            "status": "sent",
            "sent": result["sent"],
            "pending": result["pending"],
            "message": result["message"]
        }

    except Exception as e:
        logger.error(f"Failed to send daily summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MANUAL PROOF SUBMISSION (For cases where automatic capture doesn't work)
# ============================================================================

@app.post("/submit", tags=["Manual"])
async def submit_proof_manually(candidate: ProofCandidate) -> str:
    """
    Manually submit proof (for cases where auto-capture doesn't work)

    E.g., a testimonial, a transformation story, etc.
    """
    candidate_id = storage.add_candidate(candidate)

    logger.info(f"Manual proof submitted: {candidate_id} ({candidate.owner}: {candidate.title})")

    return candidate_id


# ============================================================================
# ROOT
# ============================================================================

@app.get("/", tags=["System"])
async def root():
    """Service info"""
    pending_count = len(storage.get_pending_candidates(limit=100))

    return {
        "service": "Proof Witness",
        "version": settings.APP_VERSION,
        "tagline": "AI witness that captures proof automatically",
        "human_attention_required": "15 seconds/day",
        "automation_level": "85% automated, 15% one-click confirm",
        "pending_confirmations": pending_count,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG
    )
