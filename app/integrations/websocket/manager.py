"""
WebSocket Connection Manager — Dashboard Live Updates

Maintains a registry of all active WebSocket connections.
Broadcasts pipeline events and system notifications to every connected
dashboard client in real time.

Thread-safety: FastAPI runs in a single async event loop per process,
so asyncio locks are sufficient for the in-memory set. If multiple
workers are added, upgrade to a Redis Pub/Sub backend.

Usage:
    # At module import time — singleton
    from app.integrations.websocket.manager import ws_manager

    # Inside a WebSocket route
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except Exception:
        ws_manager.disconnect(websocket)

    # From anywhere (e.g., event handler or pipeline)
    await ws_manager.broadcast({"event": "conversation_updated", "data": {...}})
"""

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Thread-safe in-memory WebSocket broadcaster."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info(
            "ws_client_connected",
            total=self.connection_count,
            client=websocket.client,
        )

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        logger.info(
            "ws_client_disconnected",
            total=self.connection_count,
        )

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Send a JSON payload to all connected dashboard clients."""
        if not self._connections:
            return

        # Add server timestamp
        payload.setdefault("timestamp", datetime.utcnow().isoformat())
        message = json.dumps(payload, default=str)

        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        for ws in dead:
            self.disconnect(ws)

        if dead:
            logger.debug("ws_dead_connections_removed", count=len(dead))

    async def send_to(self, websocket: WebSocket, payload: dict[str, Any]) -> None:
        """Send a JSON payload to a single client."""
        try:
            await websocket.send_text(json.dumps(payload, default=str))
        except Exception:
            self.disconnect(websocket)


# ── Singleton ──────────────────────────────────────────────────────────────────
ws_manager = ConnectionManager()
