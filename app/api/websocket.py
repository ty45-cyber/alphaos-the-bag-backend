import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.infrastructure.redis_client import (
    subscribe_to_channel,
    SIGNAL_CHANNEL,
    WHALE_ALERT_CHANNEL,
    BREAKOUT_CHANNEL,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["WebSocket"])

VALID_CHANNELS = {
    "signals": SIGNAL_CHANNEL,
    "whale_alerts": WHALE_ALERT_CHANNEL,
    "breakouts": BREAKOUT_CHANNEL,
}


class ConnectionManager:
    """Manages active WebSocket connections per channel."""

    def __init__(self) -> None:
        self._active: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        await websocket.accept()
        self._active.setdefault(channel, []).append(websocket)
        logger.info("WebSocket connected on channel=%s, total=%d", channel, len(self._active[channel]))

    def disconnect(self, websocket: WebSocket, channel: str) -> None:
        connections = self._active.get(channel, [])
        if websocket in connections:
            connections.remove(websocket)
        logger.info("WebSocket disconnected from channel=%s", channel)

    async def broadcast(self, channel: str, message: dict) -> None:
        stale: list[WebSocket] = []
        for ws in self._active.get(channel, []):
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            self.disconnect(ws, channel)


manager = ConnectionManager()


@router.websocket("/ws/{channel}")
async def signal_stream(websocket: WebSocket, channel: str):
    """
    WebSocket endpoint that streams real-time signals from Redis pub/sub.
    channel: 'signals' | 'whale_alerts' | 'breakouts'
    """
    redis_channel = VALID_CHANNELS.get(channel)
    if not redis_channel:
        await websocket.close(code=4004, reason=f"Unknown channel: {channel}")
        return

    await manager.connect(websocket, channel)
    try:
        async for signal_event in subscribe_to_channel(redis_channel):
            try:
                await websocket.send_json(signal_event)
            except WebSocketDisconnect:
                break
            except Exception as exc:
                logger.warning("Failed to send to WebSocket: %s", exc)
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WebSocket stream error on channel=%s: %s", channel, exc)
    finally:
        manager.disconnect(websocket, channel)