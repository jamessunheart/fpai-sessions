"""OpenAI Realtime API client for the Twilio voice bridge.

This is a thin async wrapper around the Realtime websocket that:
- opens a session configured with the tenant's system prompt + tools
- uses g711_ulaw directly so we can pipe Twilio μ-law frames straight through
- surfaces ``transcript`` (user + assistant) and ``function_call`` events for
  the bridge to act on.
"""
from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import websockets

from shared.config import settings
from shared.logging import get_logger

log = get_logger("voice-router.realtime")

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model={model}"


@dataclass
class RealtimeEvent:
    kind: str  # audio | transcript_user | transcript_assistant | function_call | done | error
    payload: dict[str, Any] = field(default_factory=dict)


class RealtimeSession:
    def __init__(
        self,
        *,
        system_prompt: str,
        tools: list[dict[str, Any]],
        voice: str = "alloy",
        model: str | None = None,
    ) -> None:
        self._system_prompt = system_prompt
        self._tools = tools
        self._voice = voice
        self._model = model or settings.openai_realtime_model
        self._ws: websockets.WebSocketClientProtocol | None = None
        self._inbox: asyncio.Queue[RealtimeEvent] = asyncio.Queue()
        self._reader_task: asyncio.Task | None = None

    async def connect(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not configured")
        headers = [
            ("Authorization", f"Bearer {settings.openai_api_key}"),
            ("OpenAI-Beta", "realtime=v1"),
        ]
        url = OPENAI_REALTIME_URL.format(model=self._model)
        self._ws = await websockets.connect(url, extra_headers=headers, max_size=16 * 1024 * 1024)
        await self._configure_session()
        self._reader_task = asyncio.create_task(self._reader_loop())

    async def _configure_session(self) -> None:
        assert self._ws is not None
        session_update = {
            "type": "session.update",
            "session": {
                "instructions": self._system_prompt,
                "modalities": ["audio", "text"],
                "voice": self._voice,
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "input_audio_transcription": {"model": "whisper-1"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
                "tools": [
                    {
                        "type": "function",
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": t.get("parameters", {}),
                    }
                    for t in self._tools
                ],
                "tool_choice": "auto",
                "temperature": 0.7,
            },
        }
        await self._ws.send(json.dumps(session_update))

    async def push_audio(self, ulaw_b64: str) -> None:
        """Forward a Twilio media frame (base64 μ-law) into the model."""
        assert self._ws is not None
        await self._ws.send(
            json.dumps({"type": "input_audio_buffer.append", "audio": ulaw_b64})
        )

    async def commit_audio(self) -> None:
        assert self._ws is not None
        await self._ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

    async def create_response(self) -> None:
        assert self._ws is not None
        await self._ws.send(json.dumps({"type": "response.create"}))

    async def send_tool_result(self, call_id: str, result: dict[str, Any]) -> None:
        assert self._ws is not None
        await self._ws.send(
            json.dumps(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result),
                    },
                }
            )
        )
        await self._ws.send(json.dumps({"type": "response.create"}))

    async def events(self) -> AsyncIterator[RealtimeEvent]:
        while True:
            evt = await self._inbox.get()
            yield evt
            if evt.kind in ("error",):
                return

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass

    async def _reader_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                await self._handle(msg)
        except websockets.ConnectionClosed:
            await self._inbox.put(RealtimeEvent(kind="done"))
        except Exception as e:
            log.error("realtime_reader_error", err=str(e))
            await self._inbox.put(RealtimeEvent(kind="error", payload={"err": str(e)}))

    async def _handle(self, msg: dict[str, Any]) -> None:
        t = msg.get("type", "")

        if t == "response.audio.delta":
            await self._inbox.put(
                RealtimeEvent(kind="audio", payload={"audio_b64": msg.get("delta", "")})
            )
            return

        if t == "conversation.item.input_audio_transcription.completed":
            await self._inbox.put(
                RealtimeEvent(
                    kind="transcript_user",
                    payload={"text": msg.get("transcript", "")},
                )
            )
            return

        if t == "response.audio_transcript.done":
            await self._inbox.put(
                RealtimeEvent(
                    kind="transcript_assistant",
                    payload={"text": msg.get("transcript", "")},
                )
            )
            return

        if t == "response.function_call_arguments.done":
            try:
                args = json.loads(msg.get("arguments", "{}"))
            except json.JSONDecodeError:
                args = {}
            await self._inbox.put(
                RealtimeEvent(
                    kind="function_call",
                    payload={
                        "call_id": msg.get("call_id"),
                        "name": msg.get("name"),
                        "arguments": args,
                    },
                )
            )
            return

        if t == "response.done":
            await self._inbox.put(RealtimeEvent(kind="done", payload=msg.get("response", {})))
            return

        if t == "error":
            log.error("realtime_api_error", err=msg)
            await self._inbox.put(RealtimeEvent(kind="error", payload=msg))
            return
