from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel


POLICY_FILE = Path(os.environ.get("BRAIN_MESH_POLICY_FILE", "config/policy.json"))
REQUEST_TIMEOUT_SECONDS = float(os.environ.get("BRAIN_MESH_TIMEOUT_SECONDS", "25"))
AUDIT_LOG_FILE = os.environ.get("BRAIN_MESH_AUDIT_LOG_FILE", "/var/log/brain-mesh-gateway/audit.jsonl")


class ReadRequest(BaseModel):
    brain: str
    payload: dict[str, Any]


class WriteRequest(BaseModel):
    brain: str
    payload: dict[str, Any]


class BrainIndexRequest(BaseModel):
    brains: list[str] | None = None
    query: str
    per_brain_limit: int = 3


class ZVSearchRequest(BaseModel):
    query: str
    db: str = "master_list"
    limit: int = 5
    section: str | None = None


class ZVLogRequest(BaseModel):
    summary: str
    area: str = "Admin"
    section: str = "adam-openclaw/daily"


class SunheartSearchRequest(BaseModel):
    query: str
    k: int = 5
    section: str | None = None


class SunheartAddNoteRequest(BaseModel):
    title: str
    content: str
    tags: list[str] = []
    sensitivity: str = "🟢 Public"
    section: str = "adam-openclaw/daily"


app = FastAPI(title="brain-mesh-gateway", version="0.1.0")
AUDIT_LOG: list[dict[str, Any]] = []

# Per-token sliding-window limits for /adapters/* (not applied to /read|/write|/brain-index).
_adapter_hits: dict[str, list[float]] = defaultdict(list)
_adapter_rate_lock = asyncio.Lock()


async def _enforce_adapter_rate_limit(identity: dict[str, Any], route: str) -> None:
    max_req = int(os.environ.get("BRAIN_MESH_ADAPTER_RATE_MAX", "120"))
    if max_req <= 0:
        return
    window_s = float(os.environ.get("BRAIN_MESH_ADAPTER_RATE_WINDOW", "60"))
    token_key = identity.get("_token_prefix") or "unknown"
    key = f"{token_key}:{route}"
    now = time.time()
    async with _adapter_rate_lock:
        bucket = _adapter_hits[key]
        cutoff = now - window_s
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= max_req:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "adapter_rate_limit",
                    "route": route,
                    "window_s": window_s,
                    "max": max_req,
                },
            )
        bucket.append(now)


def _record_event(event: dict[str, Any]) -> None:
    AUDIT_LOG.append(event)
    if len(AUDIT_LOG) > 500:
        del AUDIT_LOG[:200]
    try:
        audit_path = Path(AUDIT_LOG_FILE)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with audit_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    except Exception:
        pass


def _load_policy() -> dict[str, Any]:
    if not POLICY_FILE.exists():
        raise HTTPException(status_code=500, detail=f"Policy file missing: {POLICY_FILE}")
    try:
        return json.loads(POLICY_FILE.read_text())
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Policy JSON invalid: {exc}") from exc


def _auth_context(authorization: str | None) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    policy = _load_policy()
    identity = policy.get("tokens", {}).get(token)
    if not identity:
        raise HTTPException(status_code=401, detail="Invalid token")
    expires_at = identity.get("expires_at")
    if expires_at:
        try:
            dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=500, detail=f"Invalid expires_at format for token: {expires_at}")
        if dt < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Token expired")
    identity["_policy"] = policy
    identity["_token_prefix"] = token[:8]
    return identity


def _can_access(identity: dict[str, Any], brain: str, write: bool) -> None:
    allowed = set(identity.get("allow_brains", []))
    if brain not in allowed and not identity.get("allow_other_brains", False):
        raise HTTPException(status_code=403, detail=f"Token not allowed for brain '{brain}'")
    if write and not identity.get("allow_write", False):
        raise HTTPException(status_code=403, detail="Write not allowed for token")
    if not write and not identity.get("allow_read", False):
        raise HTTPException(status_code=403, detail="Read not allowed for token")


def _match_pattern(value: str, pattern: str) -> bool:
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return value == pattern


def _can_access_section(identity: dict[str, Any], payload: dict[str, Any], write: bool) -> None:
    # Section is optional for compatibility with existing clients.
    # If present, enforce tiered section access.
    section = payload.get("section")
    if not section:
        return
    patterns = identity.get("write_sections", []) if write else identity.get("read_sections", [])
    for pat in patterns:
        if _match_pattern(section, pat):
            return
    raise HTTPException(status_code=403, detail=f"Section access denied: {section}")


def _brain_config(identity: dict[str, Any], brain: str) -> dict[str, Any]:
    cfg = identity["_policy"].get("brains", {}).get(brain)
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Brain '{brain}' is not configured")
    return cfg


def _brain_auth_header(cfg: dict[str, Any]) -> dict[str, str]:
    auth_type = cfg.get("auth_type", "none")
    if auth_type == "none":
        return {}
    if auth_type == "bearer":
        env_name = cfg.get("token_env_var")
        if not env_name:
            raise HTTPException(status_code=500, detail="Missing token_env_var in brain config")
        value = os.environ.get(env_name, "").strip()
        if not value:
            raise HTTPException(status_code=500, detail=f"Missing environment value: {env_name}")
        return {"Authorization": f"Bearer {value}"}
    raise HTTPException(status_code=500, detail=f"Unsupported auth_type: {auth_type}")


async def _proxy(brain: str, payload: dict[str, Any], write: bool, identity: dict[str, Any]) -> dict[str, Any]:
    cfg = _brain_config(identity, brain)
    base = cfg["base_url"].rstrip("/")
    path = cfg["write_path"] if write else cfg["read_path"]
    url = f"{base}{path}"
    headers = {"Content-Type": "application/json"}
    headers.update(_brain_auth_header(cfg))

    started = time.time()
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = await client.post(url, json=payload, headers=headers)
    elapsed_ms = int((time.time() - started) * 1000)
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail={
                "brain": brain,
                "upstream_status": resp.status_code,
                "upstream_body": resp.text[:400],
            },
        )

    out = {
        "brain": brain,
        "ok": True,
        "status_code": resp.status_code,
        "elapsed_ms": elapsed_ms,
        "data": resp.json() if "application/json" in resp.headers.get("content-type", "") else {"text": resp.text},
    }
    event = {
        "ts": int(time.time()),
        "actor": identity.get("user_id"),
        "role": identity.get("role"),
        "token_prefix": identity.get("_token_prefix"),
        "brain": brain,
        "write": write,
        "elapsed_ms": elapsed_ms,
        "route": "proxy",
    }
    _record_event(event)
    return out


async def _run_zv(args: list[str]) -> dict[str, Any]:
    # Keep this local-only and explicit for predictable tool behavior.
    cmd = ["/usr/bin/python3", "/opt/fpai/openclaw/workspace/infrastructure/tools/zv-brain.py", *args]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    out = stdout.decode("utf-8", errors="replace").strip()
    err = stderr.decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        raise HTTPException(status_code=502, detail={"zv_error": err or out, "exit_code": proc.returncode})
    return {"ok": True, "stdout": out, "stderr": err}


def _sunheart_index_headers() -> dict[str, str]:
    token = os.environ.get("SH_INDEX_TOKEN") or os.environ.get("SH_MCP_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="Missing SH_INDEX_TOKEN/SH_MCP_TOKEN")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _sunheart_search(query: str, k: int = 5) -> dict[str, Any]:
    base = os.environ.get("SH_INDEX_BASE_URL", "http://127.0.0.1:28090").rstrip("/")
    payload = {"query": query, "k": k, "include_content": True}
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = await client.post(f"{base}/search", json=payload, headers=_sunheart_index_headers())
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail={"sunheart_status": resp.status_code, "body": resp.text[:300]})
    return {"ok": True, "results": resp.json()}


async def _sunheart_add_note(title: str, content: str, tags: list[str], sensitivity: str, actor: str) -> dict[str, Any]:
    base = os.environ.get("SH_INDEX_BASE_URL", "http://127.0.0.1:28090").rstrip("/")
    source_id = f"brain-mesh:{actor}:{int(time.time())}:{uuid.uuid4().hex[:10]}"
    payload = {
        "source": "adam-openclaw",
        "source_id": source_id,
        "title": title,
        "content": content,
        "tags": tags,
        "prefer": "local",
        "sensitivity": sensitivity,
    }
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        resp = await client.post(f"{base}/ingest/add_note", json=payload, headers=_sunheart_index_headers())
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail={"sunheart_status": resp.status_code, "body": resp.text[:300]})
    return {"ok": True, "source_id": source_id, "result": resp.json()}


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    policy = _load_policy()
    return {
        "ok": True,
        "service": "brain-mesh-gateway",
        "tokens": len(policy.get("tokens", {})),
        "brains": list(policy.get("brains", {}).keys()),
    }


@app.get("/brains")
def list_brains(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    identity = _auth_context(authorization)
    policy = identity["_policy"]
    allowed = set(identity.get("allow_brains", []))
    brains = list(policy.get("brains", {}).keys())
    if not identity.get("allow_other_brains", False):
        brains = [b for b in brains if b in allowed]
    return {"actor": identity.get("user_id"), "role": identity.get("role"), "brains": brains}


@app.post("/read")
async def read_brain(req: ReadRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    identity = _auth_context(authorization)
    _can_access(identity, req.brain, write=False)
    _can_access_section(identity, req.payload, write=False)
    return await _proxy(req.brain, req.payload, write=False, identity=identity)


@app.post("/write")
async def write_brain(req: WriteRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    identity = _auth_context(authorization)
    _can_access(identity, req.brain, write=True)
    _can_access_section(identity, req.payload, write=True)
    return await _proxy(req.brain, req.payload, write=True, identity=identity)


@app.post("/brain-index")
async def brain_index(req: BrainIndexRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    identity = _auth_context(authorization)
    policy = identity["_policy"]
    allowed = set(identity.get("allow_brains", []))
    targets = req.brains or list(policy.get("brains", {}).keys())
    if not identity.get("allow_other_brains", False):
        targets = [b for b in targets if b in allowed]
    results = []
    for brain in targets:
        _can_access(identity, brain, write=False)
        payload = {"query": req.query, "limit": req.per_brain_limit}
        try:
            proxied = await _proxy(brain, payload, write=False, identity=identity)
            results.append({"brain": brain, "ok": True, "result": proxied.get("data")})
        except HTTPException as exc:
            results.append({"brain": brain, "ok": False, "error": exc.detail})
    return {"query": req.query, "results": results}


@app.get("/activity")
def activity(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    identity = _auth_context(authorization)
    # owner can view all; others only their own.
    if identity.get("role") == "owner":
        rows = AUDIT_LOG[-100:]
    else:
        rows = [r for r in AUDIT_LOG[-300:] if r.get("actor") == identity.get("user_id")][-100:]
    return {"count": len(rows), "items": rows}


@app.get("/status")
async def status(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    identity = _auth_context(authorization)
    policy = identity["_policy"]
    allowed = set(identity.get("allow_brains", []))
    brains = list(policy.get("brains", {}).keys())
    if not identity.get("allow_other_brains", False):
        brains = [b for b in brains if b in allowed]
    out = []
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        for brain in brains:
            cfg = _brain_config(identity, brain)
            headers = _brain_auth_header(cfg)
            url = f"{cfg['base_url'].rstrip('/')}/healthz"
            try:
                resp = await client.get(url, headers=headers)
                out.append(
                    {
                        "brain": brain,
                        "ok": resp.status_code == 200,
                        "status_code": resp.status_code,
                        "health": (
                            resp.json()
                            if "application/json" in resp.headers.get("content-type", "")
                            else {"text": resp.text[:200]}
                        ),
                    }
                )
            except Exception as exc:
                out.append({"brain": brain, "ok": False, "error": str(exc)})
    return {"actor": identity.get("user_id"), "items": out}


@app.post("/adapters/zv/search")
async def adapter_zv_search(req: ZVSearchRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    identity = _auth_context(authorization)
    await _enforce_adapter_rate_limit(identity, "adapter_zv_search")
    _can_access(identity, "zen-village", write=False)
    _can_access_section(identity, {"section": req.section} if req.section else {}, write=False)
    out = await _run_zv(["search", req.db, req.query, str(req.limit)])
    _record_event(
        {
            "ts": int(time.time()),
            "actor": identity.get("user_id"),
            "role": identity.get("role"),
            "token_prefix": identity.get("_token_prefix"),
            "brain": "zen-village",
            "write": False,
            "route": "adapter_zv_search",
        }
    )
    return out


@app.post("/adapters/zv/log")
async def adapter_zv_log(req: ZVLogRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    identity = _auth_context(authorization)
    await _enforce_adapter_rate_limit(identity, "adapter_zv_log")
    _can_access(identity, "zen-village", write=True)
    _can_access_section(identity, {"section": req.section}, write=True)
    out = await _run_zv(["log", req.summary, req.area])
    _record_event(
        {
            "ts": int(time.time()),
            "actor": identity.get("user_id"),
            "role": identity.get("role"),
            "token_prefix": identity.get("_token_prefix"),
            "brain": "zen-village",
            "write": True,
            "route": "adapter_zv_log",
        }
    )
    return out


@app.post("/adapters/sunheart/search")
async def adapter_sunheart_search(req: SunheartSearchRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    identity = _auth_context(authorization)
    await _enforce_adapter_rate_limit(identity, "adapter_sunheart_search")
    _can_access(identity, "sunheart", write=False)
    _can_access_section(identity, {"section": req.section} if req.section else {}, write=False)
    out = await _sunheart_search(req.query, req.k)
    _record_event(
        {
            "ts": int(time.time()),
            "actor": identity.get("user_id"),
            "role": identity.get("role"),
            "token_prefix": identity.get("_token_prefix"),
            "brain": "sunheart",
            "write": False,
            "route": "adapter_sunheart_search",
        }
    )
    return out


@app.post("/adapters/sunheart/add-note")
async def adapter_sunheart_add_note(
    req: SunheartAddNoteRequest, authorization: str | None = Header(default=None)
) -> dict[str, Any]:
    identity = _auth_context(authorization)
    await _enforce_adapter_rate_limit(identity, "adapter_sunheart_add_note")
    _can_access(identity, "sunheart", write=True)
    _can_access_section(identity, {"section": req.section}, write=True)
    out = await _sunheart_add_note(
        title=req.title,
        content=req.content,
        tags=req.tags,
        sensitivity=req.sensitivity,
        actor=identity.get("user_id", "unknown"),
    )
    _record_event(
        {
            "ts": int(time.time()),
            "actor": identity.get("user_id"),
            "role": identity.get("role"),
            "token_prefix": identity.get("_token_prefix"),
            "brain": "sunheart",
            "write": True,
            "route": "adapter_sunheart_add_note",
        }
    )
    return out


@app.get("/adapters/brief")
async def adapter_brief(
    query: str = "today updates blockers opportunities",
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    identity = _auth_context(authorization)
    await _enforce_adapter_rate_limit(identity, "adapter_brief")
    _can_access(identity, "zen-village", write=False)
    _can_access(identity, "sunheart", write=False)
    # Keep this endpoint read-only and concise.
    zv = await _run_zv(["search", "master_list", query, "3"])
    sh = await _sunheart_search(query, 3)
    st = await status(authorization)
    return {"actor": identity.get("user_id"), "status": st.get("items", []), "zen_village": zv, "sunheart": sh}
