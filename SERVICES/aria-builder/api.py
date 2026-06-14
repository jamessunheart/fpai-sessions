#!/usr/bin/env python3
"""
ARIA BUILDER API
================

FastAPI endpoints for the builder system.

Endpoints:
- POST /builder/propose - Generate code proposal
- POST /builder/apply - Apply approved change
- POST /builder/rollback - Rollback change
- GET /builder/pending - List pending changes
- GET /builder/status - Builder status
- POST /builder/verify - Verify code with Gemini
"""

import os
import logging
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger("aria.builder.api")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ProposeRequest(BaseModel):
    """Request to propose a code change."""
    request: str  # Natural language request
    target_file: Optional[str] = None  # Optional target file hint
    constraints: Optional[List[str]] = None  # Optional constraints


class ApplyRequest(BaseModel):
    """Request to apply a change."""
    change_id: str


class RollbackRequest(BaseModel):
    """Request to rollback a change."""
    change_id: str


class VerifyRequest(BaseModel):
    """Request to verify code."""
    code: str
    purpose: str = "correctness and safety"


class BuilderResponse(BaseModel):
    """Standard builder response."""
    success: bool
    message: str
    data: Optional[dict] = None


# ============================================================================
# FASTAPI APP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Aria Builder API starting...")
    
    # Initialize components
    from builder import get_engine
    from model_router import get_router
    
    app.state.engine = get_engine()
    app.state.router = get_router()
    
    logger.info("✅ Aria Builder API ready")
    
    yield
    
    # Shutdown
    logger.info("Aria Builder API shutting down...")
    await app.state.router.close()


app = FastAPI(
    title="Aria Builder API",
    description="Code modification through conversation",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "aria-builder",
        "version": "1.0.0",
        "description": "Build through conversation",
        "endpoints": [
            "/builder/propose",
            "/builder/apply",
            "/builder/rollback",
            "/builder/pending",
            "/builder/status",
            "/builder/verify"
        ]
    }


@app.get("/health")
def health():
    """Health check."""
    return {"status": "healthy", "service": "aria-builder"}


@app.post("/builder/propose", response_model=BuilderResponse)
async def propose_change(req: ProposeRequest, request: Request):
    """
    Propose a code change from natural language.
    
    Example:
    ```
    POST /builder/propose
    {"request": "Add a /status command that shows memory usage"}
    ```
    """
    try:
        engine = request.app.state.engine
        
        result = await engine.process_request(req.request)
        
        return BuilderResponse(
            success=result.get("is_builder", False),
            message=result.get("message", "Processed"),
            data={
                "intent": result.get("intent"),
                "changes": result.get("changes", []),
                "needs_approval": result.get("needs_approval", False),
                "proposal": result.get("proposal")
            }
        )
    except Exception as e:
        logger.error(f"Propose error: {e}")
        raise HTTPException(500, str(e))


@app.post("/builder/apply", response_model=BuilderResponse)
async def apply_change(req: ApplyRequest, request: Request):
    """
    Apply an approved change.
    
    Example:
    ```
    POST /builder/apply
    {"change_id": "abc123"}
    ```
    """
    try:
        from builder import CodeModifier
        modifier = CodeModifier()
        
        success, message = modifier.apply_change(req.change_id)
        
        return BuilderResponse(
            success=success,
            message=message,
            data={"change_id": req.change_id}
        )
    except Exception as e:
        logger.error(f"Apply error: {e}")
        raise HTTPException(500, str(e))


@app.post("/builder/rollback", response_model=BuilderResponse)
async def rollback_change(req: RollbackRequest, request: Request):
    """
    Rollback an applied change.
    
    Example:
    ```
    POST /builder/rollback
    {"change_id": "abc123"}
    ```
    """
    try:
        from builder import CodeModifier
        modifier = CodeModifier()
        
        success, message = modifier.rollback(req.change_id)
        
        return BuilderResponse(
            success=success,
            message=message,
            data={"change_id": req.change_id}
        )
    except Exception as e:
        logger.error(f"Rollback error: {e}")
        raise HTTPException(500, str(e))


@app.delete("/builder/cancel/{change_id}", response_model=BuilderResponse)
async def cancel_change(change_id: str):
    """Cancel a pending change."""
    try:
        from builder import CodeModifier
        modifier = CodeModifier()
        
        success, message = modifier.cancel_change(change_id)
        
        return BuilderResponse(
            success=success,
            message=message,
            data={"change_id": change_id}
        )
    except Exception as e:
        logger.error(f"Cancel error: {e}")
        raise HTTPException(500, str(e))


@app.get("/builder/pending")
async def get_pending():
    """Get all pending changes."""
    try:
        from builder import CodeModifier
        modifier = CodeModifier()
        
        pending = modifier.get_pending()
        
        return {
            "count": len(pending),
            "changes": [c.to_dict() for c in pending]
        }
    except Exception as e:
        logger.error(f"Pending error: {e}")
        raise HTTPException(500, str(e))


@app.get("/builder/status")
async def builder_status(request: Request):
    """Get builder system status."""
    try:
        from builder import CodeModifier
        modifier = CodeModifier()
        
        router = request.app.state.router
        router_stats = router.get_stats()
        
        pending = modifier.get_pending()
        
        return {
            "status": "ready",
            "ai_providers": router_stats.get("available", {}),
            "ai_calls": router_stats.get("calls", {}),
            "pending_changes": len(pending),
            "scope": {
                "base_path": "/opt/fpai/aria",
                "allowed_files": [
                    "server.py", "actions.py", "smart_responses.py",
                    "memory.py", "proactive.py", "voice.py", "channels.py"
                ]
            }
        }
    except Exception as e:
        logger.error(f"Status error: {e}")
        raise HTTPException(500, str(e))


@app.post("/builder/verify", response_model=BuilderResponse)
async def verify_code(req: VerifyRequest, request: Request):
    """
    Verify code with Gemini (cheap second opinion).
    
    Example:
    ```
    POST /builder/verify
    {"code": "def hello(): print('hi')", "purpose": "greeting function"}
    ```
    """
    try:
        engine = request.app.state.engine
        
        result = await engine.verify_with_gemini(req.code, req.purpose)
        
        return BuilderResponse(
            success=result.get("is_safe", False),
            message=result.get("assessment", "Verification complete"),
            data=result
        )
    except Exception as e:
        logger.error(f"Verify error: {e}")
        raise HTTPException(500, str(e))


@app.get("/builder/scope")
async def get_scope():
    """Get builder scope information."""
    return {
        "base_path": "/opt/fpai/aria",
        "allowed_files": [
            "server.py", "actions.py", "smart_responses.py",
            "memory.py", "memory_v2.py", "proactive.py",
            "proactive_daemon.py", "voice.py", "channels.py",
            "trading_intel.py", ".env"
        ],
        "forbidden": [
            "API keys via Telegram",
            "Files outside /opt/fpai/aria/",
            "System configuration"
        ],
        "limits": {
            "max_lines_per_change": 100,
            "backup_enabled": True,
            "syntax_check_required": True
        }
    }


@app.post("/builder/read")
async def read_file(filepath: str):
    """Read a file within scope."""
    try:
        from builder import CodeModifier
        modifier = CodeModifier()
        
        content, error = modifier.read_file(filepath)
        
        if error:
            return BuilderResponse(
                success=False,
                message=error,
                data=None
            )
        
        return BuilderResponse(
            success=True,
            message=f"Read {filepath}",
            data={"content": content[:5000], "truncated": len(content) > 5000}
        )
    except Exception as e:
        logger.error(f"Read error: {e}")
        raise HTTPException(500, str(e))


# ============================================================================
# WEBHOOK INTEGRATION
# ============================================================================

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint for builder.
    
    Call this to process Telegram updates through the builder.
    """
    try:
        from telegram_builder import integrate_with_webhook
        
        data = await request.json()
        result = await integrate_with_webhook(data)
        
        return {"ok": True, "handled": result is not None}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"ok": False, "error": str(e)}


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("BUILDER_PORT", "8720"))
    uvicorn.run(app, host="0.0.0.0", port=port)


