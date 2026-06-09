"""
Coracle WebSocket Streaming Router
==================================
Real-time signal streaming via WebSocket.
"""
import asyncio
from datetime import datetime
from typing import List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings

router = APIRouter()
settings = get_settings()

# Active WebSocket connections
active_connections: Set[WebSocket] = set()


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        
        # Clean up disconnected
        for conn in disconnected:
            self.active_connections.discard(conn)


manager = ConnectionManager()


@router.websocket("/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time signal streaming.
    
    Streams:
    - Fast-path signals (100ms): BAI, OBS, CVD (order book derived)
    - Medium-path signals (1min): WADI, FR, OI
    - Slow-path signals (hourly): FGI, regime
    
    Message format:
    {
        "type": "signal_update" | "contract_generated" | "gate_change",
        "symbol": "BTC",
        "data": {...},
        "timestamp": "2024-01-01T00:00:00Z"
    }
    """
    await manager.connect(websocket)
    
    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "Coracle WebSocket connected",
            "tracked_assets": settings.tracked_assets,
            "stream_tiers": {
                "fast": {"interval_ms": 100, "signals": ["BAI", "OBS", "CVD"]},
                "medium": {"interval_s": 60, "signals": ["WADI", "FR", "OI"]},
                "slow": {"interval_s": 3600, "signals": ["FGI", "regime"]}
            }
        })
        
        # Start streaming tasks
        fast_task = asyncio.create_task(stream_fast_signals(websocket))
        medium_task = asyncio.create_task(stream_medium_signals(websocket))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=30.0  # Send heartbeat if no message in 30s
                )
                
                # Handle client messages
                if message.get("type") == "subscribe":
                    symbols = message.get("symbols", settings.tracked_assets)
                    await websocket.send_json({
                        "type": "subscribed",
                        "symbols": symbols
                    })
                
                elif message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        raise
    finally:
        # Cancel streaming tasks
        fast_task.cancel()
        medium_task.cancel()


async def stream_fast_signals(websocket: WebSocket):
    """Stream fast-path signals (100ms updates)."""
    while True:
        try:
            for symbol in settings.tracked_assets:
                # Get fast signals (BAI, OBS from orderbook)
                # This will be connected to the actual ingestor
                fast_data = {
                    "type": "fast_signals",
                    "symbol": symbol,
                    "signals": {
                        "bai": {"value": 0, "signal": "NEUTRAL"},
                        "obs": {"value": 0, "signal": "NEUTRAL"},
                        "cvd": {"value": 0, "signal": "NEUTRAL"}
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket.send_json(fast_data)
            
            await asyncio.sleep(0.1)  # 100ms
            
        except Exception:
            break


async def stream_medium_signals(websocket: WebSocket):
    """Stream medium-path signals (1 minute updates)."""
    while True:
        try:
            for symbol in settings.tracked_assets:
                medium_data = {
                    "type": "medium_signals",
                    "symbol": symbol,
                    "signals": {
                        "wadi": {"value": 0, "signal": "NEUTRAL"},
                        "fr": {"value": 0, "signal": "NEUTRAL"},
                        "oi": {"value": 0, "signal": "NEUTRAL"}
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                await websocket.send_json(medium_data)
            
            await asyncio.sleep(60)  # 1 minute
            
        except Exception:
            break


@router.websocket("/stream/fast")
async def fast_signal_stream(websocket: WebSocket):
    """
    Dedicated fast-signal stream (100ms updates).
    
    For clients that only need order book derived signals.
    """
    await websocket.accept()
    
    try:
        await websocket.send_json({
            "type": "connected",
            "stream": "fast",
            "interval_ms": 100,
            "signals": ["BAI", "OBS", "CVD"]
        })
        
        while True:
            for symbol in settings.tracked_assets[:2]:  # BTC, ETH only for fast
                data = {
                    "type": "fast_update",
                    "symbol": symbol,
                    "bai": 0,
                    "obs": 0,
                    "cvd": 0,
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_json(data)
            
            await asyncio.sleep(0.1)
            
    except WebSocketDisconnect:
        pass


@router.websocket("/stream/contracts")
async def contract_stream(websocket: WebSocket):
    """
    Stream contract generation events.
    
    Notifies when new contracts are generated or resolved.
    """
    await websocket.accept()
    
    try:
        await websocket.send_json({
            "type": "connected",
            "stream": "contracts",
            "events": ["contract_generated", "contract_resolved", "gate_passed", "gate_failed"]
        })
        
        # Keep alive
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
    except WebSocketDisconnect:
        pass


