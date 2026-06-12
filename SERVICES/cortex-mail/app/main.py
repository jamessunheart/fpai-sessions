from fastapi import FastAPI, HTTPException, Header, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import logging
import uuid
import httpx
import json
import re

from . import config, models, database

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cortex-mail")
settings = config.get_settings()

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Cortex Mail", version=settings.UDC_VERSION)

# --- Models ---

class InboundEmail(BaseModel):
    sender: str
    recipient: str
    subject: str | None = None
    raw_email: str
    timestamp: str

# --- Dependencies ---

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def verify_secret(x_cortex_secret: str = Header(...)):
    if x_cortex_secret != settings.CORTEX_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret token")

# --- Helper Logic ---

def is_blocked(sender: str, db: Session) -> bool:
    """Check if sender is in blocklist."""
    # Normalize sender (extract email from "Name <email>")
    match = re.search(r'<(.+?)>', sender)
    email = match.group(1) if match else sender
    return db.query(models.BlockedSender).filter(models.BlockedSender.email == email).first() is not None

async def execute_unsubscribe(url: str):
    """Attempt to visit the unsubscribe link."""
    try:
        async with httpx.AsyncClient() as client:
            await client.get(url, timeout=10.0)
            logger.info(f"✅ Visited unsubscribe link: {url}")
    except Exception as e:
        logger.error(f"❌ Failed to visit unsubscribe link: {e}")

async def apply_routing_rules(email_id: str, db: Session):
    """Check email against routing rules and execute actions."""
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email:
        return

    rules = db.query(models.RoutingRule).filter(models.RoutingRule.active == True).all()
    
    for rule in rules:
        match = False
        # 1. Check Conditions
        if rule.condition_type == "keyword":
            if rule.condition_value.lower() in (email.subject or "").lower():
                match = True
        elif rule.condition_type == "sender":
            if rule.condition_value.lower() in email.sender.lower():
                match = True
        elif rule.condition_type == "ai_category":
            if rule.condition_value.lower() == (email.category or "").lower():
                match = True
        
        # 2. Execute Action
        if match:
            logger.info(f"⚡ Rule '{rule.name}' matched for email {email_id}")
            
            if rule.action_type == "forward":
                # TODO: Implement actual forwarding via SMTP or API
                # For now, just log it
                email.action_taken = "forwarded"
                email.action_details = f"Forwarded to {rule.action_target} (Simulated)"
                logger.info(f"--> Forwarding to {rule.action_target}")
                
            elif rule.action_type == "notify":
                # Placeholder for Slack/Discord notification
                email.action_taken = "notified"
                email.action_details = f"Notified {rule.action_target}"
            
            db.commit()

# --- AI Logic ---

async def analyze_email(email_id: str, raw_content: str):
    """Analyze email using AI Brain."""
    logger.info(f"🧠 Analyzing email {email_id}...")
    
    try:
        async with httpx.AsyncClient() as client:
            # 1. Construct prompt
            prompt = f"""
            Analyze this email metadata and content. 
            
            TASK:
            1. Categorize: Verification, Invoice, Alert, Personal, Newsletter, Spam.
            2. Urgency: 0-100.
            3. Extract Entities:
               - verification_code: (6-digit codes, or codes from links like ?code=...)
               - api_key: (sk-..., etc)
               - amount: (financial)
               - service_name: (OpenAI, Stripe, etc)
               - unsubscribe_url: (Look for 'Unsubscribe' links or 'List-Unsubscribe' headers)
            4. Spam Score: 0-10 (10 is definitely spam).
            
            Output JSON only: {{ "category": "...", "urgency": 0, "spam_score": 0, "entities": {{...}}, "summary": "..." }}
            
            Email Content:
            {raw_content[:3000]} 
            """
            
            # 2. Call AI Brain
            response = await client.post(
                f"{settings.AI_BRAIN_URL}/ai/generate",
                headers={
                    "X-Service-Key": settings.AI_SERVICE_KEY,
                    "Content-Type": "application/json"
                },
                json={"prompt": prompt},
                timeout=30.0
            )
            
            if response.status_code == 200:
                ai_data = response.json()
                result_text = ai_data.get("response", "{}")
                
                # 3. Parse Result (Try to extract JSON)
                try:
                    # Simple cleanup if AI wraps in markdown
                    clean_json = result_text.replace("```json", "").replace("```", "").strip()
                    analysis = json.loads(clean_json)
                    
                    # 4. Update Database
                    db = database.SessionLocal()
                    email = db.query(models.Email).filter(models.Email.id == email_id).first()
                    if email:
                        email.category = analysis.get("category", "uncategorized")
                        email.urgency_score = analysis.get("urgency", 0)
                        email.entities = analysis.get("entities", {})
                        email.body_text = analysis.get("summary", "") 
                        email.processed = True
                        
                        # Auto-Flag Spam
                        spam_score = analysis.get("spam_score", 0)
                        if spam_score > 7:
                            email.category = "Spam"
                        
                        db.commit()
                        logger.info(f"✅ Analysis complete for {email_id}: {email.category}")
                        
                        # 5. Apply Rules
                        await apply_routing_rules(email.id, db)
                        
                    db.close()
                    
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse AI JSON: {result_text}")
            else:
                logger.error(f"AI Brain error: {response.text}")
                
    except Exception as e:
        logger.error(f"Analysis failed: {e}")

# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "active", "service": "cortex-mail"}

@app.get("/capabilities")
async def capabilities():
    return {
        "name": "Cortex Mail",
        "description": "Intelligent Email Router",
        "version": settings.UDC_VERSION,
        "provides": ["email_ingestion", "credential_extraction", "spam_defense"],
        "dependencies": ["team-hub", "ai-brain"]
    }

@app.post("/inbound")
async def receive_email(
    email: InboundEmail,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    authorized: bool = Depends(verify_secret)
):
    """
    Webhook endpoint for Cloudflare Worker.
    Receives raw email, encrypts it, and queues for processing.
    """
    
    # 1. Guardian Protocol: Check Blocklist
    if is_blocked(email.sender, db):
        logger.warning(f"🛡️ BLOCKED inbound email from {email.sender}")
        return {"status": "blocked", "reason": "sender_blocked"}

    logger.info(f"📧 Received email from {email.sender} to {email.recipient}: {email.subject}")
    
    # 2. Create record
    db_email = models.Email(
        id=str(uuid.uuid4()),
        sender=email.sender,
        recipient=email.recipient,
        subject=email.subject,
        # TODO: Encrypt raw_email before saving
        raw_content_encrypted=email.raw_email, 
        body_text=email.raw_email[:500], # Placeholder
        processed=False
    )
    db.add(db_email)
    db.commit()
    
    # 3. Trigger AI Analysis in background
    background_tasks.add_task(analyze_email, db_email.id, email.raw_email)
    
    return {"status": "received", "id": db_email.id}

@app.get("/api/emails")
async def list_emails(limit: int = 20, category: str = None, db: Session = Depends(get_db)):
    """List emails for the dashboard."""
    query = db.query(models.Email)
    if category:
        query = query.filter(models.Email.category == category)
        
    emails = query.order_by(models.Email.received_at.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "from": e.sender,
            "to": e.recipient,
            "subject": e.subject,
            "time": e.received_at.isoformat(),
            "category": e.category,
            "urgency": e.urgency_score,
            "processed": e.processed,
            "has_unsubscribe": "unsubscribe_url" in (e.entities or {})
        }
        for e in emails
    ]

@app.get("/api/emails/{email_id}")
async def get_email(email_id: str, db: Session = Depends(get_db)):
    """Get single email details."""
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
        
    return {
        "id": email.id,
        "from": email.sender,
        "to": email.recipient,
        "subject": email.subject,
        "body": email.body_text,
        "raw": email.raw_content_encrypted,
        "category": email.category,
        "entities": email.entities,
        "time": email.received_at.isoformat()
    }

@app.post("/api/emails/{email_id}/block")
async def block_sender(email_id: str, db: Session = Depends(get_db)):
    """Block the sender of this email."""
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    
    # Extract clean email
    sender = email.sender
    match = re.search(r'<(.+?)>', sender)
    clean_email = match.group(1) if match else sender
    
    # Add to blocklist
    if not db.query(models.BlockedSender).filter(models.BlockedSender.email == clean_email).first():
        blocked = models.BlockedSender(email=clean_email, reason="Manual Block")
        db.add(blocked)
        db.commit()
        logger.info(f"🛡️ Manually blocked sender: {clean_email}")
        
    return {"status": "blocked", "sender": clean_email}

@app.post("/api/emails/{email_id}/unsubscribe")
async def unsubscribe(email_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Attempt to unsubscribe using AI-found link."""
    email = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
        
    entities = email.entities or {}
    url = entities.get("unsubscribe_url")
    
    if not url:
        raise HTTPException(status_code=400, detail="No unsubscribe link found by AI")
        
    # Trigger background visit
    background_tasks.add_task(execute_unsubscribe, url)
    
    return {"status": "unsubscribe_initiated", "url": url}

@app.get("/state")
async def state(db: Session = Depends(get_db)):
    count = db.query(models.Email).count()
    blocked_count = db.query(models.BlockedSender).count()
    recent = db.query(models.Email).order_by(models.Email.received_at.desc()).limit(5).all()
    
    return {
        "total_emails": count,
        "blocked_senders": blocked_count,
        "recent_activity": [
            {
                "from": e.sender,
                "subject": e.subject,
                "time": e.received_at
            } for e in recent
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.SERVICE_PORT)
