"""
Credentials Manager - FastAPI Application
Secure storage for API keys, billing details, and helper access management
"""

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import List

from .config import settings
from .models import (
    Credential, AccessToken, AuditLog,
    CredentialCreate, CredentialResponse, CredentialValue, CredentialUpdate,
    AccessTokenCreate, AccessTokenResponse,
    AuditLogResponse
)
from .database import get_db, init_db
from .crypto import crypto
from .auth import (
    create_access_token, get_current_user, require_admin,
    check_credential_access
)

# Initialize application
app = FastAPI(
    title="Credentials Manager",
    description="Secure storage for API keys, billing details, and helper access management",
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


# Admin Authentication

@app.post("/auth/admin")
async def admin_login(username: str, password: str):
    """Admin login - returns JWT token"""
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    if username != settings.admin_username:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not pwd_context.verify(password, settings.admin_password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "type": "admin",
        "username": username
    })

    return {"access_token": token, "token_type": "bearer"}


# Credential Management

@app.post("/credentials", response_model=CredentialResponse)
async def create_credential(
    credential: CredentialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
    request: Request = None
):
    """Create new credential (admin only)"""

    # Encrypt value
    encrypted_value = crypto.encrypt(credential.value)

    # Create credential
    new_credential = Credential(
        name=credential.name,
        type=credential.type.value,
        encrypted_value=encrypted_value,
        service=credential.service,
        metadata=credential.metadata,
        expires_at=credential.expires_at
    )

    db.add(new_credential)
    await db.commit()
    await db.refresh(new_credential)

    # Log creation
    if settings.enable_audit_log:
        log = AuditLog(
            credential_id=new_credential.id,
            action="create",
            accessor=current_user.get("username", "admin"),
            ip_address=request.client.host if request else None,
            success=True,
            details={"service": credential.service}
        )
        db.add(log)
        await db.commit()

    return new_credential


@app.get("/credentials", response_model=List[CredentialResponse])
async def list_credentials(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """List all credentials (admin sees all, helpers see only allowed)"""

    if current_user.get("type") == "admin":
        result = await db.execute(select(Credential))
        credentials = result.scalars().all()
    else:
        # Helpers only see their allowed credentials
        allowed_ids = current_user.get("credential_ids", [])
        result = await db.execute(
            select(Credential).where(Credential.id.in_(allowed_ids))
        )
        credentials = result.scalars().all()

    return credentials


@app.get("/credentials/{credential_id}", response_model=CredentialValue)
async def get_credential(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    request: Request = None
):
    """Get credential with decrypted value (requires access)"""

    # Check access
    check_credential_access(credential_id, current_user)

    # Get credential
    result = await db.execute(
        select(Credential).where(Credential.id == credential_id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    if not credential.is_active:
        raise HTTPException(status_code=403, detail="Credential is inactive")

    # Decrypt value
    decrypted_value = crypto.decrypt(credential.encrypted_value)

    # Log access
    if settings.enable_audit_log:
        accessor = current_user.get("username") or current_user.get("helper_name")
        log = AuditLog(
            credential_id=credential_id,
            token_id=current_user.get("token_id"),
            action="access",
            accessor=accessor,
            ip_address=request.client.host if request else None,
            success=True
        )
        db.add(log)
        await db.commit()

    return CredentialValue(
        name=credential.name,
        value=decrypted_value,
        service=credential.service,
        type=credential.type
    )


@app.put("/credentials/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: int,
    update: CredentialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
    request: Request = None
):
    """Update credential (admin only)"""

    result = await db.execute(
        select(Credential).where(Credential.id == credential_id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Update fields
    if update.value is not None:
        credential.encrypted_value = crypto.encrypt(update.value)

    if update.is_active is not None:
        credential.is_active = update.is_active

    if update.metadata is not None:
        credential.metadata = update.metadata

    credential.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(credential)

    # Log update
    if settings.enable_audit_log:
        log = AuditLog(
            credential_id=credential_id,
            action="update",
            accessor=current_user.get("username", "admin"),
            ip_address=request.client.host if request else None,
            success=True
        )
        db.add(log)
        await db.commit()

    return credential


@app.delete("/credentials/{credential_id}")
async def delete_credential(
    credential_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin),
    request: Request = None
):
    """Delete credential (admin only)"""

    result = await db.execute(
        select(Credential).where(Credential.id == credential_id)
    )
    credential = result.scalar_one_or_none()

    if not credential:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Log deletion before deleting
    if settings.enable_audit_log:
        log = AuditLog(
            credential_id=credential_id,
            action="delete",
            accessor=current_user.get("username", "admin"),
            ip_address=request.client.host if request else None,
            success=True,
            details={"service": credential.service, "name": credential.name}
        )
        db.add(log)
        await db.commit()

    await db.delete(credential)
    await db.commit()

    return {"status": "deleted", "credential_id": credential_id}


# Helper Access Tokens

@app.post("/tokens", response_model=AccessTokenResponse)
async def create_access_token_for_helper(
    token_request: AccessTokenCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Create access token for helper (admin only)"""

    # Generate token
    token_value = crypto.generate_token()
    token_hash = crypto.hash_token(token_value)

    # Calculate expiry
    expires_at = datetime.utcnow() + timedelta(hours=token_request.expires_hours)

    # Create token record
    access_token = AccessToken(
        token_hash=token_hash,
        helper_name=token_request.helper_name,
        credential_ids=token_request.credential_ids,
        scope=token_request.scope.value,
        expires_at=expires_at
    )

    db.add(access_token)
    await db.commit()
    await db.refresh(access_token)

    # Create JWT
    jwt_token = create_access_token({
        "type": "helper",
        "token_id": access_token.id,
        "helper_name": token_request.helper_name,
        "credential_ids": token_request.credential_ids,
        "scope": token_request.scope.value
    }, expires_delta=timedelta(hours=token_request.expires_hours))

    return AccessTokenResponse(
        token=jwt_token,
        helper_name=token_request.helper_name,
        credential_ids=token_request.credential_ids,
        scope=token_request.scope,
        expires_at=expires_at
    )


@app.delete("/tokens/{token_id}")
async def revoke_token(
    token_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Revoke helper access token (admin only)"""

    result = await db.execute(
        select(AccessToken).where(AccessToken.id == token_id)
    )
    access_token = result.scalar_one_or_none()

    if not access_token:
        raise HTTPException(status_code=404, detail="Token not found")

    access_token.revoked = True
    access_token.revoked_at = datetime.utcnow()

    await db.commit()

    return {"status": "revoked", "token_id": token_id}


# Audit Logs

@app.get("/audit", response_model=List[AuditLogResponse])
async def get_audit_logs(
    limit: int = 100,
    credential_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_admin)
):
    """Get audit logs (admin only)"""

    query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)

    if credential_id:
        query = query.where(AuditLog.credential_id == credential_id)

    result = await db.execute(query)
    logs = result.scalars().all()

    return logs


# Health & UDC Endpoints

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Credentials Manager",
        "version": "1.0.0",
        "description": "Secure storage for API keys, billing details, and helper access",
        "droplet_id": 25,
        "capabilities": [
            "AES-256 encrypted credential storage",
            "Scoped helper access tokens",
            "Audit logging of all access",
            "Auto-revoke after expiry",
            "Admin and helper authentication"
        ],
        "endpoints": {
            "/auth/admin": "Admin login",
            "/credentials": "Manage credentials",
            "/tokens": "Manage helper access",
            "/audit": "View audit logs"
        }
    }


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    """Health check"""
    try:
        # Test database connection
        await db.execute(select(1))
        db_status = "healthy"
    except:
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "service": "credentials-manager",
        "version": "1.0.0",
        "database": db_status
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=True
    )
