"""voice-router (port 8822) — Twilio webhook + OpenAI Realtime bridge.

Pipeline:
  POST /twilio/inbound  → TwiML that opens <Connect><Stream>
  WS   /media            → bidirectional μ-law bridge to OpenAI Realtime
  POST /twilio/status    → lifecycle transitions (answered, completed)

Tool calls execute in-process via ``voice_router.tools.dispatch_tool``.
``escalate_to_human`` triggers ``warm_transfer.redirect_to_agent`` once the
handoff-broker returns a matched agent phone.
"""
from __future__ import annotations

import asyncio
import json

import httpx
from fastapi import Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy import text

from shared.app_factory import create_app
from shared.config import settings
from shared.db import SessionLocal, tenant_session
from shared.events import Event, Topics, publish
from shared.features import get_feature
from shared.logging import get_logger

from .realtime import RealtimeEvent, RealtimeSession
from .tenant_loader import load_active_voice_pack
from .tools import dispatch_tool, log_utterance
from .warm_transfer import redirect_to_agent

app = create_app("voice-router")
log = get_logger("voice-router")


# ---------------------- Tenant resolution ----------------------

async def _tenant_by_phone(to_number: str) -> tuple[str, str] | None:
    async with SessionLocal() as session:
        await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
        row = (
            await session.execute(
                text(
                    """
                    SELECT id::text, plan
                      FROM tenants
                     WHERE metadata->'phone_numbers' ? :p
                     LIMIT 1
                    """
                ),
                {"p": to_number},
            )
        ).first()
    return (row[0], row[1]) if row else None


# ---------------------- Twilio webhooks ------------------------

@app.post("/twilio/inbound")
async def twilio_inbound(request: Request):
    form = await request.form()
    to_number = str(form.get("To") or "")
    from_number = str(form.get("From") or "")
    call_sid = str(form.get("CallSid") or "")

    resolved = await _tenant_by_phone(to_number)
    if not resolved:
        return _twiml(
            '<Response><Say voice="alice">Sorry, this number is not configured.</Say><Hangup/></Response>'
        )
    tenant_id, plan = resolved

    async with tenant_session(tenant_id) as session:
        realtime_flag = await get_feature(session, "realtime_voice", plan=plan)
        if not realtime_flag.enabled:
            return _twiml(
                '<Response><Say voice="alice">Please hold, connecting you now.</Say>'
                f'<Dial>{settings.twilio_default_from or ""}</Dial></Response>'
            )

        conv = (
            await session.execute(
                text(
                    """
                    INSERT INTO conversations
                      (tenant_id, channel, direction, status, external_ids)
                    VALUES
                      (CAST(:tid AS uuid), 'voice', 'inbound', 'open',
                       CAST(:ext AS jsonb))
                    RETURNING id::text
                    """
                ),
                {
                    "tid": tenant_id,
                    "ext": json.dumps(
                        {"twilio_call_sid": call_sid, "from": from_number, "to": to_number}
                    ),
                },
            )
        ).first()
        conversation_id = conv[0]
        await publish(
            session,
            Event(
                topic=Topics.CONVERSATION_STARTED,
                tenant_id=tenant_id,
                payload={
                    "conversation_id": conversation_id,
                    "channel": "voice",
                    "direction": "inbound",
                    "from": from_number,
                    "twilio_call_sid": call_sid,
                },
            ),
        )

    if settings.ws_public_base_url:
        ws_base = settings.ws_public_base_url.rstrip("/")
    else:
        ws_base = (
            str(request.base_url)
            .rstrip("/")
            .replace("http://", "wss://")
            .replace("https://", "wss://")
        )
    ws_url = (
        f"{ws_base}/media?conv={conversation_id}&tenant={tenant_id}&call={call_sid}"
    )
    twiml = (
        "<Response>"
        "<Connect>"
        f'<Stream url="{ws_url}"/>'
        "</Connect>"
        "</Response>"
    )
    return _twiml(twiml)


@app.post("/twilio/status")
async def twilio_status(
    CallSid: str = Form(...),
    CallStatus: str = Form(...),
):
    if CallStatus in ("completed", "canceled", "failed", "busy", "no-answer"):
        async with SessionLocal() as session:
            await session.execute(text("SET LOCAL app.is_superuser = 'true'"))
            row = (
                await session.execute(
                    text(
                        """
                        UPDATE conversations
                           SET status = 'closed', closed_at = now()
                         WHERE external_ids->>'twilio_call_sid' = :sid
                           AND status <> 'closed'
                        RETURNING id::text, tenant_id::text
                        """
                    ),
                    {"sid": CallSid},
                )
            ).first()
            if row:
                await publish(
                    session,
                    Event(
                        topic=Topics.CONVERSATION_CLOSED,
                        tenant_id=row[1],
                        payload={"conversation_id": row[0], "twilio_status": CallStatus},
                    ),
                )
            await session.commit()
    return {"ok": True}


# ---------------------- Media websocket ------------------------

@app.websocket("/media")
async def twilio_media(ws: WebSocket):
    await ws.accept()
    q = ws.query_params
    tenant_id = q.get("tenant")
    conversation_id = q.get("conv")
    call_sid = q.get("call")
    if not (tenant_id and conversation_id):
        await ws.close(code=1008)
        return

    pack = await load_active_voice_pack(tenant_id)
    if not pack:
        log.warn("no_voice_pack", tenant_id=tenant_id)
        await ws.close(code=1011)
        return

    session = RealtimeSession(
        system_prompt=pack.system_prompt,
        tools=pack.tools,
        voice=settings.openai_tts_voice,
    )
    try:
        await session.connect()
    except Exception as e:
        log.error("realtime_connect_failed", err=str(e))
        await ws.close(code=1011)
        return

    stream_sid: str | None = None

    async def twilio_to_model() -> None:
        nonlocal stream_sid
        try:
            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                event = msg.get("event")
                if event == "start":
                    stream_sid = msg.get("start", {}).get("streamSid")
                    log.info("twilio_stream_started", stream_sid=stream_sid)
                    await session.create_response()
                elif event == "media":
                    await session.push_audio(msg["media"]["payload"])
                elif event == "stop":
                    log.info("twilio_stream_stopped")
                    break
        except WebSocketDisconnect:
            pass
        except Exception as e:
            log.error("twilio_to_model_error", err=str(e))

    async def model_to_twilio() -> None:
        async for evt in session.events():
            if evt.kind == "audio" and stream_sid:
                await ws.send_text(
                    json.dumps(
                        {
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": evt.payload["audio_b64"]},
                        }
                    )
                )
            elif evt.kind == "transcript_user":
                await log_utterance(
                    tenant_id, conversation_id, "caller", evt.payload.get("text", "")
                )
            elif evt.kind == "transcript_assistant":
                await log_utterance(
                    tenant_id, conversation_id, "ai", evt.payload.get("text", "")
                )
            elif evt.kind == "function_call":
                asyncio.create_task(
                    _handle_tool_call(
                        session=session,
                        tenant_id=tenant_id,
                        conversation_id=conversation_id,
                        call_sid=call_sid,
                        event=evt,
                    )
                )
            elif evt.kind in ("done", "error"):
                continue

    try:
        await asyncio.gather(twilio_to_model(), model_to_twilio())
    finally:
        await session.close()
        try:
            await ws.close()
        except Exception:
            pass


async def _handle_tool_call(
    *,
    session: RealtimeSession,
    tenant_id: str,
    conversation_id: str,
    call_sid: str | None,
    event: RealtimeEvent,
) -> None:
    name = event.payload.get("name", "")
    call_id = event.payload.get("call_id", "")
    args = event.payload.get("arguments", {})
    log.info("tool_call", name=name, call_id=call_id, conv=conversation_id)

    result = await dispatch_tool(name, tenant_id, conversation_id, args)

    if name == "escalate_to_human" and result.get("ok") and call_sid:
        asyncio.create_task(_poll_and_transfer(tenant_id, result.get("id"), call_sid))

    await session.send_tool_result(call_id, result)


async def _poll_and_transfer(tenant_id: str, escalation_id: str | None, call_sid: str) -> None:
    """Wait for the escalation to be accepted, then warm-transfer to the agent.

    Polls handoff-broker for up to ``sla_seconds``. On timeout, the AI keeps
    the conversation going (the tool result already told the model the
    current status so it can speak naturally while we wait).
    """
    if not escalation_id:
        return

    async with httpx.AsyncClient(timeout=5.0) as client:
        for _ in range(30):  # 30 × 2s = 60s
            await asyncio.sleep(2.0)
            try:
                r = await client.get(
                    f"{settings.handoff_broker_url}/escalations/{escalation_id}",
                    headers={
                        "X-Internal-Token": settings.internal_service_token,
                        "X-Tenant-Id": tenant_id,
                    },
                )
                if r.status_code == 404:
                    continue
                r.raise_for_status()
                data = r.json()
                if data.get("status") == "accepted" and data.get("agent_phone"):
                    whisper = (
                        "Incoming Concierge call for tenant. "
                        "Brief context: caller is requesting human assistance."
                    )
                    ok = await redirect_to_agent(call_sid, data["agent_phone"], whisper)
                    if ok:
                        log.info("warm_transfer_sent", escalation_id=escalation_id)
                    return
            except Exception as e:
                log.warn("poll_error", err=str(e))


# ---------------------- Utilities ------------------------------

def _twiml(xml: str) -> Response:
    return Response(content=xml, media_type="application/xml")
