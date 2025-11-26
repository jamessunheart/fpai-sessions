"""Simple in-memory websocket broadcast bus."""
from __future__ import annotations

import asyncio
from typing import Iterable

from fastapi import WebSocket


class TelemetryBus:
    """Tracks websocket connections and broadcasts telemetry events."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def broadcast(self, message: dict) -> None:
        async with self._lock:
            targets: Iterable[WebSocket] = tuple(self._connections)
        for connection in targets:
            try:
                await connection.send_json(message)
            except Exception:
                await self.disconnect(connection)

