"""FastAPI routes for the Hermes web adapter."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from curator.hermes.adapters.web_adapter import WebAdapter
from curator.hermes.gateway import ChannelNotRegistered, HermesDisabled, HermesGateway

router = APIRouter(prefix="/hermes", tags=["hermes"])
security = HTTPBearer(auto_error=False)


def _gateway(request: Request) -> HermesGateway:
    existing = getattr(request.app.state, "hermes_gateway", None)
    if existing is not None:
        return existing
    gateway = HermesGateway()
    gateway.register("web", WebAdapter())
    request.app.state.hermes_gateway = gateway
    return gateway


@router.post("/web/message")
async def web_message(
    payload: dict[str, Any],
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    from app import authenticate, require_scope

    agent = await authenticate(creds)
    require_scope(agent, "personal")
    try:
        response = await _gateway(request).process(payload, "web")
    except HermesDisabled as exc:
        raise HTTPException(503, str(exc)) from exc
    except ChannelNotRegistered as exc:
        raise HTTPException(400, f"channel not registered: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return response.to_dict()
