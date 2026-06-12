import uuid
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Body, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
import uvicorn
import shutil
from pathlib import Path

from . import models, database, udc, config, auth
from .integrations import credits_client, intel_client, comms_client, api_portal_client, cortex_client, genesis_client, godmode_client, mission_client, brain_client, whale_client, cf_client
from cryptography.fernet import Fernet
import os

# Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = config.get_settings()

# Vault Security
VAULT_KEY = os.getenv("VAULT_ENCRYPTION_KEY")
if not VAULT_KEY:
    VAULT_KEY = Fernet.generate_key().decode()

cipher_suite = Fernet(VAULT_KEY.encode())

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="Team Portal", version=settings.UDC_VERSION)
recruiter_tracker = {"state": "idle", "last_run": None}

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Team Hub Starting...")
    try:
        if await genesis_client.enroll():
            await genesis_client.retrieve_credentials()
    except Exception as e:
        logger.error(f"Genesis enrollment failed: {e}")

    # Announce existence to the Brain
    try:
        await brain_client.register_execution_layer("https://fullpotential.ai/services/team")
    except Exception as e:
        logger.error(f"Brain registration failed: {e}")

@app.post("/api/finance/transfer")
async def transfer_funds(
    payload: dict = Body(...),
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Transfer funds between wallets."""
    from_wallet = payload.get("from_wallet")
    to_wallet = payload.get("to_wallet")
    amount = float(payload.get("amount", 0))
    ref = payload.get("reference", "Manual Transfer")
    
    if not from_wallet or not to_wallet or amount <= 0:
        raise HTTPException(400, "Invalid transfer parameters")
        
    # Check ownership: Admin moves all, User moves own
    if not current_user.is_admin:
        member = db.query(models.TeamMember).filter(models.TeamMember.id == current_user.member_id).first()
        if not member or member.wallet_id != from_wallet:
             raise HTTPException(403, "Cannot transfer from this wallet")

    success = await credits_client.transfer(from_wallet, to_wallet, amount, ref)
    if not success:
        raise HTTPException(500, "Transfer failed")
        
    return {"status": "success", "amount": amount, "from": from_wallet, "to": to_wallet}

@app.post("/api/genesis/chat")
async def chat_with_service(
    payload: dict = Body(...),
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
):
    """Chat with a specific service context via AI Brain."""
    service_name = payload.get("service_name")
    message = payload.get("message")
    
    if not service_name or not message:
        raise HTTPException(400, "Service name and message required")
        
    # Forward to AI Brain
    response = await brain_client.ask(message, context=service_name)
    
    return {"response": response}


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _skill_score(task: models.WorkAssignment, member: models.TeamMember) -> float:
    """Estimate how well a member's skills match the assignment context."""
    if not member.skills:
        return 0.3
    
    haystack = " ".join(
        filter(
            None,
            [
                task.title or "",
                task.description or "",
                task.context_summary or "",
            ],
        )
    ).lower()
    
    if not haystack:
        return 0.4
    
    matches = sum(1 for skill in member.skills if skill.lower() in haystack)
    return matches / len(member.skills) if matches else 0.2


def _availability_score(member: models.TeamMember, db: Session) -> float:
    active = (
        db.query(models.WorkAssignment)
        .filter(
            models.WorkAssignment.assignee_id == member.id,
            models.WorkAssignment.status.in_(["pending", "in_progress"]),
        )
        .count()
    )
    return 1 / (1 + active)


def _responsiveness_score(member: models.TeamMember) -> float:
    base = 0.4 + ((member.context_level or 0) / 200)
    base = max(0.2, min(1.0, base))
    if member.status != "active":
        base *= 0.6
    return base


def _collect_member_dashboard(member: models.TeamMember, db: Session) -> dict:
    completed = (
        db.query(func.count(models.WorkAssignment.id))
        .filter(
            models.WorkAssignment.assignee_id == member.id,
            models.WorkAssignment.status.in_(["completed", "verified"]),
        )
        .scalar()
        or 0
    )
    active = (
        db.query(func.count(models.WorkAssignment.id))
        .filter(
            models.WorkAssignment.assignee_id == member.id,
            models.WorkAssignment.status.in_(["pending", "in_progress"]),
        )
        .scalar()
        or 0
    )
    uc_earned = (
        db.query(func.coalesce(func.sum(models.WorkAssignment.uc_reward), 0.0))
        .filter(
            models.WorkAssignment.assignee_id == member.id,
            models.WorkAssignment.status.in_(["completed", "verified"]),
        )
        .scalar()
        or 0.0
    )
    
    recent = (
        db.query(models.WorkAssignment)
        .filter(models.WorkAssignment.assignee_id == member.id)
        .order_by(models.WorkAssignment.created_at.desc())
        .limit(5)
        .all()
    )
    
    return {
        "summary": {
            "completed": completed,
            "active": active,
            "uc_earned": uc_earned,
            "trust": member.trust_score,
        },
        "recent_assignments": [
            {
                "id": item.id,
                "title": item.title,
                "status": item.status,
                "uc_reward": item.uc_reward,
                "created_at": item.created_at.isoformat(),
            }
            for item in recent
        ],
    }

# --- UDC Endpoints (Mandatory) ---

@app.get("/health")
async def health():
    return udc.get_health()

@app.get("/capabilities")
async def capabilities():
    return udc.get_capabilities()

@app.get("/state")
async def state(db: Session = Depends(get_db)):
    member_count = db.query(models.TeamMember).count()
    active_tasks = (
        db.query(models.WorkAssignment)
        .filter(models.WorkAssignment.status.in_(["pending", "in_progress"]))
        .count()
    )
    paid_uc = (
        db.query(func.coalesce(func.sum(models.WorkAssignment.uc_reward), 0.0))
        .filter(models.WorkAssignment.status.in_(["completed", "verified"]))
        .scalar()
        or 0.0
    )
    procurement_backlog = (
        db.query(func.count(models.WorkAssignment.id))
        .filter(
            models.WorkAssignment.type == "api_procurement",
            models.WorkAssignment.status.in_(["pending", "in_progress"]),
        )
        .scalar()
        or 0
    )
    
    # Fetch Infrastructure Health
    infra_health = await godmode_client.get_health()
    
    # Fetch Treasury Snapshot
    treasury = await whale_client.get_snapshot()
    
    # Add mock budget data for now if not in snapshot
    if "budgets" not in treasury:
        treasury["budgets"] = [
            {"name": "Operations", "allocated": 50000, "spent": 12000},
            {"name": "Growth", "allocated": 25000, "spent": 8500},
            {"name": "Research", "allocated": 10000, "spent": 1500}
        ]
    if "wallets" not in treasury:
        treasury["wallets"] = [
            {"name": "Main Vault", "address": "0xTreasury", "balance": 850000},
            {"name": "Whale Trading", "address": "0xWhale", "balance": 50000},
            {"name": "Ops Hot Wallet", "address": "0xOps", "balance": 5000}
        ]

    return {
        "active_humans": member_count,
        "open_tasks": active_tasks,
        "total_uc_paid": round(paid_uc, 2),
        "procurement_backlog": procurement_backlog,
        "recruiter": recruiter_tracker,
        "infrastructure": infra_health,
        "treasury": treasury,
        "uptime": "active",  # Simplified
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/dependencies")
async def dependencies():
    return {"required": udc.get_capabilities()["dependencies"]}

@app.post("/message")
async def receive_message(payload: dict = Body(...)):
    # Async message handler (e.g. from Mission Hub)
    logger.info(f"Received message: {payload}")
    return {"status": "received"}

@app.post("/send")
async def send_message(payload: dict = Body(...)):
    # Mock send
    return {"status": "sent"}


# --- Authentication API ---

@app.post("/auth/request-magic-link", response_model=models.MagicLinkResponse)
async def request_magic_link(
    payload: models.MagicLinkRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Request a magic link for passwordless login."""
    email = payload.email.lower().strip()
    
    # Check if member exists or has pending invite
    member = db.query(models.TeamMember).filter(
        models.TeamMember.email == email
    ).first()
    
    invite = db.query(models.Invitation).filter(
        models.Invitation.email == email,
        models.Invitation.used == False,
        models.Invitation.expires_at > datetime.utcnow(),
    ).first()
    
    # Allow login for existing members or pending invites
    if not member and not invite:
        # Check if admin email (always allowed)
        if not auth.is_admin(email):
            raise HTTPException(
                status_code=403,
                detail="Email not registered. Please request an invite.",
            )
    
    # Create magic link
    token, expires_at = auth.create_magic_link(email, db)
    
    # Build magic link URL
    base_url = str(request.base_url).rstrip("/")
    magic_url = f"{base_url}/auth/verify?token={token}"
    
    # Send via Communication Hub
    await comms_client.send_email(
        to=email,
        subject="Your Team Portal Login Link",
        body=(
            f"Click here to log in to the Team Portal:\n\n"
            f"{magic_url}\n\n"
            f"This link expires in {settings.MAGIC_LINK_EXPIRE_MINUTES} minutes.\n"
            f"If you didn't request this, please ignore this email."
        ),
    )
    
    logger.info(f"Magic link sent to {email}: {magic_url}")
    
    return models.MagicLinkResponse(
        message=f"Magic link sent to {email}",
        expires_in_minutes=settings.MAGIC_LINK_EXPIRE_MINUTES,
    )


@app.get("/auth/verify")
async def verify_magic_link(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Verify magic link and return JWT token."""
    link = db.query(models.MagicLink).filter(
        models.MagicLink.token == token,
        models.MagicLink.used == False,
        models.MagicLink.expires_at > datetime.utcnow(),
    ).first()
    
    if not link:
        raise HTTPException(status_code=400, detail="Invalid or expired magic link")
    
    email = link.email
    
    # Mark link as used
    link.used = True
    link.used_at = datetime.utcnow()
    
    # Find or create member
    member = db.query(models.TeamMember).filter(
        models.TeamMember.email == email
    ).first()
    
    if not member:
        # Check for pending invite
        invite = db.query(models.Invitation).filter(
            models.Invitation.email == email,
            models.Invitation.used == False,
        ).first()
        
        role = "member"
        if invite:
            role = invite.role
            invite.used = True
        
        # Auto-create member for admins or invited users
        if auth.is_admin(email) or invite:
            wallet_id = await credits_client.create_wallet(owner_id=email, type="USER")
            if not wallet_id:
                wallet_id = f"w_{uuid.uuid4()}"
            
            member = models.TeamMember(
                id=str(uuid.uuid4()),
                name=email.split("@")[0].title(),
                email=email,
                skills=[],
                wallet_id=wallet_id,
                status="active",
            )
            db.add(member)
            db.commit()
            db.refresh(member)
            logger.info(f"Auto-created member for {email}")
            
            # Auto-mint Email Alias (Cloudflare)
            alias_prefix = email.split("@")[0]
            # Avoid creating recursive loops if email is already @fullpotential.ai
            if not email.endswith("@fullpotential.ai"):
                background_tasks.add_task(cf_client.create_email_rule, alias_prefix, email)
                logger.info(f"Triggered Cloudflare alias minting: {alias_prefix}@fullpotential.ai -> {email}")

        else:
            raise HTTPException(status_code=403, detail="No account found for this email")
    
    # Determine role
    role = auth.get_role(email)
    
    # Create JWT
    access_token = auth.create_access_token(member.id, email, role)
    
    # Store session
    token_hash = hashlib.sha256(access_token.encode()).hexdigest()[:32]
    session = models.Session(
        id=str(uuid.uuid4()),
        member_id=member.id,
        token_hash=token_hash,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:200],
        expires_at=datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    )
    db.add(session)
    db.commit()
    
    # Redirect to dashboard with token in query param (more reliable than hash fragment)
    # Use the public dashboard URL, not the API URL
    redirect_url = f"https://fullpotential.ai/dashboards/team/?auth_token={access_token}"
    
    return RedirectResponse(url=redirect_url, status_code=302)


@app.get("/auth/me")
async def get_current_user_info(
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Get current authenticated user info."""
    member = db.query(models.TeamMember).filter(
        models.TeamMember.id == current_user.member_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    stats = _collect_member_dashboard(member, db)
    balance = 0.0
    if member.wallet_id:
        balance = await credits_client.get_balance(member.wallet_id)
    
    return {
        "member": {
            "id": member.id,
            "name": member.name,
            "email": member.email,
            "skills": member.skills,
            "trust_score": member.trust_score,
            "status": member.status,
            "avatar_url": member.avatar_url,
            "phone": member.phone,
            "whatsapp": member.whatsapp,
            "telegram": member.telegram,
            "timezone": member.timezone,
            "bio": member.bio,
        },
        "role": current_user.role,
        "is_admin": current_user.is_admin,
        "stats": stats["summary"],
        "balance_uc": balance,
    }


@app.post("/auth/logout")
async def logout(
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Logout and revoke session."""
    # Revoke all sessions for this user (simple approach)
    db.query(models.Session).filter(
        models.Session.member_id == current_user.member_id,
        models.Session.revoked == False,
    ).update({"revoked": True})
    db.commit()
    
    return {"status": "logged_out"}


# --- Invite API (Admin Only) ---

@app.post("/api/invites", response_model=models.InviteResponse)
async def create_invite(
    payload: models.InviteRequest,
    request: Request,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Create an invite for a new team member (admin only)."""
    email = payload.email.lower().strip()
    
    # Check if already exists
    existing = db.query(models.TeamMember).filter(
        models.TeamMember.email == email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Member already exists")
    
    # Create invite
    token = auth.create_invite_token(email, payload.role, db)
    
    # Build invite URL
    base_url = str(request.base_url).rstrip("/")
    invite_url = f"{base_url}/join?invite={token}"
    
    # Get the invite record
    invite = db.query(models.Invitation).filter(
        models.Invitation.token == token
    ).first()
    
    # Send invite email
    await comms_client.send_email(
        to=email,
        subject="You're Invited to Join the Full Potential AI Team!",
        body=(
            f"You've been invited to join the Team Portal.\n\n"
            f"Click here to accept and set up your account:\n"
            f"{invite_url}\n\n"
            f"This invite expires in 7 days."
        ),
    )
    
    logger.info(f"Invite sent to {email}: {invite_url}")
    
    return models.InviteResponse(
        token=token,
        email=email,
        role=payload.role,
        expires_at=invite.expires_at,
        invite_url=invite_url,
    )


@app.get("/api/invites")
async def list_invites(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """List all pending invites (admin only)."""
    invites = db.query(models.Invitation).filter(
        models.Invitation.used == False,
        models.Invitation.expires_at > datetime.utcnow(),
    ).all()
    
    return [
        {
            "token": inv.token,
            "email": inv.email,
            "role": inv.role,
            "expires_at": inv.expires_at.isoformat(),
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invites
    ]

@app.delete("/api/invites/{token}")
async def delete_invite(
    token: str,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Delete an invitation (admin only)."""
    invite = db.query(models.Invitation).filter(models.Invitation.token == token).first()
    if not invite:
        raise HTTPException(404, "Invite not found")
    
    db.delete(invite)
    db.commit()
    return {"status": "deleted"}


# --- Vault API (Secure Credentials) ---

@app.post("/api/vault/items", response_model=models.VaultItemResponse)
async def create_vault_item(
    payload: models.VaultItemCreate,
    current_user: auth.CurrentUser = Depends(auth.require_admin), # Start with admin only for creation
    db: Session = Depends(get_db),
):
    """Store a secret in the vault."""
    encrypted = cipher_suite.encrypt(payload.content.encode()).decode()
    
    item = models.VaultItem(
        id=str(uuid.uuid4()),
        name=payload.name,
        category=payload.category,
        type=payload.type,
        content_encrypted=encrypted,
        filename=payload.filename,
        created_by_id=current_user.member_id,
        min_role=payload.min_role
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@app.delete("/api/vault/items/{item_id}")
async def delete_vault_item(
    item_id: str,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Delete a secret (Admin only)."""
    item = db.query(models.VaultItem).filter(models.VaultItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    
    db.delete(item)
    db.commit()
    return {"status": "deleted"}

@app.patch("/api/vault/items/{item_id}")
async def update_vault_item(
    item_id: str,
    payload: models.VaultItemCreate,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Update a secret (Admin only)."""
    item = db.query(models.VaultItem).filter(models.VaultItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    
    encrypted = cipher_suite.encrypt(payload.content.encode()).decode()
    
    item.name = payload.name
    item.category = payload.category
    item.type = payload.type
    item.min_role = payload.min_role
    item.content_encrypted = encrypted
    if payload.filename:
        item.filename = payload.filename
        
    db.commit()
    db.refresh(item)
    return item

@app.get("/api/vault/items", response_model=List[models.VaultItemResponse])
async def list_vault_items(
    category: Optional[str] = None,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """List available secrets (metadata only)."""
    query = db.query(models.VaultItem)
    if category:
        query = query.filter(models.VaultItem.category == category)
        
    # Filter by role permission (simple hierarchy: admin > developer > assistant > member)
    # TODO: Implement robust RBAC. For now, admins see all.
    if not current_user.is_admin:
        # Basic: only show if min_role is member or matches user role
        # This is a simplification.
        pass
        
    return query.all()

@app.get("/api/vault/retrieve")
async def retrieve_vault_item(
    name: str,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve a secret by name (Agent friendly)."""
    # Case-insensitive search
    item = db.query(models.VaultItem).filter(func.lower(models.VaultItem.name) == name.lower()).first()
    
    if not item:
        raise HTTPException(404, f"Secret '{name}' not found")
        
    # Check Access
    if not current_user.is_admin and item.min_role == "admin":
        raise HTTPException(403, "Access denied")
        
    try:
        decrypted = cipher_suite.decrypt(item.content_encrypted.encode()).decode()
        return {
            "name": item.name,
            "secret": decrypted,
            "type": item.type,
            "filename": item.filename
        }
    except Exception:
        raise HTTPException(500, "Decryption failed")

@app.post("/api/vault/items/{item_id}/reveal")
async def reveal_vault_item(
    item_id: str,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Decrypt and show secret."""
    item = db.query(models.VaultItem).filter(models.VaultItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
        
    # Check Access
    if not current_user.is_admin and item.min_role == "admin":
        raise HTTPException(403, "Access denied")
        
    try:
        decrypted = cipher_suite.decrypt(item.content_encrypted.encode()).decode()
        return {
            "content": decrypted,
            "type": item.type,
            "filename": item.filename
        }
    except Exception:
        raise HTTPException(500, "Decryption failed")

@app.post("/api/vault/items/{item_id}/share")
async def create_vault_share(
    item_id: str,
    payload: models.VaultShareCreate,
    request: Request,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Generate a secure, time-limited link."""
    token = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
    
    pw_hash = None
    if payload.password:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        pw_hash = pwd_context.hash(payload.password)
    
    share = models.VaultShare(
        token=token,
        vault_item_id=item_id,
        created_by_id=current_user.member_id,
        expires_at=datetime.utcnow() + timedelta(hours=payload.expires_in_hours),
        one_time_use=payload.one_time_use,
        password_hash=pw_hash
    )
    db.add(share)
    db.commit()
    
    base_url = str(request.base_url).rstrip("/")
    return {"share_url": f"{base_url}/vault/share/{token}", "expires_at": share.expires_at}

@app.patch("/api/vault/items/{item_id}")
async def update_vault_item(
    item_id: str,
    payload: dict = Body(...),
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Update vault item (Admin only)."""
    item = db.query(models.VaultItem).filter(models.VaultItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
        
    if "name" in payload:
        item.name = payload["name"]
    if "category" in payload:
        item.category = payload["category"]
    if "min_role" in payload:
        item.min_role = payload["min_role"]
    
    # Update content if provided (re-encrypt)
    if "content" in payload and payload["content"]:
        encrypted = cipher_suite.encrypt(payload["content"].encode()).decode()
        item.content_encrypted = encrypted
        
    db.commit()
    return {"status": "updated", "item": item.name}

@app.delete("/api/vault/items/{item_id}")
async def delete_vault_item(
    item_id: str,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Delete a vault item (Admin only)."""
    item = db.query(models.VaultItem).filter(models.VaultItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
        
    # Delete shares first? Cascade should handle it if set, otherwise manual.
    db.query(models.VaultShare).filter(models.VaultShare.vault_item_id == item_id).delete()
    
    db.delete(item)
    db.commit()
    return {"status": "deleted"}

@app.post("/vault/share/{token}")
async def access_shared_secret(
    token: str, 
    payload: dict = Body(default={}),
    db: Session = Depends(get_db)
):
    """Public access point for shared secrets."""
    share = db.query(models.VaultShare).filter(
        models.VaultShare.token == token,
        models.VaultShare.used == False,
        models.VaultShare.expires_at > datetime.utcnow()
    ).first()
    
    if not share:
        raise HTTPException(404, "Link invalid or expired")
        
    # Check Password
    if share.password_hash:
        password = payload.get("password")
        if not password:
            return {"status": "password_required"}
            
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        if not pwd_context.verify(password, share.password_hash):
            raise HTTPException(401, "Incorrect Password")
        
    item = db.query(models.VaultItem).filter(models.VaultItem.id == share.vault_item_id).first()
    
    if share.one_time_use:
        share.used = True
        share.used_at = datetime.utcnow()
        db.commit()
        
    try:
        content = cipher_suite.decrypt(item.content_encrypted.encode()).decode()
        return {
            "status": "revealed",
            "name": item.name,
            "secret": content, 
            "warning": "This link is now burned (if one-time)." if share.one_time_use else f"Expires: {share.expires_at}"
        }
    except Exception:
        return {"error": "Decryption failed"}
    
@app.get("/vault/share/{token}")
async def view_shared_secret_page(token: str):
    """Serve the public UI for the shared secret."""
    # We serve a simple HTML page that calls the POST endpoint
    return FileResponse("app/static/share.html")

# --- Public Utility (FP SafeLink) ---

@app.get("/services/safelink")
async def serve_safelink_ui():
    return FileResponse("app/static/safelink.html")

@app.post("/api/public/safelink")
async def create_public_safelink(
    request: Request,
    payload: dict = Body(...),
    db: Session = Depends(get_db),
):
    """Create a public, ephemeral secret link."""
    content = payload.get("content")
    if not content or len(content) > 5000:
        raise HTTPException(400, "Content too long or empty")
        
    # Create anonymous Vault Item
    encrypted = cipher_suite.encrypt(content.encode()).decode()
    item_id = str(uuid.uuid4())
    
    item = models.VaultItem(
        id=item_id,
        name="Public Secret",
        category="public",
        type="text",
        content_encrypted=encrypted,
        created_by_id="system_public", # Special ID
        min_role="public"
    )
    db.add(item)
    
    # Create Share Link
    token = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
    share = models.VaultShare(
        token=token,
        vault_item_id=item_id,
        created_by_id="system_public",
        expires_at=datetime.utcnow() + timedelta(hours=24),
        one_time_use=True,
    )
    db.add(share)
    db.commit()
    
    base_url = str(request.base_url).rstrip("/")
    # Redirect to main domain if we are behind proxy
    if "fullpotential.ai" in str(request.headers.get("host", "")):
        base_url = "https://fullpotential.ai"
        
    return {"share_url": f"{base_url}/vault/share/{token}"}


# --- Team Management API ---

@app.get("/api/team", response_model=List[models.TeamMemberResponse])
async def list_team(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """List all team members (admin only)."""
    return db.query(models.TeamMember).all()


@app.post("/api/team", response_model=models.TeamMemberResponse)
async def add_team_member(
    member: models.TeamMemberCreate,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    # Create real wallet in Credits Manager
    wallet_id = await credits_client.create_wallet(owner_id=member.email, type="USER")
    if not wallet_id:
        logger.warning("Failed to create wallet in Credits Manager, using local fallback")
        wallet_id = f"w_{uuid.uuid4()}" # Fallback

    db_member = models.TeamMember(
        id=str(uuid.uuid4()),
        name=member.name,
        email=member.email,
        skills=member.skills,
        wallet_id=wallet_id
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

@app.get("/api/team/{member_id}", response_model=models.TeamMemberResponse)
async def get_team_member(
    member_id: str,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Get team member details (admin or self only)."""
    if not current_user.is_admin and current_user.member_id != member_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    member = db.query(models.TeamMember).filter(models.TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@app.delete("/api/team/{member_id}")
async def delete_team_member(
    member_id: str,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Delete a team member (admin only)."""
    member = db.query(models.TeamMember).filter(models.TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Delete associated data if needed? Or just the member record
    # For now, cascading delete via DB should handle it if configured, otherwise explicit
    # But SQLAlchemy defaults won't cascade unless configured. 
    # We'll just delete the member. SQLite might complain about foreign keys if enforced.
    
    db.delete(member)
    db.commit()
    return {"status": "deleted", "member_id": member_id}


@app.get("/api/team/{member_id}/dashboard")
async def get_team_member_dashboard(
    member_id: str,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Get member dashboard (admin or self only)."""
    if not current_user.is_admin and current_user.member_id != member_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    member = db.query(models.TeamMember).filter(models.TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    stats = _collect_member_dashboard(member, db)
    balance = 0.0
    if member.wallet_id:
        balance = await credits_client.get_balance(member.wallet_id)
    
    return {
        "member": {
            "id": member.id,
            "name": member.name,
            "email": member.email,
            "skills": member.skills,
            "trust_score": member.trust_score,
            "status": member.status,
            "source": member.source,
        },
        "stats": stats["summary"],
        "recent_assignments": stats["recent_assignments"],
        "balance_uc": balance,
    }


@app.patch("/api/team/{member_id}/profile")
async def update_profile(
    member_id: str,
    payload: models.ProfileUpdateRequest,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Update own profile (self only, admin can update anyone)."""
    if not current_user.is_admin and current_user.member_id != member_id:
        raise HTTPException(status_code=403, detail="Can only update your own profile")
    
    member = db.query(models.TeamMember).filter(models.TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    if payload.name is not None:
        member.name = payload.name
    if payload.skills is not None:
        member.skills = payload.skills
        
    # New fields
    if payload.phone is not None:
        member.phone = payload.phone
    if payload.whatsapp is not None:
        member.whatsapp = payload.whatsapp
    if payload.telegram is not None:
        member.telegram = payload.telegram
    if payload.timezone is not None:
        member.timezone = payload.timezone
    if payload.bio is not None:
        member.bio = payload.bio
    
    db.commit()
    db.refresh(member)
    
    return {"status": "updated", "member_id": member_id}

@app.post("/api/team/{member_id}/avatar")
async def upload_avatar(
    member_id: str,
    file: UploadFile = File(...),
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Upload profile picture."""
    if not current_user.is_admin and current_user.member_id != member_id:
        raise HTTPException(status_code=403, detail="Access denied")
        
    member = db.query(models.TeamMember).filter(models.TeamMember.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
        
    # Ensure static/avatars exists
    avatar_dir = Path("app/static/avatars")
    avatar_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"{member_id}.{ext}"
    file_path = avatar_dir / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Update DB
    member.avatar_url = f"/static/avatars/{filename}"
    db.commit()
    
    return {"avatar_url": member.avatar_url}

@app.get("/api/finance/balance/{member_id}")
async def get_balance(member_id: str, db: Session = Depends(get_db)):
    member = db.query(models.TeamMember).filter(models.TeamMember.id == member_id).first()
    if not member or not member.wallet_id:
        return {"balance_uc": 0.0}
    
    balance = await credits_client.get_balance(member.wallet_id)
    return {"balance_uc": balance}

# --- Recruiting Agent (Stub) ---

@app.post("/api/recruiter/start")
async def start_recruiter(
    background_tasks: BackgroundTasks,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Start recruiter agent (admin only)."""
    recruiter_tracker["state"] = "scouting"
    recruiter_tracker["last_run"] = datetime.utcnow().isoformat()
    background_tasks.add_task(run_recruiter_agent)
    return {"status": "Recruiter agent started", "mode": "scout"}

async def run_recruiter_agent():
    logger.info("Recruiter agent scanning GitHub...")
    import httpx
    
    found_candidates = []
    
    try:
        async with httpx.AsyncClient() as client:
            # Search for "python ai agent"
            resp = await client.get(
                "https://api.github.com/search/users?q=python+ai+agent&sort=followers&order=desc",
                headers={"User-Agent": "FullPotentialOS"}
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])[:3] # Get top 3
                for item in items:
                    found_candidates.append({
                        "name": f"{item['login']} (GitHub)",
                        "email": f"{item['login']}@github-scout.com", # Placeholder
                        "skills": ["Python", "AI", "Agents", "GitHub"],
                        "source": "github_scout",
                        "profile": item["html_url"]
                    })
    except Exception as e:
        logger.error(f"GitHub Search Error: {e}")
        # Fallback to simulation if API fails
        found_candidates.append({
            "name": "Alex Chen (AI Scouted)",
            "email": "alex.dev@example.com",
            "skills": ["Python", "FastAPI", "React"],
            "source": "simulation"
        })

    # --- Outreach Logic (OnlineJobs.ph Simulation) ---
    try:
        # Simulate finding Virtual Assistants
        outreach_targets = [
            {"name": "Maria S. (VA)", "email": "maria.va@simulated-outreach.com", "skills": ["Admin", "Research", "Data Entry"], "source": "onlinejobs_ph"},
            {"name": "John D. (Lead Gen)", "email": "john.lead@simulated-outreach.com", "skills": ["Lead Gen", "Email", "Scraping"], "source": "upwork_scraper"}
        ]
        
        for target in outreach_targets:
            # Check if exists
            if not db.query(models.TeamMember).filter(models.TeamMember.email == target["email"]).first():
                # Create "Invited" member
                new_member = models.TeamMember(
                    id=str(uuid.uuid4()),
                    name=target["name"],
                    email=target["email"],
                    skills=target["skills"],
                    status="invited", # New status
                    source=target["source"],
                    scouted_by="recruiter_outreach_v1",
                    trust_score=50 # Lower start trust
                )
                db.add(new_member)
                
                # Simulate sending outreach email
                logger.info(f"Recruiter: Sending outreach to {target['name']} -> 'Earn UC completing tasks'")
                await comms_client.send_email(
                    to=target["email"],
                    subject="Paid Opportunity: AI Research Assistant (Remote)",
                    body=f"Hi {target['name']},\n\nWe found your profile on {target['source']}. We have immediate tasks available paid in Universal Credits (UC).\n\nView Bounties: https://fullpotential.ai/bounties\n\n- Full Potential AI"
                )
                
        db.commit()
    except Exception as e:
        logger.error(f"Recruiter Outreach Error: {e}")

    try:
        for cand in found_candidates:
            # Check if exists
            if not db.query(models.TeamMember).filter(models.TeamMember.email == cand["email"]).first():
                new_member = models.TeamMember(
                    id=str(uuid.uuid4()),
                    name=cand["name"],
                    email=cand["email"],
                    skills=cand["skills"],
                    status="pending",
                    source=cand["source"],
                    scouted_by="recruiter_agent_v2",
                    trust_score=65
                )
                db.add(new_member)
                logger.info(f"Recruiter: Added {cand['name']}")
        db.commit()
    except Exception as e:
        logger.error(f"Recruiter DB Error: {e}")
    finally:
        db.close()
        recruiter_tracker["state"] = "idle"
        recruiter_tracker["last_run"] = datetime.utcnow().isoformat()

# --- Work Assignment API ---

@app.post("/api/assignments", response_model=models.AssignmentResponse)
async def create_assignment(
    task: models.AssignmentCreate,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Create a new assignment (admin only)."""
    # Fetch Context Pack from Strategic Intel
    context = await intel_client.get_context_pack(f"{task.title}: {task.description}")
    
    db_task = models.WorkAssignment(
        id=str(uuid.uuid4()),
        title=task.title,
        description=task.description,
        type=task.type,
        uc_reward=task.uc_reward,
        mission_id=task.mission_id,
        context_summary=context.get("summary"),
        relevant_docs=context.get("docs", [])
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


@app.get("/api/assignments", response_model=List[models.AssignmentResponse])
async def list_assignments(
    status: Optional[str] = None,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """List assignments. Members see only their own or open tasks."""
    query = db.query(models.WorkAssignment)
    
    if not current_user.is_admin:
        # Members see: their assignments OR open pending tasks
        query = query.filter(
            (models.WorkAssignment.assignee_id == current_user.member_id) |
            (models.WorkAssignment.status == "pending")
        )
    
    if status:
        query = query.filter(models.WorkAssignment.status == status)
    
    return query.order_by(models.WorkAssignment.created_at.desc()).all()

@app.get("/api/assignments/{task_id}", response_model=models.AssignmentResponse)
async def get_assignment(
    task_id: str,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Get assignment details."""
    task = db.query(models.WorkAssignment).filter(models.WorkAssignment.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Members can only see their own or pending tasks
    if not current_user.is_admin:
        if task.assignee_id != current_user.member_id and task.status != "pending":
            raise HTTPException(status_code=403, detail="Access denied")
    
    return task


@app.post("/api/assignments/{task_id}/claim")
async def claim_assignment(
    task_id: str,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Claim an open assignment (any authenticated member)."""
    task = db.query(models.WorkAssignment).filter(models.WorkAssignment.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    if task.status != "pending":
        raise HTTPException(status_code=400, detail="Task is not available for claiming")
    
    if task.assignee_id:
        raise HTTPException(status_code=400, detail="Task already claimed")
    
    # Assign to current user
    task.assignee_id = current_user.member_id
    task.status = "in_progress"
    db.commit()
    db.refresh(task)
    
    # Get member for notification
    member = db.query(models.TeamMember).filter(
        models.TeamMember.id == current_user.member_id
    ).first()
    
    logger.info(f"Task {task_id} claimed by {member.name if member else current_user.email}")
    
    return {
        "status": "claimed",
        "assignment_id": task.id,
        "assignee": member.name if member else current_user.email,
    }


@app.post("/api/assignments/{task_id}/complete")
async def complete_assignment(
    task_id: str,
    payload: models.AssignmentCompleteRequest,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Complete an assignment (assignee or admin only)."""
    task = db.query(models.WorkAssignment).filter(models.WorkAssignment.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Only assignee or admin can complete
    if not current_user.is_admin and task.assignee_id != current_user.member_id:
        raise HTTPException(status_code=403, detail="Only the assignee can complete this task")
    
    if task.status not in ["pending", "in_progress"]:
        raise HTTPException(status_code=400, detail="Assignment already closed")
    
    completion_doc = None
    if payload.notes:
        completion_doc = {
            "type": "completion_notes",
            "content": payload.notes,
            "timestamp": datetime.utcnow().isoformat(),
        }
        docs = task.relevant_docs or []
        docs.append(completion_doc)
        task.relevant_docs = docs
    
    task.status = "completed"
    task.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    
    portal_status = False
    if task.procurement_id:
        portal_status = await api_portal_client.submit_mission_result(
            task.procurement_id,
            payload.notes or f"Completed via Team Portal for {task.title}",
            payload.credentials or [],
        )
    
    # Sync with Mission Hub
    if task.mission_id:
        await mission_client.update_mission_status(task.mission_id, "completed", current_user.email)
        
    # Notify Brain
    await brain_client.notify_mission_update(
        mission_id=task.id,
        status="completed",
        context=f"Completed by {current_user.email}. Notes: {payload.notes}"
    )
    
    return {
        "status": "completed",
        "assignment_id": task.id,
        "api_portal_sync": portal_status,
        "notes_stored": completion_doc is not None,
    }

@app.post("/api/smart-assign/{task_id}")
async def smart_assign(
    task_id: str,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Smart assign a task to best candidate (admin only)."""
    task = db.query(models.WorkAssignment).filter(models.WorkAssignment.id == task_id).first()
    if not task:
        raise HTTPException(404, "Task not found")
    
    candidates = db.query(models.TeamMember).filter(models.TeamMember.status != "inactive").all()
    if not candidates:
        return {"status": "failed", "reason": "No candidates available"}
    
    best_choice = None
    best_score = -1.0
    best_breakdown = {}
    
    for member in candidates:
        skill_component = _skill_score(task, member)
        availability_component = _availability_score(member, db)
        trust_component = (member.trust_score or 0) / 100
        responsiveness_component = _responsiveness_score(member)
        
        score = (
            skill_component * 0.4
            + availability_component * 0.25
            + trust_component * 0.2
            + responsiveness_component * 0.15
        )
        
        if score > best_score:
            best_score = score
            best_choice = member
            best_breakdown = {
                "skill_match": round(skill_component, 2),
                "availability": round(availability_component, 2),
                "trust": round(trust_component, 2),
                "responsiveness": round(responsiveness_component, 2),
            }
    
    if not best_choice:
        return {"status": "failed", "reason": "Unable to rank candidates"}
    
    task.assignee_id = best_choice.id
    task.status = "in_progress"
    db.commit()
    db.refresh(task)
    
    await comms_client.send_email(
        to=best_choice.email,
        subject=f"New Assignment: {task.title}",
        body=(
            f"You have a new assignment worth {task.uc_reward} UC.\n\n"
            f"Description: {task.description}\n"
            f"Please visit the Team Portal to view full context."
        ),
    )
    
    return {
        "status": "assigned",
        "assignee": best_choice.name,
        "score": round(best_score, 2),
        "breakdown": best_breakdown,
    }

@app.post("/api/integrate/sync")
async def sync_all_missions(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Sync missions from API Portal AND Mission Hub (admin only)."""
    # 1. API Portal (Procurement)
    api_missions = await api_portal_client.get_procurement_missions()
    count = 0
    for mission in api_missions:
        existing = db.query(models.WorkAssignment).filter(models.WorkAssignment.procurement_id == mission['id']).first()
        if not existing:
            reward = mission.get("payment_amount") or mission.get("uc_reward") or 100
            new_task = models.WorkAssignment(
                id=str(uuid.uuid4()),
                title=f"API: {mission['title']}",
                description=mission.get('description', 'Procurement task'),
                type="api_procurement",
                uc_reward=reward,
                status="pending",
                procurement_id=mission['id']
            )
            db.add(new_task)
            count += 1
            
    # 2. Mission Hub (Strategic)
    strat_missions = await mission_client.get_missions()
    for mission in strat_missions:
        # Only import 'active' or 'pending' missions that aren't assigned yet?
        existing = db.query(models.WorkAssignment).filter(models.WorkAssignment.mission_id == mission['id']).first()
        if not existing and mission.get('status') in ['active', 'pending']:
            # Auto-Tagging Logic for Role Dispatch
            title_lower = mission['title'].lower()
            desc_lower = mission.get('description', '').lower()
            text = f"{title_lower} {desc_lower}"
            
            auto_tags = []
            if any(k in text for k in ["procure", "find", "research", "schedule", "email", "contact", "list", "data"]):
                auto_tags.append("role:assistant")
            if any(k in text for k in ["code", "deploy", "fix", "api", "bug", "server", "database", "python"]):
                auto_tags.append("role:developer")
            if any(k in text for k in ["strategy", "plan", "review", "audit"]):
                auto_tags.append("role:strategist")
                
            # Default to assistant if ambiguous but procurement-like
            if not auto_tags and mission.get("reward_uc", 0) < 200:
                auto_tags.append("role:assistant")

            # Add tags to description for filtering (simple solution without schema change)
            final_desc = mission.get('description', 'Strategic Mission')
            if auto_tags:
                final_desc += f"\n\n[TAGS]: {', '.join(auto_tags)}"

            new_task = models.WorkAssignment(
                id=str(uuid.uuid4()),
                title=f"MISSION: {mission['title']}",
                description=final_desc,
                type="mission",
                uc_reward=mission.get("reward_uc", 500),
                status="pending",
                mission_id=mission['id']
            )
            db.add(new_task)
            count += 1

    db.commit()
    return {"status": "synced", "new_tasks": count}

@app.get("/api/emails")
async def get_emails(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Fetch emails from Cortex Mail (admin only)."""
    return await cortex_client.get_emails()

@app.post("/api/emails/{email_id}/block")
async def block_email_sender(
    email_id: str,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Block sender via Cortex Mail (admin only)."""
    return await cortex_client.block_sender(email_id)

@app.post("/api/emails/{email_id}/unsubscribe")
async def unsubscribe_email(
    email_id: str,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Unsubscribe via Cortex Mail (admin only)."""
    return await cortex_client.unsubscribe(email_id)

@app.get("/api/config/swarm-secret")
async def get_swarm_secret(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Get the Swarm Secret for display (Admin only)."""
    return {"secret": "fpai-swarm-genesis-permanent-link-v1"}

@app.post("/api/genesis/keys")
async def generate_genesis_key(
    payload: dict = Body(...),
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Generate a new Agent Key."""
    agent_name = payload.get("agent_name")
    if not agent_name:
        raise HTTPException(400, "Agent name required")
        
    key = await genesis_client.generate_key(agent_name)
    if not key:
        raise HTTPException(500, "Failed to generate key")
        
    return {"agent_name": agent_name, "key": key}

@app.post("/api/genesis/enrollment-key")
async def set_enrollment_key(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Generate or Rotate the Master Enrollment Key."""
    key = await genesis_client.set_enrollment_key()
    if not key:
        raise HTTPException(500, "Failed to set enrollment key")
    return {"enrollment_key": key}

@app.get("/api/genesis/agents")
async def list_genesis_agents(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """List all registered agents."""
    return await genesis_client.get_all_agents()

@app.get("/api/genesis/servers")
async def list_genesis_servers(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    return await genesis_client.get_servers()

@app.get("/api/genesis/services")
async def list_genesis_services(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    return await genesis_client.get_services()

@app.get("/api/portal/needs")
async def get_api_needs(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Proxy to get API needs from API Portal."""
    return await api_portal_client.get_needs()

@app.post("/api/portal/missions")
async def create_api_mission(
    payload: dict = Body(...),
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Proxy to create a procurement mission."""
    return await api_portal_client.create_mission(payload)

# --- Compliance & Legal API ---

@app.post("/api/compliance/docs")
async def upload_compliance_doc(
    title: str = Body(...),
    description: str = Body(default=None),
    category: str = Body(default="legal"),
    file: UploadFile = File(...),
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Upload a legal template PDF."""
    doc_dir = Path("app/static/docs")
    doc_dir.mkdir(parents=True, exist_ok=True)
    
    doc_id = str(uuid.uuid4())
    # Allow other extensions if not strict legal
    ext = "pdf"
    if file.filename:
        parts = file.filename.split(".")
        if len(parts) > 1: ext = parts[-1]
        
    filename = f"{doc_id}.{ext}"
    file_path = doc_dir / filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc = models.ComplianceDoc(
        id=doc_id,
        title=title,
        description=description,
        category=category,
        file_path=f"/static/docs/{filename}"
    )
    db.add(doc)
    db.commit()
    return {"status": "uploaded", "doc_id": doc.id}

@app.get("/api/compliance/docs")
async def list_compliance_docs(
    category: Optional[str] = None,
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """List all templates (Admin)."""
    query = db.query(models.ComplianceDoc)
    if category:
        query = query.filter(models.ComplianceDoc.category == category)
    
    docs = query.all()
    return [
        {
            "id": d.id,
            "title": d.title,
            "description": d.description,
            "category": d.category,
            "file_path": d.file_path,
            "created_at": d.created_at.isoformat(),
            "pending_count": len([s for s in d.signatures if s.status == 'pending']),
            "signed_count": len([s for s in d.signatures if s.status == 'signed'])
        }
        for d in docs
    ]

@app.post("/api/admin/backup-vault")
async def backup_vault(
    current_user: auth.CurrentUser = Depends(auth.require_admin),
):
    """Trigger a vault database backup manually."""
    try:
        import subprocess
        result = subprocess.run(["sudo", "/opt/fpai/scripts/backup-vault.sh"], capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "output": result.stdout}
        else:
            raise HTTPException(500, f"Backup failed: {result.stderr}")
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/voice/call")
async def initiate_voice_call(
    payload: dict = Body(...),
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
):
    """Initiate a Red Phone call to the user."""
    phone_number = payload.get("phone_number")
    if not phone_number:
        raise HTTPException(400, "Phone number required")
        
    # Proxy to Voice Service (Port 8888)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "http://localhost:8888/call",
                json={"phone_number": phone_number}
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                raise HTTPException(502, f"Voice Service Error: {resp.text}")
    except Exception as e:
        raise HTTPException(502, f"Connection Failed: {e}")

@app.post("/api/compliance/assign")
async def assign_compliance_doc(
    payload: dict = Body(...), # {doc_id, member_ids: []}
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db),
):
    """Assign a document to members to sign."""
    doc_id = payload.get("doc_id")
    member_ids = payload.get("member_ids", [])
    
    doc = db.query(models.ComplianceDoc).filter(models.ComplianceDoc.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
        
    count = 0
    for mid in member_ids:
        # Check if already assigned
        existing = db.query(models.Signature).filter(
            models.Signature.doc_id == doc_id,
            models.Signature.member_id == mid
        ).first()
        
        if not existing:
            sig = models.Signature(
                id=str(uuid.uuid4()),
                doc_id=doc_id,
                member_id=mid,
                status="pending"
            )
            db.add(sig)
            
            # Notify member
            member = db.query(models.TeamMember).filter(models.TeamMember.id == mid).first()
            if member:
                await comms_client.send_email(
                    to=member.email,
                    subject=f"Action Required: Sign {doc.title}",
                    body=f"Please log in to the Team Portal to review and sign: {doc.title}"
                )
            count += 1
            
    db.commit()
    return {"status": "assigned", "count": count}

@app.get("/api/compliance/my-signatures")
async def get_my_signatures(
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Get pending and signed docs for current user."""
    sigs = db.query(models.Signature).filter(
        models.Signature.member_id == current_user.member_id
    ).all()
    
    return [
        {
            "id": s.id,
            "doc_title": s.document.title,
            "doc_url": s.document.file_path,
            "status": s.status,
            "signed_at": s.signed_at.isoformat() if s.signed_at else None,
            "vault_id": s.vault_item_id
        }
        for s in sigs
    ]

@app.post("/api/compliance/sign/{sig_id}")
async def sign_document(
    sig_id: str,
    payload: dict = Body(...), # {signature_text: "John Doe"}
    request: Request = None,
    current_user: auth.CurrentUser = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Sign a document."""
    sig = db.query(models.Signature).filter(
        models.Signature.id == sig_id,
        models.Signature.member_id == current_user.member_id
    ).first()
    
    if not sig:
        raise HTTPException(404, "Signature request not found")
    
    if sig.status == "signed":
        raise HTTPException(400, "Already signed")
        
    signature_text = payload.get("signature_text")
    if not signature_text:
        raise HTTPException(400, "Signature text required")
        
    # 1. Create Proof
    timestamp = datetime.utcnow()
    proof_content = (
        f"DIGITAL SIGNATURE MANIFEST\n"
        f"--------------------------\n"
        f"Document: {sig.document.title}\n"
        f"Signer: {current_user.email}\n"
        f"Signature: {signature_text}\n"
        f"Date: {timestamp.isoformat()}\n"
        f"IP: {request.client.host if request else 'unknown'}\n"
        f"User Agent: {request.headers.get('user-agent')}\n"
        f"Ref ID: {sig.id}\n"
    )
    
    # 2. Vault It
    encrypted = cipher_suite.encrypt(proof_content.encode()).decode()
    vault_item = models.VaultItem(
        id=str(uuid.uuid4()),
        name=f"Signed: {sig.document.title} - {current_user.email}",
        category="legal",
        type="text",
        content_encrypted=encrypted,
        created_by_id=current_user.member_id,
        min_role="admin", # Only admins can see signed proofs? Or user too?
        allowed_users=[current_user.member_id] # Allow signer to see it
    )
    db.add(vault_item)
    
    # 3. Update Signature Record
    sig.status = "signed"
    sig.signed_at = timestamp
    sig.signature_text = signature_text
    sig.ip_address = request.client.host if request else None
    sig.user_agent = request.headers.get('user-agent')
    sig.vault_item_id = vault_item.id
    
    db.commit()
    
    return {"status": "signed", "proof_id": vault_item.id}

@app.post("/api/admin/broadcast")
async def admin_broadcast(
    payload: dict = Body(...),
    current_user: auth.CurrentUser = Depends(auth.require_admin),
    db: Session = Depends(get_db)
):
    """
    Global Command Terminal Broadcast.
    Safety: Requires explicit confirmation for live mode.
    """
    message = payload.get("message")
    mode = payload.get("mode", "test") # test, live
    confirmation = payload.get("confirmation")
    
    if not message:
        raise HTTPException(400, "Message required")
        
    if mode == "live":
        if confirmation != "BROADCAST_CONFIRM":
            raise HTTPException(400, "Safety Lock Engaged: Confirmation code required for LIVE broadcast.")
            
        # Fetch all active members (or filtering logic)
        recipients = db.query(models.TeamMember).filter(models.TeamMember.status == "active").all()
        count = 0
        for member in recipients:
            # In production, queue this via a worker!
            await comms_client.send_email(
                to=member.email,
                subject="🚨 Global Command Broadcast",
                body=f"SYSTEM BROADCAST:\n\n{message}\n\n--\nFull Potential OS"
            )
            count += 1
        
        logger.warning(f"LIVE BROADCAST sent to {count} members by {current_user.email}")
        return {"status": "sent", "count": count, "mode": "LIVE"}
        
    else:
        # Test Mode: Send only to sender
        member = db.query(models.TeamMember).filter(models.TeamMember.id == current_user.member_id).first()
        await comms_client.send_email(
            to=member.email,
            subject="[TEST] Global Command Broadcast",
            body=f"TEST BROADCAST (Only you received this):\n\n{message}\n\n--\nFull Potential OS"
        )
        return {"status": "sent", "count": 1, "mode": "TEST"}

# --- UI ---

@app.get("/")
async def serve_ui():
    return FileResponse("app/static/index.html")

@app.get("/bounties")
async def serve_bounties():
    return FileResponse("app/static/bounties.html")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.SERVICE_PORT, reload=True)
