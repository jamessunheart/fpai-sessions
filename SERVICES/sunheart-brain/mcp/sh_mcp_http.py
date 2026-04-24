"""
Sunheart Brain — MCP over HTTPS+SSE with bearer-token auth.

Same tools as sh_mcp_server.py (stdio) but exposed publicly so clients
(Claude Desktop, Cursor, GPT Custom Connector) can attach without any
local Python install.

Routes:
    GET  /healthz          unauthenticated — liveness
    GET  /mcp/sse          bearer-auth    — SSE stream
    POST /mcp/messages/    bearer-auth    — client → server messages

Env:
    SH_MCP_TOKENS_FILE     /etc/sh-brain/mcp-tokens.json
    SH_MCP_HTTP_HOST       default 127.0.0.1
    SH_MCP_HTTP_PORT       default 28091
    (plus all the SH_* that sh_mcp_server.py needs)
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

import sh_mcp_server as sh


@dataclass(frozen=True)
class AgentInfo:
    agent: str
    scopes: frozenset[str]

log = logging.getLogger("sh-mcp-http")
logging.basicConfig(
    level=os.environ.get("SH_MCP_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s sh-mcp-http %(message)s",
    stream=sys.stderr,
)

TOKENS_FILE = os.environ.get("SH_MCP_TOKENS_FILE", "/etc/sh-brain/mcp-tokens.json")
HOST = os.environ.get("SH_MCP_HTTP_HOST", "127.0.0.1")
PORT = int(os.environ.get("SH_MCP_HTTP_PORT", "28091"))


DEFAULT_SCOPES = frozenset({"public"})


def _coerce(raw) -> AgentInfo | None:
    if isinstance(raw, str):
        return AgentInfo(agent=raw, scopes=DEFAULT_SCOPES)
    if isinstance(raw, dict):
        agent = raw.get("agent") or raw.get("name")
        if not agent:
            return None
        scopes = raw.get("scopes") or []
        if isinstance(scopes, str):
            scopes = [s.strip() for s in scopes.split(",") if s.strip()]
        if not scopes:
            scopes = list(DEFAULT_SCOPES)
        return AgentInfo(agent=agent, scopes=frozenset(scopes))
    return None


def _load_tokens() -> dict[str, AgentInfo]:
    p = Path(TOKENS_FILE)
    if not p.exists():
        log.warning("tokens file %s missing", p)
        return {}
    try:
        data = json.loads(p.read_text())
    except Exception as e:
        log.error("failed to parse %s: %s", p, e)
        return {}
    out: dict[str, AgentInfo] = {}
    for k, v in data.items():
        if isinstance(v, dict):
            info = _coerce(v)
            if info:
                out[k] = info
        elif isinstance(v, str):
            if len(k) > len(v):
                info = _coerce(v)
                if info:
                    out[k] = info
            else:
                info = _coerce(k)
                if info:
                    out[v] = info
    return out


def _authenticate(request: Request) -> AgentInfo:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(401, "missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    info = _load_tokens().get(token)
    if not info:
        log.warning("rejected unknown token (%s…)", token[:8])
        raise HTTPException(401, "invalid token")
    return info


sse_transport = SseServerTransport("/mcp/messages/")


async def healthz(request: Request) -> JSONResponse:
    return JSONResponse({
        "ok": True,
        "service": "sh-mcp-http",
        "tokens_loaded": len(_load_tokens()),
        "tools": [t.name for t in sh.TOOLS],
    })


async def handle_sse(request: Request):
    info = _authenticate(request)
    log.info("sse connect agent=%s scopes=%s", info.agent, sorted(info.scopes))
    tok_a = sh.agent_ctx.set(info.agent)
    tok_s = sh.scopes_ctx.set(info.scopes)
    try:
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send,
        ) as (read_stream, write_stream):
            await sh.server.run(
                read_stream, write_stream,
                sh.server.create_initialization_options(),
            )
    finally:
        sh.agent_ctx.reset(tok_a)
        sh.scopes_ctx.reset(tok_s)
        log.info("sse disconnect agent=%s", info.agent)
    return JSONResponse({"ok": True})


async def handle_messages(scope, receive, send):
    request = Request(scope, receive)
    try:
        _authenticate(request)
    except HTTPException as e:
        resp = JSONResponse({"error": e.detail}, status_code=e.status_code)
        await resp(scope, receive, send)
        return
    await sse_transport.handle_post_message(scope, receive, send)


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    await sh._ensure_ready()
    log.info("ready — %d/%d dbs, %d tokens loaded",
             len(sh.client.db_ids) if sh.client else 0,
             len(sh.DB_SPEC),
             len(_load_tokens()))
    try:
        yield
    finally:
        if sh.client and sh.client.client:
            await sh.client.client.aclose()


class TrustedProxyHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            request.scope["client"] = (fwd.split(",")[0].strip(), 0)
        return await call_next(request)


app = Starlette(
    routes=[
        Route("/healthz", endpoint=healthz, methods=["GET"]),
        Route("/mcp/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/mcp/messages/", app=handle_messages),
    ],
    middleware=[Middleware(TrustedProxyHeaders)],
    lifespan=lifespan,
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
